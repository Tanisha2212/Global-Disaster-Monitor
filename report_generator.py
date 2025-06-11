from fpdf import FPDF
import pandas as pd
from datetime import datetime
from config import Config

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Global Disaster Monitor Report', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1)
        self.ln(4)
    
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 8, body)
        self.ln()

def generate_report(df, report_name):
    pdf = PDF()
    pdf.add_page()
    
    # Report metadata
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 10, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.cell(0, 10, f"Time Period: {df['date'].min().date()} to {df['date'].max().date()}", 0, 1)
    pdf.cell(0, 10, f"Countries: {', '.join(df['country'].unique())}", 0, 1)
    pdf.cell(0, 10, f"Disaster Types: {', '.join(df['disaster_type'].unique())}", 0, 1)
    pdf.ln(10)
    
    # Summary statistics
    pdf.chapter_title("Summary Statistics")
    stats = [
        f"Total Disasters: {len(df)}",
        f"Average Severity: {df['severity'].mean():.1f}/5",
        f"Total Mentions: {df['mentions'].sum():,}",
        f"Countries Affected: {df['country'].nunique()}"
    ]
    pdf.chapter_body("\n".join(stats))
    
    # Disaster distribution
    pdf.chapter_title("Disaster Type Distribution")
    type_counts = df['disaster_type'].value_counts()
    for disaster, count in type_counts.items():
        pdf.cell(0, 10, f"{disaster.title()}: {count} ({count/len(df)*100:.1f}%)", 0, 1)
    
    # Top severe events
    pdf.add_page()
    pdf.chapter_title("Top 10 Most Severe Events")
    top_severe = df.sort_values('severity', ascending=False).head(10)
    for i, (_, row) in enumerate(top_severe.iterrows(), 1):
        pdf.cell(0, 10, f"{i}. {row['disaster_type'].title()} in {row['country']} (Severity: {row['severity']})", 0, 1)
        pdf.cell(0, 10, f"   Location: {row['location_name']}, Date: {row['date_str']}", 0, 1)
        pdf.cell(0, 10, f"   Mentions: {row['mentions']}, Keywords: {row['topic_keywords']}", 0, 1)
        pdf.ln(5)
    
    # Country analysis
    pdf.add_page()
    pdf.chapter_title("Country Analysis")
    country_stats = df.groupby('country').agg({
        'severity': 'mean',
        'mentions': 'sum',
        'disaster_type': 'count'
    }).sort_values('severity', ascending=False)
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(60, 10, "Country", 1)
    pdf.cell(30, 10, "Avg Severity", 1)
    pdf.cell(30, 10, "Total Mentions", 1)
    pdf.cell(30, 10, "Event Count", 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 10)
    for country, data in country_stats.iterrows():
        pdf.cell(60, 10, country, 1)
        pdf.cell(30, 10, f"{data['severity']:.1f}", 1)
        pdf.cell(30, 10, f"{data['mentions']:,}", 1)
        pdf.cell(30, 10, str(data['disaster_type']), 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin1')