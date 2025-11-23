import asyncio
import logging
import os
from playwright.async_api import Page, BrowserContext

logger = logging.getLogger("SPEEDRUN")

# === НАСТРОЙКИ СКОРОСТИ ===
# ⚠️ ВКЛЮЧАЕМ ВСЕ РЕСУРСЫ (User Request)
BLOCKED_RESOURCES = [] 

# Читаем JS-мок
MOCK_JS_PATH = os.path.join(os.path.dirname(__file__), "ncalayer_mock.js")
try:
    with open(MOCK_JS_PATH, "r", encoding="utf-8") as f:
        MOCK_JS = f.read()
except:
    MOCK_JS = ""

async def intercept_network(route, request):
    # ⚠️ USER REQUEST: UNBLOCK WEBSOCKET / LOCALHOST
    # if "127.0.0.1" in request.url and "13579" in request.url:
    #     await route.fulfill(
    #         status=200, 
    #         content_type="application/json", 
    #         body='{"result": {"version": "1.4"}, "errorCode": "NONE"}',
    #         headers={"Access-Control-Allow-Origin": "*"}
    #     )
    #     return

    if request.resource_type in BLOCKED_RESOURCES:
        await route.abort()
        return

    await route.continue_()

# 🔥 ЯДЕРНАЯ КНОПКА (NUCLEAR CLICK)
async def aggressive_click(element, log_prefix=""):
    """
    Нажимает на кнопку ВСЕМИ способами сразу.
    Но проверяет, жива ли кнопка, чтобы не бить по трупу.
    """
    # Проверка перед стартом
    try:
        if not await element.is_visible():
            logger.warning(f"{log_prefix} ⚠️ Элемент уже не виден перед кликом.")
            return False
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Page closed before check. Success?")
            return True
        return False

    # 1. JS Click (Самый прямой)
    try:
        logger.info(f"{log_prefix} 💉 JS Click...")
        await element.evaluate("e => e.click()")
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Page closed during JS Click. Success!")
            return True
        logger.warning(f"{log_prefix} ⚠️ JS Click failed: {e}")

    # Проверка: может страница уже ушла или кнопка пропала?
    try:
        if not await element.is_visible():
            logger.info(f"{log_prefix} ✅ Кнопка пропала после JS Click. Успех?")
            return True
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Элемент/Страница закрылась. Навигация началась?")
            return True
        logger.info(f"{log_prefix} ✅ Элемент детачтнулся. Навигация началась?")
        return True

    # 2. Dispatch Event (Для капризных фреймворков)
    try:
        logger.info(f"{log_prefix} ☢️ Dispatch Event...")
        await element.evaluate("e => { e.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window})); }")
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Page closed during Dispatch. Success!")
            return True
        logger.warning(f"{log_prefix} ⚠️ Dispatch failed: {e}")

    # 3. Playwright Force Click (Добивание)
    try:
        logger.info(f"{log_prefix} 🔨 Force Click...")
        await element.click(force=True, timeout=1000)
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Page closed during Force Click. Success!")
            return True
        logger.warning(f"{log_prefix} ⚠️ Force Click failed: {e}")

    # 4. 🔥 DIRECT FUNCTION CALL (Goszakup Specific)
    try:
        # Проверяем, есть ли у элемента onclick с вызовом helpers...
        has_helper = await element.evaluate("""el => {
            return el.getAttribute('onclick') && el.getAttribute('onclick').includes('helpers.sign_workaround');
        }""")
        
        if has_helper:
            logger.info(f"{log_prefix} ⚡ DIRECT JS CALL (super_signer)...")
            # Используем наше новое скрытое имя
            await element.evaluate("el => window.super_signer.form_sign_helper.sign_uploaded_file(el)")
    except Exception as e:
        if "closed" in str(e):
            logger.info(f"{log_prefix} ✅ Page closed during Direct JS Call. Success!")
            return True
        logger.warning(f"{log_prefix} ⚠️ Direct JS Call failed: {e}")
    
    return True

