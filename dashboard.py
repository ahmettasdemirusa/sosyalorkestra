import os
from datetime import datetime, timedelta
import uuid
from io import BytesIO

# --- Standart Kütüphaneler ---
import openai
import pandas as pd
import numpy as np
import pyotp
import qrcode
import requests

# --- Üçüncü Parti Kütüphaneler ---
import streamlit as st
from dotenv import load_dotenv
from PIL import Image
import plotly.graph_objects as go
from streamlit_calendar import calendar
from streamlit_cropper import st_cropper
from streamlit_option_menu import option_menu
from werkzeug.security import generate_password_hash, check_password_hash

# --- Yerel Uygulama Kütüphaneleri ---
import database
from platforms.base_platform import BasePlatform
from platforms.facebook_platform import FacebookPlatform
from platforms.instagram_platform import InstagramPlatform
from platforms.linkedin_platform import LinkedInPlatform
from ngrok_utils import get_ngrok_url
import json

# .env dosyasındaki çevre değişkenlerini yükle
load_dotenv()

# Veritabanını ve tabloları uygulamanın en başında başlat
database.init_db()

# ngrok URL'sini dinamik olarak al
BACKEND_URL = get_ngrok_url()
print(f"🔗 Arayüz, backend'e şu adresten erişecek: {BACKEND_URL}")

def set_page_config():
    """Uygulamanın sayfa yapılandırmasını ayarlar."""
    # Streamlit'in teması config.toml üzerinden veya bu fonksiyonla ayarlanır.
    # Dinamik tema değişimi için bu yaklaşım en iyisidir.
    # Ancak, set_page_config sadece bir kez çağrılabilir.
    # Bu yüzden, bu fonksiyonu sadece uygulamanın en başında çağırıyoruz.
    st.set_page_config(
        page_title="Sosyal Orkestra",
        page_icon="🎻",
        layout="wide",
        initial_sidebar_state="auto" # Kenar çubuğunu içeriğe göre yönet
    )

# --- Modern Stil ve Fontlar için CSS ---
# Bu CSS, hem aydınlık hem de karanlık modda iyi çalışacak şekilde geneldir.
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    html, body, [class*="st-"], [class*="css-"] {
        font-family: 'Poppins', sans-serif;
    }

    /* Kenar çubuğu (sidebar) stilini değiştirme */
    [data-testid="stSidebar"] {
        background-color: #1c1c2e; /* Koyu mor/mavi bir arka plan */
        transition: all 0.3s ease-in-out; /* Kenar çubuğu için yumuşak açılış/kapanış animasyonu */
    }

    /* Başlık stilleri */
    h1, h2 {
        font-weight: 600;
        color: #ececec;
    }

    /* Takvim stilleri */
    .fc-event {
        border-radius: 5px !important;
        border: none !important;
        padding: 3px 5px !important;
        font-size: 0.8em !important;
        font-weight: 500 !important;
        cursor: pointer;
    }
    .fc-daygrid-day.fc-day-other .fc-daygrid-day-top {
        opacity: 0.3; /* Sonraki/önceki ayın günlerini soluklaştır */
    }
</style>
""", unsafe_allow_html=True)

# --- Session State (Oturum Yönetimi) ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
if 'managing_account_id' not in st.session_state:
    st.session_state.managing_account_id = None
if 'calendar_edit_mode' not in st.session_state:
    st.session_state.calendar_edit_mode = False
if 'editing_post_id' not in st.session_state:
    st.session_state.editing_post_id = None
if 'mfa_required' not in st.session_state:
    st.session_state.mfa_required = False
if 'mfa_user' not in st.session_state:
    st.session_state.mfa_user = None
if 'theme' not in st.session_state:
    st.session_state.theme = None # Varsayılan tema
if 'new_post_date' not in st.session_state:
    st.session_state.new_post_date = None
if 'ai_generated_text' not in st.session_state:
    st.session_state.ai_generated_text = ""
if 'ai_generated_hashtags' not in st.session_state:
    st.session_state.ai_generated_hashtags = ""
if 'editing_image_bytes' not in st.session_state:
    st.session_state.editing_image_bytes = None
if 'editing_image_name' not in st.session_state:
    st.session_state.editing_image_name = None
if 'ai_target' not in st.session_state:
    st.session_state.ai_target = 'post' # 'post' or 'schedule'
if 'selected_conversation_id' not in st.session_state:
    st.session_state.selected_conversation_id = None
if 'selected_brand_id' not in st.session_state:
    st.session_state.selected_brand_id = None
if 'generated_alt_text' not in st.session_state:
    st.session_state.generated_alt_text = ""

def display_main_dashboard_page(user_id):
    """Tüm platformlardan gelen verileri özetleyen ana gösterge panelini oluşturur."""
    st.title("🎻 Ana Panel")
    st.write("Tüm sosyal medya kanallarınızdaki genel performansa bir bakış.")

    if st.button("Verileri Yenile", help="Tüm platformlardan en güncel takipçi sayılarını çeker."):
        with st.spinner("Veriler senkronize ediliyor... Bu işlem biraz sürebilir."):
            # Bu, backend'e bir API çağrısı yapacak.
            # Gerçek bir uygulamada, Streamlit'in cookie'lerini veya bir token'ı
            # backend'e göndermek için daha gelişmiş bir mekanizma gerekir.
            # Şimdilik, bu butonun mantığını doğrudan burada simüle ediyoruz.
            st.info("Senkronizasyon özelliği için backend entegrasyonu gereklidir. Şimdilik arayüzü gösteriyoruz.")
            # Gerçek çağrı şöyle olurdu: requests.get(f"{os.getenv('BACKEND_URL')}/dashboard/sync", cookies=...)
            st.rerun()

    # --- Veri Çekme (Gerçek ve Örnek Karışık) ---
    # Not: Gerçek API entegrasyonları yapıldığında bu bölüm gerçek verilerle doldurulacaktır.
    dashboard_data = database.get_main_dashboard_data(st.session_state.selected_brand_id)

    # --- Üst Düzey Metrikler (KPIs) ---
    kpi_cols = st.columns(4)
    # Veritabanından gelen gerçek takipçi sayısını kullan
    kpi_cols[0].metric("Toplam Takipçi", f"{dashboard_data['total_followers']:,}")
    kpi_cols[1].metric("Toplam Etkileşim (28 Gün)", f"{dashboard_data['total_engagement']:,}")
    kpi_cols[2].metric("Toplam Gönderi", f"{dashboard_data['total_posts']:,}")
    kpi_cols[3].metric("Toplam Erişim (28 Gün)", f"{dashboard_data['total_reach']:,}")

    st.divider()

    # --- Grafik Alanı ---
    chart_cols = st.columns([2, 1])
    with chart_cols[0]:
        st.subheader("Takipçi Artışı (Tüm Platformlar)")

        # Platforma göre filtreleme
        user_accounts = database.get_user_accounts(st.session_state.selected_brand_id)
        available_platforms = sorted(list(set(acc['platform_name'] for acc in user_accounts)))
        
        if not available_platforms:
            available_platforms = ["Instagram", "Facebook", "LinkedIn"] # Varsayılan

        selected_platforms = st.multiselect(
            "Gösterilecek Platformlar:",
            options=available_platforms,
            default=available_platforms
        )

        date_cols = st.columns(2)
        today = datetime.now().date()
        start_date = date_cols[0].date_input("Başlangıç Tarihi", today - timedelta(days=30))
        end_date = date_cols[1].date_input("Bitiş Tarihi", today)

        if start_date <= end_date:
            date_range = pd.date_range(start=start_date, end=end_date)
            # Sadece seçili platformlar için veri oluştur
            chart_data = pd.DataFrame(index=date_range)
            for platform in selected_platforms:
                # Her platform için rastgele ama tutarlı bir trend oluştur
                start_val = 10000 + (hash(platform) % 15000)
                end_val = start_val + (hash(platform) % 5000)
                chart_data[platform] = np.linspace(start_val, end_val, len(date_range)) + np.random.rand(len(date_range)) * (200 + (hash(platform) % 300))
            st.area_chart(chart_data.astype(int))
        else:
            st.error("Başlangıç tarihi, bitiş tarihinden sonra olamaz.")

    with chart_cols[1]:
        st.subheader("Platforma Göre Etkileşim")
        # Örnek Veri
        engagement_data = pd.DataFrame({
            "Platform": ["Instagram", "Facebook", "LinkedIn", "X (Twitter)"],
            "Etkileşim": [75000, 35000, 12000, 3400]
        })
        fig = go.Figure(data=[go.Pie(labels=engagement_data["Platform"], values=engagement_data["Etkileşim"], hole=.3)])
        fig.update_layout(height=300, margin={'l': 20, 'r': 20, 't': 30, 'b': 20}, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- Son Gönderiler ---
    st.subheader("Son Gönderiler")
    if not dashboard_data['recent_posts']:
        st.info("Henüz yayınlanmış bir gönderi yok.")
    else:
        post_cols = st.columns(len(dashboard_data['recent_posts']))
        for i, post in enumerate(dashboard_data['recent_posts']):
            with post_cols[i]:
                if os.path.exists(post['image_path']):
                    st.image(post['image_path'])
                st.caption(f"({post['platform_name']}) - {datetime.strptime(post['scheduled_time'], '%Y-%m-%d %H:%M:%S').strftime('%d %b')}")

def login_page():
    """Kullanıcı Giriş ve Kayıt Sayfasını oluşturur."""
    st.markdown("<h1 style='text-align: center;'>🎻 Sosyal Orkestra'ya Hoş Geldiniz</h1>", unsafe_allow_html=True)
    
    login_tab, signup_tab = st.tabs(["Giriş Yap", "Kayıt Ol"])

    def perform_login(user):
        """Kullanıcıyı giriş yapmış olarak ayarlar ve oturum ID'si oluşturur."""
        session_id = str(uuid.uuid4())
        database.update_user_session_id(user['id'], session_id)
        st.session_state.logged_in = True
        st.session_state.username = user['username']
        st.session_state.theme = user['theme']
        st.query_params["session_id"] = session_id

    if st.session_state.mfa_required:
        st.subheader("İki Aşamalı Doğrulama")
        with st.form("mfa_form"):
            otp_code = st.text_input("Authenticator uygulamanızdaki 6 haneli kodu girin:")
            mfa_submit = st.form_submit_button("Doğrula", type="primary")

            if mfa_submit:
                user = st.session_state.mfa_user
                totp = pyotp.TOTP(user['otp_secret'])
                if totp.verify(otp_code):
                    perform_login(user)
                else:
                    st.error("Doğrulama kodu yanlış.")
    else:
        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Kullanıcı Adı")
                password = st.text_input("Parola", type="password")
                login_button = st.form_submit_button("Giriş Yap", use_container_width=True, type="primary")

                if login_button:
                    user = database.get_user(username)
                    if user and check_password_hash(user['password_hash'], password):
                        if user['otp_enabled']:
                            st.session_state.mfa_required = True
                            st.session_state.mfa_user = user
                            st.rerun()
                        else:
                            perform_login(user)
                    else:
                        st.error("Kullanıcı adı veya parola hatalı.")

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Yeni Kullanıcı Adı")
            new_password = st.text_input("Yeni Parola", type="password")
            signup_button = st.form_submit_button("Kayıt Ol", use_container_width=True)

            if signup_button:
                if new_username and new_password:
                    hashed_password = generate_password_hash(new_password)
                    user_id = database.add_user(new_username, hashed_password)
                    if user_id:
                        # Yeni kullanıcı için otomatik olarak varsayılan bir takım oluştur.
                        default_team_name = f"{new_username}'s Takımı"
                        team_id = database.create_team(default_team_name, user_id)
                        # Kullanıcının başlangıç deneyimini basitleştirmek için otomatik bir varsayılan marka oluştur.
                        database.create_brand(team_id, "Varsayılan Markam")
                        st.success("Kayıt başarılı! Şimdi 'Giriş Yap' sekmesinden giriş yapabilirsiniz.")
                    else:
                        st.error("Bu kullanıcı adı zaten alınmış.")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")

