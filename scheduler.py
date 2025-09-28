import schedule
import time
import os
from dotenv import load_dotenv

import database
from platforms.facebook_platform import FacebookPlatform
from platforms.instagram_platform import InstagramPlatform
from platforms.linkedin_platform import LinkedInPlatform
from platforms.pinterest_platform import PinterestPlatform
from platforms.google_my_business_platform import GoogleMyBusinessPlatform
from ngrok_utils import get_ngrok_url
# Diğer platformlar eklendikçe buraya import edilecek

load_dotenv()

def check_and_post_due_posts():
    """Zamanı gelen gönderileri kontrol eder ve yayınlar."""
    # Her döngüde URL'yi dinamik olarak al
    backend_url = get_ngrok_url()
    print(f"🕒 Zamanlanmış gönderiler kontrol ediliyor... ({time.ctime()})")
    
    # Veritabanından zamanı gelmiş gönderileri al
    due_posts = database.get_due_posts()
    if not due_posts:
        print("⌛ Yayınlanacak gönderi bulunamadı.")
        return

    for post in due_posts:
        post_id = post['id']
        user_id = post['user_id']
        caption = post['caption']
        media_path = post['image_path']
        platform_name = post['platform_name']
        access_token = post['access_token']
        platform_account_id = post['platform_account_id']
        media_type = post.get('media_type', 'IMAGE')
        platform_specific_data = post.get('platform_specific_data')
        
        print(f"🚀 '{caption[:30]}...' başlıklı gönderi {platform_name} için yayınlanıyor...")
        
        try:
            platform_post_id = None
            if platform_name == "Facebook":
                # Facebook video yüklemesi de ayrı bir mantık gerektirir, şimdilik sadece resim
                if media_type == 'IMAGE':
                    platform = FacebookPlatform()
                    platform_post_id = platform.post(image_path=media_path, caption=caption, access_token=access_token, page_id=platform_account_id)
            
            elif platform_name == "Instagram":
                platform = InstagramPlatform()
                if media_type == 'VIDEO':
                    platform_post_id = platform.post_video(video_path=media_path, caption=caption, access_token=access_token, ig_user_id=platform_account_id)
                else: # IMAGE                    
                    platform_post_id = platform.post(image_path=media_path, caption=caption, access_token=access_token, ig_user_id=platform_account_id, backend_url=backend_url)

            elif platform_name == "LinkedIn":
                platform = LinkedInPlatform()
                platform_post_id = platform.post(caption=caption, access_token=access_token, author_urn=platform_account_id)

            elif platform_name == "Pinterest":
                import json
                specific_data = json.loads(platform_specific_data) if platform_specific_data else {}
                platform = PinterestPlatform()
                platform_post_id = platform.post(image_path=media_path, caption=caption, access_token=access_token, board_id=specific_data.get('board_id'), backend_url=backend_url)

            elif platform_name == "Google My Business":
                # Google'ın token'ı refresh token içerebilir, şimdilik ilk kısmı kullanıyoruz.
                gmb_access_token = access_token.split('::')[0]
                platform = GoogleMyBusinessPlatform()
                platform_post_id = platform.post(image_path=media_path, caption=caption, access_token=gmb_access_token, location_id=platform_account_id, backend_url=backend_url)
            
            # Gönderi başarılıysa durumu güncelle
            database.update_post_status(post_id, is_posted=1, status="Yayınlandı", platform_post_id=platform_post_id)
            success_message = f"'{caption[:20]}...' gönderiniz {platform_name} üzerinde başarıyla yayınlandı."
            database.add_notification(user_id, success_message, "success")
            print(f"✅ Gönderi başarıyla yayınlandı ve veritabanı güncellendi.")

        except Exception as e:
            # Store the full error message for better debugging in the history page
            error_message = str(e)
            print(f"❌ Gönderi yayınlanırken hata oluştu: {error_message}")
            # Hata durumunda durumu güncelle
            database.update_post_status(post_id, is_posted=1, status=error_message) # is_posted=1 to prevent retries
            fail_message = f"'{caption[:20]}...' gönderiniz yayınlanamadı. Detaylar için gönderi geçmişine bakın."
            database.add_notification(user_id, fail_message, "error")

if __name__ == "__main__":
    print("🗓️ Sosyal Orkestra Zamanlayıcı başlatıldı. Gönderiler her dakika kontrol edilecek.")
    schedule.every(1).minutes.do(check_and_post_due_posts)

    while True:
        schedule.run_pending()
        time.sleep(1)