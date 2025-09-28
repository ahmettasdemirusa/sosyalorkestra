from flask import Flask, request, redirect, session, send_from_directory
import os
from dotenv import load_dotenv
import requests
import database
import tweepy
import base64
import hashlib
import hmac
import random
import json
import openai
from datetime import datetime

from flask import make_response
from pdf_utils import create_analytics_pdf
from ngrok_utils import get_ngrok_url
from pytrends.request import TrendReq
# .env dosyasındaki çevre değişkenlerini yükle
load_dotenv()
database.init_db()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "varsayilan-cok-guvensiz-anahtar")

# ngrok URL'sini dinamik olarak al. Eğer ngrok çalışmıyorsa .env'den okur.
BACKEND_URL = get_ngrok_url()
print(f"🔗 Backend URL'si şu şekilde ayarlandı: {BACKEND_URL}")

# --- Statik Sayfalar (Gizlilik Politikası ve Hizmet Şartları) ---

@app.route('/privacy-policy')
def privacy_policy():
    # Not: Bu metinler sadece birer taslaktır. Yasal geçerlilik için bir hukuk danışmanına başvurmanız önerilir.
    return """
    <h1>Gizlilik Politikası</h1>
    <p>Son Güncelleme: 24 Mayıs 2024</p>
    <p>Sosyal Orkestra ("biz", "bize", veya "bizim") olarak, gizliliğinize önem veriyoruz.</p>
    <p>Bu gizlilik politikası, hizmetimizi kullandığınızda bilgilerinizi nasıl topladığımızı, kullandığımızı ve paylaştığımızı açıklar.</p>
    <h2>Topladığımız Bilgiler</h2>
    <p>Kullanıcı kaydı sırasında sağladığınız kullanıcı adı ve şifrelenmiş parola gibi kişisel bilgileri toplarız.</p>
    <p>Uygulamamıza bağladığınız sosyal medya hesaplarından (Facebook, Instagram, vb.) gelen verileri, yalnızca sizin adınıza gönderi paylaşmak ve analizleri göstermek amacıyla kullanırız. Bu veriler, ilgili platformların API'leri aracılığıyla güvenli bir şekilde alınır ve erişim anahtarlarınız (access token) veritabanımızda saklanır.</p>
    <h2>Bilgilerin Paylaşımı</h2>
    <p>Yasal zorunluluklar dışında kişisel bilgilerinizi üçüncü taraflarla paylaşmayız.</p>
    <p>Daha fazla bilgi için lütfen bizimle iletişime geçin: [E-posta Adresiniz]</p>
    """

@app.route('/terms-of-service')
def terms_of_service():
    # Not: Bu metinler sadece birer taslaktır. Yasal geçerlilik için bir hukuk danışmanına başvurmanız önerilir.
    return """
    <h1>Hizmet Şartları</h1>
    <p>Son Güncelleme: 24 Mayıs 2024</p>
    <p>Lütfen Sosyal Orkestra hizmetini kullanmadan önce bu hizmet şartlarını dikkatlice okuyun.</p>
    <h2>Hesaplar</h2>
    <p>Hizmetimizi kullanmak için bir hesap oluşturduğunuzda, bize doğru, eksiksiz ve güncel bilgiler vermelisiniz. Bunu yapmamanız, Şartların ihlali anlamına gelir ve hizmetimizdeki hesabınızın derhal feshedilmesine neden olabilir.</p>
    <h2>Sorumluluk</h2>
    <p>Uygulamamız, sosyal medya platformlarının API'lerini kullanarak çalışır. Bu platformların hizmet şartlarındaki veya API'lerindeki değişikliklerden kaynaklanabilecek hizmet kesintilerinden sorumlu değiliz.</p>
    <p>Daha fazla bilgi için lütfen bizimle iletişime geçin: [E-posta Adresiniz]</p>
    """

# --- Yönlendirme Fonksiyonları ---

@app.route('/login/<platform_name>')
def login_redirect(platform_name):
    user_id = request.args.get('user_id')
    if not user_id:
        return "Hata: Kullanıcı kimliği belirtilmedi.", 400
    brand_id = request.args.get('brand_id') # brand_id'yi de al
    session['user_id'] = user_id
    session['brand_id'] = brand_id # brand_id'yi session'a kaydet

    if platform_name == 'facebook':
        return facebook_login()
    elif platform_name == 'instagram':
        return instagram_login()
    elif platform_name == 'x':
        return twitter_login()
    elif platform_name == 'linkedin':
        return linkedin_login()
    elif platform_name == 'pinterest':
        return pinterest_login()
    elif platform_name == 'google my business':
        return google_my_business_login()
    else:
        return f"{platform_name.capitalize()} için bağlantı henüz desteklenmiyor.", 404