def display_platform_dashboard(platform_name):
    """
    Seçilen platforma özel performans metriklerini ve kadranları gösterir.
    """
    st.divider()
    st.header(f"{platform_name} Performans Paneli (Örnek Veri)")

    # Platforma özel metrikleri tanımla
    if platform_name == "Instagram":
        metrics = {
            "gauge_title": "Etkileşim Oranı (%)", "gauge_value": 4.5, "gauge_max": 10,
            "delta_title": "Profil Ziyaretleri (Haftalık)", "delta_value": 2350, "delta_ref": 2100,
            "metric1": ("En Çok Kaydedilen Gönderi", "Reels: 'Yeni Ürün'"),
            "metric2": ("Toplam Erişim", "125,450", "+5.2k"),
            "metric3": ("Takipçi Değişimi", "+450", "Geçen Haftaya Göre")
        }
    elif platform_name == "Facebook":
        metrics = {
            "gauge_title": "Sayfa Erişimi (Haftalık)", "gauge_value": 78000, "gauge_max": 100000,
            "delta_title": "Sayfa Beğenileri", "delta_value": 152, "delta_ref": 140,
            "metric1": ("En Çok Yorum Alan Gönderi", "Soru-Cevap Etkinliği"),
            "metric2": ("Video İzlenmeleri (3sn)", "45,100", "+2.1k"),
            "metric3": ("Gönderi Etkileşimleri", "12,300", "-5%")
        }
    elif platform_name == "YouTube":
        metrics = {
            "gauge_title": "Ort. Görüntüleme Süresi (sn)", "gauge_value": 185, "gauge_max": 300,
            "delta_title": "Haftalık Yeni Abone", "delta_value": 430, "delta_ref": 450,
            "metric1": ("En Popüler Video", "Ürün İncelemesi"),
            "metric2": ("Toplam İzlenme", "1.2M", "50k"),
            "metric3": ("Toplam İzlenme Süresi (saat)", "25,400", "+1.2k")
        }
    elif platform_name in ["X (Twitter)", "LinkedIn"]:
        metrics = {
            "gauge_title": "Gösterimler (Haftalık)", "gauge_value": 250000, "gauge_max": 500000,
            "delta_title": "Profil Tıklamaları", "delta_value": 1800, "delta_ref": 1650,
            "metric1": ("En Çok Etkileşim Alan Konu", "#YapayZeka"),
            "metric2": ("Yeniden Paylaşımlar", "850", "+75"),
            "metric3": ("Yeni Bağlantılar/Takipçiler", "210", "+15%")
        }
    else: # Diğer platformlar için varsayılan metrikler
        metrics = {
            "gauge_title": "Genel Aktivite (%)", "gauge_value": 55, "gauge_max": 100,
            "delta_title": "Haftalık Etkileşim", "delta_value": 830, "delta_ref": 800,
            "metric1": ("Popüler Konu", "#Teknoloji"),
            "metric2": ("Yeniden Paylaşım", "250", "30"),
            "metric3": ("Yorum Sayısı", "480", "-5%")
        }

    col1, col2, col3 = st.columns(3)

    with col1:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = metrics["gauge_value"],
            title = {'text': metrics["gauge_title"], 'font': {'size': 18}},
            gauge = {
                'axis': {'range': [None, metrics["gauge_max"]], 'tickwidth': 1, 'tickcolor': "darkblue"},
                'bar': {'color': "#636EFA"},
                'steps': [
                    {'range': [0, metrics["gauge_max"] * 0.5], 'color': '#EAEAF2'}, 
                    {'range': [metrics["gauge_max"] * 0.5, metrics["gauge_max"] * 0.8], 'color': '#D2D4F1'}
                ],
            }))
        fig.update_layout(height=250, margin={'l': 20, 'r': 20, 't': 50, 'b': 20})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Indicator(
            mode = "number+delta",
            value = metrics["delta_value"],
            title = {"text": metrics["delta_title"], 'font': {'size': 18}},
            delta = {
                'reference': metrics["delta_ref"], 
                'relative': False, 
                'position' : "bottom",
                'increasing': {'symbol': '▲', 'color': '#3D9970'},
                'decreasing': {'symbol': '▼', 'color': '#FF4136'}
            }))
        fig2.update_layout(height=250, margin={'l': 20, 'r': 20, 't': 50, 'b': 20})
        st.plotly_chart(fig2, use_container_width=True)

    with col3:
        st.metric(label=metrics["metric1"][0], value=metrics["metric1"][1])
        st.metric(label=metrics["metric2"][0], value=metrics["metric2"][1], delta=metrics["metric2"][2])
        st.metric(label=metrics["metric3"][0], value=metrics["metric3"][1], delta=metrics["metric3"][2])

def display_post_history(user_id):
    """Kullanıcının yayınlanmış gönderi geçmişini gösterir."""
    st.title("📮 Gönderi Geçmişi")
    st.write("Daha önce yayınlanmış veya yayınlanırken hata almış gönderilerinizi burada görebilirsiniz.")

    # --- Filtreleme Alanı ---
    st.divider()
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # Kullanıcının bağlı olduğu platformları seçenek olarak sun
        user_accounts = database.get_user_accounts(st.session_state.selected_brand_id)
        available_platforms = sorted(list(set(acc['platform_name'] for acc in user_accounts)))
        selected_platforms = st.multiselect("Platforma Göre Filtrele:", options=available_platforms)

    with col2:
        start_date = st.date_input("Başlangıç Tarihi", value=None)

    with col3:
        end_date = st.date_input("Bitiş Tarihi", value=None)
    st.divider()

    posted_posts = database.get_posted_posts_for_user(st.session_state.selected_brand_id, selected_platforms, start_date, end_date)

    if not posted_posts:
        st.info("Henüz yayınlanmış bir gönderiniz bulunmuyor.")
        return

    for post in posted_posts:
        with st.container(border=True):
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.caption(f"Platform: {post['platform_name']} | Hesap: {post['account_name']}")
                st.write(post['caption'])
                if os.path.exists(post['image_path']):
                    st.image(post['image_path'], width=150)
            with col2:
                is_success = post['status'] == 'Yayınlandı'
                if is_success and post.get('platform_post_id'):
                    if st.button("Analiz Et", key=f"analyze_{post['id']}", use_container_width=True):
                        st.session_state.analyzing_post = post
                else:
                    # Hatalı veya platform_post_id'si olmayan gönderiler için butonu gösterme
                    st.write("") 
            with col3:
                scheduled_time = datetime.strptime(post['scheduled_time'], '%Y-%m-%d %H:%M:%S').strftime('%d %b, %H:%M')
                st.caption(f"Yayınlandı: {scheduled_time}")
                status_label = "Başarılı" if is_success else "Hata"
                
                with st.status(label=status_label, state="complete" if is_success else "error"):
                    # Show the detailed error message if the post failed
                    st.write(post['status'])

    if 'analyzing_post' in st.session_state and st.session_state.analyzing_post:
        post_to_analyze = st.session_state.analyzing_post
        
        @st.dialog("Gönderi Performansı")
        def show_analytics_dialog():
            st.subheader(f"'{post_to_analyze['caption'][:30]}...' Performansı")
            platform_name = post_to_analyze['platform_name']
            # Doğru platform sınıfını bul ve istatistikleri getir            
            platform_map = {"Facebook": FacebookPlatform, "Instagram": InstagramPlatform, "LinkedIn": LinkedInPlatform}
            platform = platform_map.get(platform_name, BasePlatform)()
            stats = platform.get_post_stats(post_id=post_to_analyze['platform_post_id'])
            for key, value in stats.items():
                st.metric(label=key, value=f"{value:,}")
            if st.button("Kapat"):
                st.session_state.analyzing_post = None
                st.rerun()
        
        show_analytics_dialog()

def display_analytics_page(user_id):
    """Kullanıcı için temel bir analiz ve raporlama sayfası oluşturur."""
    st.title("📊 Analiz ve Raporlama")
    st.write("Platformdaki genel aktivitenize ve gönderi dağılımınıza buradan göz atabilirsiniz.")

    # PDF İndirme Butonu
    # Bu butonu veriler yüklendikten sonra en üste koyuyoruz.
    pdf_button_placeholder = st.empty()

    data = database.get_user_analytics_data(st.session_state.selected_brand_id)

    # --- Üst Metrikler ---
    col1, col2 = st.columns(2)
    col1.metric("Toplam Bağlı Hesap", data['total_accounts'])
    col2.metric("Toplam Yayınlanmış Gönderi", data['total_posts'])

    st.divider()

    # --- Görselleştirmeler ---
    col3, col4 = st.columns(2)
    chart_image_paths = {}

    with col3:
        st.subheader("Platforma Göre Gönderi Dağılımı")
        if data['posts_by_platform']:
            platform_names = [item['platform_name'] for item in data['posts_by_platform']]
            post_counts = [item['count'] for item in data['posts_by_platform']]
            
            fig = go.Figure([go.Bar(x=platform_names, y=post_counts)])
            fig.update_layout(
                xaxis_title="Platform",
                yaxis_title="Gönderi Sayısı",
                title="Platform Bazında Gönderi Sayısı"
            )
            # Grafiği resim olarak kaydet
            img_bytes = fig.to_image(format="png")
            image_path = f"uploads/chart_platform_{user_id}.png"
            with open(image_path, "wb") as f:
                f.write(img_bytes)
            chart_image_paths['posts_by_platform'] = image_path
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Grafik oluşturmak için yeterli gönderi verisi bulunmuyor.")

    with col4:
        st.subheader("Son 30 Günlük Gönderi Aktivitesi")
        if data['posts_over_time']:
            dates = [item['post_date'] for item in data['posts_over_time']]
            counts = [item['count'] for item in data['posts_over_time']]

            fig = go.Figure([go.Scatter(x=dates, y=counts, mode='lines+markers', fill='tozeroy')])
            fig.update_layout(
                xaxis_title="Tarih",
                yaxis_title="Gönderi Sayısı",
                title="Günlük Gönderi Sayısı (Son 30 Gün)"
            )
            # Grafiği resim olarak kaydet
            img_bytes = fig.to_image(format="png")
            image_path = f"uploads/chart_time_{user_id}.png"
            with open(image_path, "wb") as f:
                f.write(img_bytes)
            chart_image_paths['posts_over_time'] = image_path
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Son 30 günde yayınlanmış gönderi bulunmuyor.")

    # PDF indirme butonunu şimdi doldur
    if data['total_posts'] > 0:
        if pdf_button_placeholder.button("Raporu PDF Olarak İndir", type="primary"):
            with st.spinner("PDF Raporu oluşturuluyor..."):
                payload = {
                    "analytics_data": data,
                    "chart_image_paths": chart_image_paths
                }
                response = requests.post(f"{BACKEND_URL}/reports/export-pdf", json=payload)
                if response.status_code == 200:
                    st.download_button(label="İndirme Hazır", data=response.content, file_name="SosyalOrkestra_Rapor.pdf", mime="application/pdf")
                else:
                    st.error("PDF oluşturulurken bir hata oluştu.")

def display_templates_page(user_id):
    """Kullanıcının içerik şablonlarını yönetebileceği bir sayfa oluşturur."""
    st.title("📝 İçerik Şablonları")
    st.write("Sık kullandığınız gönderi metinlerini şablon olarak kaydedin ve yeniden kullanın.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Yeni Şablon Oluştur")
        with st.form("new_template_form", clear_on_submit=True):
            template_name = st.text_input("Şablon Adı")
            template_caption = st.text_area("Şablon Metni", height=200)
            if st.form_submit_button("Şablonu Kaydet", type="primary"):
                if template_name and template_caption:
                    database.add_template(user_id, st.session_state.selected_brand_id, template_name, template_caption)
                    st.success(f"'{template_name}' şablonu kaydedildi.")
                else:
                    st.warning("Lütfen şablon adı ve metnini girin.")
    
    with col2:
        st.subheader("Mevcut Şablonlar")
        templates = database.get_user_templates(st.session_state.selected_brand_id)
        if not templates:
            st.info("Henüz oluşturulmuş bir şablonunuz yok.")
        else:
            for template in templates:
                with st.expander(f"{template['template_name']}"):
                    st.code(template['caption'])
                    if st.button("Sil", key=f"delete_template_{template['id']}", type="secondary"):
                        database.delete_template(template['id'])
                        st.rerun()

def generate_qr_code(otp_uri):
    """Verilen OTP URI'si için bir QR kodu oluşturur ve byte olarak döndürür."""
    img = qrcode.make(otp_uri)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return buf

