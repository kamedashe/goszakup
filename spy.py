import asyncio
import logging
from playwright.async_api import async_playwright
from config import GOV_URL, GOV_PASSWORD, KEY_PATH

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("SPY")

async def main():
    logger.info("🕵️ ЗАПУСК ШПИОНА...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(storage_state="auth.json" if "auth.json" else None)
        page = await context.new_page()

        # 1. Вход (если нужно)
        await page.goto("https://v3bl.goszakup.gov.kz/ru/cabinet/profile", wait_until="domcontentloaded")
        if "login" in page.url:
            logger.info("🔑 Входим...")
            await page.click("#selectP12File")
            await asyncio.sleep(2)
            await page.fill("input[type='password']", GOV_PASSWORD)
            await page.press("input[type='password']", "Enter")
            await page.wait_for_url("**/cabinet/**")

        # 2. Переход к лоту (замените на ваш URL лота)
        # ВАЖНО: Вставьте сюда ссылку на лот, где вы застряли
        lot_url = "https://v3bl.goszakup.gov.kz/ru/application/docs/15668732/67780329"
        
        logger.info(f"🚀 Идем на лот: {lot_url}")
        await page.goto(lot_url, wait_until="domcontentloaded")

        # 3. Переход к финалу
        logger.info("➡️ Жму 'Далее'...")
        next_btn = page.locator("button:has-text('Далее'), a.btn-primary:has-text('Далее')").first
        if await next_btn.count() > 0:
            await next_btn.click()
            await page.wait_for_load_state("domcontentloaded")

        # 4. ШПИОНАЖ
        logger.info("📸 СНИМАЮ ДАННЫЕ С ФИНАЛЬНОЙ СТРАНИЦЫ...")
        await asyncio.sleep(3) # Даем прогрузиться

        # Ищем кнопку
        sign_btn = page.locator("button:has-text('Подписать заявку')").first
        if await sign_btn.count() > 0:
            logger.info("✅ Кнопка 'Подписать заявку' найдена!")
            
            # --- АНАЛИЗ 1: HTML ВОКРУГ КНОПКИ ---
            # Мы ищем родительскую форму этой кнопки
            form_info = await page.evaluate("""() => {
                const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Подписать заявку'));
                if (!btn) return "BUTTON_NOT_FOUND";
                
                const form = btn.closest('form');
                if (!form) return "NO_PARENT_FORM";

                // Собираем все инпуты в этой форме
                const inputs = Array.from(form.querySelectorAll('input, textarea, select')).map(i => {
                    return `<${i.tagName} name="${i.name}" id="${i.id}" type="${i.type}" value="${i.value}">`;
                });

                return {
                    action: form.action,
                    method: form.method,
                    id: form.id,
                    inputs: inputs,
                    html: form.outerHTML
                };
            }""")
            
            print("\n" + "="*20 + " ОТЧЕТ ШПИОНА " + "="*20)
            if isinstance(form_info, dict):
                print(f"URL Action: {form_info['action']}")
                print(f"Method: {form_info['method']}")
                print(f"Form ID: {form_info['id']}")
                print("\n--- СКРЫТЫЕ ПОЛЯ (INPUTS) ---")
                for inp in form_info['inputs']:
                    print(inp)
                
                # Сохраняем полный HTML в файл
                with open("final_page_dump.html", "w", encoding="utf-8") as f:
                    f.write(form_info['html'])
                logger.info("\n💾 Полный HTML формы сохранен в 'final_page_dump.html'")
            else:
                print(f"❌ Ошибка анализа: {form_info}")
                # Если формы нет, дампим всю страницу
                content = await page.content()
                with open("full_page_dump.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("⚠️ Форма не найдена. Сохранена вся страница в 'full_page_dump.html'")

        else:
            logger.error("❌ Кнопка 'Подписать заявку' не найдена на этой странице.")

        print("="*50)
        input("Нажмите Enter, чтобы закрыть...")

if __name__ == "__main__":
    asyncio.run(main())