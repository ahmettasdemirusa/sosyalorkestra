import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# .env dosyasından şifreleme anahtarını yükle. Bu anahtar ÇOK GİZLİ kalmalıdır.
# Eğer .env'de yoksa, yeni bir anahtar oluştur (sadece ilk kurulumda).
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    # Bu anahtarı .env dosyasına manuel olarak eklemeniz önerilir.
    print(f"Yeni Şifreleme Anahtarı Oluşturuldu: {ENCRYPTION_KEY}\nLütfen bunu .env dosyanıza ENCRYPTION_KEY olarak ekleyin.")

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

def encrypt_credential(data: str) -> str:
    """Verilen metni şifreler."""
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_credential(encrypted_data: str) -> str:
    """Şifrelenmiş metni çözer."""
    return cipher_suite.decrypt(encrypted_data.encode()).decode()