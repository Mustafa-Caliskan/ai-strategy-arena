"""
start.py — AI Strategy Arena v2.0 Tek Komutla Başlatıcı
"""
import webbrowser
import threading
import time
import uvicorn
from pathlib import Path

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    print("=" * 60)
    print(">>> AI Strategy Arena v2.0 Başlatılıyor... <<<")
    print(">>> Web Arayüzü: http://localhost:8000")
    print("=" * 60)
    threading.Thread(target=open_browser, daemon=True).start()
    
    import sys
    backend_dir = str(Path(__file__).parent / "backend")
    sys.path.insert(0, backend_dir)
    
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, app_dir=backend_dir)