# --- Platforma Özel Fonksiyonlar ---

def facebook_login():
    app_id = os.getenv("FACEBOOK_APP_ID")
    redirect_uri = f"{BACKEND_URL}/callback/facebook"
    scope = "pages_show_list,pages_manage_posts,pages_read_engagement,read_insights"
    dialog_url = f"https://www.facebook.com/v19.0/dialog/oauth?client_id={app_id}&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(dialog_url)

def instagram_login():
    app_id = os.getenv("FACEBOOK_APP_ID")
    redirect_uri = f"{BACKEND_URL}/callback/instagram"
    scope = "pages_show_list,pages_read_engagement,instagram_basic,instagram_content_publish,instagram_manage_insights"
    dialog_url = f"https://www.facebook.com/v19.0/dialog/oauth?client_id={app_id}&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(dialog_url)

def twitter_login():
    callback_url = f"{BACKEND_URL}/callback/x"
    auth = tweepy.OAuth1UserHandler(os.getenv("TWITTER_API_KEY"), os.getenv("TWITTER_API_SECRET_KEY"), callback=callback_url)
    redirect_url = auth.get_authorization_url()
    session['request_token'] = auth.request_token
    return redirect(redirect_url)

def linkedin_login():
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    redirect_uri = f"{BACKEND_URL}/callback/linkedin"
    scope = "profile%20email%20w_member_social%20openid" # URL-encoded scope
    dialog_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(dialog_url)

def pinterest_login():
    app_id = os.getenv("PINTEREST_APP_ID")
    redirect_uri = f"{BACKEND_URL}/callback/pinterest"
    scope = "boards:read,pins:read,pins:write,user_accounts:read"
    dialog_url = f"https://www.pinterest.com/oauth/?client_id={app_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}"
    return redirect(dialog_url)

def google_my_business_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = f"{BACKEND_URL}/callback/google_my_business"
    # access_type=offline refresh_token almak için gereklidir.
    scope = "https://www.googleapis.com/auth/business.manage"
    dialog_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&access_type=offline&prompt=consent"
    return redirect(dialog_url)

# --- Callback (Geri Arama) Fonksiyonları ---

@app.route('/callback/<platform_name>')
def callback_handler(platform_name):
    if platform_name == 'facebook':
        return handle_facebook_callback()
    elif platform_name == 'instagram':
        return handle_instagram_callback()
    elif platform_name == 'x':
        return handle_twitter_callback()
    elif platform_name == 'linkedin':
        return handle_linkedin_callback()
    elif platform_name == 'pinterest':
        return handle_pinterest_callback()
    elif platform_name == 'google_my_business':
        return handle_google_my_business_callback()
    else:
        return "Bilinmeyen callback.", 404

def handle_facebook_callback():
    auth_code = request.args.get('code')
    if not auth_code: return "Hata: Yetki kodu alınamadı.", 400
    
    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'redirect_uri': f"{BACKEND_URL}/callback/facebook",
        'client_secret': os.getenv("FACEBOOK_APP_SECRET"),
        'code': auth_code
    }
    response = requests.get(token_url, params=params)
    access_token = response.json().get('access_token')
    if not access_token: return "Hata: Access Token alınamadı.", 400

    pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}"
    accounts = requests.get(pages_url).json().get('data', [])
    if not accounts: return "Hata: Yönettiğiniz Facebook sayfası bulunamadı.", 400

    user_id = session.get('user_id')
    if not user_id: return "Hata: Oturum hatası.", 400

    for account in accounts:
        brand_id = session.get('brand_id')
        database.add_connected_account(user_id, brand_id, 'Facebook', account['id'], account['name'], account['access_token'])
    
    return "Başarılı! Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."

