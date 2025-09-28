import sqlite3
from datetime import datetime
import contextlib

DB_FILE = "sosyal_orkestra.db"

@contextlib.contextmanager
def get_db_connection():
    """Veritabanı bağlantısını yöneten bir context manager."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def _update_schema(conn):
    """Veritabanı şemasını kontrol eder ve eksik sütunları ekler."""
    cursor = conn.cursor()
    
    # 'users' tablosundaki sütunları kontrol et
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [row['name'] for row in cursor.fetchall()]
    
    if 'otp_secret' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN otp_secret TEXT")
        print("🔧 'users' tablosuna 'otp_secret' sütunu eklendi.")
    if 'otp_enabled' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN otp_enabled BOOLEAN DEFAULT 0")
        print("🔧 'users' tablosuna 'otp_enabled' sütunu eklendi.")
    if 'theme' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'light'")
        print("🔧 'users' tablosuna 'theme' sütunu eklendi.")
    if 'layout_theme' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN layout_theme TEXT DEFAULT 'modern_v1'")
        print("🔧 'users' tablosuna 'layout_theme' sütunu eklendi.")
    if 'session_id' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN session_id TEXT")
        print("🔧 'users' tablosuna 'session_id' sütunu eklendi.")
    
    cursor.execute("PRAGMA table_info(connected_accounts)")
    account_columns = [row['name'] for row in cursor.fetchall()]
    if 'follower_count' not in account_columns:
        cursor.execute("ALTER TABLE connected_accounts ADD COLUMN follower_count INTEGER DEFAULT 0")
        print("🔧 'connected_accounts' tablosuna 'follower_count' sütunu eklendi.")
    if 'total_engagement' not in account_columns:
        cursor.execute("ALTER TABLE connected_accounts ADD COLUMN total_engagement INTEGER DEFAULT 0")
        print("🔧 'connected_accounts' tablosuna 'total_engagement' sütunu eklendi.")
    if 'total_reach' not in account_columns:
        cursor.execute("ALTER TABLE connected_accounts ADD COLUMN total_reach INTEGER DEFAULT 0")
        print("🔧 'connected_accounts' tablosuna 'total_reach' sütunu eklendi.")

    cursor.execute("PRAGMA table_info(scheduled_posts)")
    post_columns = [row['name'] for row in cursor.fetchall()]
    if 'media_type' not in post_columns:
        cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN media_type TEXT DEFAULT 'IMAGE'")
        print("🔧 'scheduled_posts' tablosuna 'media_type' sütunu eklendi.")
    if 'platform_specific_data' not in post_columns:
        cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN platform_specific_data TEXT") # JSON formatında veri tutacak
        print("🔧 'scheduled_posts' tablosuna 'platform_specific_data' sütunu eklendi.")
    if 'alt_text' not in post_columns:
        cursor.execute("ALTER TABLE scheduled_posts ADD COLUMN alt_text TEXT")
        print("🔧 'scheduled_posts' tablosuna 'alt_text' sütunu eklendi.")

    cursor.execute("PRAGMA table_info(team_members)")
    member_columns = [row['name'] for row in cursor.fetchall()]
    if 'can_post' not in member_columns:
        cursor.execute("ALTER TABLE team_members ADD COLUMN can_post BOOLEAN DEFAULT 1")
        cursor.execute("ALTER TABLE team_members ADD COLUMN can_approve BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE team_members ADD COLUMN can_view_reports BOOLEAN DEFAULT 1")
        cursor.execute("ALTER TABLE team_members ADD COLUMN can_manage_team BOOLEAN DEFAULT 0")
        # Eski 'role' sütununu artık kullanmayacağız ama veri kaybı olmasın diye silmiyoruz.
        # Yeni kurulumlarda bu sütun hiç olmayacak.
        print("🔧 'team_members' tablosuna detaylı izin sütunları eklendi.")
    
    cursor.execute("PRAGMA table_info(messages)")
    message_columns = [row['name'] for row in cursor.fetchall()]
    if 'is_hidden' not in message_columns:
        cursor.execute("ALTER TABLE messages ADD COLUMN is_hidden BOOLEAN DEFAULT 0")
        cursor.execute("ALTER TABLE messages ADD COLUMN is_flagged BOOLEAN DEFAULT 0")

    # Diğer tablolara brand_id ekle
    tables_to_update = ['connected_accounts', 'scheduled_posts', 'content_templates', 
                        'hashtag_groups', 'conversations', 'competitors', 'moderation_rules', 'content_buckets']
    for table in tables_to_update:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row['name'] for row in cursor.fetchall()]
        if 'brand_id' not in columns:
            # ON DELETE CASCADE, bir marka silindiğinde ona ait tüm verilerin silinmesini sağlar.
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN brand_id INTEGER REFERENCES brands(id) ON DELETE CASCADE")
            print(f"🔧 '{table}' tablosuna 'brand_id' sütunu eklendi.")

    # team_members tablosunda son erişilen markayı tutmak için
    cursor.execute("PRAGMA table_info(team_members)")
    member_columns = [row['name'] for row in cursor.fetchall()]
    if 'last_accessed_brand_id' not in member_columns:
        cursor.execute("ALTER TABLE team_members ADD COLUMN last_accessed_brand_id INTEGER REFERENCES brands(id)")
        print("🔧 'team_members' tablosuna 'last_accessed_brand_id' sütunu eklendi.")



def init_db():
    """Veritabanını başlatır ve gerekli tüm tabloları oluşturur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            otp_secret TEXT,
            otp_enabled BOOLEAN DEFAULT 0,
            theme TEXT DEFAULT 'light',
            layout_theme TEXT DEFAULT 'modern_v1',
            session_id TEXT
        )
    """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS connected_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            platform_name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            account_name TEXT,
            access_token TEXT NOT NULL, -- Platform API'si için erişim anahtarı
            refresh_token TEXT,
            token_expiry DATETIME,
            is_active BOOLEAN DEFAULT 1,
            follower_count INTEGER DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            total_reach INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
    """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            caption TEXT NOT NULL,
            image_path TEXT NOT NULL,
            scheduled_time DATETIME NOT NULL,
            is_posted BOOLEAN DEFAULT 0,
            platform_post_id TEXT, -- Platformdan dönen gönderi ID'si
            status TEXT DEFAULT 'Bekliyor',
            bucket_id INTEGER,
            media_type TEXT DEFAULT 'IMAGE',
            platform_specific_data TEXT,
            alt_text TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (account_id) REFERENCES connected_accounts (id),
            FOREIGN KEY (bucket_id) REFERENCES content_buckets(id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
    """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL, -- 'success' or 'error'
            is_read BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            template_name TEXT NOT NULL,
            caption TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS hashtag_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            group_name TEXT NOT NULL,
            hashtags TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES users (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT, -- Geriye dönük uyumluluk için. Yeni sistemde kullanılmayacak.
            can_post BOOLEAN DEFAULT 1,
            can_approve BOOLEAN DEFAULT 0,
            can_view_reports BOOLEAN DEFAULT 1,
            can_manage_team BOOLEAN DEFAULT 0,
            last_accessed_brand_id INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        # Bu tablo, tüm platformlardan gelen mesajları/yorumları birleştirecek
        # Gerçek entegrasyonu gelecekte yapılacak, şimdilik altyapısı kuruluyor.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            connected_account_id INTEGER NOT NULL,
            platform_conversation_id TEXT UNIQUE NOT NULL, -- e.g., post_id for comments
            snippet TEXT,
            last_updated DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE,
            FOREIGN KEY (connected_account_id) REFERENCES connected_accounts (id)
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            platform_message_id TEXT UNIQUE NOT NULL,
            sender_name TEXT,
            sender_id TEXT,
            message TEXT,
            timestamp DATETIME,
            is_hidden BOOLEAN DEFAULT 0,
            is_flagged BOOLEAN DEFAULT 0,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS post_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            note_text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES scheduled_posts (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            platform_name TEXT NOT NULL,
            competitor_username TEXT NOT NULL,
            competitor_id TEXT, -- Platformdan alınan ID
            UNIQUE(user_id, platform_name, competitor_username),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS competitor_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            snapshot_date DATE NOT NULL,
            follower_count INTEGER,
            engagement_rate REAL,
            FOREIGN KEY (competitor_id) REFERENCES competitors (id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderation_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            keyword TEXT NOT NULL,
            action TEXT NOT NULL, -- 'hide' or 'flag'
            UNIQUE(user_id, keyword),
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL,
            brand_name TEXT NOT NULL,
            FOREIGN KEY (team_id) REFERENCES teams (id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS content_buckets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brand_id INTEGER NOT NULL,
            bucket_name TEXT NOT NULL,
            color TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE
        )
        """)

        conn.commit()
        
        # Şema güncellemelerini uygula
        _update_schema(conn)

        print("🗃️ Çoklu kullanıcı veritabanı başarıyla başlatıldı.")

