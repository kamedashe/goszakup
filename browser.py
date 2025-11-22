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

        # ... (после блока с version и xml) ...

        # --- СЦЕНАРИЙ 3: ПОДПИСАНИЕ ФАЙЛА (NATIVE MODE) ---
        elif module == "NURSign" and req_type == "binary":
            upload_url = req.get("upload_url")
            logger.info(f"📥 Запрос от сайта. Скачиваю файл: {upload_url}")
            
            try:
                # Грузим куки из файла для скачивания
                cookies = {}
                if os.path.exists("auth.json"):
                    with open("auth.json", 'r') as f:
                        data = json.load(f)
                        for c in data['cookies']:
                            cookies[c['name']] = c['value']

                # Качаем файл
                import aiohttp
                async with aiohttp.ClientSession(cookies=cookies) as session:
                    async with session.get(upload_url, ssl=False) as resp:
                        if resp.status == 200:
                            file_bytes = await resp.read()
                            logger.info(f"✅ Файл скачан ({len(file_bytes)} байт). Подписываю...")
                            
                            # Кодируем в Base64
                            import base64
                            data_b64 = base64.b64encode(file_bytes).decode('utf-8')
                            
                            # Подписываем (CMS)
                            from signer import sign_cms_data
                            signed_cms = await sign_cms_data(data_b64)
                            
                            if signed_cms:
                                # ВОЗВРАЩАЕМ ТО, ЧТО ЖДЕТ NURSIGN
                                response = {
                                    "result": signed_cms,
                                    "errorCode": "NONE",
                                    "status": True,
                                    "code": "200"
                                }
                                logger.info("✅ CMS подпись отправлена сайту!")
                            else:
                                response = {"errorCode": "WRONG_PASSWORD"}
                        else:
                            logger.error(f"❌ Ошибка скачивания: {resp.status}")
                            response = {"errorCode": "FILE_DOWNLOAD_ERROR"}

            except Exception as e:
                logger.error(f"🔥 Ошибка binary: {e}")
                response = {"errorCode": "INTERNAL_ERROR"}

        # --- ЗАГЛУШКИ ДЛЯ СТАРЫХ МОДУЛЕЙ (На всякий случай) ---
        elif module == "kz.gov.pki.knca.commonUtils":
            response = {
                "result": True,
                "errorCode": "NONE"
            }
        
        else:
            # ЭТО ЛОВУШКА ДЛЯ НОВЫХ ЗАПРОСОВ
            logger.warning(f"⚠️ ПОЙМАН НЕИЗВЕСТНЫЙ ЗАПРОС: {msg_json}")
            
            # Пытаемся сохранить его в файл, чтобы ты мог скинуть мне
            with open("unknown_request.json", "a", encoding="utf-8") as f:
                f.write(msg_json + "\n")

            # Возвращаем "успех", чтобы сайт не завис, а показал ошибку (или прошел дальше)
            response = {
                "status": True,
                "result": "TRUE", 
                "responseObject": "TRUE",
                "code": "200",
                "errorCode": "NONE"
            }

        return json.dumps(response)

    except Exception as e:
        logger.error(f"🔥 CRITICAL ERROR: {e}")
        return json.dumps({"errorCode": "INTERNAL_ERROR"})


