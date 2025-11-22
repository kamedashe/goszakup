import aiohttp
import base64
import logging
import os
from config import NCANODE_URL, KEY_PATH, KEY_PASSWORD

logger = logging.getLogger(__name__)

async def _read_key_file():
    """Вспомогательная функция: читает ключ с диска и переводит в Base64"""
    if not os.path.exists(KEY_PATH):
        logger.error(f"❌ Файл ключа не найден: {KEY_PATH}")
        return None
        
    with open(KEY_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

async def sign_xml_data(xml_string):
    """Подпись XML (Вход)"""
    key_b64 = await _read_key_file()
    if not key_b64: return None

    payload = {
        "xml": xml_string,
        # 🔥 ДОДАЙ ЦІ ДВА РЯДКИ! БЕЗ НИХ ТЕНДЕР НЕ ПІДПИШЕТЬСЯ 🔥
        "createTsp": True,
        "useTsaPolicy": "TSA_GOST_POLICY",
        "signers": [
            {
                "key": key_b64, # <--- Шлем КЛЮЧ, а не ПУТЬ
                "password": KEY_PASSWORD,
                "keyType": "GOST"
            }
        ]
    }

    return await _send_request("xml/sign", payload, is_xml=True)

async def sign_cms_data(data_b64):
    """Подпись CMS (Файлы)"""
    key_b64 = await _read_key_file()
    if not key_b64: return None

    payload = {
        "data": data_b64,
        "with_content": True, # Обязательно для файлов
        "signers": [
            {
                "key": key_b64, # <--- ВОТ ТУТ БЫЛА ОШИБКА. ТЕПЕРЬ ИСПРАВЛЕНО.
                "password": KEY_PASSWORD,
                "keyType": "GOST" 
            }
        ]
    }

    return await _send_request("cms/sign", payload, is_xml=False)

async def _send_request(endpoint, payload, is_xml):
    url = f"{NCANODE_URL}/{endpoint}"
    logger.info(f"🚀 Отправка в NCANode ({endpoint})...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    
                    # Проверяем оба варианта (0 или 200)
                    if res.get('status') == 0 or res.get('status') == 200:
                        # Если XML - поле 'xml', если CMS - поле 'cms'
                        result = res.get('xml') if is_xml else res.get('cms')
                        
                        if result:
                            # Чистим XML от мусора (для входа это важно)
                            if is_xml:
                                result = result.replace("&#13;", "").replace("\r", "").replace("\n", "")
                            
                            logger.info(f"✅ Успешно подписано ({endpoint})")
                            return result
                    
                    logger.error(f"❌ Ошибка внутри NCANode: {res}")
                else:
                    logger.error(f"❌ HTTP Ошибка {resp.status}: {await resp.text()}")
    except Exception as e:
        logger.error(f"🔥 Ошибка сети: {e}")
    
    return None