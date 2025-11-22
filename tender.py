import asyncio
import logging
from datetime import datetime
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
    # Если есть таблица с документами - значит список.
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
        "Техническое задание" # Иногда называется просто так
    ]

    for doc_name in TARGET_DOCS:
        logger.info(f"🔎 Ищу документ: {doc_name}")
        
        # Ищем ссылку (тег 'a'), внутри которой есть этот текст
        link = page.locator(f"a:has-text('{doc_name}')").first
        
        if await link.count() > 0 and await link.is_visible():
            # Проверяем, есть ли рядом зеленый статус (галочка)
            # Это сложно сделать универсально, поэтому просто заходим и проверяем кнопки внутри.
            
            logger.info(f"✨ Нашел! Захожу внутрь...")
            await link.click()
            await page.wait_for_load_state("domcontentloaded")
            
            # --- ЗАЧИСТКА ---
            await sign_current_page(page)
            # ----------------
            
            logger.info("🔙 Возвращаюсь к списку документов (Hard Reset)...")
            
            # Просто переходим по ссылке списка принудительно
            # Это сбрасывает все глюки страницы документа
            try:
                await page.goto(list_url, wait_until="domcontentloaded", timeout=30000)
                logger.info("✅ Вернулись в список.")
            except Exception as e:
                logger.error(f"❌ Ошибка возврата: {e}")
            
        else:
            logger.info(f"⏩ Ссылка '{doc_name}' не найдена. Пропускаем.")

    logger.info("🏁 Все документы из списка обработаны. Ищу кнопку 'Подать заявку'...")
    # Тут можно добавить клик на финальную кнопку подачи, если она появится в списке


# === 3. УНИВЕРСАЛЬНАЯ ПОДПИСЬ И ВОЗВРАТ ===
async def sign_current_page(page: Page):
    """
    1. Подписывает все зеленые кнопки.
    2. Жмет Сохранить.
    3. Жмет Вернуться.
    """
    logger.info("⚔️ Зачистка документа...")

    # А) ПОДПИСЬ ВСЕХ ФАЙЛОВ
    while True:
        try: await page.locator(".blockUI").wait_for(state="detached", timeout=2000)
        except: pass

        sign_btn = page.locator("button.btn-add-signature").first
        
        if await sign_btn.count() == 0:
            logger.info("✅ Больше кнопок 'Подписать' нет.")
            break 

        logger.info("🎯 Нашел кнопку 'Подписать'. Вызываю SUPER_SIGN...")
        try:
            await sign_btn.wait_for(state="visible", timeout=5000)
            file_url = await sign_btn.get_attribute("data-url")
            form_id = await sign_btn.get_attribute("data-form-id")

            if file_url and form_id:
                # Вызываем JS напрямую
                await page.evaluate(f"window.SUPER_SIGN('{file_url}', '{form_id}')")
                
                logger.info("⏳ Жду обновления страницы...")
                try:
                    await page.wait_for_load_state("networkidle", timeout=20000)
                    logger.info("🔄 Страница обновлена.")
                except:
                    logger.warning("⚠️ Тайм-аут обновления страницы.")
            else:
                logger.error("❌ Кнопка без атрибутов!")
                break
        except Exception as e:
            logger.error(f"🔥 Ошибка подписи: {e}")
            break

    # Б) СОХРАНЕНИЕ (Если есть кнопка "Сохранить")
    try:
        save_btn = page.locator("button:has-text('Сохранить')").first
        if await save_btn.count() > 0 and await save_btn.is_visible():
            logger.info("💾 Нашел кнопку 'Сохранить'. Жму...")
            await save_btn.click()
            await page.wait_for_load_state("networkidle")
    except: pass

    # В) ВОЗВРАТ В СПИСОК
    logger.info("🔙 Ищу кнопку 'Вернуться'...")
    try:
        # Ищем кнопку по тексту (регистронезависимо через regex или варианты)
        back_btn = page.locator("a:has-text('Вернуться'), button:has-text('Вернуться'), a:has-text('Назад')").first
        
        if await back_btn.count() > 0 and await back_btn.is_visible():
            await back_btn.click()
            await page.wait_for_load_state("domcontentloaded")
            logger.info("✅ Нажали 'Вернуться'.")
        else:
            logger.warning("⚠️ Кнопка возврата не найдена (бот вернется через history.back или goto).")
    except Exception as e:
        logger.error(f"❌ Ошибка возврата: {e}")