def handle_instagram_callback():
    auth_code = request.args.get('code')
    if not auth_code: return "Hata: Yetki kodu alınamadı.", 400

    token_url = "https://graph.facebook.com/v19.0/oauth/access_token"
    params = {
        'client_id': os.getenv("FACEBOOK_APP_ID"),
        'redirect_uri': f"{BACKEND_URL}/callback/instagram",
        'client_secret': os.getenv("FACEBOOK_APP_SECRET"),
        'code': auth_code
    }
    response = requests.get(token_url, params=params)
    access_token = response.json().get('access_token')
    if not access_token: return "Hata: Access Token alınamadı.", 400

    pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={access_token}"
    fb_pages = requests.get(pages_url).json().get('data', [])
    if not fb_pages: return "Hata: Yönettiğiniz Facebook sayfası bulunamadı.", 400

    user_id = session.get('user_id')
    if not user_id: return "Hata: Oturum hatası.", 400
    brand_id = session.get('brand_id')
    if not brand_id: return "Hata: Marka kimliği bulunamadı.", 400

    for page in fb_pages:
        insta_url = f"https://graph.facebook.com/v19.0/{page['id']}?fields=instagram_business_account&access_token={access_token}"
        insta_response = requests.get(insta_url).json()
        if 'instagram_business_account' in insta_response:
            ig_account = insta_response['instagram_business_account']
            database.add_connected_account(user_id, brand_id, 'Instagram', ig_account['id'], page['name'], access_token)

    return "Başarılı! Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."

def handle_twitter_callback():
    oauth_verifier = request.args.get('oauth_verifier')
    request_token = session.pop('request_token', None)
    user_id = session.get('user_id')
    brand_id = session.get('brand_id')
    if not brand_id: return "Hata: Marka kimliği bulunamadı.", 400
    if not all([oauth_verifier, request_token, user_id]): return "Hata: Twitter bilgileri eksik.", 400

    auth = tweepy.OAuth1UserHandler(os.getenv("TWITTER_API_KEY"), os.getenv("TWITTER_API_SECRET_KEY"))
    auth.request_token = request_token
    
    try:
        access_token, access_token_secret = auth.get_access_token(oauth_verifier)
        client = tweepy.Client(consumer_key=os.getenv("TWITTER_API_KEY"), consumer_secret=os.getenv("TWITTER_API_SECRET_KEY"),
                               access_token=access_token, access_token_secret=access_token_secret)
        user_info = client.get_me(user_fields=["id", "username"]).data
        full_token = f"{access_token}::{access_token_secret}"
        database.add_connected_account(user_id, brand_id, 'X (Twitter)', user_info.id, user_info.username, full_token)
        return "Başarılı! Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."
    except Exception as e:
        return f"Twitter Access Token alınırken hata: {e}", 500

def handle_linkedin_callback():
    auth_code = request.args.get('code')
    if not auth_code: return "Hata: LinkedIn yetki kodu alınamadı.", 400

    user_id = session.get('user_id')
    brand_id = session.get('brand_id')
    if not brand_id: return "Hata: Marka kimliği bulunamadı.", 400
    if not user_id: return "Hata: Oturum hatası.", 400

    # Access Token al
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    params = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': f"{BACKEND_URL}/callback/linkedin",
        'client_id': os.getenv("LINKEDIN_CLIENT_ID"),
        'client_secret': os.getenv("LINKEDIN_CLIENT_SECRET")
    }
    response = requests.post(token_url, data=params)
    if response.status_code != 200:
        return f"Hata: LinkedIn Access Token alınamadı. {response.text}", 400
    
    access_token = response.json().get('access_token')

    # Kullanıcı bilgilerini al
    profile_url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(profile_url, headers=headers).json()
    
    linkedin_user_urn = profile_response.get('sub') # 'sub' alanı kullanıcı URN'sini içerir
    user_name = f"{profile_response.get('given_name', '')} {profile_response.get('family_name', '')}"

    database.add_connected_account(user_id, brand_id, 'LinkedIn', linkedin_user_urn, user_name, access_token)
    return "Başarılı! LinkedIn hesabınız bağlandı. Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."

def handle_pinterest_callback():
    auth_code = request.args.get('code')
    if not auth_code: return "Hata: Pinterest yetki kodu alınamadı.", 400

    user_id = session.get('user_id')
    brand_id = session.get('brand_id')
    if not brand_id: return "Hata: Marka kimliği bulunamadı.", 400
    if not user_id: return "Hata: Oturum hatası.", 400

    # Access Token al
    token_url = "https://api.pinterest.com/v5/oauth/token"
    app_id = os.getenv("PINTEREST_APP_ID")
    app_secret = os.getenv("PINTEREST_APP_SECRET")
    auth_header = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    headers = {'Authorization': f'Basic {auth_header}'}
    payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': f"{BACKEND_URL}/callback/pinterest"
    }
    response = requests.post(token_url, headers=headers, data=payload)
    if response.status_code != 200:
        return f"Hata: Pinterest Access Token alınamadı. {response.text}", 400
    
    token_data = response.json()
    access_token = token_data.get('access_token')

    # Kullanıcı bilgilerini al
    user_info_url = "https://api.pinterest.com/v5/user_account"
    user_headers = {'Authorization': f'Bearer {access_token}'}
    user_info_response = requests.get(user_info_url, headers=user_headers).json()

    database.add_connected_account(user_id, brand_id, 'Pinterest', user_info_response.get('username'), user_info_response.get('username'), access_token)
    return "Başarılı! Pinterest hesabınız bağlandı. Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."

