from .base_platform import BasePlatform
import requests
import json

class LinkedInPlatform(BasePlatform):
    """LinkedIn kişisel profilleri için işlemleri yöneten sınıf."""

    def __init__(self):
        super().__init__("LinkedIn")
        self.API_BASE_URL = "https://api.linkedin.com/v2"

    def post(self, caption: str, access_token: str, author_urn: str, **kwargs):
        """LinkedIn profiline metin tabanlı bir gönderi paylaşır."""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        post_data = {"author": author_urn, "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": caption}, "shareMediaCategory": "NONE"}}, "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}}
        response = requests.post(f"{self.API_BASE_URL}/ugcPosts", headers=headers, data=json.dumps(post_data))
        if response.status_code not in [200, 201]:
            raise Exception(f"LinkedIn gönderisi paylaşılamadı: {response.text}")
        print(f"✅ LinkedIn'de gönderi başarıyla paylaşıldı: {caption[:30]}...")
        return response.headers.get('x-restli-id')