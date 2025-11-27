# goszakup/main.py
import asyncio
import logging
from config import load_config
from browser import init_browser, perform_login
from tender_fast import process_lot_parallel 
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SNIPER")

async def main():
    print("--- STARTING MAIN ---")
    cfg = load_config()
    lot_url = cfg['target']['lot_url']
    
    logger.info("🚀 СНАЙПЕР: Старт...")
    
    playwright = None
    browser = None
    
    try:
        logger.info("🖥️ Запускаю браузер...")
        playwright, browser, context, page = await init_browser(headless=False)
        
        logger.info(f"⚡ Переход на лот: {lot_url}")
        try: await page.goto(lot_url, wait_until="domcontentloaded")
        except: pass

        # Проверка входа
        if "login" in page.url or "auth" in page.url:
            logger.warning("⛔ Требуется вход...")
            if await perform_login(page, context):
                 logger.info("✅ Вход выполнен.")
                 await page.goto(lot_url, wait_until="domcontentloaded")
            else:
                 logger.error("❌ Не удалось войти автоматом. Зайди руками!")
                 await page.pause()

        logger.info("⚔️ РАБОТА ПО ЛОТУ...")
        await process_lot_parallel(context, lot_url, cfg['data'])

    except Exception as e:
        logger.error(f"💥 CRASH: {e}")
    finally:
        logger.info("🏁 Работа скрипта завершена. БРАУЗЕР ОСТАЕТСЯ ОТКРЫТЫМ.")
        # Оставляем браузер висеть вечно
        if page:
            await page.pause()

if __name__ == "__main__":
    asyncio.run(main())