def handle_google_my_business_callback():
    auth_code = request.args.get('code')
    if not auth_code: return "Hata: Google yetki kodu alınamadı.", 400

    user_id = session.get('user_id')
    brand_id = session.get('brand_id')
    if not brand_id: return "Hata: Marka kimliği bulunamadı.", 400
    if not user_id: return "Hata: Oturum hatası.", 400

    # Access Token ve Refresh Token al
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        'code': auth_code,
        'client_id': os.getenv("GOOGLE_CLIENT_ID"),
        'client_secret': os.getenv("GOOGLE_CLIENT_SECRET"),
        'redirect_uri': f"{BACKEND_URL}/callback/google_my_business",
        'grant_type': 'authorization_code'
    }
    response = requests.post(token_url, data=payload).json()
    access_token = response.get('access_token')
    refresh_token = response.get('refresh_token') # Refresh token'ı saklamak önemlidir.

    if not access_token:
        return "Hata: Google Access Token alınamadı.", 400

    # Kullanıcının yönettiği GMB hesaplarını listele
    headers = {'Authorization': f'Bearer {access_token}'}
    accounts_url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    accounts_response = requests.get(accounts_url, headers=headers).json()
    
    gmb_accounts = accounts_response.get('accounts', [])
    if not gmb_accounts:
        return "Yönettiğiniz bir Google My Business hesabı bulunamadı.", 400

    # Her bir hesaptaki konumları listele
    for account in gmb_accounts:
        locations_url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account['name']}/locations?readMask=name,title"
        locations_response = requests.get(locations_url, headers=headers).json()
        
        locations = locations_response.get('locations', [])
        for location in locations:
            location_id = location['name'] # "locations/12345" formatında
            location_name = location['title']
            
            # Refresh token'ı access token ile birlikte saklayalım
            full_token = f"{access_token}::{refresh_token}"
            
            database.add_connected_account(user_id, brand_id, 'Google My Business', location_id, location_name, full_token)

    return "Başarılı! Google My Business konumlarınız bağlandı. Bu pencereyi kapatıp dashboard'u yenileyebilirsiniz."



# --- Facebook Veri Silme Geri Çağrısı (Callback) ---

def parse_signed_request(signed_request, secret):
    """Facebook'tan gelen signed_request'i doğrular ve veriyi çözer."""
    try:
        encoded_sig, payload = signed_request.split('.', 1)

        # İmza ve payload'u decode et
        decoded_sig = base64.urlsafe_b64decode(encoded_sig + "=" * (4 - len(encoded_sig) % 4))
        decoded_payload = base64.urlsafe_b64decode(payload + "=" * (4 - len(payload) % 4))
        data = json.loads(decoded_payload)

        # İmzanın HMAC-SHA256 ile uyuşup uyuşmadığını kontrol et
        if data.get('algorithm').upper() != 'HMAC-SHA256':
            return None

        expected_sig = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()

        if hmac.compare_digest(expected_sig, decoded_sig):
            return data
        else:
            return None
    except Exception as e:
        print(f"Hata: signed_request ayrıştırılamadı - {e}")
        return None

@app.route('/facebook/data-deletion', methods=['POST'])
def facebook_data_deletion_callback():
    """Facebook'tan gelen veri silme taleplerini işler."""
    signed_request = request.form.get('signed_request')
    if not signed_request:
        return "Hatalı istek.", 400

    app_secret = os.getenv("FACEBOOK_APP_SECRET")
    data = parse_signed_request(signed_request, app_secret)

    if not data:
        return "Geçersiz signed_request.", 400

    platform_user_id = data.get('user_id')
    database.delete_data_by_platform_id('Facebook', platform_user_id)

    # Facebook'a işlemin başarılı olduğunu ve takip numarasını bildir.
    confirmation_code = f"user_{platform_user_id}_deleted"
    return json.dumps({'url': f"{BACKEND_URL}/status/{confirmation_code}", 'confirmation_code': confirmation_code})

