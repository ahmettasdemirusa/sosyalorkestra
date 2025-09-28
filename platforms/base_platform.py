class BasePlatform:
    """
    Tüm sosyal medya platformları için temel bir şablon (template) görevi görür.
    Her yeni platform bu sınıftan miras almalı ve metodları kendi platformuna göre
    uyarlamalıdır (override).
    """
    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    def post(self, image_path: str, caption: str, **kwargs):
        """Bir platforma gönderi paylaşmak için genel metot."""
        raise NotImplementedError("Bu metot, alt sınıflar tarafından uygulanmalıdır.")

    def get_post_stats(self, post_id: str, **kwargs):
        """Belirli bir gönderinin istatistiklerini getirmek için genel metot."""
        # Bu metot, alt sınıflarda gerçek API çağrıları ile doldurulacaktır.
        # Şimdilik örnek (mock) veri döndürüyoruz.
        import random
        return {
            "Beğeni": random.randint(100, 5000),
            "Yorum": random.randint(10, 500),
            "Paylaşım/Kaydetme": random.randint(5, 100),
            "Erişim": random.randint(5000, 50000)
        }