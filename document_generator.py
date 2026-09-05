import os
import hashlib
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

SAMPLE_DIR = Path(__file__).parent.parent.parent / "sample_documents"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

def create_tender_pdf(filename: str):
    filepath = SAMPLE_DIR / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'TenderTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#0f172a'),
        alignment=1,
        spaceAfter=15
    )
    
    header_style = ParagraphStyle(
        'TenderHeader',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1e3a8a'),
        spaceBefore=10,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'TenderBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    story.append(Paragraph("GOVERNMENT e-MARKETPLACE (GeM) HIGH-TECH TENDER SPECIFICATION", title_style))
    story.append(Paragraph("Tender ID: GEM/2026/B/891204 | Ministry of Electronics & IT", ParagraphStyle('Sub', alignment=1, fontSize=11, textColor=colors.gray)))
    story.append(Spacer(1, 15))

    story.append(Paragraph("1. Scope of Work & Technical Standard", header_style))
    story.append(Paragraph("Procurement of 10,000 High-Performance AI & Data Processing Servers with ISO 9001:2015 Quality Accreditation.", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. Mandatory Eligibility Matrix", header_style))
    
    table_data = [
        ["Parameter", "Mandatory Requirement Value", "Automated AI Audit Rule"],
        ["GST Registration", "Valid GSTIN (State Codes 27, 07, 29, 09)", "Regex Check & State Code Audit"],
        ["PAN Card", "Valid Permanent Account Number", "Tax Entity Format Check"],
        ["Minimum Annual Turnover", "INR 50.0 Lakhs (3 Yr Avg)", "Audit Financial Extraction"],
        ["Work Experience", "Minimum 3 Years in Enterprise Hardware", "Work Order Timeline Audit"],
        ["Quality Certification", "ISO 9001:2015 (Valid till 2026+)", "Certificate Expiry Audit"],
        ["Anti-Collusion Policy", "Zero Common Ownership / IP Sharing", "GNN Graph Centrality Audit"]
    ]

    t = Table(table_data, colWidths=[140, 180, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8fafc')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('FONTSIZE', (0,1), (-1,-1), 8.5),
    ]))
    story.append(t)
    doc.build(story)
    return filepath

def create_vendor_bid_pdf(filename: str, vendor_data: dict):
    filepath = SAMPLE_DIR / filename
    doc = SimpleDocTemplate(str(filepath), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'BidTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        'BidBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )

    story.append(Paragraph(f"BID PROPOSAL: {vendor_data['vendor_name']}", title_style))
    story.append(Paragraph(f"Tender Ref: GEM/2026/B/891204 | Bid ID: {vendor_data['bid_id']} | Timestamp: {vendor_data.get('creation_timestamp', '2026-01-15T14:30:00')}", ParagraphStyle('Ref', fontSize=9, textColor=colors.HexColor('#2563eb'))))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Vendor Attributes & Legal Declaration:</b>", body_style))
    story.append(Spacer(1, 8))

    table_data = [
        ["Attribute Field", "Declared Vendor Value"],
        ["Legal Company Name", vendor_data['vendor_name']],
        ["GST Identification No (GSTIN)", vendor_data['gst_number']],
        ["Permanent Account No (PAN)", vendor_data['pan_number']],
        ["Annual Turnover (Lakhs INR)", f"INR {vendor_data['turnover_lakhs']} Lakhs"],
        ["Total Bid Price (Lakhs INR)", f"INR {vendor_data.get('bid_price_lakhs', 0.0)} Lakhs"],
        ["Technical Experience", f"{vendor_data['experience_years']} Years"],
        ["ISO 9001 Certificate Expiry", str(vendor_data['iso_expiry_year'])],
        ["Managing Director", vendor_data['director_name']],
        ["Submission Terminal IP Address", vendor_data['ip_address']],
        ["Primary Bank Account Number", vendor_data['bank_account_no']]
    ]


    t = Table(table_data, colWidths=[200, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#ffffff')),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Self-Authentication Statement:</b>", body_style))
    story.append(Paragraph(f"Authorized Signature by {vendor_data['director_name']} on behalf of {vendor_data['vendor_name']}.", body_style))

    doc.build(story)
    return filepath

def generate_all_sample_pdfs():
    print("Generating High-Tech Sample Tender PDF...")
    create_tender_pdf("Tender_GeM_2026_Hardware.pdf")

    vendors = [
        {
            "bid_id": "BID-101",
            "vendor_id": "VEND-A",
            "vendor_name": "TechCorp Solutions Pvt Ltd",
            "gst_number": "27AAACT1234A1Z5",
            "pan_number": "AAACT1234A",
            "turnover_lakhs": 85.5,
            "bid_price_lakhs": 85.0,
            "experience_years": 5,
            "iso_expiry_year": 2028,
            "director_name": "Mr. Ramesh Verma",
            "ip_address": "103.22.45.12",
            "bank_account_no": "5010098234120",
            "creation_timestamp": "2026-01-15T10:15:22",
            "filename": "Vendor_A_TechCorp_VALID.pdf"
        },
        {
            "bid_id": "BID-102",
            "vendor_id": "VEND-B",
            "vendor_name": "InfoTech Enterprise",
            "gst_number": "07BBBBI5678B1Z2",
            "pan_number": "BBBBI5678B",
            "turnover_lakhs": 60.0,
            "bid_price_lakhs": 72.5,
            "experience_years": 4,
            "iso_expiry_year": 2021,  # EXPIRED CERT
            "director_name": "Ms. Sunita Rao",
            "ip_address": "114.31.89.55",
            "bank_account_no": "4021008761234",
            "creation_timestamp": "2026-01-15T11:40:05",
            "filename": "Vendor_B_Infotech_EXPIRED_CERT.pdf"
        },
        {
            "bid_id": "BID-103",
            "vendor_id": "VEND-C",
            "vendor_name": "Global Digital Solutions",
            "gst_number": "99INVALID1234X",  # FAKE GST
            "pan_number": "INVALID_PAN",    # FAKE PAN
            "turnover_lakhs": 22.0,         # LOW TURNOVER
            "bid_price_lakhs": 99.0,
            "experience_years": 1,          # LOW EXPERIENCE
            "iso_expiry_year": 2020,
            "director_name": "Mr. Vikram Shah",
            "ip_address": "185.220.101.5",
            "bank_account_no": "10099882233",
            "creation_timestamp": "2026-01-15T12:05:11",
            "filename": "Vendor_C_GlobalSol_INVALID_GST.pdf"
        },
        {
            "bid_id": "BID-104",
            "vendor_id": "VEND-D",
            "vendor_name": "Alpha Network Systems",
            "gst_number": "29CCCAD9012C1Z8",
            "pan_number": "CCCAD9012C",
            "turnover_lakhs": 90.0,
            "bid_price_lakhs": 88.0,        # Identical Price to BID-105 (Collusive Indicator)
            "experience_years": 6,
            "iso_expiry_year": 2027,
            "director_name": "Rajesh Sharma",       # SHARED DIRECTOR (CARTEL)
            "ip_address": "192.168.1.105",          # SHARED IP (CARTEL)
            "bank_account_no": "918237465019",      # SHARED BANK (CARTEL)
            "creation_timestamp": "2026-01-15T14:32:01",  # IDENTICAL TIMESTAMP
            "filename": "Vendor_D_AlphaSys_COLLUSIVE_RING1.pdf"
        },
        {
            "bid_id": "BID-105",
            "vendor_id": "VEND-E",
            "vendor_name": "Beta Systematics Pvt Ltd",
            "gst_number": "29DDDBD3456D1Z9",
            "pan_number": "DDDBD3456D",
            "turnover_lakhs": 95.0,
            "bid_price_lakhs": 88.0,        # Identical Price to BID-104 (Collusive Indicator)
            "experience_years": 6,
            "iso_expiry_year": 2027,
            "director_name": "Rajesh Sharma",       # SHARED DIRECTOR (CARTEL)
            "ip_address": "192.168.1.105",          # SHARED IP (CARTEL)
            "bank_account_no": "918237465019",      # SHARED BANK (CARTEL)
            "creation_timestamp": "2026-01-15T14:32:01",  # IDENTICAL TIMESTAMP
            "filename": "Vendor_E_BetaSys_COLLUSIVE_RING2.pdf"
        },
        {
            "bid_id": "BID-106",
            "vendor_id": "VEND-F",
            "vendor_name": "CyberTech Innovations",
            "gst_number": "09EEEEC7890E1Z4",
            "pan_number": "EEEEC7890E",
            "turnover_lakhs": 120.0,
            "bid_price_lakhs": 95.0,
            "experience_years": 7,
            "iso_expiry_year": 2029,
            "director_name": "Dr. Ananya Sen",
            "ip_address": "49.207.180.22",
            "bank_account_no": "7009823145671",
            "creation_timestamp": "2026-01-15T15:10:45",
            "filename": "Vendor_F_CyberTech_VALID.pdf"
        },
        {
            "bid_id": "BID-107",
            "vendor_id": "VEND-G",
            "vendor_name": "Apex Hardware Traders",
            "gst_number": "27FFFFA1122F1Z1",
            "pan_number": "FFFFA1122F",
            "turnover_lakhs": 48.0,          # BORDERLINE TURNOVER
            "bid_price_lakhs": 65.0,
            "experience_years": 3,
            "iso_expiry_year": 2026,
            "director_name": "Mr. Anil Mehta",
            "ip_address": "122.169.44.80",
            "bank_account_no": "3019882200114",
            "creation_timestamp": "2026-01-15T16:22:30",
            "filename": "Vendor_G_ApexHardware_BORDERLINE.pdf"
        }
    ]

    for v in vendors:
        print(f"Generating PDF for {v['vendor_name']} -> {v['filename']}")
        create_vendor_bid_pdf(v['filename'], v)
    
    print("All Sample PDFs generated in sample_documents/!")

if __name__ == "__main__":
    generate_all_sample_pdfs()
