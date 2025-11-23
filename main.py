import asyncio
import logging
import os
from config import load_config, GOV_URL
from browser import init_browser, perform_login
# 👇 1. ИМПОРТИРУЕМ НОВУЮ ФУНКЦИЮ
from tender_fast import process_lot_parallel 
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SNIPER")

async def main():
    cfg = load_config()
    lot_url = cfg['target']['lot_url']
    
    logger.info("🚀 СНАЙПЕР: Запуск. Доверяю кукам от Keeper.")
    await send_telegram(f"🔫 <b>Снайпер вышел на охоту!</b>\nЦель: {lot_url}")

    playwright = None
    browser = None
    
    try:
        # 1. ИНИЦИАЛИЗАЦИЯ + КУКИ
        playwright, browser, context, page = await init_browser(headless=False)
        
        # 2. ПРЯМОЙ ПРЫЖОК НА ЛОТ
        logger.info(f"⚡ Мгновенный переход на лот...")
        
        try:
            response = await page.goto(lot_url, wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки (возможно, редирект): {e}")
            response = None

        # 3. ПРОВЕРКА АВТОРИЗАЦИИ
        if "login" in page.url or "auth" in page.url:
            logger.warning("⛔ КУКИ ПРОТУХЛИ! Аварийный вход...")
            if await perform_login(page, context):
                 logger.info("✅ Вход выполнен. Повторный прыжок на лот...")
                 await page.goto(lot_url, wait_until="domcontentloaded")
            else:
                 raise Exception("Не удалось войти в систему.")
        
        elif response and response.status == 403:
             raise Exception("403 Forbidden. Лот недоступен или бан IP.")

        # 4. АТАКА (SPEEDRUN)
        logger.info("⚔️ ЦЕЛЬ ЗАХВАЧЕНА. ЗАПУСКАЮ SPEEDRUN (PARALLEL).")
        
        # 👇 2. ВСТАВЛЯЕМ НОВЫЙ ВЫЗОВ ЗДЕСЬ
        # Важно: передаем 'context', а не 'page', чтобы открывать вкладки
        await process_lot_parallel(
            context, 
            lot_url, 
            cfg['data']  # Передаем весь блок data (там должны быть и повара, и дипломы)
        )

        await send_telegram("✅ <b>Снайпер отработал успешно!</b>")

    except Exception as e:
        logger.error(f"💥 CRASH: {e}")
        await send_telegram(f"💥 <b>Снайпер упал:</b> {e}")
        await asyncio.sleep(3600) 

    finally:
        logger.info("💤 Работа завершена.")
        if browser: await browser.close()
        if playwright: await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())