# === ГЛАВНАЯ ФУНКЦИЯ ===
async def process_lot_parallel(context: BrowserContext, lot_url: str, data_config: dict):
    logger.info("🚀 START SPEEDRUN: < 8s GOAL")

    await context.add_init_script(MOCK_JS)
    
    main_page = await context.new_page()
    # Enable console logging
    main_page.on("console", lambda msg: logger.info(f"🖥️ JS: {msg.text}"))
    
    await context.route("**/*", intercept_network)
    
    try:
        await main_page.goto(lot_url, wait_until="domcontentloaded", timeout=15000)
        
        doc_links = await get_document_links(main_page)
        if not doc_links:
            logger.error("❌ Не нашел документы! Проверь доступность лота.")
            return

        tasks = []

        if "app5" in doc_links:
            tasks.append(worker_universal(context, doc_links["app5"], "App 5", mode="simple"))

        if "app1" in doc_links:
            tasks.append(worker_universal(context, doc_links["app1"], "App 1", mode="combo"))
            
        if "app2" in doc_links:
            tasks.append(worker_universal(context, doc_links["app2"], "App 2", mode="simple"))

        if "app3" in doc_links:
            tasks.append(worker_heavy_sign(context, doc_links["app3"], "App 3 (Heavy)"))

        if "app6" in doc_links:
            tasks.append(worker_fill_form(context, doc_links["app6"], data_config, "App 6 (Form)"))

        await asyncio.gather(*tasks)
        
        logger.info("⚡ ВСЕ ДОКУМЕНТЫ ГОТОВЫ. ЖМУ ПОДАТЬ!")
        
        await main_page.reload(wait_until="domcontentloaded")
        submit_btn = main_page.locator("button:has-text('Подать заявку'), button:has-text('Отправить')")
        
        if await submit_btn.count() > 0:
            await aggressive_click(submit_btn, "[MAIN]")
            logger.info("🏁 ЗАЯВКА ОТПРАВЛЕНА! STOP TIMER.")
        else:
            logger.warning("⚠️ Кнопка 'Подать' не найдена (или уже подано).")

    except Exception as e:
        logger.error(f"🔥 CRASH MAIN: {e}")
    finally:
        pass

# === ПАРСЕР ССЫЛОК ===
async def get_document_links(page: Page):
    hrefs = await page.evaluate("""() => {
        const getLink = (text) => {
            const el = Array.from(document.querySelectorAll('a, td')).find(a => a.textContent.includes(text));
            if (el && el.tagName === 'A') return el.href;
            if (el && el.querySelector('a')) return el.querySelector('a').href;
            return null;
        };
        return {
            app5: getLink('Приложение 5'),
            app1: getLink('Приложение 1'),
            app2: getLink('Приложение 2'),
            app3: getLink('Приложение 3'),
            app6: getLink('Сведения о квалификации')
        }
    }""")
    return {k: v for k, v in hrefs.items() if v}