def add_user(username, password_hash):
    """Veritabanına yeni bir kullanıcı ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            user_id = cursor.lastrowid
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None

def get_user(username):
    """Kullanıcı adına göre kullanıcı bilgilerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return user

def get_user_by_session_id(session_id):
    """Oturum ID'sine göre kullanıcı bilgilerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE session_id = ?", (session_id,))
        user = cursor.fetchone()
        return user

def update_user_session_id(user_id, session_id):
    """Bir kullanıcının oturum ID'sini günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET session_id = ? WHERE id = ?",
            (session_id, user_id)
        )
        conn.commit()

def add_connected_account(user_id, brand_id, platform_name, account_id, account_name, access_token):
    """Veritabanına yeni bir bağlı hesap ekler veya mevcut olanı günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM connected_accounts WHERE brand_id = ? AND account_id = ?", (brand_id, account_id))
        if cursor.fetchone():
            cursor.execute("UPDATE connected_accounts SET access_token = ? WHERE brand_id = ? AND account_id = ?", (access_token, brand_id, account_id))
        else:
            cursor.execute("INSERT INTO connected_accounts (user_id, brand_id, platform_name, account_id, account_name, access_token) VALUES (?, ?, ?, ?, ?, ?)",
                           (user_id, brand_id, platform_name, account_id, account_name, access_token))
        conn.commit()

def get_user_accounts(brand_id, platform_name=None, user_id=None): # user_id geriye dönük uyumluluk için eklendi
    """Bir kullanıcının bağlı hesaplarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM connected_accounts WHERE brand_id = ?"
        params = [brand_id] # Sorgu her zaman brand_id'ye göre yapılır

        if platform_name:
            query += " AND platform_name = ?"
            params.append(platform_name)

        cursor.execute(query, params)
        accounts = cursor.fetchall()
        return [dict(row) for row in accounts]

