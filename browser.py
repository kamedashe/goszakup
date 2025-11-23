import asyncio
import json
import logging
import os
from playwright.async_api import async_playwright
from config import GOV_URL, GOV_PASSWORD, KEY_PATH
from signer import sign_xml_data, sign_cms_data

# Настройка логгера
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Читаем JS-мок (убедись, что файл ncalayer_mock.js лежит рядом)
MOCK_JS_PATH = os.path.join(os.path.dirname(__file__), "ncalayer_mock.js")
try:
    with open(MOCK_JS_PATH, "r", encoding="utf-8") as f:
        MOCK_JS = f.read()
except FileNotFoundError:
    logger.error(f"❌ Не найден файл {MOCK_JS_PATH}!")
    MOCK_JS = ""

async def handle_ncalayer_request(msg_json):
    try:
        req = json.loads(msg_json)
        module = req.get("module")
        req_type = req.get("type")
        
        logger.info(f"📩 PYTHON получил: {module} -> {req_type}")

        # 1. ВЕРСИЯ
        if module == "NURSign" and req_type == "version":
            response = {"result": {"version": "1.4"}, "errorCode": "NONE"}
            logger.info("✅ Отправляем версию 1.4")

        # 2. ВХОД (XML)
        elif module == "NURSign" and req_type == "xml":
            xml_to_sign = req.get("data")
            logger.info("✍️ Подписываем XML (Login)...")
            signed_xml = await sign_xml_data(xml_to_sign)
            if signed_xml:
                response = {"result": signed_xml, "errorCode": "NONE", "status": True, "code": "200"}
            else:
                response = {"errorCode": "WRONG_PASSWORD"}

        # 3. ПОДПИСЬ ФАЙЛА (ОТ JS - CMS_RAW)
        elif module == "NURSign" and req_type == "cms_raw":
            data_b64 = req.get("data")
            logger.info(f"📥 Получен файл от JS. Размер: {len(data_b64)}")
            signed_cms = await sign_cms_data(data_b64)
            if signed_cms:
                response = {"result": signed_cms, "errorCode": "NONE", "status": True, "responseObject": signed_cms, "code": "200"}
                logger.info("✅ CMS подписан!")
            else:
                response = {"errorCode": "WRONG_PASSWORD"}

        # 4. ПОДПИСЬ ФАЙЛА (ОТ САЙТА - BINARY - ТО, ЧЕГО НЕ ХВАТАЛО!)
        elif module == "NURSign" and req_type == "binary":
            upload_url = req.get("upload_url")
            logger.info(f"📥 Сайт просит скачать файл: {upload_url}")
            
            # Качаем через aiohttp с куками
            import aiohttp
            cookies = {}
            if os.path.exists("auth.json"):
                with open("auth.json", 'r') as f:
                    data = json.load(f)
                    for c in data['cookies']: cookies[c['name']] = c['value']

            try:
                async with aiohttp.ClientSession(cookies=cookies) as session:
                    async with session.get(upload_url, ssl=False) as resp:
                        if resp.status == 200:
                            file_bytes = await resp.read()
                            import base64
                            data_b64 = base64.b64encode(file_bytes).decode('utf-8')
                            
                            signed_cms = await sign_cms_data(data_b64)
                            if signed_cms:
                                response = {"result": signed_cms, "errorCode": "NONE", "status": True, "code": "200"}
                                logger.info("✅ Файл скачан и подписан (Native Mode)!")
                            else:
                                response = {"errorCode": "WRONG_PASSWORD"}
                        else:
                            logger.error(f"❌ Ошибка скачивания: {resp.status}")
                            response = {"errorCode": "FILE_DOWNLOAD_ERROR"}
            except Exception as e:
                logger.error(f"🔥 Ошибка binary: {e}")
                response = {"errorCode": "INTERNAL_ERROR"}

        # ЗАГЛУШКИ
        elif module == "kz.gov.pki.knca.commonUtils":
            response = {"result": True, "errorCode": "NONE"}
        else:
            logger.warning(f"⚠️ НЕИЗВЕСТНЫЙ ЗАПРОС: {msg_json}")
            response = {"status": True, "result": "TRUE", "code": "200", "errorCode": "NONE"}

        return json.dumps(response)

    except Exception as e:
        logger.error(f"🔥 CRITICAL: {e}")
        return json.dumps({"errorCode": "INTERNAL_ERROR"})

