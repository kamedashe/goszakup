import asyncio
import logging
import sys
from browser import run_browser_task
from config import load_config
from tender import process_lot

# Настройка логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DEBUG_RUNNER")

async def main():
    print("🚀 ЗАПУСК ОТЛАДКИ ПОЛНОГО ЦИКЛА...")
    
    # 1. Грузим конфиг
    cfg = load_config()

    # Переменные для очистки
    playwright = None
    browser = None

    try:
        # 2. Логинимся (получаем 4 объекта!)
        logger.info("🔑 ЭТАП 1: ВХОД В СИСТЕМУ...")
        playwright, browser, context, page = await run_browser_task()
        
        if not page:
            logger.error("❌ Браузер не вернулся. Ошибка входа.")
            return

        # 3. ЗАПУСКАЕМ ТЕНДЕРНУЮ ЛОГИКУ
        logger.info("⚔️ ЭТАП 2: ОБРАБОТКА ЛОТА...")
        
        # Убедись, что в config.yaml target.lot_url ведет на страницу СО СПИСКОМ документов!
        await process_lot(
            page, 
            cfg['target']['lot_url'], 
            cfg['data']['cooks']
        )

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В РАННЕРЕ: {e}")
        import traceback
        traceback.print_exc() # Покажет, где именно упало
    
    finally:
        logger.info("🛑 ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ. Браузер висит на паузе.")
        # Оставляем браузер висеть, чтобы ты мог посмотреть результат
        if 'page' in locals() and page:
            await page.pause()

if __name__ == "__main__":
    asyncio.run(main())