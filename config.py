import os
import yaml
import logging

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CONFIG")

def load_config():
    config_path = "config.yaml"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Файл конфигурации не найден: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Загружаем данные
try:
    cfg = load_config()
    logger.info("✅ Config loaded from YAML")
except Exception as e:
    logger.error(f"Config error: {e}")
    exit(1)

# --- ЭКСПОРТ ПЕРЕМЕННЫХ (ОСТАВЛЯЕМ ИМЕНА КАК БЫЛИ) ---

# 1. Telegram
TOKEN = cfg['telegram']['token']

# 2. Данные входа
GOV_LOGIN = cfg['account']['login']
GOV_PASSWORD = cfg['account']['password']
GOV_URL = cfg['target']['url']
KEY_PASSWORD = cfg['account']['sign_password']

# --- ТЕХНИЧЕСКАЯ ЛОГИКА (DOCKER vs LOCAL) ---

IN_DOCKER = os.path.exists("/.dockerenv")

# Имя файла ключа
key_filename = cfg['paths']['key_filename']

if IN_DOCKER:
    logger.info("🐳 Detected Environment: DOCKER")
    NCANODE_URL = cfg['services']['ncanode_docker']
    # Склеиваем путь: /goszakup/data + имя файла
    KEY_PATH = os.path.join(cfg['paths']['docker_dir'], key_filename)
else:
    logger.info("💻 Detected Environment: LOCAL (Windows)")
    NCANODE_URL = cfg['services']['ncanode_local']
    # Склеиваем путь: d:/goszakup/data + имя файла
    KEY_PATH = os.path.join(cfg['paths']['local_dir'], key_filename)

# Выводим для проверки (но пароли не палим)
logger.info(f"🔑 KEY_PATH: {KEY_PATH}")
logger.info(f"🔗 NCANODE: {NCANODE_URL}")