# signer.py
import aiohttp
import base64
import logging
import os
from config import NCANODE_URL, KEY_PATH, KEY_PASSWORD

logger = logging.getLogger(__name__)

async def _read_key_file():
    if not os.path.exists(KEY_PATH):
        logger.error(f"❌ Файл ключа не найден: {KEY_PATH}")
        return None
    with open(KEY_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

async def sign_xml_data(xml_string):
    if not xml_string: return None
    key_b64 = await _read_key_file()
    if not key_b64: return None

    # Очистка (убираем BOM и пробелы по краям, но переносы внутри тегов лучше оставить)
    clean_xml = xml_string.strip().replace(u'\ufeff', '') 
    
    payload = {
        "xml": clean_xml,
        "signers": [{
            "key": key_b64,
            "password": KEY_PASSWORD,
            "keyType": "GOST"
        }]
    }
    # Добавляем try внутри send_request или тут, чтобы увидеть ошибку 500
    res = await _send_request("xml/sign", payload, is_xml=True)
    return res
    
async def sign_cms_data(data_b64):
    key_b64 = await _read_key_file()
    if not key_b64: return None
    payload = {
        "data": data_b64,
        "with_content": True,
        "signers": [{"key": key_b64, "password": KEY_PASSWORD, "keyType": "GOST"}]
    }
    return await _send_request("cms/sign", payload, is_xml=False)

async def _send_request(endpoint, payload, is_xml):
    url = f"{NCANODE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    if res.get('status') == 0 or res.get('status') == 200:
                        return res.get('xml') if is_xml else res.get('cms')
                    logger.error(f"❌ NCANode Error: {res}")
                else:
                    logger.error(f"❌ HTTP {resp.status}: {await resp.text()}")
    except Exception as e:
        logger.error(f"🔥 Network Error: {e}")
    return None