@app.route('/webhook/facebook', methods=['GET', 'POST'])
def facebook_webhook():
    """Facebook Webhook'larını doğrular ve gelen verileri işler."""
    if request.method == 'GET':
        # Webhook doğrulama isteği
        verify_token = os.getenv("FACEBOOK_WEBHOOK_VERIFY_TOKEN")
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == verify_token:
            print("✅ Webhook doğrulandı.")
            return request.args.get('hub.challenge'), 200
        else:
            print("❌ Webhook doğrulaması başarısız.")
            return 'Doğrulama hatası', 403

    if request.method == 'POST':
        # Webhook'tan gelen olay verisi
        data = request.json
        print("📬 Webhook'tan yeni veri alındı:", json.dumps(data, indent=2))

        if data.get('object') == 'page':
            for entry in data.get('entry', []):
                page_id = entry.get('id')
                for change in entry.get('changes', []):
                    if change.get('field') == 'feed' and change.get('value', {}).get('item') == 'comment':
                        comment_data = change.get('value')
                        
                        # Bu page_id'ye sahip hesabı veritabanında bul
                        account = database.get_account_by_platform_id(page_id)
                        if account:
                            user_id = account['user_id']
                            connected_account_id = account['id']
                            access_token = account['access_token']

                            # Yorum verilerini işle
                            post_id = comment_data.get('post_id')
                            comment_id = comment_data.get('comment_id')
                            sender_name = comment_data.get('from', {}).get('name')
                            sender_id = comment_data.get('from', {}).get('id')
                            message = comment_data.get('message', '').lower()
                            created_time = datetime.fromtimestamp(comment_data.get('created_time')).isoformat()

                            # Moderasyon kurallarını kontrol et
                            rules = database.get_user_moderation_rules(account['brand_id'])
                            is_hidden = False
                            is_flagged = False

                            for rule in rules:
                                if rule['keyword'] in message:
                                    if rule['action'] == 'hide':
                                        try:
                                            hide_url = f"https://graph.facebook.com/v19.0/{comment_id}"
                                            payload = {'is_hidden': 'true', 'access_token': access_token}
                                            requests.post(hide_url, data=payload)
                                            is_hidden = True
                                            print(f"✅ Yorum '{comment_id}' otomatik olarak gizlendi.")
                                        except Exception as e:
                                            print(f"❌ Yorum gizlenirken hata: {e}")
                                    elif rule['action'] == 'flag':
                                        is_flagged = True
                                    
                                    # Kural eşleşti, döngüden çık
                                    break
                            
                            # Görüşmeyi ve mesajı veritabanına ekle
                            snippet = f"{sender_name}: {comment_data.get('message', '')[:30]}..."
                            conversation_id_db = database.upsert_conversation(user_id, account['brand_id'], connected_account_id, post_id, snippet, created_time)
                            database.add_message(conversation_id_db, comment_id, sender_name, sender_id, comment_data.get('message', ''), created_time, is_hidden=is_hidden, is_flagged=is_flagged)
                            print(f"✅ Yeni yorum veritabanına eklendi: Post ID {post_id}")

        return 'Event Received', 200



# --- Statik Dosya Sunucusu (Yüklenen görseller için) ---
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """'uploads' klasöründeki dosyaları sunar."""
    return send_from_directory('uploads', filename)

# --- Social Inbox API ---

@app.route('/inbox/sync/<platform_name>')
def sync_inbox(platform_name):
    user_id = session.get('user_id')
    brand_id = session.get('brand_id')
    if not user_id:
        return "Hata: Oturum bulunamadı.", 401

    if platform_name.lower() == 'facebook' and brand_id:
        accounts = database.get_user_accounts(user_id, 'Facebook')
        for acc in accounts:
            # Sayfanın son gönderilerini al
            posts_url = f"https://graph.facebook.com/v19.0/{acc['account_id']}/posts?limit=5&access_token={acc['access_token']}"
            posts_response = requests.get(posts_url).json()
            
            if 'data' not in posts_response: continue

            for post in posts_response['data']:
                post_id = post['id']
                # Gönderinin yorumlarını al
                comments_url = f"https://graph.facebook.com/v19.0/{post_id}/comments?fields=from,message,created_time&access_token={acc['access_token']}"
                comments_response = requests.get(comments_url).json()

                if 'data' in comments_response and comments_response['data']:
                    # En son yorumu snippet olarak kullan
                    last_comment = comments_response['data'][0]
                    snippet = f"{last_comment['from']['name']}: {last_comment['message'][:30]}..."
                    last_updated = last_comment['created_time']

                    # Görüşmeyi veritabanına ekle/güncelle
                    conversation_id_db = database.upsert_conversation(user_id, brand_id, acc['id'], post_id, snippet, last_updated)

                    # Tüm yorumları mesaj olarak ekle
                    for comment in comments_response['data']:
                        database.add_message(conversation_id_db, comment['id'], comment['from']['name'], comment['from']['id'], comment['message'], comment['created_time'])

        return "Facebook yorumları başarıyla senkronize edildi."
    else:
        return f"{platform_name} için senkronizasyon henüz desteklenmiyor.", 404