def display_settings_page(username):
    """Kullanıcının profil ayarlarını (parola değiştirme) yönetebileceği bir sayfa oluşturur."""
    st.title("⚙️ Kullanıcı Ayarları")
    
    user = database.get_user(username)
    if not user:
        st.error("Kullanıcı bilgileri alınamadı.")
        return

    st.subheader("Parola Değiştir")

    with st.form("change_password_form", clear_on_submit=True):
        current_password = st.text_input("Mevcut Parola", type="password")
        new_password = st.text_input("Yeni Parola", type="password")
        new_password_confirm = st.text_input("Yeni Parola (Tekrar)", type="password")
        
        submitted = st.form_submit_button("Parolayı Değiştir", type="primary")

        if submitted:
            if not current_password or not new_password or not new_password_confirm:
                st.warning("Lütfen tüm alanları doldurun.")
            elif not check_password_hash(user['password_hash'], current_password):
                st.error("Mevcut parolanız yanlış.")
            elif new_password != new_password_confirm:
                st.error("Yeni parolalar eşleşmiyor.")
            else:
                new_hashed_password = generate_password_hash(new_password)
                database.update_user_password(user['id'], new_hashed_password)
                st.success("Parolanız başarıyla güncellendi!")
    
    st.divider()
    st.subheader("İki Aşamalı Doğrulama (2FA)")

    if user['otp_enabled']:
        st.success("İki aşamalı doğrulama (2FA) şu anda aktif.")
        if st.button("2FA'yı Devre Dışı Bırak", type="secondary"):
            database.disable_otp(user['id'])
            st.rerun()
    else:
        st.info("Hesap güvenliğinizi artırmak için iki aşamalı doğrulamayı etkinleştirin.")
        if st.button("2FA'yı Etkinleştir"):
            # Yeni bir OTP sırrı oluştur ve URI'yi hazırla
            otp_secret = pyotp.random_base32()
            otp_uri = pyotp.totp.TOTP(otp_secret).provisioning_uri(
                name=username,
                issuer_name="Sosyal Orkestra"
            )
            st.session_state.otp_secret_to_verify = otp_secret
            st.session_state.otp_uri = otp_uri

    if 'otp_secret_to_verify' in st.session_state:
        st.warning("Lütfen aşağıdaki QR kodunu Google Authenticator veya benzeri bir uygulama ile tarayın.")
        qr_code_bytes = generate_qr_code(st.session_state.otp_uri)
        st.image(qr_code_bytes)
        st.code(st.session_state.otp_secret_to_verify)
        
        with st.form("verify_otp_form"):
            otp_code = st.text_input("Authenticator uygulamanızdaki 6 haneli kodu girerek kurulumu tamamlayın:")
            if st.form_submit_button("Doğrula ve Etkinleştir", type="primary"):
                totp = pyotp.TOTP(st.session_state.otp_secret_to_verify)
                if totp.verify(otp_code):
                    database.enable_otp(user['id'], st.session_state.otp_secret_to_verify)
                    del st.session_state.otp_secret_to_verify
                    del st.session_state.otp_uri
                    st.success("2FA başarıyla etkinleştirildi!")
                    st.rerun()
                else:
                    st.error("Doğrulama kodu yanlış. Lütfen tekrar deneyin.")

    st.divider()
    st.subheader("Görünüm Ayarları")

    def on_theme_change():
        """Callback function to update theme in db and session."""
        new_theme = st.session_state.theme_selector
        database.update_user_theme(user['id'], new_theme)
        st.session_state.theme = new_theme

    current_theme = user['theme']
    theme_options = ['light', 'dark']
    theme_display = ['Aydınlık Mod', 'Karanlık Mod']
    
    st.radio(
        "Uygulama Teması:",
        options=theme_options,
        format_func=lambda x: 'Karanlık Mod' if x == 'dark' else 'Aydınlık Mod',
        index=theme_options.index(current_theme),
        key="theme_selector",
        on_change=on_theme_change
    )

    st.divider()
    st.subheader("Arayüz Teması")
    st.info("Uygulamanın genel yerleşim düzenini buradan değiştirebilirsiniz. Gelecekte yeni temalar eklenecektir.")
    
    with st.form("layout_theme_form"):
        st.radio(
            "Arayüz Düzeni:",
            options=['modern_v1'],
            format_func=lambda x: "Modern Tema V1 (Tavsiye Edilen)",
            key="layout_theme_selector"
        )
        if st.form_submit_button("Arayüzü Kaydet", type="primary"):
            new_layout_theme = st.session_state.layout_theme_selector
            database.update_user_layout_theme(user['id'], new_layout_theme)
            st.toast("Arayüz teması güncellendi!")

def display_team_management_page(user_id):
    """Takım üyelerini ve rollerini yönetme sayfası."""
    st.title("👥 Takım Yönetimi")
    
    user_team = database.get_user_team(user_id)

    if not user_team:
        st.info("Henüz bir takıma ait değilsiniz.")
        with st.form("create_team_form"):
            team_name = st.text_input("Yeni Takım Adı")
            if st.form_submit_button("Takım Oluştur", type="primary"):
                if team_name:
                    database.create_team(team_name, user_id)
                    st.success(f"'{team_name}' takımı başarıyla oluşturuldu!")
                    st.rerun()
                else:
                    st.warning("Lütfen bir takım adı girin.")
    else:
        st.subheader(f"Takımınız: {user_team['team_name']}")
        st.write(f"Rolünüz: **{user_team['role'].capitalize()}**")

        st.divider()

        # --- Takım Üyelerini Listeleme ---
        st.subheader("Takım Üyeleri")
        # Sadece takım yöneticileri üyeleri ve izinlerini görebilir/yönetebilir
        if user_team.get('can_manage_team'):
            team_members = database.get_team_members(user_team['team_id'])
            for member in team_members:
                with st.expander(f"@{member['username']}"):
                    is_owner = member['id'] == user_id
                    with st.form(key=f"form_member_{member['id']}"):
                        st.write(f"**{member['username']} İzinleri**")
                        permissions = {
                            'can_post': st.checkbox("Gönderi Oluşturabilir/Planlayabilir", value=member['can_post'], key=f"post_{member['id']}", disabled=is_owner),
                            'can_approve': st.checkbox("Gönderi Onaylayabilir", value=member['can_approve'], key=f"approve_{member['id']}", disabled=is_owner),
                            'can_view_reports': st.checkbox("Raporları Görüntüleyebilir", value=member['can_view_reports'], key=f"reports_{member['id']}", disabled=is_owner),
                            'can_manage_team': st.checkbox("Takımı Yönetebilir (Üye Ekle/Çıkar)", value=member['can_manage_team'], key=f"team_{member['id']}", disabled=is_owner),
                        }
                        
                        col1, col2 = st.columns([1,3])
                        with col1:
                            if st.form_submit_button("İzinleri Güncelle", type="primary", disabled=is_owner):
                                database.update_team_member_permissions(user_team['team_id'], member['id'], permissions)
                                st.toast(f"@{member['username']} izinleri güncellendi.")
                                st.rerun()
                        with col2:
                             if st.form_submit_button("Takımdan Kaldır", type="secondary", disabled=is_owner):
                                database.remove_team_member(user_team['team_id'], member['id'])
                                st.toast(f"@{member['username']} takımdan kaldırıldı.")
                                st.rerun()

        # --- Yeni Üye Davet Etme (Sadece Adminler için) ---
        if user_team.get('can_manage_team'):
            st.divider()
            st.subheader("Yeni Üye Davet Et")
            with st.form("invite_member_form", clear_on_submit=True):
                invitee_username = st.text_input("Davet Edilecek Kullanıcının Adı")
                if st.form_submit_button("Davet Et", type="primary"):
                    invited_user = database.get_user(invitee_username)
                    if not invited_user:
                        st.error(f"'{invitee_username}' adında bir kullanıcı bulunamadı.")
                    elif database.get_user_team(invited_user['id']):
                        st.error(f"'{invitee_username}' zaten başka bir takımın üyesi.")
                    else:
                        # Varsayılan olarak en düşük izinlerle ekle
                        default_permissions = {'can_post': True, 'can_approve': False, 'can_view_reports': True, 'can_manage_team': False}
                        database.add_team_member(user_team['team_id'], invited_user['id'], default_permissions)
                        st.success(f"'{invitee_username}' takıma eklendi! Lütfen izinlerini düzenleyin.")
                        st.rerun()

def display_social_inbox_page(user_id):
    """Tüm platformlardan gelen etkileşimleri gösteren birleşik gelen kutusu."""
    # st.title("📥 Birleşik Gelen Kutusu") # Başlık artık sekme adından geliyor

    # Bu fonksiyon backend'e istek gönderir
    def send_reply(conversation_id, reply_text):
        # Bu, backend'e bir API çağrısı yapacak.
        # Gerçek bir uygulamada, Streamlit'in cookie'lerini veya bir token'ı
        # backend'e göndermek için daha gelişmiş bir mekanizma gerekir.
        response = requests.post(f"{BACKEND_URL}/inbox/reply", json={'conversation_id': conversation_id, 'reply_text': reply_text})
        return response.json()
    
    def like_comment(conversation_id, platform_message_id):
        response = requests.post(f"{BACKEND_URL}/inbox/like", json={'conversation_id': conversation_id, 'platform_message_id': platform_message_id})
        return response.json()

    st.info("🟢 Gelen kutunuz, Facebook ve Instagram'dan gelen yeni yorumlarla otomatik olarak güncellenir.", icon="ℹ️")

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Görüşmeler")
        conversations = database.get_conversations(st.session_state.selected_brand_id)
        if not conversations:
            st.info("Görüşme bulunamadı. Lütfen senkronize etmeyi deneyin.")
        
        for conv in conversations:
            with st.container(border=True):
                st.caption(f"Hesap: {conv['account_name']}")
                st.write(f"**{conv['snippet']}**")
                if st.button("Görüntüle", key=f"conv_{conv['id']}", use_container_width=True):
                    st.session_state.selected_conversation_id = conv['id']
                    st.rerun()

    with col2:
        st.subheader("Mesaj Akışı")
        if st.session_state.selected_conversation_id:
            messages = database.get_messages(st.session_state.selected_conversation_id)
            for msg in messages:
                with st.chat_message(name="user"): # Tüm mesajları aynı stilde göster
                    msg_display = msg['message']
                    if msg.get('is_hidden'):
                        msg_display = f"_{msg_display}_ (Bu yorum otomatik olarak gizlendi) 👁️‍🗨️"
                    elif msg.get('is_flagged'):
                        msg_display = f"{msg_display} 🚩"

                    col1, col2 = st.columns([10, 1])
                    with col1:
                        st.write(f"**{msg['sender_name']}**")
                        st.markdown(msg_display)
                        st.caption(datetime.fromisoformat(msg['timestamp']).strftime('%d %b, %H:%M'))
                    with col2:
                        if st.button("👍", key=f"like_{msg['id']}", help="Beğen"):
                            response = like_comment(st.session_state.selected_conversation_id, msg['platform_message_id'])
                            if response.get('status') == 'success':
                                st.toast("Yorum beğenildi!")
            
            st.divider()
            with st.form("reply_form", clear_on_submit=True):
                reply_text = st.text_area("Yanıtınız:", key="reply_text", placeholder="Yanıtınızı buraya yazın...")
                if st.form_submit_button("Gönder", type="primary"):
                    response = send_reply(st.session_state.selected_conversation_id, reply_text)
                    if response.get('status') == 'success':
                        st.rerun()
                    else:
                        st.error(f"Yanıt gönderilemedi: {response.get('message')}")
        else:
            st.info("Görüntülemek için soldaki listeden bir görüşme seçin.")

def display_approval_queue_page(user_team):
    """Adminlerin, editörler tarafından oluşturulan gönderileri onaylayıp reddedebileceği sayfa."""
    st.title("✅ Onay Bekleyen Gönderiler")
    st.write("Takımınızdaki editörler tarafından oluşturulan ve onayınızı bekleyen gönderiler.")

    pending_posts = database.get_pending_approval_posts(user_team['team_id'])

    if not pending_posts:
        st.info("Onay bekleyen bir gönderi bulunmuyor.")
        return

    for post in pending_posts:
        with st.container(border=True):
            st.caption(f"Oluşturan: {post['author']} | Platform: {post['platform_name']} | Hedef: {post['account_name']}")
            st.caption(f"Planlanan Zaman: {datetime.strptime(post['scheduled_time'], '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y, %H:%M')}")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(post['caption'])
                if os.path.exists(post['image_path']):
                    st.image(post['image_path'], width=150)
            with col2:
                if st.button("Onayla", key=f"approve_{post['id']}", type="primary", use_container_width=True):
                    database.update_post_approval_status(post['id'], "Bekliyor")
                    st.rerun()
                if st.button("Reddet", key=f"reject_{post['id']}", type="secondary", use_container_width=True):
                    database.update_post_approval_status(post['id'], "rejected")
                    st.rerun()