def delete_connected_account(account_id):
    """Verilen ID'ye sahip bağlı hesabı veritabanından siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM connected_accounts WHERE id = ?", (account_id,))
        conn.commit()
        print(f"✅ {account_id} ID'li hesap veritabanından silindi.")

def add_scheduled_post(user_id, brand_id, account_id, caption, image_path, scheduled_time, status='Bekliyor', bucket_id=None, media_type='IMAGE', platform_specific_data=None, alt_text=None):
    """Veritabanına yeni bir planlanmış gönderi ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scheduled_posts (user_id, brand_id, account_id, caption, image_path, scheduled_time, status, bucket_id, media_type, platform_specific_data, alt_text) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, brand_id, account_id, caption, image_path, scheduled_time, status, bucket_id, media_type, platform_specific_data, alt_text)
        )
        conn.commit()
        print(f"✅ {scheduled_time} için yeni gönderi '{status}' durumuyla planlandı.")

def update_post_status(post_id, is_posted, status, platform_post_id=None):
    """Bir gönderinin durumunu günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE scheduled_posts SET is_posted = ?, status = ?, platform_post_id = ? WHERE id = ?",
            (is_posted, status, platform_post_id, post_id)
        )
        conn.commit()

def get_scheduled_posts(account_id):
    """Bir hesaba ait, henüz yayınlanmamış tüm planlı gönderileri getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM scheduled_posts WHERE account_id = ? AND is_posted = 0 ORDER BY scheduled_time ASC",
            (account_id,)
        )
        posts = cursor.fetchall()
        return [dict(row) for row in posts]

def delete_scheduled_post(post_id):
    """Verilen ID'ye sahip planlanmış gönderiyi siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_posts WHERE id = ?", (post_id,))
        conn.commit()
        print(f"✅ Planlanmış gönderi (ID: {post_id}) başarıyla silindi.")

def get_scheduled_post_by_id(post_id):
    """Verilen ID'ye sahip tek bir planlanmış gönderiyi getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scheduled_posts WHERE id = ?", (post_id,))
        post = cursor.fetchone()
        return dict(post) if post else None

def update_scheduled_post(post_id, caption, image_path, scheduled_time):
    """Verilen ID'ye sahip planlanmış gönderiyi günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE scheduled_posts SET caption = ?, image_path = ?, scheduled_time = ? WHERE id = ?",
            (caption, image_path, scheduled_time, post_id)
        )
        conn.commit()
        print(f"✅ Planlanmış gönderi (ID: {post_id}) başarıyla güncellendi.")

def reschedule_post(post_id, new_scheduled_time):
    """Bir planlanmış gönderinin sadece zamanını günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE scheduled_posts SET scheduled_time = ? WHERE id = ?",
            (new_scheduled_time, post_id)
        )
        conn.commit()
        print(f"✅ Planlanmış gönderi (ID: {post_id}) {new_scheduled_time} tarihine yeniden zamanlandı.")

