import asyncio
import logging
import sys
print("DEBUG: Importing browser module...")
from browser import run_browser_task
print("DEBUG: Browser module imported.")

# Configure logging to stdout and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("debug_runner.log", encoding='utf-8')
    ]
)

async def main():
    print("🚀 Starting standalone browser debug...")
    try:
        result = await run_browser_task()
        print(f"✅ Result:\n{result}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
