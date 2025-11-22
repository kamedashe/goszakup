import aiohttp
import base64
import logging
import json
# Убедись, что эти переменные есть в config.py
from config import NCANODE_URL, KEY_PATH, KEY_PASSWORD

logger = logging.getLogger(__name__)

async def sign_xml_data(xml_string):
    """Отправляет XML в NCANode и возвращает чистую подпись"""
    try:
        logger.info(f"🔑 Читаем ключ: {KEY_PATH}")
        with open(KEY_PATH, "rb") as f:
            p12_b64 = base64.b64encode(f.read()).decode()

        payload = {
            "xml": xml_string,
            "createTsp": True, # Для входа обычно TSP не нужен, если будет ошибка - включи True
            "signers": [
                {
                    "key": p12_b64,
                    "password": KEY_PASSWORD,
                    "keyAlias": None # NCANode сам найдет алиас
                }
            ]
        }

        logger.info(f"🚀 Отправка в NCANode: {NCANODE_URL}")
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{NCANODE_URL}/xml/sign", json=payload) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    signed_xml = res.get("xml")
                    
                    if signed_xml:
                        # Очистка от спецсимволов, как ты и делал
                        signed_xml = signed_xml.replace("&#13;", "").replace("\r", "").replace("\n", "")
                        logger.info("✅ XML успешно подписан")
                        return signed_xml
                    else:
                        logger.error(f"❌ NCANode вернул пустой XML. Ответ: {res}")
                else:
                    logger.error(f"❌ Ошибка NCANode HTTP {resp.status}: {await resp.text()}")
    except Exception as e:
        logger.error(f"❌ Ошибка в signer.py: {e}")
    return None