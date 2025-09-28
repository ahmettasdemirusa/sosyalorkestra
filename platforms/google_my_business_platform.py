from .base_platform import BasePlatform
import requests
import os
import json

class GoogleMyBusinessPlatform(BasePlatform):
    """Google My Business (GMB) için işlemleri yöneten sınıf."""

    def __init__(self):
        super().__init__("Google My Business")
        self.API_BASE_URL = "https://mybusiness.googleapis.com/v4"
        self.MEDIA_UPLOAD_URL = "https://mybusiness.googleapis.com/v4"

    def post(self, image_path: str, caption: str, access_token: str, location_id: str, backend_url: str, **kwargs):
        """GMB konumuna yeni bir Local Post oluşturur."""
        
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        media_items = []

        # 1. Adım: Medyayı Yükle (varsa)
        if image_path and os.path.exists(image_path):
            media_headers = {'Authorization': f'Bearer {access_token}'}
            media_payload = {
                "mediaFormat": "PHOTO",
                "sourceUrl": f"{backend_url}/uploads/{os.path.basename(image_path)}"
            }
            # Konum ID'si 'locations/12345' formatında olmalı.
            upload_url = f"{self.API_BASE_URL}/{location_id}/media:startUpload"
            
            # Bu API akışı daha karmaşıktır ve doğrudan URL ile yüklemeyi desteklemeyebilir.
            # Gerçek bir implementasyonda, Google Cloud Storage'a yükleme gerekebilir.
            # Şimdilik, API'nin doğrudan URL'yi kabul ettiğini varsayıyoruz.
            # Bu kısım, GMB API'nin güncel dokümantasyonuna göre ayarlanmalıdır.
            # Basit bir medya objesi oluşturuyoruz.
            media_items.append({
                "mediaFormat": "PHOTO",
                "sourceUrl": f"{backend_url}/uploads/{os.path.basename(image_path)}"
            })

        # 2. Adım: Local Post Oluştur
        post_url = f"{self.API_BASE_URL}/{location_id}/localPosts"
        
        post_data = {
            "languageCode": "tr-TR",
            "summary": caption,
            "topicType": "STANDARD"
        }

        if media_items:
            post_data["media"] = media_items

        response = requests.post(post_url, headers=headers, json=post_data)

        if response.status_code not in [200, 201]:
            raise Exception(f"Google My Business gönderisi oluşturulamadı: {response.text}")

        print(f"✅ Google My Business'ta gönderi başarıyla oluşturuldu: {caption[:30]}...")
        return response.json().get('name') # e.g., "locations/12345/localPosts/67890"