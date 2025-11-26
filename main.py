import asyncio
import logging
import os
from config import load_config, GOV_URL
from browser import init_browser, perform_login
from tender_fast import process_lot_parallel 
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SNIPER")

async def main():
    print("--- STARTING MAIN ---") # Самый первый принт
    cfg = load_config()
    lot_url = cfg['target']['lot_url']
    
    logger.info("🚀 СНАЙПЕР: Инициализация...")
    await send_telegram(f"🔫 <b>Bot started X-RAY</b>")

    playwright = None
    browser = None
    
    try:
        logger.info("🖥️ Запускаю браузер...")
        playwright, browser, context, page = await init_browser(headless=False)
        logger.info("✅ Браузер запущен.")
        
        logger.info(f"⚡ Переход на лот: {lot_url}")
        try:
            await page.goto(lot_url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка перехода (игнорирую): {e}")

        # Проверка входа
        if "login" in page.url or "auth" in page.url:
            logger.warning("⛔ Требуется вход...")
            if await perform_login(page, context):
                 logger.info("✅ Вход выполнен.")
                 await page.goto(lot_url, wait_until="domcontentloaded")
            else:
                 raise Exception("Не удалось войти.")

        logger.info("⚔️ ЗАПУСК X-RAY...")
        await process_lot_parallel(context, lot_url, cfg['data'])

    except Exception as e:
        logger.error(f"💥 CRASH: {e}")
    finally:
        logger.info("💤 Завершение работы.")
        if browser: await browser.close()
        if playwright: await playwright.stop()

if __name__ == "__main__":
    asyncio.run(main())