def display_reports_page(user_id):
    """Analizler ve Gönderi Geçmişi için sekmeli bir sayfa oluşturur."""
    st.title("📈 Raporlar ve Geçmiş")

    analytics_tab, history_tab, competitor_tab, bucket_tab = st.tabs(["Genel Analizler", "Gönderi Geçmişi", "Rakip Analizi", "İçerik Kovası Performansı"])

    with analytics_tab:
        display_analytics_page(user_id)

    with history_tab:
        display_post_history(user_id)
    
    with competitor_tab:
        display_competitor_analysis_page(user_id)
    
    with bucket_tab:
        st.subheader("İçerik Kovası Performansı")
        st.write("Hangi içerik kategorilerinizin daha fazla etkileşim aldığını görün.")
        bucket_data = database.get_bucket_performance_data(st.session_state.selected_brand_id)

        if not bucket_data:
            st.info("Performansını analiz etmek için lütfen gönderilerinizi içerik kovalarına atayın.")
        else:
            df = pd.DataFrame(bucket_data)
            fig = go.Figure(go.Bar(
                x=df['name'],
                y=df['engagement'],
                marker_color=df['color']
            ))
            fig.update_layout(title_text='Kovalara Göre Toplam Etkileşim (Simüle Edilmiş Veri)', xaxis_title="İçerik Kovası", yaxis_title="Toplam Etkileşim")
            st.plotly_chart(fig, use_container_width=True)

def display_master_settings_page(user_id, username):
    """Tüm ayar sayfalarını sekmeler halinde birleştirir."""
    st.title("🛠️ Genel Ayarlar")

    tabs = [
        "Kullanıcı Ayarları", 
        "Takım Yönetimi", 
        "İçerik Şablonları", 
        "Hashtag Grupları",
        "İçerik Kovaları",
        "Otomatik Moderasyon",
        "Marka Yönetimi"
    ]
    settings_tab, team_tab, templates_tab, hashtags_tab, buckets_tab, moderation_tab, brand_management_tab = st.tabs(tabs)

    with settings_tab:
        display_settings_page(username)
    with team_tab:
        display_team_management_page(user_id)
    with templates_tab:
        display_templates_page(user_id)
    with hashtags_tab:
        display_hashtag_groups_page(user_id)
    with buckets_tab:
        display_content_buckets_page(user_id)
    with moderation_tab:
        display_moderation_page(user_id)
    with brand_management_tab:
        display_brand_management_page(user_id)

def display_moderation_page(user_id):
    """Kullanıcının otomatik moderasyon kurallarını yönetebileceği sayfa."""
    st.subheader("Otomatik Yorum Moderasyonu")
    st.write("Belirlediğiniz anahtar kelimeleri içeren yorumlara otomatik olarak işlem uygulayın.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.write("**Yeni Kural Ekle**")
        with st.form("new_rule_form", clear_on_submit=True):
            keyword = st.text_input("Yasaklı Anahtar Kelime (küçük harfle girin)")
            action = st.selectbox("Uygulanacak Eylem", ["hide", "flag"], format_func=lambda x: "Yorumu Gizle" if x == "hide" else "İnceleme için İşaretle")
            if st.form_submit_button("Kural Ekle", type="primary"):
                if keyword:
                    if database.add_moderation_rule(user_id, st.session_state.selected_brand_id, keyword, action):
                        st.success(f"'{keyword}' kelimesi için kural eklendi.")
                        st.rerun()
                    else:
                        st.warning(f"'{keyword}' için zaten bir kural mevcut.")
                else:
                    st.warning("Lütfen bir anahtar kelime girin.")
    
    with col2:
        st.write("**Mevcut Kurallar**")
        rules = database.get_user_moderation_rules(st.session_state.selected_brand_id)
        if not rules:
            st.info("Henüz bir moderasyon kuralınız yok.")
        else:
            for rule in rules:
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(rule['keyword'])
                c2.write("Yorumu Gizle" if rule['action'] == 'hide' else "İşaretle")
                if c3.button("Sil", key=f"delete_rule_{rule['id']}", type="secondary"):
                    database.delete_moderation_rule(rule['id'])
                    st.rerun()

def brand_delete_confirmation_dialog(brand):
    """Marka silme işlemi için bir onay diyaloğu gösterir."""
    st.warning(f"**DİKKAT:** '{brand['brand_name']}' markasını silmek üzeresiniz.")
    st.write("Bu işlem geri alınamaz ve bu markaya bağlı olan **tüm hesaplar, planlanmış gönderiler, raporlar ve ayarlar kalıcı olarak silinecektir**.")
    
    if st.button("Evet, Bu Markayı ve Tüm Verilerini Sil", type="primary"):
        with st.spinner("Marka siliniyor..."):
            database.delete_brand(brand['id'])
            st.session_state.selected_brand_id = None # Seçili markayı temizle
            st.success(f"'{brand['brand_name']}' markası başarıyla silindi.")
            st.rerun()
    if st.button("İptal"):
        st.rerun()

def display_brand_management_page(user_id):
    """Kullanıcının markaları yönetebileceği sayfa."""
    st.subheader("Marka Yönetimi")
    st.write("Ajansınız için yeni müşteri markaları oluşturun veya mevcutları yönetin.")

    user_team = database.get_user_team(user_id)
    if not user_team or not user_team.get('can_manage_team'):
        st.warning("Bu bölümü görüntülemek için takım yöneticisi olmalısınız.")
        return

    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("**Yeni Marka Oluştur**")
        with st.form("new_brand_form", clear_on_submit=True):
            brand_name = st.text_input("Marka Adı")
            if st.form_submit_button("Marka Oluştur", type="primary"):
                if brand_name:
                    database.create_brand(user_team['team_id'], brand_name)
                    st.success(f"'{brand_name}' markası oluşturuldu.")
                    st.rerun()
    
    with col2:
        st.write("**Mevcut Markalar**")
        brands = database.get_brands_for_team(user_team['team_id'])
        if not brands:
            st.info("Henüz bir marka oluşturulmadı.")
        for brand in brands:
            with st.expander(f"**{brand['brand_name']}**"):
                st.write("Bu markaya bağlı hesaplar:")
                accounts = database.get_user_accounts(brand['id'])
                if not accounts:
                    st.caption("Bu markaya bağlı hesap yok.")
                for acc in accounts:
                    st.caption(f"- {acc['platform_name']}: {acc['account_name']}")
                if st.button("Bu Markayı Sil", key=f"delete_brand_{brand['id']}", type="secondary"):
                    st.dialog(f"'{brand['brand_name']}' Markasını Silmeyi Onayla", lambda: brand_delete_confirmation_dialog(brand))

def display_content_ideas_page(user_id):
    """Yapay zeka destekli içerik fikirleri ve trendler sayfası."""
    st.title("💡 İçerik Fikirleri ve Trendler")
    st.write("Yeni içerikleriniz için ilham alın ve gündemi yakalayın.")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("🤖 Yapay Zeka ile Fikir Üret")
        with st.form("content_idea_form"):
            topic = st.text_input("Hangi konu hakkında fikir arıyorsunuz?", placeholder="Örn: Sürdürülebilir moda, evde kahve demleme")
            tone = st.selectbox("İçerik Tonu:", ["Profesyonel", "Samimi", "Esprili", "Bilgilendirici", "İlham Verici"])
            platform_format = st.selectbox("İçerik Formatı:", ["Instagram Gönderisi", "Instagram Reel Fikri", "Blog Yazısı Başlığı", "Tweet Serisi", "LinkedIn Makalesi"])
            
            if st.form_submit_button("Fikir Üret", type="primary"):
                if topic:
                    with st.spinner("Yaratıcı fikirler hazırlanıyor..."):
                        try:
                            full_prompt = f"Bir sosyal medya yöneticisi olarak, '{topic}' konusunda, '{tone}' bir tonda, '{platform_format}' formatı için 3 adet yaratıcı ve dikkat çekici içerik fikri öner. Her fikri bir başlık ve kısa bir açıklama ile sun."
                            openai.api_key = os.getenv("OPENAI_API_KEY")
                            response = openai.chat.completions.create(
                                model="gpt-3.5-turbo",
                                messages=[{"role": "user", "content": full_prompt}]
                            )
                            generated_ideas = response.choices[0].message.content
                            st.markdown(generated_ideas)
                        except Exception as e:
                            st.error(f"Yapay zeka ile fikir üretilirken bir hata oluştu: {e}")
                else:
                    st.warning("Lütfen bir konu girin.")

    with col2:
        st.subheader("📈 Gündemdeki Konular (Google Trends)")

        @st.cache_data(ttl=3600) # Veriyi 1 saat boyunca önbellekte tut        
        def fetch_google_trends():
            try:
                response = requests.get(f"{BACKEND_URL}/trends/google")
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                print(f"Trendler alınırken hata: {e}")
                return None

        trends = fetch_google_trends()
        if trends:
            for i, trend in enumerate(trends[:10]): # İlk 10 trendi göster
                st.markdown(f"{i+1}. {trend['0']}")
        else:
            st.warning("Trend verileri şu anda alınamıyor.")

def display_content_buckets_page(user_id):
    """Kullanıcının içerik kovalarını yönetebileceği sayfa."""
    st.title("🪣 İçerik Kovaları")
    st.write("Gönderilerinizi kategorilere ayırarak içerik stratejinizi planlayın ve analiz edin.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Yeni Kova Oluştur")
        with st.form("new_bucket_form", clear_on_submit=True):
            bucket_name = st.text_input("Kova Adı (Örn: Tanıtım, Eğitici İçerik)")
            bucket_color = st.color_picker("Kova Rengi", "#808080")
            if st.form_submit_button("Kovayı Oluştur", type="primary"):
                if bucket_name:
                    database.add_content_bucket(user_id, st.session_state.selected_brand_id, bucket_name, bucket_color)
                    st.success(f"'{bucket_name}' kovası oluşturuldu.")
                    st.rerun()
                else:
                    st.warning("Lütfen bir kova adı girin.")
    
    with col2:
        st.subheader("Mevcut Kovalar")
        buckets = database.get_user_content_buckets(st.session_state.selected_brand_id)
        if not buckets:
            st.info("Henüz oluşturulmuş bir içerik kovanız yok.")
        else:
            for bucket in buckets:
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"<div style='padding: 10px; border-radius: 5px; background-color: {bucket['color']}; color: white; text-shadow: 1px 1px 2px black;'>{bucket['bucket_name']}</div>", unsafe_allow_html=True)
                with c2:
                    if st.button("Sil", key=f"delete_bucket_{bucket['id']}", type="secondary"):
                        database.delete_content_bucket(bucket['id'])
                        st.rerun()

def display_bulk_upload_page(user_id):
    """Kullanıcıların CSV dosyası ile toplu gönderi planlamasını sağlar."""
    st.title("📤 Toplu Gönderi Yükleme")
    st.write("Bir CSV dosyası kullanarak birden fazla gönderiyi tek seferde planlayın.")

    st.info("""
    **Nasıl Kullanılır?**
    1. Aşağıdaki butonu kullanarak CSV şablonunu indirin.
    2. Medya dosyalarınızı (görsel/video) projenin `uploads` klasörüne yükleyin.
    3. Şablonu, her satır bir gönderi olacak şekilde doldurun. `media_path` sütununa `uploads/dosya_adi.jpg` gibi dosya yolunu doğru yazdığınızdan emin olun.
    4. Doldurduğunuz CSV dosyasını aşağıdaki alana yükleyin.
    """)

    # CSV Şablonu İçeriği
    csv_template = "platform_name,account_name,caption,media_path,scheduled_datetime,bucket_name\n" \
                   "Instagram,Hesap Adiniz,\"Bu bir örnek gönderidir. #topluyukleme\",\"uploads/ornek.jpg\",\"2024-12-25 10:30:00\",Tanıtım\n" \
                   "Facebook,Sayfa Adiniz,\"Bu başka bir gönderi.\",\"uploads/baska_bir_gorsel.png\",\"2024-12-26 18:00:00\","

    st.download_button(
        label="CSV Şablonunu İndir",
        data=csv_template,
        file_name="sosyal_orkestra_sablon.csv",
        mime="text/csv",
    )

    st.divider()

    uploaded_file = st.file_uploader("Doldurduğunuz CSV dosyasını buraya yükleyin", type="csv")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Yüklenen Veri Önizlemesi:")
            st.dataframe(df)

            if st.button("Gönderileri Planla", type="primary"):
                user_accounts = {(acc['platform_name'], acc['account_name']): acc['id'] for acc in database.get_user_accounts(st.session_state.selected_brand_id)}
                user_buckets = {b['bucket_name']: b['id'] for b in database.get_user_content_buckets(st.session_state.selected_brand_id)}
                
                success_count = 0
                errors = []

                with st.spinner("Gönderiler planlanıyor..."):
                    for index, row in df.iterrows():
                        account_key = (row['platform_name'], row['account_name'])
                        media_path = row['media_path']
                        
                        if account_key not in user_accounts:
                            errors.append(f"Satır {index+2}: '{row['account_name']}' adlı {row['platform_name']} hesabı bulunamadı.")
                        elif not os.path.exists(media_path):
                            errors.append(f"Satır {index+2}: Medya dosyası bulunamadı: '{media_path}'")
                        else:
                            bucket_id = user_buckets.get(row.get('bucket_name'))
                            media_type = 'VIDEO' if any(media_path.lower().endswith(ext) for ext in ['.mp4', '.mov']) else 'IMAGE'
                            database.add_scheduled_post(user_id, st.session_state.selected_brand_id, user_accounts[account_key], row['caption'], media_path, row['scheduled_datetime'], bucket_id=bucket_id, media_type=media_type)
                            success_count += 1
                
                st.success(f"{success_count} adet gönderi başarıyla planlandı!")
                if errors:
                    st.error("Aşağıdaki hatalar nedeniyle bazı gönderiler planlanamadı:")
                    for error in errors:
                        st.write(error)
        except Exception as e:
            st.error(f"CSV dosyası işlenirken bir hata oluştu: {e}")