async def run_browser_task():
    async with async_playwright() as p:
        logger.info("🚀 Запуск браузера (MANUAL MODE)...")
        
        # 1. ЗАПУСКАЕМ ВРУЧНУЮ (БЕЗ 'with')
        playwright = await async_playwright().start()
    
        browser = await playwright.chromium.launch(
            headless=False, 
            args=["--start-maximized", "--ignore-certificate-errors"]
        )
        
        # 2. КОНТЕКСТ
        if os.path.exists("auth.json"):
            logger.info("📂 Грузим куки...")
            context = await browser.new_context(no_viewport=True, ignore_https_errors=True, storage_state="auth.json")
        else:
            logger.info("🆕 Чистая сессия.")
            context = await browser.new_context(no_viewport=True, ignore_https_errors=True)
        
        page = await context.new_page()
        
        # ==========================================
        # 🛠️ НАСТРОЙКА ОКРУЖЕНИЯ (ДЕЛАЕМ ЭТО СНАЧАЛА!)
        # ==========================================
        
        # Логи
        page.on("console", lambda msg: logger.info(f"🖥️ BROWSER: {msg.text}"))
        
        # Мост Python <-> JS
        await page.expose_function("pythonSigner", handle_ncalayer_request)
        
        # JS Инъекция
        await page.add_init_script(MOCK_JS)

        # ⛔ КАПКАН v7: МГНОВЕННЫЙ ЩИТ
        async def block_error_page(route):
            if "not_installed" in route.request.url:
                logger.warning("🛡️ Блокирую (204). Ждем пока сайт переварит подпись.")
                await route.fulfill(status=204, body="")
            else:
                await route.continue_()

        # Применяем капкан
        await page.route("**/sign_workaround/not_installed", block_error_page)
        
        # 🔥 HTTP ПЕРЕХВАТЧИК (ВОТ ОН ДОЛЖЕН БЫТЬ ТУТ, ВВЕРХУ!)
        async def handle_local_http(route, request):
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Content-Type": "application/json"
            }
            if request.method == "OPTIONS":
                await route.fulfill(status=200, headers=headers)
                return
            
            response_body = {"result": {"version": "1.4"}, "errorCode": "NONE"}
            await route.fulfill(status=200, body=json.dumps(response_body), headers=headers)

        # Включаем перехват ДО того, как пойдем на сайт
        await page.route(lambda url: "13579" in url, handle_local_http)

        # ==========================================
        # 🛡️ ТЕПЕРЬ МОЖНО ЛОГИНИТЬСЯ
        # ==========================================
        
        TARGET_URL = "https://v3bl.goszakup.gov.kz/ru/cabinet/profile"
        logger.info(f"🌍 Проверка сессии: {TARGET_URL}")
        
        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)
        except:
            logger.warning("⚠️ Ошибка загрузки при проверке сессии.")

        # Если выкинуло на логин — входим заново
        if "login" in page.url or "auth" in page.url:
            logger.warning("🔄 СЕССИЯ ИСТЕКЛА. Релогин...")
            
            if GOV_URL not in page.url:
                await page.goto(GOV_URL, wait_until="domcontentloaded")

            # Кнопка ключа
            logger.info("🖱️ Ищу кнопку 'Выберите ключ'...")
            try:
                key_btn = page.get_by_text("Выберите ключ", exact=False)
                await key_btn.wait_for(state="visible", timeout=10000)
                await key_btn.click()
            except:
                logger.warning("⚠️ Кнопка не нажалась с первого раза. Ждем отработки 'Бумеранга'...")
                # Вместо жесткой перезагрузки, просто подождем, пока JS сам обновит страницу
                await asyncio.sleep(3)
                
                # И попробуем найти кнопку снова
                try:
                    key_btn = page.get_by_text("Выберите ключ", exact=False)
                    await key_btn.wait_for(state="visible", timeout=5000)
                    await key_btn.click()
                except:
                    # Если совсем всё плохо - идем на URL входа явно
                    logger.warning("⚠️ Кнопка так и не появилась. Идем на страницу входа принудительно.")
                    await page.goto(GOV_URL, wait_until="domcontentloaded")
            # Галочка
            try:
                cb = page.locator("input[type='checkbox']")
                await cb.check(force=True)
                if not await cb.is_checked(): await cb.evaluate("e => e.click()")
            except: pass

            # Пароль
            await page.locator("input[type='password']").fill(GOV_PASSWORD)
            await asyncio.sleep(0.5)
            await page.locator(".btn-success").click()
            logger.info("🚀 Вход нажат...")

            # Ждем кабинет и сохраняем
            try:
                await page.wait_for_url("**/cabinet/**", timeout=30000)
                logger.info("🏠 КАБИНЕТ ЗАГРУЖЕН!")
                await context.storage_state(path="auth.json")
                logger.info("💾 Куки обновлены.")
            except Exception as e:
                logger.error(f"❌ Ошибка входа: {e}")
                await page.screenshot(path="login_fail.png")
                return None, None, None # Возвращаем пустоту при ошибке

        else:
            logger.info("✅ Куки валидны! Мы в кабинете.")

        # ==========================================

        logger.info("🔓 Готов к работе. Передаю управление...")
        # Возвращаем и playwright тоже, чтобы потом его закрыть корректно
        return playwright, browser, context, page

if __name__ == "__main__":
    asyncio.run(run_browser_task())