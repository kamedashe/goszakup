# goszakup/tender_fast.py
import asyncio
import logging
from playwright.async_api import Page, BrowserContext, Locator
from config import GOV_URL, GOV_PASSWORD
from browser import perform_login, TARGET_PRICE, MOCK_JS

logging.basicConfig(format='%(asctime)s | %(message)s', datefmt='%H:%M:%S', level=logging.INFO)
logger = logging.getLogger("SURGEON")

async def safe_reload(page: Page):
    try: await page.reload(wait_until="domcontentloaded", timeout=30000)
    except: pass

async def ensure_ncalayer(page: Page):
    try:
        if not await page.evaluate("() => window.ncalayerInstalled === true"):
            await page.evaluate(MOCK_JS)
    except: pass

async def aggressive_click(page: Page, locator: Locator, name="Button"):
    """Клик: JS -> Dispatch -> Force"""
    try:
        if await locator.count() > 0:
            btn = locator.first
            if await btn.is_visible():
                logger.info(f"🖱️ Кликаю {name}...")
                try:
                    await btn.evaluate("el => el.click()") # Сразу JS, самый надежный
                    return True
                except:
                    await btn.click(force=True)
                    return True
    except: pass
    return False

async def process_lot_parallel(context: BrowserContext, lot_url: str, data_config: dict):
    logger.info(f"🚀 {lot_url}")
    page = await context.new_page()
    page.set_default_timeout(60000)
    page.on("console", lambda msg: print(f"🔵 [JS]: {msg.text}") if "NCALayer" in msg.text else None)

    try: await page.goto(lot_url, wait_until="domcontentloaded")
    except: pass

    MAX_RETRIES = 5 # Уменьшил кол-во попыток, чтобы не висеть вечно
    for attempt in range(1, MAX_RETRIES + 1):
        logger.info(f"🔄 [ПОПЫТКА {attempt}/{MAX_RETRIES}]")
        
        # === 1. ЛЕЧЕНИЕ СОГЛАШЕНИЯ (БЕЗ РЕ-ЛОГИНА) ===
        agreement = page.locator("a[href*='usage_agreement']")
        if await agreement.count() > 0 and await agreement.first.is_visible():
            logger.warning("🛑 СОГЛАШЕНИЕ! Иду подписывать...")
            
            # 1. Клик по ссылке
            await aggressive_click(page, agreement, "Ссылка соглашения")
            
            # 2. Ждем перехода
            try: await page.wait_for_url("**/usage_agreement", timeout=10000)
            except: pass # Если не сменился, может это модалка или AJAX
            
            await asyncio.sleep(2)

            # 3. Жмем "Сохранить/Принять"
            btns = page.locator("input[value='Сохранить'], button:has-text('Сохранить'), button:has-text('Принять')")
            if await btns.count() > 0:
                logger.info("✍️ Жму кнопку подтверждения...")
                await aggressive_click(page, btns, "Кнопка принятия")
                await asyncio.sleep(3)
            else:
                logger.info("ℹ️ Кнопки принятия нет (может уже ок).")

            # 4. Возвращаемся
            logger.info("🔙 Возвращаюсь к лоту...")
            await page.goto(lot_url, wait_until="domcontentloaded")
            continue 

        # === 2. ЗАПУСК ВОРКЕРОВ ===
        logger.info("🔍 Работа с документами...")
        links = await get_document_links(page)
        
        # Выполняем по очереди
        if links['guarantee']: await worker_guarantee(context, links['guarantee'])
        if links['app6']: await worker_app6_smart(context, links['app6'])
        if links['app3']: await worker_app3(context, links['app3'])
        if links['app5']: await worker_app5(context, links['app5'])
        if links['app1']: await worker_app1(context, links['app1'])
        
        # Обновляем страницу, чтобы подтянуть статусы
        await safe_reload(page)

        # === 3. ЦЕНА ===
        logger.info(f"💉 [JS] Цена: {TARGET_PRICE}")
        await page.evaluate(f"""() => {{
            const price = "{TARGET_PRICE}";
            document.querySelectorAll("input[name*='[price]'], input.offer, input.price-input").forEach(el => {{
                el.removeAttribute('readonly'); el.removeAttribute('disabled');
                el.value = price;
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            }});
        }}""")
        await asyncio.sleep(1)

        # === 4. ПОДПИСАНИЕ ===
        sign_btn = page.locator("#sign_offers")
        chk = page.locator("input[type='checkbox']")
        cnt = await chk.count()
        for i in range(cnt): 
            if await chk.nth(i).is_visible(): await chk.nth(i).check()
        
        try:
            mod = page.locator(".modal.in button:has-text('Подтвердить')")
            if await mod.count() > 0 and await mod.first.is_visible(): await mod.first.click()
        except: pass

        if await sign_btn.is_visible():
            logger.info("✍️ [MAIN] Жму 'Подписать'...")
            await sign_btn.click()
            
            logger.info("⏳ Жду подпись (10с)...")
            try:
                await page.wait_for_selector("#signature_injected_success", state="attached", timeout=15000)
                logger.info("✅ Подписано!")
            except:
                logger.warning("⚠️ Маркер не появился.")
        else:
            logger.warning("⚠️ Кнопки 'Подписать' нет (уже готово?).")

        # === 5. ОТПРАВКА ===
        next_btn = page.locator("#next, button:has-text('Далее')").first
        if await next_btn.count() > 0 and await next_btn.is_visible():
            logger.info("🚀 Жму 'Далее'...")
            if await next_btn.get_attribute("disabled"):
                await page.evaluate("el => el.disabled = false", await next_btn.element_handle())
            await next_btn.click()
            
            await asyncio.sleep(5)
            if "priceoffers" not in page.url:
                logger.info("🏆 УСПЕХ! Заявка ушла (URL сменился).")
                return # ПОБЕДА, ВЫХОДИМ
            else:
                errs = await page.locator(".alert-danger").all_inner_texts()
                real_errs = [e.strip() for e in errs if e.strip() and "соединение" not in e.lower()]
                
                if real_errs:
                     logger.error(f"❌ Ошибки: {real_errs}")
                     # Если ошибка не про соединение - пробуем еще раз
                     await safe_reload(page)
                     continue
                else:
                     logger.info("ℹ️ Вроде чисто.")
                     if "соединение" in (str(errs).lower()):
                         logger.warning("⚠️ Опять 'Соединение прервано', но ре-логин отключен. Пробуем просто рефреш...")
                         await safe_reload(page)
                         continue

        # Если дошли сюда - значит успех или конец попыток
        break

    logger.info("🏁 Работа завершена. Жду...")
    await page.pause()