@app.route('/inbox/reply', methods=['POST'])
def reply_to_conversation():
    user_id = session.get('user_id')
    if not user_id:
        return "Hata: Oturum bulunamadı.", 401

    data = request.json
    conversation_id = data.get('conversation_id')
    reply_text = data.get('reply_text')

    if not conversation_id or not reply_text:
        return "Eksik bilgi: conversation_id ve reply_text gereklidir.", 400

    # Görüşme detaylarını ve token'ı al
    conv_details = database.get_conversation_details(conversation_id)
    if not conv_details:
        return "Görüşme bulunamadı.", 404

    post_id = conv_details['platform_conversation_id']
    access_token = conv_details['access_token']

    # Facebook API'sine yorumu gönder
    reply_url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
    payload = {'message': reply_text, 'access_token': access_token}
    response = requests.post(reply_url, data=payload).json()

    if 'id' in response:
        # Başarılı olursa, gönderilen yanıtı kendi veritabanımıza da ekle
        # 'me' endpoint'i ile kendi kullanıcı adımızı alalım
        me_url = f"https://graph.facebook.com/v19.0/me?access_token={access_token}"
        me_response = requests.get(me_url).json()
        sender_name = me_response.get('name', 'Sosyal Orkestra')
        database.add_message(conversation_id, response['id'], sender_name, me_response.get('id'), reply_text, datetime.now().isoformat())
        return {"status": "success", "message": "Yanıt başarıyla gönderildi."}
    else:
        return {"status": "error", "message": f"Yanıt gönderilemedi: {response.get('error', {}).get('message')}"}, 500

@app.route('/dashboard/sync')
def sync_dashboard_data():
    """Tüm bağlı hesaplardan temel metrikleri (takipçi sayısı vb.) senkronize eder."""
    brand_id = session.get('brand_id')
    if not brand_id:
        return "Hata: Marka seçilmedi.", 400


    accounts = database.get_user_accounts(brand_id)
    if not accounts:
        return "Senkronize edilecek hesap bulunamadı.", 200

    for acc in accounts:
        try:
            follower_count = 0
            engagement = 0
            reach = 0

            if acc['platform_name'] == 'Facebook':
                url = f"https://graph.facebook.com/v19.0/{acc['account_id']}?fields=fan_count&access_token={acc['access_token']}"
                data = requests.get(url).json()
                follower_count = data.get('fan_count', 0)

                # Etkileşim ve Erişim verilerini çek (son 28 gün)
                insights_url = f"https://graph.facebook.com/v19.0/{acc['account_id']}/insights?metric=page_post_engagements,page_impressions_unique&period=day&date_preset=last_28d&access_token={acc['access_token']}"
                insights_data = requests.get(insights_url).json().get('data', [])
                for insight in insights_data:
                    if insight['name'] == 'page_post_engagements':
                        engagement = sum(v.get('value', 0) for v in insight.get('values', []))
                    if insight['name'] == 'page_impressions_unique':
                        reach = sum(v.get('value', 0) for v in insight.get('values', []))

            elif acc['platform_name'] == 'Instagram':
                url = f"https://graph.facebook.com/v19.0/{acc['account_id']}?fields=followers_count&access_token={acc['access_token']}"
                data = requests.get(url).json()
                follower_count = data.get('followers_count', 0)

                # Etkileşim ve Erişim verilerini çek (son 28 gün)
                insights_url = f"https://graph.facebook.com/v19.0/{acc['account_id']}/insights?metric=engagement,reach&period=day&date_preset=last_28d&access_token={acc['access_token']}"
                insights_data = requests.get(insights_url).json().get('data', [])
                # Instagram API'si bu metrikleri toplu olarak verebilir

            elif acc['platform_name'] == 'X (Twitter)':
                token_parts = acc['access_token'].split('::')
                if len(token_parts) == 2:
                    access_token, access_token_secret = token_parts
                    client = tweepy.Client(
                        consumer_key=os.getenv("TWITTER_API_KEY"), 
                        consumer_secret=os.getenv("TWITTER_API_SECRET_KEY"),
                        access_token=access_token, 
                        access_token_secret=access_token_secret
                    )
                    user_data = client.get_me(user_fields=["public_metrics"]).data
                    follower_count = user_data.public_metrics.get('followers_count', 0)

            if follower_count > 0:
                database.update_follower_count(acc['id'], follower_count)
            database.update_account_metrics(acc['id'], engagement=engagement, reach=reach)

        except Exception as e:
            print(f"Hata: {acc['account_name']} hesabı senkronize edilirken sorun oluştu: {e}")
            continue # Bir hesapta hata olursa diğerleriyle devam et

    return "Veriler başarıyla senkronize edildi."

