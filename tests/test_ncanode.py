#!/usr/bin/env python3
import asyncio
import aiohttp
import base64
from config import KEY_PATH, KEY_PASSWORD, NCANODE_URL

async def test_ncanode():
    try:
        # Read the P12 file
        with open(KEY_PATH, 'rb') as f:
            p12_b64 = base64.b64encode(f.read()).decode()
        
        # Simple XML to sign
        test_xml = '<?xml version="1.0" encoding="UTF-8"?><root><test>Hello</test></root>'
        
        payload = {
            "xml": test_xml,
            "signers": [
                {
                    "key": p12_b64,
                    "password": KEY_PASSWORD
                }
            ]
        }
        
        print(f"Тестирую подпись через NCANode...")
        print(f"URL: {NCANODE_URL}/xml/sign")
        print(f"Пароль: {KEY_PASSWORD}")
        print(f"Длина P12: {len(p12_b64)} байт (base64)")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{NCANODE_URL}/xml/sign", json=payload) as resp:
                status = resp.status
                text = await resp.text()
                
                print(f"\nСтатус ответа: {status}")
                
                if status == 200:
                    result = await resp.json()
                    signed_xml = result.get('xml')
                    if signed_xml and '<ds:Signature' in signed_xml:
                        print("✅ УСПЕХ! NCANode успешно подписал XML!")
                        print(f"Длина подписанного XML: {len(signed_xml)} символов")
                        print(f"\nПервые 500 символов подписи:")
                        print(signed_xml[:500])
                        return True
                    else:
                        print(f"❌ Ответ получен, но нет подписи")
                        print(f"Ответ: {text[:500]}")
                else:
                    print(f"❌ Ошибка от NCANode:")
                    print(text)
                    return False
    except Exception as e:
        print(f"❌ Исключение: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_ncanode())
    print(f"\n{'='*80}")
    print(f"Результат: {'✅ Работает' if result else '❌ Не работает'}")