async def init_browser(headless=False):
    """Запускает браузер и настраивает все моки"""
    logger.info("🚀 Запуск браузера...")
    
    playwright = await async_playwright().start()
    
    browser = await playwright.chromium.launch(
        headless=headless, 
        args=["--start-maximized", "--ignore-certificate-errors"]
    )

    # Пробуем загрузить куки
    if os.path.exists("auth.json"):
        logger.info("📂 Грузим сохраненную сессию...")
        try:
            context = await browser.new_context(no_viewport=True, ignore_https_errors=True, storage_state="auth.json")
        except Exception as e:
             logger.warning(f"⚠️ Куки битые, создаем чистый контекст: {e}")
             context = await browser.new_context(no_viewport=True, ignore_https_errors=True)
    else:
        logger.info("🆕 Чистая сессия (куки не найдены).")
        context = await browser.new_context(no_viewport=True, ignore_https_errors=True)
    
    page = await context.new_page()
    
    # --- НАСТРОЙКА ПЕРЕХВАТЧИКОВ ---
    page.on("console", lambda msg: logger.info(f"🖥️ BROWSER: {msg.text}"))
    
    # 1. Мост Python
    await page.expose_function("pythonSigner", handle_ncalayer_request)
    # 2. JS Мок
    await page.add_init_script(MOCK_JS)

    # ==========================================
    # 🛠️ ROUTING ORDER IS CRITICAL (Last registered = First checked)
    # ==========================================

    # 1. GLOBAL INTERCEPTOR (Lowest Priority - Registered First)
    async def intercept_network(route, request):
        # Блокируем картинки для скорости
        if request.resource_type in ["image", "media", "font"]:
            await route.abort()
            return
        
        try:
            await route.continue_()
        except Exception:
            pass # Ignore network errors during continue

    await page.route("**/*", intercept_network)

    # 2. ERROR TRAP (Medium Priority)
    import re
    async def block_error_page(route):
        logger.warning(f"🛡️ Блокирую редирект на ошибку: {route.request.url}")
        await route.fulfill(status=204, body="")
    
    await page.route(re.compile(r".*sign_workaround/not_installed.*"), block_error_page)
    
    # 3. NCALAYER LOCALHOST MOCK (High Priority)
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
        
        # Ответ "Я живой"
        response_body = {"result": {"version": "1.4"}, "errorCode": "NONE"}
        await route.fulfill(status=200, body=json.dumps(response_body), headers=headers)

    # Ловим все запросы к порту 13579 (localhost, 127.0.0.1)
    await page.route(lambda url: "13579" in url, handle_local_http)

    return playwright, browser, context, page


async def check_auth(page):
    """Проверяет, жива ли сессия, пытаясь зайти в кабинет"""
    TARGET_URL = "https://v3bl.goszakup.gov.kz/ru/cabinet/profile"
    logger.info(f"🌍 Проверка сессии: {TARGET_URL}")
    
    try:
        await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(2)
        
        if "login" in page.url or "auth" in page.url:
            logger.warning("🔄 СЕССИЯ ИСТЕКЛА (Редирект на логин).")
            return False
        else:
            logger.info("✅ Куки валидны! Мы в кабинете.")
            return True
            
    except Exception as e:
        logger.warning(f"⚠️ Ошибка проверки сессии: {e}")
        return False