@app.route('/inbox/like', methods=['POST'])
def like_comment():
    """Gelen bir yorumu beğenmek için kullanılır."""
    user_id = session.get('user_id')
    if not user_id:
        return "Hata: Oturum bulunamadı.", 401

    data = request.json
    conversation_id = data.get('conversation_id')
    platform_message_id = data.get('platform_message_id')

    if not conversation_id or not platform_message_id:
        return "Eksik bilgi: conversation_id ve platform_message_id gereklidir.", 400

    # Görüşme detaylarını ve token'ı al
    conv_details = database.get_conversation_details(conversation_id)
    if not conv_details:
        return "Görüşme bulunamadı.", 404

    access_token = conv_details['access_token']

    # Facebook API'sine beğenme isteği gönder
    like_url = f"https://graph.facebook.com/v19.0/{platform_message_id}/likes"
    payload = {'access_token': access_token}
    response = requests.post(like_url, data=payload).json()

    if response.get('success'):
        return {"status": "success", "message": "Yorum başarıyla beğenildi."}
    else:
        return {"status": "error", "message": f"Yorum beğenilemedi: {response.get('error', {}).get('message')}"}, 500

@app.route('/analytics/best-time')
def get_best_time_to_post():
    """Kullanıcının geçmiş gönderi performansına göre en iyi paylaşım zamanlarını analiz eder."""
    brand_id = session.get('brand_id')
    if not brand_id:
        return "Hata: Marka seçilmedi.", 400


    performance_data = database.get_post_performance_data(brand_id)
    if not performance_data:
        return {"error": "Analiz için yeterli gönderi verisi bulunmuyor."}, 404

    # Veriyi gün ve saate göre gruplandırmak için bir yapı oluşturalım
    # Haftanın günleri (Pazartesi=0, Pazar=6)
    heatmap_data = {day: {hour: {'total_engagement': 0, 'count': 0} for hour in range(24)} for day in range(7)}

    for post in performance_data:
        from datetime import datetime
        post_time = datetime.fromisoformat(post['time'])
        day_of_week = post_time.weekday()
        hour_of_day = post_time.hour
        
        heatmap_data[day_of_week][hour_of_day]['total_engagement'] += post['engagement']
        heatmap_data[day_of_week][hour_of_day]['count'] += 1

    # Ortalama etkileşimi hesapla
    results = []
    for day, hours in heatmap_data.items():
        for hour, data in hours.items():
            if data['count'] > 0:
                avg_engagement = data['total_engagement'] / data['count']
                results.append({'day': day, 'hour': hour, 'avg_engagement': avg_engagement})

    # Sonuçları en yüksek etkileşimden en düşüğe sırala
    sorted_results = sorted(results, key=lambda x: x['avg_engagement'], reverse=True)
    
    return json.dumps(sorted_results)

@app.route('/competitors/sync')
def sync_competitors_data():
    """Tüm rakiplerin verilerini senkronize eder."""
    brand_id = session.get('brand_id')
    if not brand_id:
        return "Hata: Marka seçilmedi.", 400


    # Şimdilik sadece Instagram destekleniyor
    competitors = database.get_competitors(brand_id, 'Instagram')
    if not competitors:
        return "İzlenecek rakip bulunamadı.", 200

    for comp in competitors:
        try:
            # --- SİMÜLASYON ---
            # Gerçek dünyada, burada bir üçüncü parti API'ye veya scraping servisine istek atılır.
            # Örnek: response = requests.get(f"https://some-insta-api.com/user/{comp['competitor_username']}")
            # follower_count = response.json()['follower_count']
            # Biz burada kullanıcı adına göre tahmin edilebilir ama rastgele bir sayı üretiyoruz.
            base_followers = 10000 + (abs(hash(comp['competitor_username'])) % 90000)
            daily_fluctuation = random.randint(-100, 300)
            follower_count = base_followers + daily_fluctuation
            # --- SİMÜLASYON SONU ---

            database.add_competitor_snapshot(comp['id'], follower_count)
            print(f"✅ Rakip '{comp['competitor_username']}' senkronize edildi. Takipçi: {follower_count}")
        except Exception as e:
            print(f"❌ Rakip '{comp['competitor_username']}' senkronize edilirken hata: {e}")
            continue

    return "Rakip verileri başarıyla senkronize edildi."

