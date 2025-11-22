import asyncio
import json
import logging
import os
from playwright.async_api import async_playwright
from config import GOV_URL, GOV_PASSWORD
from signer import sign_xml_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Читаем JS-мок
MOCK_JS_PATH = os.path.join(os.path.dirname(__file__), "ncalayer_mock.js")
with open(MOCK_JS_PATH, "r", encoding="utf-8") as f:
    MOCK_JS = f.read()

async def handle_ncalayer_request(msg_json):
    try:
        # await asyncio.sleep(0.1) # Уменьши задержку, 0.5 это вечность для 8 секунд
        
        req = json.loads(msg_json)
        module = req.get("module")
        req_type = req.get("type")
        
        logger.info(f"📩 PYTHON получил: {module} -> {req_type}")

        # --- СЦЕНАРИЙ 1: ПРОВЕРКА ВЕРСИИ ---
        if module == "NURSign" and req_type == "version":
            # ОТВЕЧАЕМ СТРОГО ПО ПРОТОКОЛУ САЙТА
            response = {
                "result": {
                    "version": "1.4"  # Ставь 1.4, сайт может не принять 1.3
                },
                "errorCode": "NONE"
            }
            logger.info("✅ Отправляем версию 1.4")

        # --- СЦЕНАРИЙ 2: ПОДПИСАНИЕ XML ---
        elif module == "NURSign" and req_type == "xml":
            xml_to_sign = req.get("data")
            logger.info("✍️ Подписываем XML через NCANode...")
            
            # Тут вызываем твой signer.py
            signed_xml = await sign_xml_data(xml_to_sign)
            
            if signed_xml:
                response = {
                    "result": signed_xml,  # Сайт ждет подпись в поле result
                    "errorCode": "NONE",

                    # Формат для твоих кастомных хелперов (на всякий случай)
                    "status": True,
                    "responseObject": signed_xml,
                    "code": "200"
                }
                logger.info("✅ XML подписан успешно")
            else:
                # Если ошибка, эмулируем отказ пользователя или ошибку слоя
                response = {
                    "errorCode": "WRONG_PASSWORD" # Или другой код ошибки NCALayer
                }
                logger.error("❌ Ошибка подписи")

        # --- ЗАГЛУШКИ ДЛЯ СТАРЫХ МОДУЛЕЙ (На всякий случай) ---
        elif module == "kz.gov.pki.knca.commonUtils":
            response = {
                "result": True,
                "errorCode": "NONE"
            }
        
        else:
            # Дефолтный ответ, чтобы не висело
            response = {"errorCode": "NONE"}

        return json.dumps(response)

    except Exception as e:
        logger.error(f"🔥 CRITICAL ERROR: {e}")
        return json.dumps({"errorCode": "INTERNAL_ERROR"})