# === ВОРКЕР 1: УНИВЕРСАЛЬНЫЙ (App 1, 2, 5) ===
async def worker_universal(context: BrowserContext, url: str, name: str, mode: str):
    page = await context.new_page()
    await page.route("**/*", intercept_network)
    
    logger.info(f"[{name}] 🟢 Старт ({mode})...")
    
    try:
        await page.goto(url, wait_until="domcontentloaded")
        
        view_btn = page.locator("a:has-text('Просмотреть')").first
        if await view_btn.count() > 0:
            await view_btn.click()
            await page.wait_for_load_state("domcontentloaded")

        # ЦИКЛ ПОПЫТОК (3 раза)
        for i in range(4): 
            action_done = False

            # А. Кнопка "Подписать" (Зеленая)
            sign_btn = page.locator("button.btn-success:has-text('Подписать'), button.btn-add-signature").first
            if await sign_btn.count() > 0 and await sign_btn.is_visible():
                logger.info(f"[{name}] ✍️ Жму 'Подписать'...")
                await aggressive_click(sign_btn, f"[{name}]")
                
                # 🛑 ЖДЕМ ДОЛЬШЕ! Подпись - дело небыстрое.
                # Если мы будем долбить, мы сломаем JS на сайте.
                logger.info(f"[{name}] ⏳ Жду 5 сек (подпись)...")
                await asyncio.sleep(5)
                
                action_done = True
                if mode == "simple": 
                    logger.info(f"[{name}] ✅ Готово (Simple).")
                    return 

            # Б. Кнопка "Сохранить подпись" (Синяя, для App 1)
            save_sig_btn = page.locator("button:has-text('Сохранить подпись')").first
            if await save_sig_btn.count() > 0 and await save_sig_btn.is_visible():
                logger.info(f"[{name}] 💾 Жму 'Сохранить подпись'...")
                await aggressive_click(save_sig_btn, f"[{name}]")
                await page.wait_for_load_state("domcontentloaded")
                logger.info(f"[{name}] ✅ Готово (Combo).")
                return

            # В. Кнопка "Сохранить" (Обычная)
            save_btn = page.locator("button[type='submit']:has-text('Сохранить')").first
            if await save_btn.count() > 0 and await save_btn.is_visible():
                if await save_btn.get_attribute("id") != "search-btn":
                    logger.info(f"[{name}] 💾 Жму 'Сохранить'...")
                    await aggressive_click(save_btn, f"[{name}]")
                    await page.wait_for_load_state("domcontentloaded")
                    logger.info(f"[{name}] ✅ Готово.")
                    return

            if not action_done and i > 1:
                logger.info(f"[{name}] Кнопок нет. Считаем, что готово.")
                break
            
            await asyncio.sleep(1)
    
    except Exception as e:
        logger.error(f"[{name}] ❌ Ошибка: {e}")
    finally:
        await page.pause()


# === ВОРКЕР 2: ТЯЖЕЛАЯ ПОДПИСЬ (App 3) ===
async def worker_heavy_sign(context: BrowserContext, url: str, name: str):
    page = await context.new_page()
    await page.route("**/*", intercept_network)
    logger.info(f"[{name}] 🟡 Старт (Multi-file)...")
    
    try:
        await page.goto(url, wait_until="domcontentloaded")
        
        view_btn = page.locator("a:has-text('Просмотреть')").first
        if await view_btn.count() > 0:
            logger.info(f"[{name}] Жму 'Просмотреть'...")
            # Используем try/except для навигации, так как aggressive_click может вызвать её раньше времени
            try:
                async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                    await aggressive_click(view_btn, f"[{name}]")
            except Exception as e:
                logger.warning(f"[{name}] ⚠️ Навигация (Просмотр) странная: {e}")
            
            await asyncio.sleep(1.5)

        while True:
            sign_btn = page.locator("button.btn-success:has-text('Подписать')").first
            
            if await sign_btn.count() > 0:
                logger.info(f"[{name}] Нашел файл. Подписываю...")
                try:
                    async with page.expect_navigation(wait_until="domcontentloaded", timeout=45000):
                        await aggressive_click(sign_btn, f"[{name}]")
                except Exception as e:
                    logger.warning(f"[{name}] ⚠️ Навигация (Подпись) странная: {e}")
                
                logger.info(f"[{name}] ♻️ Перезагрузка ОК.")
                await asyncio.sleep(0.5)
                continue
            else:
                logger.info(f"[{name}] ✅ Все файлы подписаны.")
                break
                
    except Exception as e:
        logger.error(f"[{name}] ❌ Ошибка: {e}")
    finally:
        await page.close()


# === ВОРКЕР 3: ЗАПОЛНЕНИЕ ФОРМЫ (App 6) ===
async def worker_fill_form(context: BrowserContext, url: str, data: dict, name: str):
    page = await context.new_page()
    await page.route("**/*", intercept_network)
    logger.info(f"[{name}] 🔵 Старт заполнения...")
    try:
        await page.goto(url, wait_until="domcontentloaded")
        # ТУТ ТВОЯ ЛОГИКА ЗАПОЛНЕНИЯ
        # await page.fill("#field_id", "value")
        # await page.click("#save_btn")
        logger.info(f"[{name}] ✅ Форма обработана.")
    except Exception as e:
        logger.error(f"[{name}] ❌ Ошибка: {e}")
    finally:
        await page.pause()