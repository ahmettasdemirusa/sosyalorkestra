from .base_platform import BasePlatform
import requests
import time

class InstagramPlatform(BasePlatform):
    """Instagram Business hesapları için işlemleri yöneten sınıf."""

    def __init__(self):
        super().__init__("Instagram")
        self.BASE_URL = "https://graph.facebook.com/v19.0"

    def post(self, image_path: str, caption: str, access_token: str, ig_user_id: str, backend_url: str):
        """Instagram Business hesabına görsel ve metin gönderir."""
        # 1. Adım: Görseli yükle ve container ID'si al
        image_url = f"{backend_url}/uploads/{image_path.split('/')[-1]}" # Görselin public URL'i
        post_container_url = f"{self.BASE_URL}/{ig_user_id}/media"
        container_payload = {'image_url': image_url, 'caption': caption, 'access_token': access_token}
        container_response = requests.post(post_container_url, data=container_payload).json()
        if 'id' not in container_response:
            raise Exception(f"Instagram container oluşturulamadı: {container_response.get('error', {}).get('message')}")
        container_id = container_response['id']

        # 2. Adım: Container'ı kullanarak gönderiyi yayınla
        publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
        publish_payload = {'creation_id': container_id, 'access_token': access_token}
        publish_response = requests.post(publish_url, data=publish_payload).json()
        if 'id' not in publish_response:
            raise Exception(f"Instagram gönderisi yayınlanamadı: {publish_response.get('error', {}).get('message')}")
        print(f"✅ Instagram'da gönderi başarıyla paylaşıldı: {caption[:30]}...")
        return publish_response.get('id')

    def post_video(self, video_path: str, caption: str, access_token: str, ig_user_id: str):
        """Instagram Business hesabına video (Reel) gönderir."""
        # 1. Adım: Video yükleme oturumu başlat
        session_url = f"{self.BASE_URL}/{ig_user_id}/media"
        session_payload = {
            'media_type': 'VIDEO',
            'video_url': f"{os.getenv('BACKEND_URL')}/uploads/{os.path.basename(video_path)}",
            'caption': caption,
            'access_token': access_token
        }
        session_response = requests.post(session_url, data=session_payload).json()
        if 'id' not in session_response:
            raise Exception(f"Instagram video oturumu başlatılamadı: {session_response.get('error', {}).get('message')}")
        
        container_id = session_response['id']

        # 2. Adım: Yüklemenin tamamlanmasını bekle
        # API, videoyu arka planda işler. Bu işlem zaman alabilir.
        # Yükleme durumunu periyodik olarak kontrol etmeliyiz.
        status_url = f"{self.BASE_URL}/{container_id}"
        params = {'fields': 'status_code', 'access_token': access_token}
        
        for _ in range(20): # Maksimum 20 deneme (yaklaşık 2 dakika)
            status_response = requests.get(status_url, params=params).json()
            status_code = status_response.get('status_code')

            if status_code == 'FINISHED':
                break
            elif status_code == 'ERROR':
                raise Exception("Instagram video yüklemesi başarısız oldu.")
            
            time.sleep(6) # 6 saniye bekle ve tekrar kontrol et
        else:
            raise Exception("Instagram video yüklemesi zaman aşımına uğradı.")

        # 3. Adım: Yüklenen videoyu yayınla
        publish_url = f"{self.BASE_URL}/{ig_user_id}/media_publish"
        publish_payload = {'creation_id': container_id, 'access_token': access_token}
        publish_response = requests.post(publish_url, data=publish_payload).json()
        if 'id' not in publish_response:
            raise Exception(f"Instagram video yayınlanamadı: {publish_response.get('error', {}).get('message')}")
        
        print(f"✅ Instagram'da video (Reel) başarıyla paylaşıldı: {caption[:30]}...")
        return publish_response.get('id')