def get_all_scheduled_posts_for_brand(brand_id):
    """Bir kullanıcıya ait, henüz yayınlanmamış tüm planlı gönderileri platform bilgisiyle birlikte getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
        SELECT p.*, ca.platform_name, ca.account_name
        FROM scheduled_posts p
        JOIN connected_accounts ca ON p.account_id = ca.id
        WHERE p.brand_id = ? AND p.is_posted = 0
        """, (brand_id,)
        )
        posts = cursor.fetchall()
        return [dict(row) for row in posts]

def get_posted_posts_for_user(brand_id, platforms=None, start_date=None, end_date=None):
    """Bir kullanıcıya ait, yayınlanmış veya hatalı tüm gönderileri filtreleyerek getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
        SELECT p.*, ca.platform_name, ca.account_name
        FROM scheduled_posts p
        JOIN connected_accounts ca ON p.account_id = ca.id
        WHERE p.brand_id = ? AND p.is_posted = 1
        """
        params = [brand_id]

        if platforms:
            placeholders = ','.join('?' for _ in platforms)
            query += f" AND ca.platform_name IN ({placeholders})"
            params.extend(platforms)

        if start_date:
            query += " AND date(p.scheduled_time) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(p.scheduled_time) <= date(?)"
            params.append(end_date)

        query += " ORDER BY p.scheduled_time DESC"
        cursor.execute(query, params)
        posts = cursor.fetchall()
        return [dict(row) for row in posts]

def get_user_analytics_data(brand_id):
    """Kullanıcının analiz verilerini toplar."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Toplam bağlı hesap sayısı
        cursor.execute("SELECT COUNT(*) FROM connected_accounts WHERE brand_id = ?", (brand_id,))
        total_accounts = cursor.fetchone()[0]

        # Toplam yayınlanmış gönderi sayısı
        cursor.execute("SELECT COUNT(*) FROM scheduled_posts WHERE brand_id = ? AND status = 'Yayınlandı'", (brand_id,))
        total_posts = cursor.fetchone()[0]

        # Platforma göre gönderi dağılımı
        cursor.execute("""
            SELECT ca.platform_name, COUNT(p.id) as count
            FROM scheduled_posts p
            JOIN connected_accounts ca ON p.account_id = ca.id
            WHERE p.brand_id = ? AND p.status = 'Yayınlandı'
            GROUP BY ca.platform_name
        """, (brand_id,))
        posts_by_platform = cursor.fetchall()

        # Son 30 gündeki gönderi dağılımı
        cursor.execute("""
            SELECT date(scheduled_time) as post_date, COUNT(id) as count
            FROM scheduled_posts
            WHERE brand_id = ? AND status = 'Yayınlandı' AND scheduled_time >= date('now', '-30 days')
            GROUP BY post_date
            ORDER BY post_date ASC
        """, (brand_id,))
        posts_over_time = cursor.fetchall()

        return {
            "total_accounts": total_accounts,
            "total_posts": total_posts,
            "posts_by_platform": [dict(row) for row in posts_by_platform],
            "posts_over_time": [dict(row) for row in posts_over_time]
        }

def update_user_password(user_id, new_password_hash):
    """Bir kullanıcının parolasını günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user_id)
        )
        conn.commit()
        print(f"✅ Kullanıcı (ID: {user_id}) parolası güncellendi.")

def update_user_theme(user_id, theme):
    """Bir kullanıcının tema tercihini günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET theme = ? WHERE id = ?",
            (theme, user_id)
        )
        conn.commit()
        print(f"✅ Kullanıcı (ID: {user_id}) teması {theme} olarak güncellendi.")

def update_user_layout_theme(user_id, layout_theme):
    """Bir kullanıcının arayüz tema tercihini günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET layout_theme = ? WHERE id = ?",
            (layout_theme, user_id)
        )
        conn.commit()

def enable_otp(user_id, otp_secret):
    """Bir kullanıcı için 2FA'yı etkinleştirir ve sırrı kaydeder."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET otp_secret = ?, otp_enabled = 1 WHERE id = ?",
            (otp_secret, user_id)
        )
        conn.commit()

def disable_otp(user_id):
    """Bir kullanıcı için 2FA'yı devre dışı bırakır."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET otp_secret = NULL, otp_enabled = 0 WHERE id = ?", (user_id,))
        conn.commit()

