from fpdf import FPDF
from datetime import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Sosyal Orkestra - Performans Raporu', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Sayfa {self.page_no()}', 0, 0, 'C')

def create_analytics_pdf(analytics_data, chart_image_paths):
    """
    Verilen analiz verileri ve grafik resimlerinden bir PDF raporu oluşturur.
    """
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)

    # Rapor Başlığı ve Tarih
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Genel Analiz Raporu', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f"Rapor Tarihi: {datetime.now().strftime('%d-%m-%Y %H:%M')}", 0, 1, 'L')
    pdf.ln(10)

    # Üst Metrikler
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(95, 10, 'Toplam Bagli Hesap', 1, 0, 'C')
    pdf.cell(95, 10, 'Toplam Yayinlanmis Gonderi', 1, 1, 'C')
    pdf.set_font('Arial', '', 12)
    pdf.cell(95, 10, str(analytics_data.get('total_accounts', 'N/A')), 1, 0, 'C')
    pdf.cell(95, 10, str(analytics_data.get('total_posts', 'N/A')), 1, 1, 'C')
    pdf.ln(15)

    # Grafikleri Ekle
    if chart_image_paths.get('posts_by_platform'):
        pdf.image(chart_image_paths['posts_by_platform'], x=10, w=190)
        pdf.ln(5)
    if chart_image_paths.get('posts_over_time'):
        pdf.image(chart_image_paths['posts_over_time'], x=10, w=190)

    return pdf.output(dest='S').encode('latin-1')