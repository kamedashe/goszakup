import aiohttp
import logging
from config import load_config

logger = logging.getLogger("NOTIFIER")

async def send_telegram(message: str):
    """Отправляет сообщение в Телеграм админу"""
    cfg = load_config()
    token = cfg['telegram']['token']
    chat_id = cfg['telegram']['admin_id']
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Экранирование спецсимволов для Markdown (если нужно) или просто текст
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML" # Чтобы можно было делать жирный текст
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info("📨 Уведомление отправлено в Telegram")
                else:
                    logger.error(f"❌ Ошибка отправки в TG: {resp.status} {await resp.text()}")
    except Exception as e:
        logger.error(f"❌ Ошибка сети TG: {e}")

# Тест (можно запустить файл отдельно)
if __name__ == "__main__":
    import asyncio
    asyncio.run(send_telegram("🤖 Бот запущен! <b>Системы в норме.</b>"))