async def run_browser_task():
    async with async_playwright() as p:
        logger.info("🚀 Запуск браузера...")
        
        # 1. ЗАПУСК БРАУЗЕРА
        browser = await p.chromium.launch(
            headless=False,  # Для отладки видим окно. Для сервера ставь True.
            args=[
                "--start-maximized",
                "--ignore-certificate-errors"  # Игнор ошибок SSL для локалхоста
            ]
        )
        
        # 2. СОЗДАНИЕ КОНТЕКСТА (С КУКАМИ ИЛИ БЕЗ)
        if os.path.exists("auth.json"):
            logger.info("📂 Нашел сохраненную сессию (auth.json). Грузим куки...")
            context = await browser.new_context(
                no_viewport=True,
                ignore_https_errors=True,
                storage_state="auth.json" # <--- Загрузка куки
            )
        else:
            logger.info("🆕 Сохраненной сессии нет. Будем логиниться с нуля.")
            context = await browser.new_context(
                no_viewport=True,
                ignore_https_errors=True
            )
        
        page = await context.new_page()
        
        # --- НАСТРОЙКА ОКРУЖЕНИЯ (ЛОГИ, МОКИ, ПЕРЕХВАТЧИКИ) ---
        
        # Логи из консоли браузера
        page.on("console", lambda msg: logger.info(f"🖥️ BROWSER: {msg.text}"))
        
        # Пробрасываем функцию подписи в JS
        await page.expose_function("pythonSigner", handle_ncalayer_request)
        
        # Инжектим наш JS-хак (WebSocket + Image + Fetch mock)
        await page.add_init_script(MOCK_JS)

        # ⛔ КАПКАН: Глушим редирект на страницу ошибки (отвечаем 204 No Content)
        async def block_error_page(route):
            if "not_installed" in route.request.url:
                logger.warning(f"⛔ Глушу редирект на ошибку: {route.request.url}")
                await route.fulfill(status=204, body="")
            else:
                await route.continue_()

        await page.route("**/sign_workaround/not_installed", block_error_page)
        
        # 🛡️ ЭМУЛЯТОР HTTP СЕРВЕРА (CORS + OPTIONS)
        async def handle_local_http(route, request):
            # logger.info(f"🛡️ ПЕРЕХВАТ ЗАПРОСА: {request.method} {request.url}")
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": "application/json"
            }
            if request.method == "OPTIONS":
                await route.fulfill(status=200, headers=headers)
                return
            
            # Ответ "Я живой"
            response_body = {"result": {"version": "1.4"}, "errorCode": "NONE"}
            await route.fulfill(status=200, body=json.dumps(response_body), headers=headers)

        # Ловим всё на 13579
        await page.route(lambda url: "13579" in url, handle_local_http)

        # --- ЛОГИКА НАВИГАЦИИ ---

        target_url = "https://v3bl.goszakup.gov.kz/ru/cabinet/profile" # Сразу в кабинет
        login_url = GOV_URL # Страница логина

        logger.info(f"🌍 Пробуем зайти в кабинет: {target_url}")
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки (возможно, редирект): {e}")

        # Проверяем, пустило ли нас (или выкинуло на логин)
        # Ждем немного, чтобы URL устаканился
        await asyncio.sleep(2)
        
        if "login" not in page.url:
            logger.info("✅ УРА! Мы уже в кабинете (куки сработали).")
        
        else:
            logger.info("🔒 Нас перекинуло на логин. Начинаем процедуру входа...")
            
            # Если мы на логине, но страница "зависла" из-за капкана, надо убедиться, что элементы прогрузились
            # Или перейти на логин явно, если мы еще не там
            if page.url != login_url:
                 try:
                    await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)
                 except: pass

            # 1. Жмем "Выберите ключ"
            logger.info("🖱️ Ищу кнопку 'Выберите ключ'...")
            try:
                key_btn = page.get_by_text("Выберите ключ", exact=False)
                await key_btn.wait_for(state="visible", timeout=10000)
                await key_btn.click()
                logger.info("✅ Кнопка ключа нажата.")
            except Exception as e:
                logger.error(f"❌ Не нашел кнопку ключа: {e}")
                # Скриншот для отладки
                await page.screenshot(path="debug_no_key_btn.png")
                return

            # 2. Ждем появления поля пароля и галочки
            logger.info("⏳ Жду форму пароля...")
            # Ждем появления input password
            try:
                password_input = page.locator("input[type='password']")
                await password_input.wait_for(timeout=10000)
            except:
                logger.error("❌ Форма пароля не появилась после выбора ключа!")
                return

            # 3. Ставим галочку (HARD MODE)
            try:
                checkbox = page.locator("input[type='checkbox']")
                await checkbox.check(force=True)
                if not await checkbox.is_checked():
                    await checkbox.evaluate("el => el.click()") # JS клик если не сработало
                logger.info("✅ Галочка проставлена.")
            except Exception as e:
                logger.warning(f"⚠️ Проблема с галочкой: {e}")

            # 4. Вводим пароль
            await password_input.fill(GOV_PASSWORD)
            logger.info("🔑 Пароль введен.")
            
            await asyncio.sleep(0.5)

            # 5. Жмем Войти
            await page.locator(".btn-success").click()
            logger.info("🚀 Кнопка 'Войти' нажата! Ждем подписи XML...")

            # 6. Ждем загрузки кабинета и СОХРАНЯЕМ КУКИ
            try:
                # Ждем, пока URL перестанет содержать 'login' или появится элемент кабинета
                await page.wait_for_url("**/cabinet/**", timeout=30000)
                logger.info("🏠 КАБИНЕТ ЗАГРУЖЕН!")
                
                # СОХРАНЯЕМ КУКИ
                await context.storage_state(path="auth.json")
                logger.info("💾 Куки сохранены в auth.json")
                
            except Exception as e:
                logger.error(f"⚠️ Не дождался кабинета или тайм-аут: {e}")
                await page.screenshot(path="login_fail.png")

        # --- ЗДЕСЬ НАЧИНАЕТСЯ ТВОЯ БИЗНЕС-ЛОГИКА (ЗАЯВКИ) ---
        logger.info("🤖 Бот готов к работе в кабинете...")
        
        # ОСТАНАВЛИВАЕМ СКРИПТ И ОТКРЫВАЕМ ОКНО ЗАПИСИ
        await page.pause() 

        logger.info("🔓 Логин успешен. Передаю управление...")
        # Мы НЕ закрываем браузер, мы возвращаем объекты, чтобы работать дальше
        return browser, context, page

if __name__ == "__main__":
    asyncio.run(run_browser_task())