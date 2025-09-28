from .base_platform import BasePlatform
import requests
import os
import json

class PinterestPlatform(BasePlatform):
    """Pinterest hesapları için işlemleri yöneten sınıf."""

    def __init__(self):
        super().__init__("Pinterest")
        self.API_BASE_URL = "https://api.pinterest.com/v5"

    def post(self, image_path: str, caption: str, access_token: str, board_id: str, backend_url: str, **kwargs):
        """Pinterest panosuna yeni bir Pin oluşturur."""
        if not board_id:
            raise ValueError("Pin oluşturmak için bir Pano ID'si gereklidir.")

        headers = {'Authorization': f'Bearer {access_token}'}
        
        # Şimdilik, görselin public bir URL'de olduğunu varsayıyoruz.
        image_url = f"{backend_url}/uploads/{os.path.basename(image_path)}"

        pin_data = {
            'board_id': board_id,
            'note': caption,
            'media_source': {'source_type': 'image_url', 'url': image_url}
        }
        response = requests.post(f"{self.API_BASE_URL}/pins", headers=headers, json=pin_data)
        if response.status_code not in [200, 201]:
            raise Exception(f"Pinterest Pin'i oluşturulamadı: {response.text}")
        
        print(f"✅ Pinterest'te Pin başarıyla oluşturuldu: {caption[:30]}...")
        return response.json().get('id')