def add_notification(user_id, message, status):
    """Veritabanına yeni bir bildirim ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO notifications (user_id, message, status) VALUES (?, ?, ?)",
            (user_id, message, status)
        )
        conn.commit()

def get_unread_notifications(user_id):
    """Bir kullanıcının okunmamış bildirimlerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def mark_notifications_as_read(user_id):
    """Bir kullanıcının tüm bildirimlerini okundu olarak işaretler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def add_template(user_id, brand_id, template_name, caption):
    """Veritabanına yeni bir içerik şablonu ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO content_templates (user_id, brand_id, template_name, caption) VALUES (?, ?, ?, ?)",
            (user_id, brand_id, template_name, caption)
        )
        conn.commit()

def get_user_templates(brand_id):
    """Bir kullanıcının tüm içerik şablonlarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM content_templates WHERE brand_id = ? ORDER BY template_name ASC", (brand_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_template(template_id):
    """Verilen ID'ye sahip şablonu siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM content_templates WHERE id = ?", (template_id,))
        conn.commit()

def add_hashtag_group(user_id, brand_id, group_name, hashtags):
    """Veritabanına yeni bir hashtag grubu ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO hashtag_groups (user_id, brand_id, group_name, hashtags) VALUES (?, ?, ?, ?)",
            (user_id, brand_id, group_name, hashtags)
        )
        conn.commit()

def get_user_hashtag_groups(brand_id):
    """Bir kullanıcının tüm hashtag gruplarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM hashtag_groups WHERE brand_id = ? ORDER BY group_name ASC", (brand_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_hashtag_group(group_id):
    """Verilen ID'ye sahip hashtag grubunu siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hashtag_groups WHERE id = ?", (group_id,))
        conn.commit()

def update_follower_count(account_id, count):
    """Bir hesabın takipçi sayısını günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE connected_accounts SET follower_count = ? WHERE id = ?", (count, account_id))
        conn.commit()

def update_account_metrics(account_id, engagement=None, reach=None):
    """Bir hesabın etkileşim ve erişim metriklerini günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if engagement is not None:
            cursor.execute("UPDATE connected_accounts SET total_engagement = ? WHERE id = ?", (engagement, account_id))
        if reach is not None:
            cursor.execute("UPDATE connected_accounts SET total_reach = ? WHERE id = ?", (reach, account_id))
        conn.commit()

def get_main_dashboard_data(brand_id):
    """Ana Panel için gerekli olan verileri toplar."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Toplam takipçi sayısı
        cursor.execute("SELECT SUM(follower_count) FROM connected_accounts WHERE brand_id = ?", (brand_id,))
        total_followers = cursor.fetchone()[0] or 0

        # Toplam etkileşim ve erişim
        cursor.execute("SELECT SUM(total_engagement), SUM(total_reach) FROM connected_accounts WHERE brand_id = ?", (brand_id,))
        metrics = cursor.fetchone()
        total_engagement = metrics[0] or 0
        total_reach = metrics[1] or 0

        # Toplam yayınlanmış gönderi sayısı
        cursor.execute("SELECT COUNT(*) FROM scheduled_posts WHERE brand_id = ? AND status = 'Yayınlandı'", (brand_id,))
        total_posts = cursor.fetchone()[0]

        # Son 5 gönderi
        cursor.execute("SELECT p.*, ca.platform_name FROM scheduled_posts p JOIN connected_accounts ca ON p.account_id = ca.id WHERE p.brand_id = ? AND p.is_posted = 1 ORDER BY p.scheduled_time DESC LIMIT 5", (brand_id,))
        recent_posts = [dict(row) for row in cursor.fetchall()]

        return {
            "total_followers": total_followers,
            "total_engagement": total_engagement,
            "total_reach": total_reach,
            "total_posts": total_posts,
            "recent_posts": recent_posts
        }

def get_post_performance_data(brand_id):
    """
    Analiz için kullanıcının yayınlanmış tüm gönderilerinin performans verilerini getirir.
    Not: Gerçek etkileşim verileri (beğeni, yorum vb.) gelecekte eklenecektir.
    Şimdilik, analiz altyapısını kurmak için zaman damgalarını kullanıyoruz.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Gerçek etkileşim verileri eklendiğinde, bu sorgu o verileri de içerecek şekilde güncellenmelidir.
        # Örnek: SELECT scheduled_time, likes, comments FROM ...
        cursor.execute(
            "SELECT scheduled_time FROM scheduled_posts WHERE brand_id = ? AND status = 'Yayınlandı'",
            (brand_id,)
        )
        posts = cursor.fetchall()
        # Her gönderi için rastgele bir "etkileşim puanı" oluşturalım
        import random
        return [{"time": row['scheduled_time'], "engagement": random.randint(50, 1000)} for row in posts]

def get_bucket_performance_data(brand_id):
    """
    Kullanıcının içerik kovalarının performansını analiz eder.
    Her bir kovadaki gönderilerin toplam (simüle edilmiş) etkileşimini döndürür.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Bu sorgu, her bir kovaya ait gönderileri ve bu gönderilere ait (simüle edilmiş) etkileşimleri toplar.
        # Gerçek etkileşim verisi eklendiğinde, bu sorgu güncellenmelidir.
        cursor.execute("""
            SELECT b.bucket_name, b.color, COUNT(p.id) as post_count
            FROM content_buckets b
            JOIN scheduled_posts p ON b.id = p.bucket_id
            WHERE p.brand_id = ? AND p.status = 'Yayınlandı'
            GROUP BY b.id, b.bucket_name, b.color
        """, (brand_id,))
        buckets = cursor.fetchall()
        import random
        return [{"name": row['bucket_name'], "color": row['color'], "engagement": row['post_count'] * random.randint(100, 500)} for row in buckets]

