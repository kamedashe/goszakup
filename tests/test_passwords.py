#!/usr/bin/env python3
import base64
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
from config import KEY_PATH

# Попробуем разные пароли
passwords_to_try = [
    "1Qaz2wsx!",      # Текущий пароль из config
    "1Qaz2wsx",       # Без восклицательного знака
    "Qaz2wsx!",       # Без 1
    "",               # Пустой пароль
    "123456",         # Простой пароль
]

print(f"Пытаюсь открыть: {KEY_PATH}\n")

with open(KEY_PATH, 'rb') as f:
    p12_data = f.read()

for password in passwords_to_try:
    try:
        private_key, certificate, additional_certs = pkcs12.load_key_and_certificates(
            p12_data,
            password.encode() if password else None,
            default_backend()
        )
        print(f"✅ УСПЕХ! Правильный пароль: '{password}'")
        print(f"\nВладелец сертификата:")
        for attr in certificate.subject:
            print(f"  {attr.oid._name}: {attr.value}")
        break
    except Exception as e:
        print(f"❌ Пароль '{password}' не подходит: {type(e).__name__}")

else:
    print("\n⚠️  Ни один из паролей не подошел. Нужен правильный пароль от пользователя.")
