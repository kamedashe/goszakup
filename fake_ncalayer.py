import asyncio
import ssl
import json
import logging
import websockets
from signer import sign_xml_data  # Твоя функция подписи через ncanode

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [FAKE_NCA] - %(message)s')
logger = logging.getLogger()

async def handler(websocket, path):
    logger.info(f"🔗 Сайт подключился! Path: {path}")
    
    try:
        async for message in websocket:
            logger.info(f"📥 Запрос от сайта: {message}")
            data = json.loads(message)
            
            module = data.get("module")
            req_type = data.get("type")
            
            response = {"errorCode": "NONE"}

            # --- ЛОГИКА ОТВЕТОВ (То, что ты уже знаешь) ---
            
            if module == "NURSign" and req_type == "version":
                response["result"] = {"version": "1.4"}
                logger.info("✅ Отправил версию 1.4")
                
            elif module == "NURSign" and req_type == "xml":
                xml = data.get("data")
                logger.info("✍️ Подписываем XML...")
                # Вызываем твой реальный signer
                signed_xml = await sign_xml_data(xml)
                
                if signed_xml:
                    response["result"] = signed_xml
                    logger.info("✅ XML подписан и отправлен")
                else:
                    response["errorCode"] = "WRONG_PASSWORD"
                    logger.error("❌ Ошибка подписи")

            # --- ОТВЕТ ОБРАТНО САЙТУ ---
            await websocket.send(json.dumps(response))
            
    except websockets.exceptions.ConnectionClosed:
        logger.info("🔌 Сайт отключился")

async def main():
    # Настройка SSL (обязательно для WSS)
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

    logger.info("🚀 Fake NCALayer запущен на wss://127.0.0.1:13579")
    
    # Запускаем сервер
    async with websockets.serve(handler, "127.0.0.1", 13579, ssl=ssl_context):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())