def get_due_posts():
    """Zamanı gelmiş ve henüz gönderilmemiş postları getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now()
        cursor.execute(
            """
        SELECT p.id, p.user_id, p.caption, p.image_path, p.media_type, p.platform_specific_data, ca.platform_name, ca.access_token, ca.account_id as platform_account_id
        FROM scheduled_posts p
        JOIN connected_accounts ca ON p.account_id = ca.id
        WHERE p.scheduled_time <= ? AND p.is_posted = 0 AND p.status = 'Bekliyor'
        """,
            (now,)
        )
        posts = cursor.fetchall()
        return posts

def delete_data_by_platform_id(platform_name, platform_user_id):
    """
    Belirli bir platform ve platform kullanıcı ID'sine göre kullanıcının tüm verilerini siler.
    Facebook'un veri silme talepleri için kullanılır.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Platform ID'sinden bizim sistemimizdeki ana kullanıcı ID'sini (user_id) bul.
        cursor.execute("SELECT user_id FROM connected_accounts WHERE platform_name = ? AND account_id = ?", (platform_name, platform_user_id))
        result = cursor.fetchone()

        if result:
            user_id = result[0]
            # 2. Bu kullanıcıya ait TÜM bağlı hesapları sil.
            cursor.execute("DELETE FROM connected_accounts WHERE user_id = ?", (user_id,))
            # 3. Bu kullanıcıya ait TÜM planlanmış gönderileri sil.
            cursor.execute("DELETE FROM scheduled_posts WHERE user_id = ?", (user_id,))
            # İsteğe bağlı: Ana kullanıcı kaydını da silebilirsiniz.
            # cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            print(f"✅ Veritabanından {user_id} ID'li kullanıcının tüm verileri silindi.")

        conn.commit()

# --- Onay Akışı Fonksiyonları ---

def get_pending_approval_posts(team_id):
    """Bir takımdaki onay bekleyen tüm gönderileri getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, u.username as author, ca.platform_name, ca.account_name
            FROM scheduled_posts p
            JOIN users u ON p.user_id = u.id
            JOIN team_members tm ON p.user_id = tm.user_id
            JOIN connected_accounts ca ON p.account_id = ca.id
            WHERE tm.team_id = ? AND p.status = 'pending_approval'
            ORDER BY p.scheduled_time ASC
        """, (team_id,))
        return [dict(row) for row in cursor.fetchall()]

def update_post_approval_status(post_id, new_status):
    """Bir gönderinin onay durumunu günceller ('Bekliyor' veya 'rejected')."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_posts SET status = ? WHERE id = ?", (new_status, post_id))
        conn.commit()

# --- Takım Yönetimi Fonksiyonları ---

def create_team(team_name, owner_id):
    """Yeni bir takım oluşturur ve sahibini admin olarak ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO teams (team_name, owner_id) VALUES (?, ?)", (team_name, owner_id))
        team_id = cursor.lastrowid
        # Takım sahibine tüm izinleri ver
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id, role, can_post, can_approve, can_view_reports, can_manage_team) 
            VALUES (?, ?, 'admin', 1, 1, 1, 1)
        """, (team_id, owner_id))
        conn.commit()
        return team_id

def get_user_team(user_id):
    """Bir kullanıcının üye olduğu takımı ve rolünü getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id as team_id, t.team_name, tm.role, tm.can_post, tm.can_approve, tm.can_view_reports, tm.can_manage_team
            FROM team_members tm
            JOIN teams t ON tm.team_id = t.id
            WHERE tm.user_id = ?
        """, (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_team_members(team_id):
    """Bir takımın tüm üyelerini kullanıcı adları ve rolleriyle birlikte listeler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, tm.role, tm.can_post, tm.can_approve, tm.can_view_reports, tm.can_manage_team
            FROM team_members tm
            JOIN users u ON tm.user_id = u.id
            WHERE tm.team_id = ?
        """, (team_id,))
        return [dict(row) for row in cursor.fetchall()]

def add_team_member(team_id, user_id, permissions):
    """Bir kullanıcıyı bir takıma ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO team_members (team_id, user_id, can_post, can_approve, can_view_reports, can_manage_team) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (team_id, user_id, permissions['can_post'], permissions['can_approve'], permissions['can_view_reports'], permissions['can_manage_team']))
            conn.commit()
            return True
        except sqlite3.IntegrityError: # Zaten üye ise
            return False

