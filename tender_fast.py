# В tender_fast.py

async def emergency_relogin(page: Page, context: BrowserContext):
    logger.info("🔄 РЕ-ЛОГИН (Через кнопку 'Выход')...")
    try:
        # 1. ВЫХОД
        profile_icon = page.locator(".navbar-right .glyphicon-user")
        if await profile_icon.count() > 0 and await profile_icon.first.is_visible():
            logger.info("👤 Выхожу из системы...")
            await profile_icon.first.click()
            await asyncio.sleep(1)
            try: 
                await page.locator("a[href*='sso_logout'], a:has-text('Выход')").first.click()
                await page.wait_for_url("**/user/login**", timeout=10000)
            except: 
                await context.clear_cookies()
                await page.goto("https://goszakup.gov.kz/ru/user/login")
        else:
            logger.info("ℹ️ Уже вышли. Иду на вход...")
            try: await page.goto("https://goszakup.gov.kz/ru/user/login", wait_until="domcontentloaded")
            except: pass

        await asyncio.sleep(3) 
        
        # 2. ВХОД (Ключ)
        logger.info("🔑 Жму 'Выберите ключ'...")
        key_btn = page.get_by_role("button", name="Выберите ключ")
        if await key_btn.count() == 0: key_btn = page.get_by_role("button", name="Выберите файл")
        
        if await key_btn.count() > 0: await key_btn.first.click()
        else: await page.locator(".btn-success").first.click()
        
        await asyncio.sleep(2)
        
        # 3. ПАРОЛЬ
        logger.info("🔐 Ввожу пароль...")
        await page.fill("input[type='password']", GOV_PASSWORD)
        await page.press("input[type='password']", "Enter")
        
        # 4. ОЖИДАНИЕ (ГИБКОЕ)
        logger.info("⏳ Жду входа...")
        try:
            # Ждем ЛИБО смены URL, ЛИБО появления иконки профиля
            await asyncio.wait([
                page.wait_for_url("**/cabinet/**", timeout=60000),
                page.wait_for_selector(".glyphicon-user", timeout=60000)
            ], return_when=asyncio.FIRST_COMPLETED)
            logger.info("✅ Успешно перелогинились!")
            return True
        except:
            logger.warning("⚠️ Таймаут ожидания, но проверяю URL...")
            if "cabinet" in page.url:
                logger.info("✅ Мы в кабинете (по URL).")
                return True
            return False

    except Exception as e:
        logger.error(f"❌ Ошибка ре-логина: {e}")
        return False

# # --- ВОРКЕРЫ ---
# async def worker_guarantee(context: BrowserContext, url: str):
#     page = await context.new_page()
#     try:
#         await page.goto(url, wait_until="domcontentloaded")
#         if await page.locator("table.table-bordered tr").count() > 1: 
#             logger.info("[Гарантия] Уже заполнено.")
#             return
#         add_btn = page.locator("a:has-text('Добавить')").first
#         if await add_btn.count() > 0:
#             await add_btn.click()
#             await page.wait_for_load_state("domcontentloaded")
#             select_el = page.locator("select[name='typeDoc']")
#             if await select_el.count() > 0:
#                 await select_el.select_option(value="3")
#                 await page.wait_for_load_state("domcontentloaded") 
#             save_btn = page.locator("input[name='save_electronic_data']")
#             if await save_btn.count() > 0:
#                 await save_btn.click()
#                 await page.wait_for_load_state("domcontentloaded")
#             back_btn = page.locator("a:has-text('Назад')").first
#             if await back_btn.count() > 0: await back_btn.click()
#             logger.info("[Гарантия] ✅ Готово.")
#     except: await page.pause()
#     finally: await page.close()

