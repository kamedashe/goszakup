import sys
import os

print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    import tender_fast
    print(f"tender_fast imported: {tender_fast}")
    print(f"dir(tender_fast): {dir(tender_fast)}")
    from tender_fast import process_lot_parallel
    print("Successfully imported process_lot_parallel")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
