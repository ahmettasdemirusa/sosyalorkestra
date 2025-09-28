import subprocess
import time
import os
import sys
import atexit

from ngrok_utils import get_ngrok_url

def main():
    """
    Sosyal Orkestra uygulamasının tüm bileşenlerini (ngrok, backend, scheduler, frontend)
    tek bir terminalden başlatan ana betik.
    """
    processes = []

    def cleanup():
        """Uygulama kapatılırken tüm alt işlemleri sonlandırır."""
        print("\n🛑 Uygulama kapatılıyor... Tüm servisler durduruluyor.")
        for p in processes:
            p.terminate()
        print("✅ Tüm servisler başarıyla durduruldu.")

    # Programdan çıkıldığında cleanup fonksiyonunun çalışmasını sağla
    atexit.register(cleanup)

    # 1. ngrok'u başlat
    print("🚀 ngrok başlatılıyor...")
    ngrok_process = subprocess.Popen("ngrok http 5000", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    processes.append(ngrok_process)
    print("... ngrok'un hazır olması için 3 saniye bekleniyor ...")
    time.sleep(3)

    # 2. ngrok URL'sini al
    backend_url = get_ngrok_url()
    if "ngrok" not in backend_url:
        print("❌ HATA: ngrok URL'si alınamadı. ngrok'un doğru bir şekilde kurulduğundan ve çalıştığından emin olun.")
        sys.exit(1)
    
    print(f"🔗 ngrok tüneli hazır: {backend_url}")

    # 3. Diğer servisleri, alınan URL ile ortam değişkeni olarak başlat
    env = os.environ.copy()
    env["BACKEND_URL"] = backend_url

    print("\n🚀 Backend (Flask) sunucusu başlatılıyor...")
    backend_process = subprocess.Popen(["python", "backend.py"], env=env)
    processes.append(backend_process)

    print("\n🚀 Zamanlayıcı (Scheduler) 'watchdog' ile başlatılıyor...")
    scheduler_command = "watchmedo auto-restart --directory=. --pattern=\"*.py\" --recursive -- python scheduler.py"
    scheduler_process = subprocess.Popen(scheduler_command, shell=True, env=env)
    processes.append(scheduler_process)

    print("\n🚀 Arayüz (Streamlit) başlatılıyor...")
    streamlit_process = subprocess.Popen(["streamlit", "run", "dashboard.py"], env=env)
    processes.append(streamlit_process)

    print("\n✅ Tüm servisler başarıyla başlatıldı! Uygulamayı kapatmak için bu terminalde Ctrl+C'ye basın.")
    
    # Ana betiğin, alt işlemler çalışırken açık kalmasını sağla
    streamlit_process.wait()

if __name__ == "__main__":
    main()