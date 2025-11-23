import asyncio
import logging
import sys
from browser import init_browser, perform_login, check_auth
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
    print("🚀 ЗАПУСК ОТЛАДКИ ПОЛНОГО ЦИКЛА (NEW ARCHITECTURE)...")
    
    # 1. Грузим конфиг
    cfg = load_config()

    # Переменные для очистки
    playwright = None
    browser = None

    try:
        # 2. Инициализация
        logger.info("🔑 ЭТАП 1: ИНИЦИАЛИЗАЦИЯ БРАУЗЕРА...")
        playwright, browser, context, page = await init_browser(headless=False)
        
        # 3. Проверка авторизации
        if not await check_auth(page):
            logger.warning("⚠️ Сессия не активна. Пробую войти...")
            if not await perform_login(page, context):
                logger.error("❌ Не удалось войти. Стоп.")
                return

        # 4. ЗАПУСКАЕМ ТЕНДЕРНУЮ ЛОГИКУ
        logger.info("⚔️ ЭТАП 2: ОБРАБОТКА ЛОТА...")
        
        await process_lot(
            page, 
            cfg['target']['lot_url'], 
            cfg['data']['cooks']
        )

    except Exception as e:
        logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА В РАННЕРЕ: {e}")
        import traceback
        traceback.print_exc() 
    
    finally:
        logger.info("🛑 ВСЕ ЗАДАЧИ ВЫПОЛНЕНЫ. Браузер висит на паузе.")
        # Оставляем браузер висеть, чтобы ты мог посмотреть результат
        if 'page' in locals() and page:
            await page.pause()

if __name__ == "__main__":
    asyncio.run(main())