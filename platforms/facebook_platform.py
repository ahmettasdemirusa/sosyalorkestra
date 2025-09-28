from .base_platform import BasePlatform
import os
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.page import Page

class FacebookPlatform(BasePlatform):
    """
    Facebook platformu için özel işlemleri yöneten sınıf.
    BasePlatform şablonundan miras alır.
    """
    def __init__(self):
        super().__init__("Facebook")
        # Bu sınıf, her işlem için özel bir access_token alacak şekilde tasarlanmıştır.
        # Bu nedenle __init__ içinde genel bir token saklamıyoruz.

    def post(self, image_path: str, caption: str, access_token: str, page_id: str):
        """
        Belirli bir Facebook sayfasına, o sayfaya ait token ve ID'yi kullanarak gönderi paylaşır.
        """
        if not page_id or not access_token:
            raise ValueError("Gönderi paylaşımı için Facebook Sayfa ID'si veya Access Token belirtilmemiş.")

        # API'yi bu işleme özel token ile başlat
        FacebookAdsApi.init(access_token=access_token)
        
        page = Page(fbid=page_id)
        response = page.create_photo(params={'message': caption, 'source': open(image_path, 'rb')})
        print(f"✅ Facebook'ta gönderi başarıyla paylaşıldı: {caption[:30]}...")
        return response.get('post_id')