import requests
import os

def get_ngrok_url():
    """
    Çalışan ngrok'un yerel API'sini sorgulayarak public HTTPS URL'sini alır.
    Eğer ngrok çalışmıyorsa veya bir hata oluşursa, .env dosyasındaki BACKEND_URL'e geri döner.
    """
    try:
        # ngrok'un yerel API adresi
        response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
        tunnels = response.json()["tunnels"]
        
        # HTTPS tünelini bul
        for tunnel in tunnels:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        
        # HTTPS tüneli bulunamazsa .env'deki adrese geri dön
        return os.getenv("BACKEND_URL")

    except (requests.ConnectionError, requests.Timeout):
        # ngrok çalışmıyorsa veya API yanıt vermiyorsa
        return os.getenv("BACKEND_URL")
    except Exception:
        # Diğer olası hatalar için (örn: JSON parse hatası)
        return os.getenv("BACKEND_URL")