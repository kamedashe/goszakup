import asyncio
import logging
import sys
from signer import sign_xml_data

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    print("🚀 Testing Signer...")
    xml = '<?xml version="1.0" encoding="UTF-8"?><root><test>Hello</test></root>'
    print(f"📝 Signing XML: {xml}")
    
    try:
        signed = await sign_xml_data(xml)
        if signed:
            print(f"✅ Signed XML: {signed[:100]}...")
        else:
            print("❌ Signing failed.")
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
