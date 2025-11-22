import asyncio
import logging
import sys
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from config import TOKEN
from browser import run_browser_task

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Привіт! Тисни /test")

@dp.message(Command("test"))
async def run_test(msg: types.Message):
    m = await msg.answer("🚀 Запускаю діагностику...")
    
    # Чистимо старі файли
    for f in ["debug_what_i_see.png", "success.png", "error_stuck.png", "debug_page.html"]:
        if os.path.exists(f): os.remove(f)

    try:
        res = await run_browser_task()
        await m.edit_text(f"📝 Звіт:\n{res}")
        
        # Відправляємо все, що знайшли
        files = ["debug_what_i_see.png", "success.png", "error_stuck.png"]
        for f in files:
            if os.path.exists(f):
                await msg.answer_photo(FSInputFile(f), caption=f"Файл: {f}")
                
        # Відправляємо HTML як документ, якщо він є (щоб ти міг відкрити і подивитись код сторінки)
        if os.path.exists("debug_page.html"):
             await msg.answer_document(FSInputFile("debug_page.html"), caption="Код сторінки")

    except Exception as e:
        await m.edit_text(f"❌ Помилка: {e}")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))