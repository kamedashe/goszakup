import os

# 1. Токен твого бота (отримай у @BotFather в Telegram)
TOKEN = "8599751581:AAGaelfUnEhaGtb0xQ7_Uxcw4sTZpFASyd8"

# 2. Твій логін і пароль для входу на сайт goszakup.gov.kz
GOV_LOGIN = "СУРАПБЕРГЕНОВ АМИР"
GOV_PASSWORD = "1Qaz2wsx!"
GOV_URL = "https://v3bl.goszakup.gov.kz/ru/user/login"

# 3. Пароль від твого файлу ключа .p12 (взяв з твого скріншоту)
KEY_PASSWORD = "1Qaz2wsx!" 

# --- ТЕХНІЧНІ НАЛАШТУВАННЯ ---

# Визначаємо, де ми запускаємось (Docker чи Local)
IN_DOCKER = os.path.exists("/.dockerenv")

if IN_DOCKER:
    NCANODE_URL = "http://ncanode:14579"
    KEY_PATH = "/goszakup/data/GOST512_030b1d6047860ccbb5ec0a1a4af9f6c0ccbf72a6.p12"
else:
    # Налаштування для локального запуску (Windows)
    NCANODE_URL = "http://localhost:14579"
    # Використовуємо абсолютний шлях для Windows
    KEY_PATH = r"d:\goszakup\data\GOST512_030b1d6047860ccbb5ec0a1a4af9f6c0ccbf72a6.p12"