import asyncio
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

# === 1. ТОЧКА ВХОДА ===
async def process_lot(page: Page, lot_url: str, cooks_data: list):
    logger.info(f"🌍 Переходим на лот: {lot_url}")
    try:
        await page.goto(lot_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning(f"⚠️ Загрузка: {e}")

    # Проверяем, где мы: в списке документов или внутри одного документа?
    if await page.locator("table").count() > 0 and await page.get_by_text("Наименование документа").count() > 0:
        logger.info("📂 Мы в СПИСКЕ документов. Начинаем обход...")
        await process_document_list(page, lot_url)
    else:
        logger.info("📄 Похоже, мы сразу внутри ДОКУМЕНТА. Зачищаем...")
        await sign_current_page(page)
        logger.info("🏁 Документ обработан.")


# === 2. ОБХОД СПИСКА ===
async def process_document_list(page: Page, list_url: str):
    # Список того, что нужно подписать (по приоритету)
    TARGET_DOCS = [
        "Приложение 5",  # Заявка физ. лиц
        "Приложение 2",  # Перечень товаров
        "Приложение 3",  # Техническое задание
        "Техническое задание"
    ]

    for doc_name in TARGET_DOCS:
        logger.info(f"🔎 Ищу документ: {doc_name}")
        
        # Ищем ссылку по тексту
        link = page.locator(f"a:has-text('{doc_name}')").first
        
        if await link.count() > 0 and await link.is_visible():
            logger.info(f"✨ Нашел! Захожу внутрь...")
            await link.click()
            await page.wait_for_load_state("domcontentloaded")
            
            # --- ПЕРЕВІРКА КНОПКИ "ПРОСМОТРЕТЬ" (Твоя логіка) ---
            try:
                view_btn = page.locator("a:has-text('Просмотреть')").first
                if await view_btn.count() > 0 and await view_btn.is_visible():
                    logger.info("👀 Нашел кнопку 'Просмотреть'. Кликаю...")
                    await view_btn.click()
                    await page.wait_for_load_state("domcontentloaded")
            except: pass
            # ---------------------------------------------
            
            # --- ПІДПИСАННЯ ---
            await sign_current_page(page)
            
            logger.info("🔙 Возвращаюсь к списку (Hard Reset)...")
            try:
                await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.error(f"❌ Ошибка возврата: {e}")
            
import asyncio
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

# === 1. ТОЧКА ВХОДА ===
async def process_lot(page: Page, lot_url: str, cooks_data: list):
    logger.info(f"🌍 Переходим на лот: {lot_url}")
    try:
        await page.goto(lot_url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning(f"⚠️ Загрузка: {e}")

    # Проверяем, где мы: в списке документов или внутри одного документа?
    if await page.locator("table").count() > 0 and await page.get_by_text("Наименование документа").count() > 0:
        logger.info("📂 Мы в СПИСКЕ документов. Начинаем обход...")
        await process_document_list(page, lot_url)
    else:
        logger.info("📄 Похоже, мы сразу внутри ДОКУМЕНТА. Зачищаем...")
        await sign_current_page(page)
        logger.info("🏁 Документ обработан.")


# === 2. ОБХОД СПИСКА ===
async def process_document_list(page: Page, list_url: str):
    # Список того, что нужно подписать (по приоритету)
    TARGET_DOCS = [
        "Приложение 5",  # Заявка физ. лиц
        "Приложение 2",  # Перечень товаров
        "Приложение 3",  # Техническое задание
        "Техническое задание"
    ]

    for doc_name in TARGET_DOCS:
        logger.info(f"🔎 Ищу документ: {doc_name}")
        
        # Ищем ссылку по тексту
        link = page.locator(f"a:has-text('{doc_name}')").first
        
        if await link.count() > 0 and await link.is_visible():
            logger.info(f"✨ Нашел! Захожу внутрь...")
            await link.click()
            await page.wait_for_load_state("domcontentloaded")
            
            # --- ПЕРЕВІРКА КНОПКИ "ПРОСМОТРЕТЬ" (Твоя логіка) ---
            try:
                view_btn = page.locator("a:has-text('Просмотреть')").first
                if await view_btn.count() > 0 and await view_btn.is_visible():
                    logger.info("👀 Нашел кнопку 'Просмотреть'. Кликаю...")
                    await view_btn.click()
                    await page.wait_for_load_state("domcontentloaded")
            except: pass
            # ---------------------------------------------
            
            # --- ПІДПИСАННЯ ---
            await sign_current_page(page)
            
            logger.info("🔙 Возвращаюсь к списку (Hard Reset)...")
            try:
                await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.error(f"❌ Ошибка возврата: {e}")
            
        else:
            logger.info(f"⏩ Ссылка '{doc_name}' не найдена. Пропускаем.")

    logger.info("🏁 Список оброблено.")


# === 3. УНИВЕРСАЛЬНАЯ ПОДПИСЬ ===
async def sign_current_page(page: Page):
    """
    1. Находит 'Подписать' (get_by_role).
    2. Жмет JS click.
    3. Находит 'Сохранить подпись' (get_by_role).
    4. Жмет Playwright click.
    """
    logger.info("⚔️ Зачистка документа...")

    while True:
        # 1. Ищем кнопку "Подписать"
        # Используем get_by_role как просил пользователь
        sign_btn = page.get_by_role("button", name="Подписать").first
        
        # Если не нашли по роли, пробуем по классу (как запасной вариант)
        if await sign_btn.count() == 0:
            sign_btn = page.locator("button.btn-add-signature").first
        
        if await sign_btn.count() == 0 or not await sign_btn.is_visible():
            logger.info("✅ Кнопок 'Подписать' больше нет.")
            break

        logger.info("🎯 Нашел кнопку 'Подписать'. Жму (JS)...")
        try:
            # Click via JS as requested
            await sign_btn.evaluate("e => e.click()")
            
            logger.info("⏳ Жду обновления страницы...")
            await asyncio.sleep(2) # Небольшая пауза
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except: pass

            # 2. Ищем кнопку "Сохранить подпись"
            logger.info("💾 Ищу кнопку 'Сохранить подпись'...")
            save_btn = page.get_by_role("button", name="Сохранить подпись").first
            
            if await save_btn.count() > 0 and await save_btn.is_visible():
                logger.info("🖱️ Жму 'Сохранить подпись' (Playwright)...")
                await save_btn.click()
                await page.wait_for_load_state("networkidle")
            else:
                logger.warning("⚠️ Кнопка 'Сохранить подпись' не найдена.")

        except Exception as e:
            logger.error(f"🔥 Ошибка в цикле подписи: {e}")
            break

    # В) ВОЗВРАТ В СПИСОК
    logger.info("🔙 Ищу кнопку 'Вернуться'...")
    try:
        back_btn = page.locator("a:has-text('Вернуться'), button:has-text('Вернуться'), a:has-text('Назад')").first
        if await back_btn.count() > 0 and await back_btn.is_visible():
            await back_btn.click()
            await page.wait_for_load_state("domcontentloaded")
    except: pass