async def perform_login(page, context):
    """
    Жесткая процедура входа (FIXED для ERR_ABORTED).
    """
    logger.info("🔑 [LOGIN] Начинаю процедуру входа...")

    # 1. ПРИНУДИТЕЛЬНО ИДЕМ НА СТРАНИЦУ ВХОДА
    if "/user/login" not in page.url:
        try:
            logger.info(f"🌍 Переход на страницу входа: {GOV_URL}")
            # Используем wait_until='commit' - это самое быстрое. 
            # Мы не ждем полной загрузки, мы ждем начала получения данных.
            await page.goto(GOV_URL, wait_until="commit", timeout=30000)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка навигации (ERR_ABORTED?): {e}")
            # Игнорируем ошибку. Страница скорее всего загрузилась.

    # ДАЕМ ВРЕМЯ ОТРИСОВАТЬСЯ (DUMB SLEEP)
    # Раз события сети сбоят, просто ждем тупо по времени.
    logger.info("⏳ Жду 5 секунд, пока страница прогрузится...")
    await asyncio.sleep(5)

    # 2. ЗАГРУЗКА КЛЮЧА (ROBUST STRATEGY)
    logger.info("📂 [LOGIN] Начинаю загрузку ключа...")
    
    try:
        # СТРАТЕГИЯ А: Прямая вставка в input (самая надежная)
        # Ищем любой input type=file, даже скрытый
        file_input = page.locator("input[type='file']")
        
        if await file_input.count() > 0:
            logger.info("✅ Нашел скрытый input[type='file'], гружу напрямую...")
            await file_input.first.set_input_files(KEY_PATH)
        else:
            # СТРАТЕГИЯ Б: Через диалог выбора файла
            logger.info("⚠️ Input не найден, пробую клик по кнопке с перехватом...")
            async with page.expect_file_chooser(timeout=10000) as fc_info:
                # Кликаем по кнопке (она точно есть, мы видели скриншот)
                await page.click("#selectP12File", force=True)
            
            file_chooser = await fc_info.value
            await file_chooser.set_files(KEY_PATH)
            
        logger.info(f"✅ Файл ключа отправлен: {KEY_PATH}")
        
    except Exception as e:
        logger.error(f"❌ [LOGIN] Ошибка загрузки ключа: {e}")
        # Пробуем последний шанс - JS клик по кнопке
        try:
            logger.warning("⚠️ Последняя попытка: JS клик...")
            async with page.expect_file_chooser(timeout=5000) as fc_info:
                await page.evaluate("document.getElementById('selectP12File').click()")
            file_chooser = await fc_info.value
            await file_chooser.set_files(KEY_PATH)
        except Exception as e2:
            logger.error(f"💀 [LOGIN] FATAL: Не удалось загрузить ключ: {e2}")
            await page.screenshot(path="login_fatal_upload.png")
            return False

    # 3. ЖДЕМ ПОЯВЛЕНИЯ ПАРОЛЯ
    logger.info("⏳ [LOGIN] Жду поле пароля (до 20 сек)...")
    try:
        password_input = page.locator("input[type='password']")
        await password_input.wait_for(state="visible", timeout=20000)
        await password_input.fill(GOV_PASSWORD)
        logger.info("✅ [LOGIN] Пароль введен.")
    except Exception as e:
        logger.error("❌ [LOGIN] Поле пароля не появилось! (Возможно, ключ не подошел или сайт тупит)")
        await page.screenshot(path="login_stuck_password.png")
        return False

    # 4. ГАЛОЧКА (Запомнить меня / Соглашение)
    try:
        cb = page.locator("input[type='checkbox']")
        if await cb.count() > 0:
            await cb.check(force=True)
    except: pass

    # 5. ВОЙТИ
    try:
        # Ищем кнопку входа более точно
        login_btn = page.locator("button.btn-success:has-text('Войти'), button[type='submit']")
        if await login_btn.count() > 0:
            await login_btn.first.click()
            logger.info("🚀 [LOGIN] Кнопка 'Войти' нажата.")
        else:
            # Fallback
            await page.locator(".btn-success").click()
    except: pass

    # 6. ФИНАЛ
    try:
        await page.wait_for_url("**/cabinet/**", timeout=30000)
        logger.info("🎉 [LOGIN] УСПЕХ! Мы внутри.")
        return True
    except:
        logger.error("❌ Не пустило в кабинет (таймаут редиректа).")
        return False

async def run_browser_task():
    """Функция для отладочного запуска (debug_runner)"""
    playwright, browser, context, page = await init_browser(headless=False)
    
    is_auth = await check_auth(page)
    if not is_auth:
        success = await perform_login(page, context)
        if success:
            await context.storage_state(path="auth.json")
        else:
            await browser.close()
            return None, None, None, None

    logger.info("🔓 Готов к работе. Передаю управление...")
    return playwright, browser, context, page

if __name__ == "__main__":
    asyncio.run(run_browser_task())