def update_team_member_permissions(team_id, user_id, permissions):
    """Bir takım üyesinin izinlerini günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE team_members SET can_post=?, can_approve=?, can_view_reports=?, can_manage_team=?
            WHERE team_id=? AND user_id=?
        """, (permissions['can_post'], permissions['can_approve'], permissions['can_view_reports'], permissions['can_manage_team'], team_id, user_id))
        conn.commit()

def remove_team_member(team_id, user_id):
    """Bir kullanıcıyı bir takımdan kaldırır."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM team_members WHERE team_id = ? AND user_id = ?", (team_id, user_id))
        conn.commit()

# --- Social Inbox Fonksiyonları ---

def upsert_conversation(user_id, brand_id, connected_account_id, platform_conversation_id, snippet, last_updated):
    """Bir görüşmeyi ekler veya günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations WHERE platform_conversation_id = ?", (platform_conversation_id,))
        row = cursor.fetchone()
        if row:
            cursor.execute("""
                UPDATE conversations SET snippet = ?, last_updated = ? WHERE id = ?
            """, (snippet, last_updated, row['id']))
            return row['id']
        else:
            cursor.execute("""
                INSERT INTO conversations (user_id, brand_id, connected_account_id, platform_conversation_id, snippet, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, brand_id, connected_account_id, platform_conversation_id, snippet, last_updated))
            return cursor.lastrowid

def add_message(conversation_id, platform_message_id, sender_name, sender_id, message, timestamp, is_hidden=False, is_flagged=False):
    """Bir görüşmeye yeni bir mesaj ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO messages (conversation_id, platform_message_id, sender_name, sender_id, message, timestamp, is_hidden, is_flagged)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (conversation_id, platform_message_id, sender_name, sender_id, message, timestamp, is_hidden, is_flagged))
            conn.commit()
        except sqlite3.IntegrityError:
            # Mesaj zaten varsa, görmezden gel
            pass

def get_conversations(brand_id):
    """Bir kullanıcının tüm görüşmelerini listeler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT c.*, ca.account_name FROM conversations c JOIN connected_accounts ca ON c.connected_account_id = ca.id WHERE c.brand_id = ? ORDER BY c.last_updated DESC", (brand_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_messages(conversation_id):
    """Bir görüşmenin tüm mesajlarını listeler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,))
        return [dict(row) for row in cursor.fetchall()]

def get_conversation_details(conversation_id):
    """Bir görüşmenin ve bağlı olduğu hesabın detaylarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.platform_conversation_id, ca.access_token
            FROM conversations c
            JOIN connected_accounts ca ON c.connected_account_id = ca.id
            WHERE c.id = ?
        """, (conversation_id,))
        return cursor.fetchone()

def get_account_by_platform_id(platform_account_id):
    """Platform account ID'sine göre bağlı hesap bilgilerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connected_accounts WHERE account_id = ?", (platform_account_id,))
        account = cursor.fetchone()
        return dict(account) if account else None

def get_account_by_id(account_id):
    """Veritabanı ID'sine göre bağlı hesap bilgilerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM connected_accounts WHERE id = ?", (account_id,))
        account = cursor.fetchone()
        return dict(account) if account else None

# --- Rakip Analizi Fonksiyonları ---

def add_competitor(user_id, brand_id, platform_name, competitor_username):
    """Veritabanına yeni bir rakip ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO competitors (user_id, brand_id, platform_name, competitor_username) VALUES (?, ?, ?, ?)",
                (user_id, brand_id, platform_name, competitor_username)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # Zaten ekli

def get_competitors(brand_id, platform_name):
    """Bir kullanıcının belirli bir platformdaki rakiplerini listeler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM competitors WHERE brand_id = ? AND platform_name = ?", (brand_id, platform_name))
        return [dict(row) for row in cursor.fetchall()]

