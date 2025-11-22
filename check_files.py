import os
import logging
from config import load_config # Твой загрузчик конфига

# Настройка логов
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger()

def check_paths():
    print("🔍 НАЧИНАЮ ПРОВЕРКУ ФАЙЛОВ ИЗ CONFIG.YAML...\n")
    
    try:
        cfg = load_config()
    except Exception as e:
        print(f"❌ Ошибка загрузки конфига: {e}")
        return

    # 1. Проверяем путь к ключу ЭЦП
    # В твоем config.py логика выбора пути (Docker/Local) уже есть, 
    # но давай проверим то, что написано в YAML для наглядности
    key_name = cfg['paths']['key_filename']
    # Предполагаем, что папка data лежит рядом со скриптом
    local_key_path = os.path.join("data", key_name)
    
    if os.path.exists(local_key_path):
        print(f"✅ Ключ ЭЦП найден: {local_key_path}")
    else:
        print(f"❌ Ключ ЭЦП НЕ НАЙДЕН: {local_key_path}")
        print("   -> Проверь папку 'data' и имя файла в config.yaml")

    print("-" * 20)

    # 2. Проверяем дипломы поваров
    cooks = cfg['data']['cooks']
    all_good = True
    
    for i, cook in enumerate(cooks):
        file_path = cook['file_path']
        # Если путь относительный (не начинается с C:\ или /), Python ищет его от текущей папки
        
        if os.path.exists(file_path):
            print(f"✅ Документ повара {i+1} ({cook['name']}) найден: {file_path}")
        else:
            print(f"❌ Документ повара {i+1} ({cook['name']}) НЕ НАЙДЕН: {file_path}")
            print(f"   -> Ты положил файл в папку data? Имя совпадает?")
            all_good = False

    print("\n" + "="*30)
    if all_good:
        print("🚀 ВСЕ ФАЙЛЫ НА МЕСТЕ. МОЖНО ЗАПУСКАТЬ БОТА.")
    else:
        print("🔥 ЕСТЬ ОШИБКИ! Бот упадет при попытке загрузки.")

if __name__ == "__main__":
    check_paths()