@app.route('/trends/google')
def get_google_trends():
    """Google Trends'den güncel arama trendlerini çeker."""
    try:
        pytrends = TrendReq(hl='tr-TR', tz=360)
        # Türkiye için günlük arama trendlerini al
        trending_df = pytrends.trending_searches(pn='turkey')
        # DataFrame'i JSON formatına çevir
        return trending_df.to_json(orient='records')
    except Exception as e:
        print(f"Google Trends verileri alınırken hata: {e}")
        # Hata durumunda veya API'ye ulaşılamadığında örnek veri döndür
        fallback_data = [{"0": "Yapay Zeka"}, {"0": "Seçim Sonuçları"}, {"0": "Yeni Dizi"}]
        return json.dumps(fallback_data), 500

@app.route('/reports/export-pdf', methods=['POST'])
def export_report_as_pdf():
    """Analiz verilerini ve grafik yollarını alıp bir PDF oluşturur ve döndürür."""
    user_id = session.get('user_id')
    if not user_id:
        return "Hata: Oturum bulunamadı.", 401

    data = request.json
    analytics_data = data.get('analytics_data', {})
    chart_image_paths = data.get('chart_image_paths', {})

    pdf_content = create_analytics_pdf(analytics_data, chart_image_paths)

    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=SosyalOrkestra_Rapor.pdf'

    return response

@app.route('/images/search')
def search_stock_images():
    """Unsplash API'sini kullanarak stok görselleri arar."""
    query = request.args.get('query')
    if not query:
        return "Hata: Arama terimi belirtilmedi.", 400

    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    if not access_key or "BURAYA" in access_key:
        return "Hata: Unsplash API anahtarı yapılandırılmamış.", 500

    headers = {'Authorization': f'Client-ID {access_key}'}
    params = {'query': query, 'per_page': 12, 'orientation': 'squarish'}
    url = "https://api.unsplash.com/search/photos"

    try:
        response = requests.get(url, headers=headers, params=params).json()
        # Sadece gerekli bilgileri alıp frontend'e gönderelim
        results = [{'id': img['id'], 'url': img['urls']['small'], 'author': img['user']['name']} for img in response.get('results', [])]
        return json.dumps(results)
    except Exception as e:
        return f"Görsel aranırken hata oluştu: {e}", 500

@app.route('/pinterest/boards')
def get_pinterest_boards():
    """Kullanıcının Pinterest panolarını listeler."""
    account_id = request.args.get('account_id')
    if not account_id:
        return "Hesap ID'si belirtilmedi.", 400

    # Veritabanından hesabı ve token'ı bul
    account = database.get_account_by_id(account_id) # Bu fonksiyonun eklenmesi gerekebilir
    if not account or 'access_token' not in account:
        return "Hesap bulunamadı veya token geçersiz.", 404

    headers = {'Authorization': f'Bearer {account["access_token"]}'}
    boards_url = "https://api.pinterest.com/v5/boards"
    response = requests.get(boards_url, headers=headers).json()

    boards = [{'id': board['id'], 'name': board['name']} for board in response.get('items', [])]
    return json.dumps(boards)

@app.route('/ai/generate-alt-text', methods=['POST'])
def generate_alt_text_for_image():
    """Verilen bir görsel URL'si için yapay zeka kullanarak alt text oluşturur."""
    data = request.json
    image_url = data.get('image_url')

    if not image_url:
        return "Hata: Görsel URL'si belirtilmedi.", 400

    try:
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Bu görsel için, görme engelli bir kullanıcıya ekran okuyucunun okuyacağı, kısa ve açıklayıcı bir alternatif metin (alt text) yaz."},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
            max_tokens=100,
        )
        alt_text = response.choices[0].message.content
        return {"alt_text": alt_text}
    except Exception as e:
        return f"Alt text oluşturulurken hata oluştu: {e}", 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