# --- ВОРКЕРЫ (УМНЫЙ ПОИСК КНОПОК) ---

async def worker_guarantee(context: BrowserContext, url: str):
    logger.info(f"🛡️ [Гарантия]")
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await ensure_ncalayer(page)
        if await page.locator("table.table-bordered tr").count() > 1: return
        
        if await aggressive_click(page, page.locator("a:has-text('Добавить')"), "Добавить"):
            await page.wait_for_load_state("domcontentloaded")
            await page.locator("select[name='typeDoc']").select_option(value="3")
            await asyncio.sleep(1)
            await aggressive_click(page, page.locator("input[name='save_electronic_data']"), "Сохранить")
            await page.wait_for_load_state("domcontentloaded")
    except: pass
    finally: await page.close()

async def worker_app3(context: BrowserContext, url: str):
    logger.info(f"📄 [App3] Техспека")
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await ensure_ncalayer(page)

        # 1. Заходим
        if not await aggressive_click(page, page.locator("a:has-text('Просмотреть'), a:has-text('Просмотр')"), "Просмотреть"):
            await aggressive_click(page, page.locator("a[href*='show_doc']").first, "Название дока")
        
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        # 2. Подписываем
        for _ in range(5):
            sign_btns = page.locator(".btn-add-signature:visible, button:has-text('Подписать'):visible")
            if await sign_btns.count() == 0: break
            
            logger.info("   -> Жму подпись...")
            await aggressive_click(page, sign_btns.first, "Подписать файл")
            await asyncio.sleep(5) # Ждем CMS подпись
            
            save = page.locator("input[value='Сохранить подпись']").first
            if await save.count() > 0: await aggressive_click(page, save, "Сохранить")
            await asyncio.sleep(1)

    except: pass
    finally: await page.close()

async def worker_app5(context: BrowserContext, url: str):
    logger.info(f"📄 [App5] Заявка")
    page = await context.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await ensure_ncalayer(page)
        
        # Сразу ищем кнопку
        sign_btn = page.locator(".btn-add-signature, button:has-text('Подписать')").first
        if await sign_btn.count() > 0 and await sign_btn.is_visible():
            logger.info("   -> Подписываю...")
            await aggressive_click(page, sign_btn, "Подписать")
            await asyncio.sleep(5)
        else:
            # Заходим внутрь
            if not await aggressive_click(page, page.locator("a:has-text('Просмотреть')"), "Просмотреть"):
                 await aggressive_click(page, page.locator("a[href*='show_doc']").first, "Название")
            
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1)
            
            sign_inner = page.locator(".btn-add-signature, button:has-text('Подписать')").first
            if await sign_inner.count() > 0:
                await aggressive_click(page, sign_inner, "Подписать (внутри)")
                await asyncio.sleep(5)

    except: pass
    finally: await page.close()

async def worker_app6_smart(context: BrowserContext, url: str):
    pass 
async def worker_app1(context: BrowserContext, url: str):
    pass

async def get_document_links(page: Page):
    return await page.evaluate("""() => {
        const getLink = (text) => {
            const el = Array.from(document.querySelectorAll('a')).find(a => a.innerText.includes(text));
            return el ? el.href : null;
        };
        return {
            app1: getLink('Приложение 1'),
            app5: getLink('Приложение 5') || getLink('Приложение 4'),
            app3: getLink('Приложение 3'),
            app6: getLink('Сведения о квалификации'),
            guarantee: getLink('Обеспечение заявки') || getLink('гарантийный')
        }
    }""")