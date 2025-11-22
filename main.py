import asyncio
import logging
from config import load_config
from browser import run_browser_task
from tender import process_lot
from notifier import send_telegram

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("COMMANDER")

async def main():

    await send_telegram("🤖 Бот запущен! <b>Системы в норме.</b>")

    cfg = load_config()
    
    # 1. АВТОРИЗАЦИЯ
    logger.info("🚀 ЗАПУСК: Вход в систему...")
    try:
        # Получаем живую страницу из browser.py
        browser, context, page = await run_browser_task()
    except Exception as e:
        logger.error(f"💥 Ошибка входа: {e}")
        return

    # 2. ПОДАЧА ЗАЯВКИ
    logger.info("⚔️ ЗАПУСК: Обработка лота...")
    try:
        await process_lot(
            page, 
            cfg['target']['lot_url'], # Ссылка на лот из конфига
            cfg['data']['cooks']      # Список поваров
        )
    except Exception as e:
        logger.error(f"💥 Ошибка в тендере: {e}")
    finally:
        # 3. УБОРКА
        logger.info("💤 Завершение работы...")
        await asyncio.sleep(5) # Даем время полюбоваться
        await browser.close()


if __name__ == "__main__":
    retries = 0
    while retries < 3:
        try:
            asyncio.run(main())
            break # Если все ок, выходим
        except Exception as e:
            retries += 1
            print(f"🔥 CRITICAL CRASH! Перезапуск через 5 сек... ({retries}/3)")
            # Тут можно отправить алерт в телеграм: "Я упал, встаю!"
            import time
            time.sleep(5)