def display_competitor_analysis_page(user_id):
    """Kullanıcının rakiplerini izleyebileceği ve analiz edebileceği sayfa."""
    st.title("🔭 Rakip Analizi")
    st.write("Rakiplerinizin sosyal medyadaki performansını izleyin ve stratejinizi şekillendirin.")

    if st.button("Rakip Verilerini Senkronize Et", help="Tüm rakiplerin en güncel takipçi sayılarını çeker."):
        with st.spinner("Rakip verileri senkronize ediliyor..."):            
            response = requests.get(f"{BACKEND_URL}/competitors/sync")
            if response.status_code == 200:
                st.toast("Rakip verileri başarıyla senkronize edildi!", icon="✅")
            else:
                st.error("Senkronizasyon sırasında bir hata oluştu.")
            st.rerun()

    # Şimdilik sadece Instagram destekleniyor
    platform = "Instagram"

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader(f"Yeni {platform} Rakibi Ekle")
        with st.form("add_competitor_form", clear_on_submit=True):
            username = st.text_input("Rakip Instagram Kullanıcı Adı", placeholder="@rakipkullaniciadi")
            if st.form_submit_button("Rakibi Ekle", type="primary"):
                if username:
                    clean_username = username.strip().lstrip('@')
                    if database.add_competitor(user_id, st.session_state.selected_brand_id, platform, clean_username):
                        st.success(f"'{clean_username}' izleme listesine eklendi. Veriler yakında toplanacak.")
                        st.rerun()
                    else:
                        st.warning(f"'{clean_username}' zaten izleme listenizde.")
                else:
                    st.warning("Lütfen bir kullanıcı adı girin.")
        
        st.divider()
        st.subheader("İzlenen Rakipler")
        competitors = database.get_competitors(st.session_state.selected_brand_id, platform)
        if not competitors:
            st.info("Henüz izlenen bir rakip yok.")
        for comp in competitors:
            with st.container(border=True):
                c1, c2 = st.columns([3,1])
                c1.write(f"**@{comp['competitor_username']}**")
                if c2.button("Kaldır", key=f"del_comp_{comp['id']}", type="secondary"):
                    database.delete_competitor(comp['id'])
                    st.rerun()

    with col2:
        st.subheader("Performans Karşılaştırması (Örnek Veri)")
        if not competitors:
            st.info("Analiz edilecek rakip bulunmuyor.")
        else:
            for comp in competitors:
                with st.container(border=True):
                    st.write(f"**@{comp['competitor_username']} Takipçi Değişimi**")
                    snapshots = database.get_competitor_snapshots(comp['id'])
                    if snapshots:
                        df = pd.DataFrame(snapshots)
                        df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
                        df = df.set_index('snapshot_date')
                        st.line_chart(df[['follower_count']])
                    else:
                        st.caption("Bu rakip için henüz veri toplanmadı. Lütfen senkronize edin.")