def delete_competitor(competitor_id):
    """Verilen ID'ye sahip rakibi ve anlık görüntülerini siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM competitor_snapshots WHERE competitor_id = ?", (competitor_id,))
        cursor.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
        conn.commit()

def add_competitor_snapshot(competitor_db_id, follower_count, engagement_rate=None):
    """Bir rakip için yeni bir anlık veri görüntüsü ekler veya günceller."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = datetime.now().date()
        # Aynı gün için zaten bir snapshot var mı diye kontrol et
        cursor.execute("SELECT id FROM competitor_snapshots WHERE competitor_id = ? AND snapshot_date = ?", (competitor_db_id, today))
        if cursor.fetchone():
            # Varsa güncelle
            cursor.execute("UPDATE competitor_snapshots SET follower_count = ? WHERE competitor_id = ? AND snapshot_date = ?", (follower_count, competitor_db_id, today))
        else:
            # Yoksa ekle
            cursor.execute(
                "INSERT INTO competitor_snapshots (competitor_id, snapshot_date, follower_count, engagement_rate) VALUES (?, ?, ?, ?)",
                (competitor_db_id, today, follower_count, engagement_rate)
            )
        conn.commit()

def get_competitor_snapshots(competitor_id):
    """Bir rakibin tüm geçmiş anlık görüntülerini getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM competitor_snapshots WHERE competitor_id = ? ORDER BY snapshot_date ASC", (competitor_id,))
        return [dict(row) for row in cursor.fetchall()]

# --- İç Takım Notları Fonksiyonları ---

def add_post_note(post_id, user_id, note_text):
    """Bir gönderiye yeni bir not ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO post_notes (post_id, user_id, note_text) VALUES (?, ?, ?)",
            (post_id, user_id, note_text)
        )
        conn.commit()

def get_post_notes(post_id):
    """Bir gönderiye ait tüm notları, yazar bilgisiyle birlikte getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pn.note_text, pn.created_at, u.username
            FROM post_notes pn
            JOIN users u ON pn.user_id = u.id
            WHERE pn.post_id = ? ORDER BY pn.created_at ASC
        """, (post_id,))
        return [dict(row) for row in cursor.fetchall()]

# --- Otomatik Moderasyon Fonksiyonları ---

def add_moderation_rule(user_id, brand_id, keyword, action):
    """Yeni bir moderasyon kuralı ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO moderation_rules (user_id, brand_id, keyword, action) VALUES (?, ?, ?, ?)", (user_id, brand_id, keyword.lower(), action))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_user_moderation_rules(brand_id):
    """Bir markanın tüm moderasyon kurallarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM moderation_rules WHERE brand_id = ?", (brand_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_moderation_rule(rule_id):
    """Verilen ID'ye sahip moderasyon kuralını siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM moderation_rules WHERE id = ?", (rule_id,))
        conn.commit()

# --- Marka Yönetimi Fonksiyonları ---

def create_brand(team_id, brand_name):
    """Yeni bir marka oluşturur."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO brands (team_id, brand_name) VALUES (?, ?)", (team_id, brand_name))
        conn.commit()

def get_brands_for_team(team_id):
    """Bir takıma ait tüm markaları listeler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM brands WHERE team_id = ?", (team_id,))
        return [dict(row) for row in cursor.fetchall()]

def set_last_accessed_brand(user_id, brand_id):
    """Kullanıcının son eriştiği markayı kaydeder."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE team_members SET last_accessed_brand_id = ? WHERE user_id = ?", (brand_id, user_id))
        conn.commit()

def delete_brand(brand_id):
    """Bir markayı ve ona bağlı tüm verileri siler (ON DELETE CASCADE sayesinde)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM brands WHERE id = ?", (brand_id,))
        conn.commit()

# --- İçerik Kovaları (Content Buckets) Fonksiyonları ---

def add_content_bucket(user_id, brand_id, bucket_name, color):
    """Veritabanına yeni bir içerik kovası ekler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO content_buckets (user_id, brand_id, bucket_name, color) VALUES (?, ?, ?, ?)",
            (user_id, brand_id, bucket_name, color)
        )
        conn.commit()

def get_user_content_buckets(brand_id):
    """Bir markanın tüm içerik kovalarını getirir."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM content_buckets WHERE brand_id = ? ORDER BY bucket_name ASC", (brand_id,))
        return [dict(row) for row in cursor.fetchall()]

def delete_content_bucket(bucket_id):
    """Verilen ID'ye sahip içerik kovasını siler."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Bu kovaya bağlı gönderilerin bucket_id'sini NULL yap
        cursor.execute("UPDATE scheduled_posts SET bucket_id = NULL WHERE bucket_id = ?", (bucket_id,))
        cursor.execute("DELETE FROM content_buckets WHERE id = ?", (bucket_id,))
        conn.commit()