# async def worker_app6_smart(context: BrowserContext, url: str):
#     page = await context.new_page()
#     try:
#         await page.goto(url, wait_until="domcontentloaded")
#         if await page.locator("a:has-text('Просмотреть')").count() > 0:
#             await page.click("a:has-text('Просмотреть')")
#             await page.wait_for_load_state("domcontentloaded")
#         if await page.locator("button:has-text('Удалить приложение')").count() > 0: return
#         sign_btn = page.locator(".btn-success:has-text('Подписать'), button:has-text('Подписать')").first
#         if await sign_btn.count() > 0 and await sign_btn.is_visible():
#             await sign_btn.click()
#             try: await sign_btn.wait_for(state="hidden", timeout=60000)
#             except: pass
#             return
#         copy_link = page.locator("a:has-text('Копировать сведения')").first
#         if await copy_link.count() > 0:
#             await copy_link.click()
#             await page.wait_for_load_state("domcontentloaded")
#             await page.fill("input[name='anno_number']", "12815138-2")
#             await page.click("input[value='Найти'], button:has-text('Найти')")
#             try:
#                 await page.wait_for_selector("input[type='radio']", timeout=10000)
#                 await page.check("input[type='radio']") 
#                 await page.check("input[type='checkbox']")
#                 await page.click("input[value='Применить'], button:has-text('Применить')")
#                 await page.wait_for_load_state("domcontentloaded")
#                 ret = page.locator("a:has-text('Вернуться')").first
#                 if await ret.count() > 0: await ret.click()
#                 else: await page.goto(url, wait_until="domcontentloaded")
#             except: await page.goto(url, wait_until="domcontentloaded")
#         try:
#             select = page.locator("select.form-control").first
#             if await select.count() > 0: await select.select_option(value="2")
#         except: pass
#         form_btn = page.locator("button:has-text('Сформировать приложение')").first
#         if await form_btn.count() > 0:
#             await form_btn.click()
#             try: await page.click("text=Сформированный документ отсутствует", timeout=2000)
#             except: pass
#             try: await page.select_option("select", index=1)
#             except: pass
#             await form_btn.click()
#             await page.wait_for_load_state("domcontentloaded")
#         sign_btn = page.locator("button:has-text('Подписать')").first
#         await sign_btn.wait_for(state="visible", timeout=15000)
#         await sign_btn.click()
#         await sign_btn.wait_for(state="hidden", timeout=60000)
#     except: await page.pause()
#     finally: await page.close()

# async def worker_app1(context: BrowserContext, url: str):
#     page = await context.new_page()
#     try:
#         await page.goto(url, wait_until="domcontentloaded")
#         if await page.locator("a:has-text('Просмотреть')").count() > 0:
#             await page.click("a:has-text('Просмотреть')")
#             await page.wait_for_load_state("domcontentloaded")
#         sign_btn = page.locator(".btn-add-signature, button:has-text('Подписать')").first
#         if await sign_btn.count() > 0:
#             await sign_btn.click()
#             await asyncio.sleep(5)
#         save_btn = page.locator("input[value='Сохранить подпись'], button:has-text('Сохранить подпись')").first
#         try:
#             await save_btn.wait_for(state="visible", timeout=30000)
#             await save_btn.click()
#             await page.wait_for_load_state("networkidle")
#         except: pass
#     except: pass
#     finally: await page.close()

# async def worker_app3(context: BrowserContext, url: str):
#     page = await context.new_page()
#     try:
#         await page.goto(url, wait_until="domcontentloaded")
#         if await page.locator("a:has-text('Просмотреть')").count() > 0:
#             await page.click("a:has-text('Просмотреть')")
#             await page.wait_for_load_state("domcontentloaded")
#         while True:
#             buttons = page.locator(".btn-add-signature, button:has-text('Подписать')")
#             if await buttons.count() == 0:
#                 await asyncio.sleep(2)
#                 if await buttons.count() == 0: break
#             try:
#                 await buttons.first.click()
#                 try: await page.wait_for_load_state("networkidle", timeout=15000)
#                 except: pass
#             except: await asyncio.sleep(2)
#     except: pass
#     finally: await page.close()

# async def worker_app5(context: BrowserContext, url: str):
#     page = await context.new_page()
#     try:
#         await page.goto(url, wait_until="domcontentloaded")
#         if await page.locator("a:has-text('Просмотреть')").count() > 0:
#             await page.click("a:has-text('Просмотреть')")
#         sign_btn = page.locator(".btn-add-signature, button:has-text('Подписать')").first
#         if await sign_btn.count() > 0:
#             await sign_btn.click()
#             await sign_btn.wait_for(state="hidden", timeout=60000)
#     except: pass
#     finally: await page.close()

# async def get_document_links(page: Page):
#     return await page.evaluate("""() => {
#         const getLink = (text) => {
#             const el = Array.from(document.querySelectorAll('a')).find(a => a.innerText.includes(text));
#             return el ? el.href : null;
#         };
#         return {
#             app1: getLink('Приложение 1'),
#             app5: getLink('Приложение 5'),
#             app3: getLink('Приложение 3'),
#             app6: getLink('Сведения о квалификации'),
#             guarantee: getLink('Обеспечение заявки') || getLink('гарантийный')
#         }
#     }""")