def display_platforms_page(user_id):
    """Sol menüde platformları ve ana alanda yönetim panelini gösterir."""
    with st.sidebar:
        st.markdown(f"<h2 style='text-align: center;'>Platformlar</h2>", unsafe_allow_html=True)
        selected_platform = option_menu(
            menu_title=None,
            options=["Facebook", "Instagram", "X (Twitter)", "LinkedIn", "Pinterest", "Google My Business"],
            icons=["facebook", "instagram", "twitter-x", "linkedin", "pinterest", "google"],
            menu_icon="list-task",
            default_index=0,
            styles={
                "container": {"padding": "0!important", "background-color": "#1c1c2e"},
                "icon": {"color": "#c4a7e7", "font-size": "20px"}, 
                "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#3a3a5a"},
                "nav-link-selected": {"background-color": "#2c2c4a"},
            }
        )

    # Ana içerik alanı
    st.title(f"🔗 {selected_platform} Platform Yönetimi")
    display_platform_dashboard(selected_platform) # Platforma özel dashboard'u göster

    management_tab, inbox_tab = st.tabs(["Hesap Yönetimi", "Gelen Kutusu"])

    with inbox_tab:
        # Gelen kutusu fonksiyonunu bu platforma özel olarak çağır
        display_social_inbox_page(user_id)

    with management_tab:
        st.subheader("Bağlı Hesaplar")
        # Kullanıcının o platforma bağlı hesaplarını getir
        connected_accounts = database.get_user_accounts(st.session_state.selected_brand_id, selected_platform)

        if not connected_accounts:
            st.warning(f"Henüz bir {selected_platform} hesabı bağlamadınız.")
        else:
            for account in connected_accounts:
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.write(f"**{account['account_name']}**")
                        st.caption(f"Platform: {account['platform_name']}")
                    with col2:
                        if st.button("Yönet", key=f"manage_{account['id']}", use_container_width=True, type="primary"):
                            st.session_state.managing_account_id = account['id']
                            st.rerun()
        
        st.divider()
        # Sadece geçerli bir marka seçiliyse hesap bağlama butonunu aktif et
        if st.session_state.selected_brand_id:
            st.link_button(f"Yeni Bir {selected_platform} Hesabı Bağla", f"{BACKEND_URL}/login/{selected_platform.lower()}?user_id={user_id}&brand_id={st.session_state.selected_brand_id}", type="primary")
        else:
            st.button(f"Yeni Bir {selected_platform} Hesabı Bağla", type="primary", disabled=True)
            st.warning("Yeni bir hesap bağlamadan önce lütfen yukarıdan bir marka seçin veya 'Ayarlar > Marka Yönetimi' bölümünden yeni bir marka oluşturun.")


    # --- Hesap Yönetim Paneli ---
    if st.session_state.managing_account_id is not None:
        # Yönetilen hesabı listeden bul (tüm hesaplar arasından)
        all_user_accounts = database.get_user_accounts(st.session_state.selected_brand_id)
        managed_account = next((acc for acc in all_user_accounts if acc['id'] == st.session_state.managing_account_id and acc['platform_name'] == selected_platform), None)
        
        if managed_account:
            st.header(f"⚙️ '{managed_account['account_name']}' Hesabını Yönet")

            # Yönetim seçenekleri için sekmeler
            post_tab, schedule_tab, delete_tab = st.tabs(["Yeni Gönderi Paylaş", "Gönderi Planla", "Ayarlar"])

            # --- Görsel Düzenleyici Diyaloğu ---
            @st.dialog("Görsel Düzenleyici")
            def image_editor_dialog():
                st.subheader("Görseli Düzenle")
                st.info("Kırpmak istediğiniz alanı seçin ve butona tıklayın.")
                if st.session_state.editing_image_bytes:                    
                    img = Image.open(BytesIO(st.session_state.editing_image_bytes))
                    
                    cropped_img = st_cropper(img, realtime_update=True, box_color='blue', aspect_ratio=None)
                    
                    if st.button("Kırp ve Kaydet", type="primary"):
                        # Düzenlenmiş görseli geçici bir dosyaya kaydet
                        uploads_dir = "uploads"
                        if not os.path.exists(uploads_dir): os.makedirs(uploads_dir)
                        
                        # Benzersiz bir dosya adı oluştur
                        import uuid
                        edited_file_name = f"cropped_{uuid.uuid4()}_{st.session_state.editing_image_name}"
                        edited_file_path = os.path.join(uploads_dir, edited_file_name)
                        cropped_img.save(edited_file_path)
                        
                        st.session_state.edited_image_path = edited_file_path
                        st.success("Görsel başarıyla kırpıldı ve kaydedildi!")
                        st.session_state.editing_image_bytes = None # Diyalog kapandıktan sonra temizle
                        st.rerun()

            # --- Yapay Zeka Yardımcı Pilot (Her iki sekme için de kullanılabilir) ---
            @st.dialog("Yapay Zeka Metin Yazarı")
            def ai_copilot_dialog():
                st.subheader("🤖 Yapay Zeka ile Metin Oluşturun")
                prompt = st.text_input("Ne hakkında bir gönderi yazmak istersiniz?", help="Örnek: Yeni çıkan kahve ürünümüzün lansmanı")
                
                col1, col2 = st.columns(2)
                with col1:
                    tone = st.selectbox("Yazı Tonu:", ["Profesyonel", "Samimi", "Esprili", "Satış Odaklı"])
                with col2:
                    include_hashtags = st.checkbox("Hashtag önerileri ekle", value=True)

                if st.button("Metin Oluştur", type="primary"):
                    try:
                        full_prompt = f"Sosyal medya için '{prompt}' konusunda, '{tone}' bir tonda dikkat çekici bir gönderi metni yaz."
                        if include_hashtags:
                            full_prompt += " Ayrıca, bu konuyla ilgili 5 adet popüler ve etkili hashtag öner."

                        openai.api_key = os.getenv("OPENAI_API_KEY")
                        response = openai.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": full_prompt}]
                        )
                        generated_text = response.choices[0].message.content
                        # Metni ve hashtag'leri ayırmaya çalışalım
                        parts = generated_text.split('#')
                        # Hedeflenen session state'i güncelle
                        st.session_state[f"ai_generated_text_{st.session_state.ai_target}"] = parts[0].strip()
                        st.session_state.ai_generated_hashtags = " ".join([f"#{part.strip()}" for part in parts[1:]])
                        st.rerun() # Formu yenileyerek metni alana yazdır
                    except Exception as e:
                        st.error(f"Yapay zeka ile metin oluşturulurken bir hata oluştu: {e}")
            
            # --- En İyi Zaman Önerisi Diyaloğu ---
            @st.dialog("En İyi Paylaşım Zamanı")
            def best_time_dialog():
                st.subheader("📈 En Yüksek Etkileşim Alınan Zamanlar")
                try:
                    response = requests.get(f"{BACKEND_URL}/analytics/best-time")
                    if response.status_code == 200:
                        best_times = response.json()
                        st.info("Aşağıdaki zaman dilimleri, geçmiş gönderilerinizin aldığı ortalama etkileşime göre sıralanmıştır. Birine tıklayarak planlama formunu doldurabilirsiniz.")
                        
                        days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
                        
                        for time_slot in best_times[:10]: # En iyi 10 zamanı göster
                            day_name = days[time_slot['day']]
                            hour = time_slot['hour']
                            if st.button(f"**{day_name}, {hour:02d}:00** (Ort. Etkileşim: {int(time_slot['avg_engagement'])})", use_container_width=True):
                                # Kullanıcının seçtiği güne en yakın gelecekteki tarihi bul
                                today = datetime.now()
                                days_ahead = time_slot['day'] - today.weekday()
                                if days_ahead < 0: days_ahead += 7
                                target_date = today + timedelta(days=days_ahead)
                                
                                # Session state'i güncelle ve formu yeniden çalıştır
                                st.session_state.schedule_date_suggestion = target_date.date()
                                st.session_state.schedule_time_suggestion = datetime.strptime(f"{hour:02d}:00", "%H:%M").time()
                                st.rerun()

                    else:
                        st.error(f"Veriler alınamadı: {response.json().get('error', 'Bilinmeyen bir hata oluştu.')}")
                except Exception as e:
                    st.error(f"Analiz servisine bağlanırken bir hata oluştu: {e}")

            # --- Stok Görsel Arama Diyaloğu ---
            @st.dialog("Stok Görsel Kütüphanesi")
            def stock_image_dialog():
                st.subheader("🖼️ Unsplash'te Görsel Ara")
                search_term = st.text_input("Aramak istediğiniz konu (İngilizce)", placeholder="e.g., coffee, business, nature")

                if search_term:
                    with st.spinner("Görseller aranıyor..."):
                        try:
                            response = requests.get(f"{BACKEND_URL}/images/search", params={'query': search_term})
                            if response.status_code == 200:
                                images = response.json()
                                if not images:
                                    st.warning("Sonuç bulunamadı.")
                                
                                # Görselleri 3'lü sütunlar halinde göster
                                cols = st.columns(3)
                                for i, img_data in enumerate(images):
                                    with cols[i % 3]:
                                        st.image(img_data['url'], caption=f"by {img_data['author']}")
                                        if st.button("Bu Görseli Seç", key=f"select_img_{img_data['id']}", use_container_width=True):
                                            # Seçilen görseli indir ve kaydet
                                            with st.spinner("Görsel indiriliyor..."):
                                                img_response = requests.get(img_data['url'])
                                                uploads_dir = "uploads"
                                                if not os.path.exists(uploads_dir): os.makedirs(uploads_dir)
                                                
                                                # Benzersiz bir dosya adı oluştur
                                                file_name = f"unsplash_{img_data['id']}.jpg"
                                                file_path = os.path.join(uploads_dir, file_name)
                                                
                                                with open(file_path, "wb") as f:
                                                    f.write(img_response.content)
                                                
                                                # Seçilen görselin yolunu session state'e kaydet
                                                st.session_state.selected_stock_image_path = file_path
                                                st.rerun()

                            else:
                                st.error(f"Görseller alınamadı: {response.text}")
                        except Exception as e:
                            st.error(f"Görsel arama servisine bağlanırken bir hata oluştu: {e}")

                if st.button("Kapat"):
                    st.rerun()


            with post_tab:
                with st.form("post_form", clear_on_submit=True):
                    # 'post' için ayrı bir session state anahtarı kullan
                    if 'ai_generated_text_post' not in st.session_state: st.session_state.ai_generated_text_post = ""
                    caption = st.text_area("Gönderi metni:", height=150, value=st.session_state.ai_generated_text_post, key="post_caption_area")
                    
                    if st.button("🤖 Yapay Zeka ile Yaz", use_container_width=True):
                        st.session_state.ai_target = 'post' # Hedefi 'post' olarak ayarla
                        ai_copilot_dialog()
                    
                    uploaded_file = st.file_uploader("Görsel seçin (JPG, PNG)", type=["jpg", "jpeg", "png"])
                    if uploaded_file and st.button("Görseli Düzenle", key="edit_post_image_button"):
                        st.session_state.editing_image_bytes = uploaded_file.getvalue()
                        st.session_state.editing_image_name = uploaded_file.name
                        image_editor_dialog()

                    templates = database.get_user_templates(user_id)
                    template_options = {t['template_name']: t['caption'] for t in templates}
                    selected_template = st.selectbox("Veya bir şablon seçin:", options=[""] + list(template_options.keys()))

                    hashtag_groups = database.get_user_hashtag_groups(user_id)
                    if hashtag_groups:
                        hashtag_options = {g['group_name']: g['hashtags'] for g in hashtag_groups}
                        hashtag_options = {"Seçim yapın...": ""} | hashtag_options
                        selected_hashtag_group = st.selectbox("Hashtag grubu ekle:", options=list(hashtag_options.keys()), key="post_hashtags")
                        if selected_hashtag_group != "Seçim yapın...":
                            st.code(hashtag_options[selected_hashtag_group])

                    submit_post = st.form_submit_button("Şimdi Paylaş", type="primary")

                    if submit_post:
                        final_caption = caption
                        if not final_caption and selected_template: # Eğer metin alanı boşsa ve şablon seçildiyse
                            final_caption = template_options[selected_template]

                        if not final_caption or not (uploaded_file or st.session_state.get('edited_image_path')):
                            st.warning("Lütfen bir gönderi metni girin (veya bir şablon seçin) ve bir görsel yükleyin.")
                        
                        if final_caption and (uploaded_file or st.session_state.get('edited_image_path')):
                            st.session_state.ai_generated_text_post = "" # İlgili formun state'ini temizle
                            st.session_state.ai_generated_hashtags = ""
                            with st.spinner("Gönderi paylaşılıyor, lütfen bekleyin..."):
                                try:
                                    # Düzenlenmiş görsel varsa onu kullan, yoksa orijinal yükleneni
                                    if st.session_state.get('edited_image_path'):
                                        file_path = st.session_state.edited_image_path
                                        del st.session_state.edited_image_path # Kullanıldıktan sonra temizle
                                    else:
                                        uploads_dir = "uploads"
                                        if not os.path.exists(uploads_dir): os.makedirs(uploads_dir)
                                        file_path = os.path.join(uploads_dir, uploaded_file.name)
                                        with open(file_path, "wb") as f:
                                            f.write(uploaded_file.getbuffer())

                                    # Platforma göre gönderi yap
                                    platform_name = managed_account['platform_name']
                                    access_token = managed_account['access_token']
                                    account_id = managed_account['account_id']

                                    if platform_name == "Facebook":
                                        platform = FacebookPlatform()
                                        platform.post(image_path=file_path, caption=final_caption, access_token=access_token, page_id=account_id)
                                    elif platform_name == "Instagram":
                                        platform = InstagramPlatform()
                                        platform.post(image_path=file_path, caption=final_caption, access_token=access_token, ig_user_id=account_id, backend_url=os.getenv("BACKEND_URL"))
                                    elif platform_name == "LinkedIn":
                                        # LinkedIn resimli gönderi API'si daha karmaşık olduğu için şimdilik metin gönderiyoruz.                                        
                                        # Resim parametresi (file_path) şimdilik kullanılmıyor.
                                        platform = LinkedInPlatform()
                                        platform.post(caption=final_caption, access_token=access_token, author_urn=account_id)
                                    
                                    st.success("Gönderiniz başarıyla paylaşıldı!")
                                except Exception as e:
                                    st.error(f"Gönderi paylaşılamadı: {e}")

            with schedule_tab:
                with st.form("schedule_form", clear_on_submit=True):
                    st.subheader("Yeni Gönderi Planla")
                    # 'schedule' için ayrı bir session state anahtarı kullan
                    if 'ai_generated_text_schedule' not in st.session_state: st.session_state.ai_generated_text_schedule = ""
                    schedule_caption = st.text_area("Gönderi metni:", height=150, value=st.session_state.ai_generated_text_schedule, key="schedule_caption_area")

                    # İçerik Kovası Seçimi
                    buckets = database.get_user_content_buckets(st.session_state.selected_brand_id)
                    bucket_options = {b['bucket_name']: b['id'] for b in buckets}
                    bucket_options = {"Kategori Seçilmedi": None} | bucket_options
                    selected_bucket_name = st.selectbox("İçerik Kovası:", options=bucket_options.keys())

                    # Pinterest için Pano seçimi
                    # Seçili hesabın platformunu bul
                    selected_account_id = managed_account['id']
                    if managed_account['platform_name'] == 'Pinterest':                        
                        # Bu çağrı cache'lenebilir
                        response = requests.get(f"{BACKEND_URL}/pinterest/boards", params={'account_id': selected_account_id})
                        if response.status_code == 200:
                            boards = response.json()
                            board_options = {b['name']: b['id'] for b in boards}
                            selected_board_name = st.selectbox("Pinterest Panosu:", options=board_options.keys())
                            st.session_state.pinterest_board_id = board_options.get(selected_board_name)
                        else:
                            st.warning("Pinterest panoları alınamadı.")

                    # En iyi zaman önerisi butonu
                    if st.button("💡 En İyi Zamanı Öner", use_container_width=True, key="suggest_time_button"):
                        best_time_dialog()


                    if st.button("🤖 Yapay Zeka ile Yaz", use_container_width=True, key="ai_button_schedule_main"):
                        st.session_state.ai_target = 'schedule' # Hedefi 'schedule' olarak ayarla
                        ai_copilot_dialog()
                    
                    # Stok görsel arama butonu
                    if st.button("🖼️ Stok Görsel Ara", use_container_width=True, key="stock_image_button"):
                        stock_image_dialog()

                    if st.session_state.get('selected_stock_image_path'):
                        st.success(f"Seçilen görsel: {os.path.basename(st.session_state.selected_stock_image_path)}")

                    schedule_uploaded_file = st.file_uploader("Görsel seçin (JPG, PNG)", type=["jpg", "jpeg", "png"], key="schedule_file")
                    if schedule_uploaded_file and st.button("Görseli Düzenle", key="edit_schedule_image_button"):
                        st.session_state.editing_image_bytes = schedule_uploaded_file.getvalue()
                        st.session_state.editing_image_name = schedule_uploaded_file.name
                        image_editor_dialog()
                    
                    alt_text_input = st.text_input("Alternatif Metin (Alt Text)", value=st.session_state.generated_alt_text, help="Görme engelli kullanıcılar için görselin açıklaması.")

                    templates = database.get_user_templates(st.session_state.selected_brand_id)
                    template_options = {t['template_name']: t['caption'] for t in templates}
                    selected_template_schedule = st.selectbox("Veya bir şablon seçin:", options=[""] + list(template_options.keys()), key="schedule_template")

                    hashtag_groups = database.get_user_hashtag_groups(st.session_state.selected_brand_id)
                    if hashtag_groups:
                        hashtag_options = {g['group_name']: g['hashtags'] for g in hashtag_groups}
                        hashtag_options = {"Seçim yapın...": ""} | hashtag_options
                        selected_hashtag_group_schedule = st.selectbox("Hashtag grubu ekle:", options=list(hashtag_options.keys()), key="schedule_hashtags")
                        if selected_hashtag_group_schedule != "Seçim yapın...":
                            st.write("Kopyalamak için tıklayın:")
                            st.code(hashtag_options[selected_hashtag_group_schedule])

                    if st.session_state.ai_generated_hashtags and st.session_state.ai_target == 'schedule':
                        st.write("AI Tarafından Önerilen Hashtag'ler:")
                        st.code(st.session_state.ai_generated_hashtags)

                    col1, col2 = st.columns(2)
                    with col1:
                        # Öneri varsa onu kullan, yoksa bugünü
                        schedule_date_val = st.session_state.get('schedule_date_suggestion', datetime.now().date())
                        schedule_date = st.date_input("Yayınlanma Tarihi", value=schedule_date_val)
                    with col2:
                        # Öneri varsa onu kullan, yoksa şimdiki zamanı
                        schedule_time_val = st.session_state.get('schedule_time_suggestion', datetime.now().time())
                        schedule_time = st.time_input("Yayınlanma Saati", value=schedule_time_val)

                    submit_schedule = st.form_submit_button("Gönderiyi Planla", type="primary")

                    if submit_schedule:
                        final_caption = schedule_caption
                        user_team = database.get_user_team(user_id)
                        
                        if not final_caption and selected_template_schedule:
                            final_caption = template_options[selected_template_schedule]
                        
                        if not final_caption or not (schedule_uploaded_file or st.session_state.get('edited_image_path') or st.session_state.get('selected_stock_image_path')):
                            st.warning("Lütfen bir gönderi metni girin (veya bir şablon seçin) ve bir görsel yükleyin.")
                        
                        if final_caption and (schedule_uploaded_file or st.session_state.get('edited_image_path') or st.session_state.get('selected_stock_image_path')):
                            # Onay akışı mantığı
                            post_status = 'Bekliyor'
                            success_message_template = "Gönderiniz {datetime} için başarıyla planlandı!"
                            if user_team and user_team['role'] == 'editor':
                                post_status = 'pending_approval'
                                success_message_template = "Gönderiniz onay için yöneticiye gönderildi!"

                            st.session_state.ai_generated_text_schedule = "" # İlgili formun state'ini temizle
                            st.session_state.ai_generated_hashtags = ""
                            # Düzenlenmiş görsel varsa onu kullan, yoksa orijinal yükleneni
                            if st.session_state.get('selected_stock_image_path'):
                                file_path = st.session_state.selected_stock_image_path
                                del st.session_state.selected_stock_image_path
                            elif st.session_state.get('edited_image_path'):
                                file_path = st.session_state.edited_image_path
                                del st.session_state.edited_image_path # Kullanıldıktan sonra temizle
                            else:
                                uploads_dir = "uploads"
                                if not os.path.exists(uploads_dir): os.makedirs(uploads_dir)
                                file_path = os.path.join(uploads_dir, schedule_uploaded_file.name)
                                with open(file_path, "wb") as f:
                                    f.write(schedule_uploaded_file.getbuffer())

                            # Tarih ve saati birleştir
                            scheduled_datetime = datetime.combine(schedule_date, schedule_time)
                            
                            platform_specific_data = None
                            if managed_account['platform_name'] == 'Pinterest':
                                platform_specific_data = json.dumps({'board_id': st.session_state.get('pinterest_board_id')})

                            bucket_id = bucket_options[selected_bucket_name]
                            database.add_scheduled_post(user_id, st.session_state.selected_brand_id, managed_account['id'], final_caption, file_path, scheduled_datetime, status=post_status, bucket_id=bucket_id, media_type=media_type, platform_specific_data=platform_specific_data, alt_text=alt_text_input)
                            st.success(success_message_template.format(datetime=scheduled_datetime.strftime('%d %B %Y, %H:%M')))
                
                st.divider()
                st.subheader("Bekleyen Planlanmış Gönderiler")

                scheduled_posts = database.get_scheduled_posts(managed_account['id'])

                if not scheduled_posts:
                    st.info("Bu hesap için bekleyen planlanmış bir gönderi bulunmuyor.")
                else:
                    for post in scheduled_posts:
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([4, 1, 1])
                            with col1:
                                st.caption(f"Planlanan Zaman: {datetime.strptime(post['scheduled_time'], '%Y-%m-%d %H:%M:%S').strftime('%d %b %Y, %H:%M')}")
                                st.write(post['caption'])
                            if post.get('media_type') == 'VIDEO' and os.path.exists(post['image_path']):
                                st.video(post['image_path'])
                            elif os.path.exists(post['image_path']):
                                    st.image(post['image_path'], width=100)

                            with col2:
                                if st.button("Düzenle", key=f"edit_post_{post['id']}", use_container_width=True):
                                    st.session_state.editing_post_id = post['id']
                                    st.rerun()
                            with col3:
                                if st.button("Sil", key=f"delete_post_{post['id']}", use_container_width=True, type="secondary"):
                                    database.delete_scheduled_post(post['id'])
                                    st.rerun() # Sayfayı yenileyerek silinen gönderiyi listeden kaldır

            with delete_tab:
                st.subheader("Hesabı Kaldır")
                st.warning(f"**DİKKAT:** '{managed_account['account_name']}' hesabını kaldırmak üzeresiniz. Bu işlem geri alınamaz.")
                
                if st.button("Bu Hesabı Kalıcı Olarak Kaldır", type="primary"):
                    database.delete_connected_account(managed_account['id'])
                    st.success(f"'{managed_account['account_name']}' hesabı başarıyla kaldırıldı.")
                    st.session_state.managing_account_id = None # Yönetim panelini kapat
                    st.rerun()
            
            if st.button("Yönetim Panelini Kapat"):
                st.session_state.managing_account_id = None
                st.rerun()

