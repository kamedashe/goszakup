import asyncio
import logging
import random
import os
import json
from playwright.async_api import async_playwright
# Импортируем твои функции. Убедись, что perform_login есть в browser.py!
from browser import handle_ncalayer_request, MOCK_JS, perform_login, init_browser
from config import GOV_URL

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [KEEPER] - %(message)s')
logger = logging.getLogger("AUTH_KEEPER")

async def run_keeper():
    logger.info("🛡️ Auth Keeper запущен. Я буду держать дверь открытой.")
    
    # ИСПОЛЬЗУЕМ ЕДИНУЮ ТОЧКУ ВХОДА С "ЖЕЛЕЗНЫМ КАПКАНОМ"
    playwright, browser, context, page = await init_browser(headless=False)

    try:
        logger.info("🌍 Вхожу в цикл поддержания жизни...")
        
        while True:
            try:
                # 2. ПРОВЕРКА СТАТУСА (С УВЕЛИЧЕННЫМ ТАЙМАУТОМ)
                if "cabinet" not in page.url:
                    logger.info(f"🔄 Я не в кабинете (URL: {page.url}). Иду проверять...")
                    try:
                        # Увеличиваем время до 60 сек и ждем только HTML
                        await page.goto(
                            "https://v3bl.goszakup.gov.kz/ru/cabinet/profile", 
                            timeout=60000, 
                            wait_until="domcontentloaded"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ Тайм-аут перехода (не страшно, проверяем логин): {e}")

                # 3. ЕСЛИ ВЫКИНУЛО - ЛОГИНИМСЯ
                if "login" in page.url or "auth" in page.url:
                    logger.warning("⚠️ Сессия мертва! Восстанавливаю...")
                    
                    # Вызываем твою мощную функцию входа
                    success = await perform_login(page, context)
                    
                    if success:
                        logger.info("🎉 Релогин успешен! Сохраняю куки.")
                        await context.storage_state(path="auth.json")
                    else:
                        logger.error("❌ Не удалось войти. Попробую в следующем цикле.")

                # 4. ЕЩЕ РАЗ СОХРАНЯЕМ (Heartbeat)
                if "cabinet" in page.url:
                     await context.storage_state(path="auth.json")
                     logger.info("💾 Куки обновлены (Heartbeat).")

                # 5. СПИМ
                sleep_time = random.randint(60, 120) # 1-2 минуты
                logger.info(f"💤 Сплю {sleep_time} сек...")
                await asyncio.sleep(sleep_time)
                
                # 6. ОБНОВЛЯЕМ СТРАНИЦУ
                logger.info("♻️ Обновляю страницу...")
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                except: pass

            except Exception as e:
                logger.error(f"🔥 Ошибка в цикле Keeper: {e}")
                await asyncio.sleep(10) 

    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    asyncio.run(run_keeper())