def main_app():
    """Ana Uygulama Arayüzünü (Dashboard) oluşturur."""
    user = database.get_user(st.session_state.username)
    if not user:
        st.error("Oturum hatası: Kullanıcı bulunamadı. Lütfen tekrar giriş yapın.")
        st.session_state.logged_in = False
        st.rerun()
        return
    
    user_id = user['id']
    user_team = database.get_user_team(user_id)

    # --- Header ve Ana Menü ---
    header_cols = st.columns([6, 1, 1])
    with header_cols[0]:
        main_menu_options = ["Ana Panel", "Platform Yönetimi", "İçerik Takvimi", "Raporlar", "Ayarlar"]
        main_menu_icons = ["house-door-fill", "grid-fill", "calendar-week", "graph-up", "gear"]
        
        if user_team and user_team['role'] == 'admin':
            main_menu_options.insert(3, "Onay Bekleyenler") # Adminler için özel sayfa
            main_menu_icons.insert(3, "check2-square")

        selected_main_page = option_menu(
            menu_title=None,
            options=main_menu_options,
            icons=main_menu_icons,
            orientation="horizontal",
            key="platform_menu",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent", "border-bottom": "1px solid #333"},
                "icon": {"color": "#c4a7e7", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px 5px", "--hover-color": "#3a3a5a", "border-radius": "5px"},
                "nav-link-selected": {"background-color": "#2c2c4a"},
            }
        )

    with header_cols[1]:
        unread_notifications = database.get_unread_notifications(user_id)
        with st.popover(f"🔔 ({len(unread_notifications)})", use_container_width=True):
            st.subheader("Yeni Bildirimler")
            if unread_notifications:
                for notif in unread_notifications:
                    if notif['status'] == 'success':
                        st.success(notif['message'], icon="✅")
                    else:
                        st.error(notif['message'], icon="❌")
                database.mark_notifications_as_read(user_id)
            else:
                st.info("Yeni bildiriminiz yok.")

    with header_cols[2]:
        with st.popover(f"👤 {st.session_state.username}", use_container_width=True):
            st.divider()
            if st.button("Çıkış Yap", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    st.divider()
    
    # --- Seçilen Ana Sayfaya Göre İçeriği Göster ---
    if selected_main_page == "Ana Panel":
        display_main_dashboard_page(user_id)
    elif selected_main_page == "Platform Yönetimi":
        display_platforms_page(user_id)
    elif selected_main_page == "İçerik Takvimi":
        display_calendar_view(user_id)
    elif selected_main_page == "Onay Bekleyenler":
        if user_team and user_team['role'] == 'admin':
            display_approval_queue_page(user_team)
        else:
            st.error("Bu sayfayı görüntüleme yetkiniz yok.")
    elif selected_main_page == "Raporlar":
        display_reports_page(user_id)
    elif selected_main_page == "Ayarlar":
        display_master_settings_page(user_id, st.session_state.username)

def display_hashtag_groups_page(user_id):
    """Kullanıcının hashtag gruplarını yönetebileceği bir sayfa oluşturur."""
    st.title("️#️⃣ Hashtag Grupları")
    st.write("Gönderilerinizde sık kullandığınız hashtag'leri gruplayarak zamandan kazanın.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Yeni Grup Oluştur")
        with st.form("new_hashtag_group_form", clear_on_submit=True):
            group_name = st.text_input("Grup Adı")
            hashtags = st.text_area("Hashtag'ler (aralarına boşluk koyarak yazın)", height=150, help="Örnek: #teknoloji #yazılım #geliştirici")
            if st.form_submit_button("Grubu Kaydet", type="primary"):
                if group_name and hashtags:
                    processed_hashtags = " ".join([f"#{tag.strip('#')}" for tag in hashtags.split()])
                    database.add_hashtag_group(user_id, st.session_state.selected_brand_id, group_name, processed_hashtags)
                    st.success(f"'{group_name}' grubu kaydedildi.")
                    st.rerun()
                else:
                    st.warning("Lütfen grup adı ve hashtag'leri girin.")
    
    with col2:
        st.subheader("Mevcut Gruplar")
        groups = database.get_user_hashtag_groups(st.session_state.selected_brand_id)
        if not groups:
            st.info("Henüz oluşturulmuş bir hashtag grubunuz yok.")
        else:
            for group in groups:
                with st.expander(f"{group['group_name']}"):
                    st.code(group['hashtags'])
                    if st.button("Sil", key=f"delete_group_{group['id']}", type="secondary"):
                        database.delete_hashtag_group(group['id'])
                        st.rerun()

def display_calendar_view(user_id):
    """Tüm planlanmış gönderiler için bir takvim görünümü oluşturur."""
    st.title("🗓️ İçerik Takvimi")
    st.write("Tüm platformlardaki planlanmış gönderilerinize buradan göz atabilirsiniz.")

    # --- Sürükle-Bırak ile Gönderi Oluşturma Alanı ---
    st.subheader("Yeni Gönderi Oluştur")
    st.info("Bilgisayarınızdan bir veya daha fazla görseli aşağıdaki alana sürükleyip bırakarak gönderi planlamaya başlayın.")
    
    uploaded_files = st.file_uploader(
        "Görselleri buraya sürükleyin veya seçin",
        type=["jpg", "jpeg", "png", "mp4", "mov"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    if uploaded_files:
        for uploaded_file in uploaded_files:
            col1, col2 = st.columns([1, 4])
            with col1:
                if uploaded_file.type.startswith('video'):
                    st.video(uploaded_file)
                else:
                    st.image(uploaded_file, width=100)
            with col2:
                st.write(f"**Dosya:** {uploaded_file.name}")
                # Bu özellik, gelecekte her bir görsel için ayrı planlama formu açacak şekilde geliştirilebilir.
                # Şimdilik, bu butonun bir sonraki adıma geçişi temsil ettiğini varsayalım.
                if st.button("Bu Görseli Planla", key=f"plan_{uploaded_file.name}"):
                    # Yeni gönderi formunu, bugünün tarihiyle aç
                    st.session_state.new_post_date = datetime.now().date()
                    # Yüklenen dosyayı session'da saklayarak forma taşıyabiliriz (gelecek geliştirme)
                    st.toast("Lütfen takvimin altındaki planlama formunu doldurun.")
                    st.rerun()

    # --- Yeni Gönderi Oluşturma Formu (Takvimden veya Sürükle-Bırak'tan tetiklenen) ---
    # --- Yeni Gönderi Oluşturma Formu (Takvimden tetiklenen) ---
    if st.session_state.new_post_date:
        with st.expander(f"🗓️ {st.session_state.new_post_date.strftime('%d %B %Y')} için Yeni Gönderi Planla", expanded=True):
            with st.form("calendar_new_post_form", clear_on_submit=True):
                
                user_accounts = database.get_user_accounts(st.session_state.selected_brand_id)
                if not user_accounts:
                    st.error("Gönderi planlamak için önce bir hesap bağlamalısınız.")
                else:
                    account_options = {f"{acc['platform_name']} - {acc['account_name']}": acc['id'] for acc in user_accounts}
                    selected_account_display = st.selectbox("Hangi hesaptan paylaşılacak?", options=account_options.keys())
                    
                    caption = st.text_area("Gönderi metni:", height=100)
                    uploaded_file = st.file_uploader("Görsel veya Video Yükle", type=["jpg", "jpeg", "png", "mp4", "mov"])
                    time_for_post = st.time_input("Yayınlanma Saati", value=datetime.now().time())

                    form_col1, form_col2 = st.columns([1,1])
                    with form_col1:
                        if st.form_submit_button("Planla", type="primary", use_container_width=True):
                            if selected_account_display and caption and uploaded_file:
                                account_id = account_options[selected_account_display]
                                
                                uploads_dir = "uploads"
                                if not os.path.exists(uploads_dir): os.makedirs(uploads_dir)
                                file_path = os.path.join(uploads_dir, uploaded_file.name)
                                with open(file_path, "wb") as f: f.write(uploaded_file.getbuffer())
                                
                                media_type = 'IMAGE'
                                if uploaded_file.type.startswith('video'):
                                    media_type = 'VIDEO'

                                scheduled_datetime = datetime.combine(st.session_state.new_post_date, time_for_post)
                                database.add_scheduled_post(user_id, st.session_state.selected_brand_id, account_id, caption, file_path, scheduled_datetime, media_type=media_type, platform_specific_data=None, alt_text=None)
                                st.success(f"Gönderiniz {scheduled_datetime.strftime('%d %B %Y, %H:%M')} için başarıyla planlandı!")
                                st.session_state.new_post_date = None
                                st.rerun()
                            else:
                                st.warning("Lütfen tüm alanları doldurun.")
                    with form_col2:
                        if st.form_submit_button("İptal", use_container_width=True):
                            st.session_state.new_post_date = None
                            st.rerun()

    st.divider()

    posts = database.get_all_scheduled_posts_for_brand(st.session_state.selected_brand_id)

    # Renkleri ve ikonları birleştirelim
    buckets = {b['id']: b for b in database.get_user_content_buckets(st.session_state.selected_brand_id)}
    calendar_events = []
    platform_colors = {
        "Facebook": "#1877F2",
        "Instagram": "#E4405F",
        "X (Twitter)": "#1DA1F2",
        "LinkedIn": "#0A66C2",
        "Pinterest": "#E60023",
        "TikTok": "#000000",
        "YouTube": "#FF0000",
    }
    platform_icons = {
        "Facebook": "🇫🇧",
        "Instagram": "📸",
        "X (Twitter)": "🐦",
        "LinkedIn": "💼",
        "Pinterest": "📌",
        "TikTok": "#000000",
        "YouTube": "#FF0000",
    }

    for post in posts:
        event = {
            # Başlığa platforma özel emoji ekleyerek okunabilirliği artır
            "title": f"{platform_icons.get(post['platform_name'], '📝')} {post['caption'][:25]}...",
            # Eğer gönderinin bir kovası varsa, onun rengini kullan; yoksa platform rengini kullan
            "color": buckets.get(post['bucket_id'], {}).get('color') or platform_colors.get(post['platform_name'], "#808080"),
            "start": post['scheduled_time'],
            "end": post['scheduled_time'],
            "extendedProps": {
                "post_id": post['id'],
                "caption": post['caption'],
                "image_path": post['image_path'],
                "account_name": post['account_name'],
                "account_id": post['account_id'] # Yönetim için gerekli
            }
        }
        calendar_events.append(event)

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "initialView": "dayGridMonth",
        "height": "700px", # Takvimin yüksekliğini sabitliyoruz
        "selectable": True,
        "editable": True, # Sürükle-bırak için temel
        "showNonCurrentDates": False, # Sadece mevcut ayı göster
    }


    calendar_callback = calendar(events=calendar_events, options=calendar_options)

    # --- Takvim Geri Bildirimlerini (Callback) İşleme ---

    # Bir gönderi sürüklenip bırakıldığında
    if calendar_callback and 'eventDrop' in calendar_callback:
        dropped_event = calendar_callback['eventDrop']['event']
        post_id = dropped_event['extendedProps']['post_id']
        new_start_time_str = dropped_event['start']
        # Saat dilimi bilgisini ('Z') kaldırıp datetime nesnesine çevir
        new_start_time = datetime.fromisoformat(new_start_time_str.replace('Z', ''))
        database.reschedule_post(post_id, new_start_time)
        st.toast(f"Gönderi {new_start_time.strftime('%d %b, %H:%M')} tarihine yeniden zamanlandı!", icon="🗓️")

    # Bir gönderiye tıklandığında
    if calendar_callback and 'eventClick' in calendar_callback:
        clicked_event = calendar_callback['eventClick']['event']
        # Takvimden bir gönderi seçildiğinde, düzenleme modunu sıfırla
        if 'post_id' in clicked_event['extendedProps'] and st.session_state.editing_post_id != clicked_event['extendedProps']['post_id']:
            st.session_state.editing_post_id = clicked_event['extendedProps']['post_id']
            st.session_state.calendar_edit_mode = False # Her yeni tıklamada düzenleme modunu kapat
            st.rerun()

    # --- Gönderi Detayı/Düzenleme (Artık Kenar Çubuğunda Değil) ---
    if st.session_state.editing_post_id:
        post_to_manage = database.get_scheduled_post_by_id(st.session_state.editing_post_id)
        if post_to_manage:
            with st.expander("Gönderi Detayları/Düzenle", expanded=True):
                if st.session_state.calendar_edit_mode:
                    # Düzenleme Modu
                    with st.form("calendar_edit_form"):
                        st.subheader("Gönderiyi Düzenle")
                        edited_caption = st.text_area("Metin:", value=post_to_manage['caption'], height=150)
                        edited_date = st.date_input("Tarih:", value=datetime.strptime(post_to_manage['scheduled_time'], '%Y-%m-%d %H:%M:%S').date())
                        edited_time = st.time_input("Saat:", value=datetime.strptime(post_to_manage['scheduled_time'], '%Y-%m-%d %H:%M:%S').time())
                        
                        if st.form_submit_button("Kaydet", type="primary"):
                            edited_datetime = datetime.combine(edited_date, edited_time)
                            database.update_scheduled_post(post_to_manage['id'], edited_caption, post_to_manage['image_path'], edited_datetime)
                            st.success("Gönderi güncellendi!")
                            st.session_state.calendar_edit_mode = False
                            st.rerun()
                        if st.form_submit_button("İptal"):
                            st.session_state.calendar_edit_mode = False
                            st.rerun()
                else:
                    # Detay Görüntüleme Modu
                    st.subheader("Gönderi Detayı")
                    st.info(f"**Hesap:** {post_to_manage['account_name']}")
                    st.write(post_to_manage['caption'])
                    if os.path.exists(post_to_manage['image_path']):
                        st.image(post_to_manage['image_path'])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("Düzenle", use_container_width=True):
                            st.session_state.calendar_edit_mode = True
                            st.rerun()
                    with col2:
                        if st.button("Sil", type="secondary", use_container_width=True):
                            database.delete_scheduled_post(st.session_state.editing_post_id)
                            st.success("Gönderi silindi!")
                            st.session_state.editing_post_id = None
                            st.rerun()
                    with col3:
                        if st.button("Detayları Kapat", use_container_width=True):
                            st.session_state.editing_post_id = None
                            st.rerun()
                
                # --- Takım İçi Notlar ---
                st.divider()
                st.subheader("Takım İçi Notlar")
                notes = database.get_post_notes(post_to_manage['id'])
                if not notes:
                    st.caption("Bu gönderi için henüz not eklenmemiş.")
                for note in notes:
                    note_time = datetime.strptime(note['created_at'], '%Y-%m-%d %H:%M:%S.%f' if '.' in note['created_at'] else '%Y-%m-%d %H:%M:%S').strftime('%d %b, %H:%M')
                    st.caption(f"**{note['username']}** - {note_time}")
                    st.markdown(f"> {note['note_text']}")

                with st.form(f"note_form_{post_to_manage['id']}", clear_on_submit=True):
                    new_note = st.text_area("Yeni not ekle:", label_visibility="collapsed", placeholder="Bu gönderi hakkında bir not ekle...")
                    if st.form_submit_button("Not Ekle"):
                        database.add_post_note(post_to_manage['id'], user_id, new_note)
                        st.rerun()

def main_app():
    """Ana Uygulama Arayüzünü (Dashboard) oluşturur."""
    user = database.get_user(st.session_state.username)
    if not user:
        st.error("Oturum hatası: Kullanıcı bulunamadı. Lütfen tekrar giriş yapın.")
        st.session_state.logged_in = False
        st.rerun()
        return
    
    user_id = user['id']
    user_team = database.get_user_team(user_id) or {}

    # --- Marka Seçimi ---
    brands = []
    if user_team:
        brands = database.get_brands_for_team(user_team['team_id'])
    
    brand_options = {brand['brand_name']: brand['id'] for brand in brands}
    
    # Eğer seçili bir marka yoksa, kullanıcının son eriştiği markayı veya ilk markayı seç
    if not st.session_state.selected_brand_id and brands:
        last_brand_id = user_team.get('last_accessed_brand_id')
        if last_brand_id in brand_options.values():
            st.session_state.selected_brand_id = last_brand_id
        else:
            st.session_state.selected_brand_id = brands[0]['id']

    def on_brand_change():
        new_brand_id = st.session_state.brand_selector
        st.session_state.selected_brand_id = new_brand_id
        database.set_last_accessed_brand(user_id, new_brand_id)

    # --- Header ve Ana Menü ---
    header_cols = st.columns([4, 2, 1, 1])
    with header_cols[0]:
        # İzinlere göre menüyü oluştur
        main_menu_items = {
            "Ana Panel": {"icon": "house-door-fill", "permission": True},
            "Platform Yönetimi": {"icon": "grid-fill", "permission": True},
            "İçerik Takvimi": {"icon": "calendar-week", "permission": user_team.get('can_post', True) if user_team else True},
            "Onay Bekleyenler": {"icon": "check2-square", "permission": user_team.get('can_approve', False) if user_team else False},
            "Toplu Yükleme": {"icon": "upload", "permission": user_team.get('can_post', True) if user_team else True},
            "Raporlar": {"icon": "graph-up", "permission": user_team.get('can_view_reports', True) if user_team else True},
            "Ayarlar": {"icon": "gear", "permission": True},
        }

        main_menu_options = [item for item, props in main_menu_items.items() if props['permission']]
        main_menu_icons = [props['icon'] for item, props in main_menu_items.items() if props['permission']]
        
        selected_main_page = option_menu(
            menu_title=None,
            options=main_menu_options,
            icons=main_menu_icons,
            orientation="horizontal",
            key="platform_menu",
            styles={
                "container": {"padding": "0!important", "background-color": "transparent", "border-bottom": "1px solid #333"},
                "icon": {"color": "#c4a7e7", "font-size": "18px"},
                "nav-link": {"font-size": "16px", "text-align": "center", "margin": "0px 5px", "--hover-color": "#3a3a5a", "border-radius": "5px"},
                "nav-link-selected": {"background-color": "#2c2c4a"},
            }
        )

    with header_cols[1]:
        if brands:
            # Marka adlarını ve ID'lerini al
            brand_names = list(brand_options.keys())
            brand_ids = list(brand_options.values())
            
            # Mevcut seçili markanın index'ini bul
            try:
                current_index = brand_ids.index(st.session_state.selected_brand_id)
            except (ValueError, TypeError):
                current_index = 0

            st.selectbox("Marka:", options=brand_ids, format_func=lambda x: {v: k for k, v in brand_options.items()}[x], index=current_index, key="brand_selector", on_change=on_brand_change, label_visibility="collapsed")

    with header_cols[2]:
        unread_notifications = database.get_unread_notifications(user_id)
        with st.popover(f"🔔 ({len(unread_notifications)})", use_container_width=True):
            st.subheader("Yeni Bildirimler")
            if unread_notifications:
                for notif in unread_notifications:
                    if notif['status'] == 'success':
                        st.success(notif['message'], icon="✅")
                    else:
                        st.error(notif['message'], icon="❌")
                database.mark_notifications_as_read(user_id)
            else:
                st.info("Yeni bildiriminiz yok.")

    with header_cols[3]:
        with st.popover(f"👤 {st.session_state.username}", use_container_width=True):
            st.divider()
            if st.button("Çıkış Yap", use_container_width=True):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    st.divider()
    
    # --- Seçilen Ana Sayfaya Göre İçeriği Göster ---
    # Eğer marka seçilmemişse, sadece Ayarlar sayfasına izin ver
    if not st.session_state.selected_brand_id and selected_main_page != "Ayarlar":
        st.warning("Başlamak için lütfen 'Ayarlar > Marka Yönetimi' bölümünden bir marka oluşturun veya yukarıdan bir marka seçin.")
    elif selected_main_page == "Ana Panel":
        display_main_dashboard_page(user_id)
    elif selected_main_page == "Platform Yönetimi":
        display_platforms_page(user_id)
    elif selected_main_page == "İçerik Takvimi":
        display_calendar_view(user_id)
    elif selected_main_page == "Toplu Yükleme":
        display_bulk_upload_page(user_id)
    elif selected_main_page == "Rakip Analizi":
        display_competitor_analysis_page(user_id) # Rakip analizi de bir rapor türü olduğu için can_view_reports'a bağlanabilir
    elif selected_main_page == "Gelen Kutusu":
        display_social_inbox_page(user_id)
    elif selected_main_page == "Onay Bekleyenler":
        if user_team and user_team.get('can_approve', False):
            display_approval_queue_page(user_team)
        else:
            st.error("Bu sayfayı görüntüleme yetkiniz yok.")
    elif selected_main_page == "Raporlar":
        display_reports_page(user_id)
    elif selected_main_page == "Ayarlar":
        # Ayarlar sayfasında takım yönetimi sekmesi de can_manage_team'e bağlanabilir
        display_master_settings_page(user_id, st.session_state.username)

# --- Uygulama Akışı ---
set_page_config() # Sayfa yapılandırmasını çağır

# Sayfa yenilendiğinde oturumu URL'den kurtarmayı dene
if not st.session_state.logged_in:
    query_params = st.query_params
    session_id_from_url = query_params.get("session_id")
    if session_id_from_url:
        user = database.get_user_by_session_id(session_id_from_url)
        if user:
            st.session_state.logged_in = True
            st.session_state.username = user['username']
            st.session_state.theme = user['theme']

if st.session_state.logged_in:
    main_app()
else:
    login_page()