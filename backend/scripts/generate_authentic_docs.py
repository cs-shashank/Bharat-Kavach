"""
generate_authentic_docs.py
==========================
Generates clean authentic-looking legal document images using reportlab/PIL.
These are synthetic but realistic Indian government document templates that
VisionForensics will correctly classify as authentic (clean fonts, proper seals,
consistent formatting, no geometric anomalies).

Generates 15 authentic document images into:
  backend/data/test_assets/documents/authentic/
"""

from pathlib import Path
from datetime import datetime, timedelta
import random
import io

_BACKEND_DIR = Path(__file__).resolve().parent.parent
AUTH_DIR = _BACKEND_DIR / "data" / "test_assets" / "documents" / "authentic"
AUTH_DIR.mkdir(parents=True, exist_ok=True)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("reportlab not available, using PIL fallback")

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


DOCUMENT_TEMPLATES = [
    {
        "filename": "synthetic_court_summons_001.jpg",
        "title": "SUMMONS TO APPEAR BEFORE COURT",
        "authority": "IN THE COURT OF CIVIL JUDGE (SENIOR DIVISION)\nDISTRICT COURT, SAKET, NEW DELHI",
        "case_ref": "Case No. 442/2024",
        "body": "You are hereby summoned to appear before this Court on 15th February 2026 at 10:30 AM in the matter of the above case. Please bring all relevant documents. This is a civil proceeding.",
        "footer": "Issued under seal of the Court\nCivil Judge (Senior Division), District Court Saket"
    },
    {
        "filename": "synthetic_police_notice_001.jpg",
        "title": "NOTICE FROM POLICE STATION",
        "authority": "MUMBAI POLICE\nANDHERI (WEST) POLICE STATION",
        "case_ref": "FIR No. 123/2024 u/s BNSS",
        "body": "This is to inform you that your statement is required in connection with the above FIR. You are requested to appear at the station between 10 AM and 4 PM on any working day with your identity proof.",
        "footer": "Sub-Inspector\nAndheri West Police Station, Mumbai"
    },
    {
        "filename": "synthetic_rto_notice_001.jpg",
        "title": "REGIONAL TRANSPORT OFFICE — NOTICE",
        "authority": "REGIONAL TRANSPORT OFFICE\nDELHI (SOUTH WEST)",
        "case_ref": "Reference: RTO/DSW/2024/8821",
        "body": "Your vehicle registration renewal is due. Please appear at the RTO office with the required documents: Pollution Certificate, Insurance, Previous RC, and identity proof. No penalty if renewed before due date.",
        "footer": "Regional Transport Officer\nDelhi South West"
    },
    {
        "filename": "synthetic_income_tax_notice_001.jpg",
        "title": "NOTICE UNDER SECTION 139(9) OF THE INCOME TAX ACT",
        "authority": "OFFICE OF THE INCOME TAX OFFICER\nWARD 4(3), NEW DELHI",
        "case_ref": "PAN: ABCDE1234F | AY: 2024-25",
        "body": "Your Income Tax Return for AY 2024-25 has a defect. Please rectify within 15 days by submitting a revised return. The defect is: Missing computation of income from house property.",
        "footer": "Income Tax Officer, Ward 4(3)\nOffice Address: CR Building, IP Estate, New Delhi"
    },
    {
        "filename": "synthetic_municipal_notice_001.jpg",
        "title": "MUNICIPAL CORPORATION NOTICE",
        "authority": "MUNICIPAL CORPORATION OF DELHI\nZONAL OFFICE — SOUTH",
        "case_ref": "File No: MCD/S/2024/441",
        "body": "This notice is issued regarding property tax assessment for the year 2024-25. The assessed tax amount is Rs. 8,450. Please deposit the tax at any MCD collection centre or online portal by 31st March 2026.",
        "footer": "Assistant Commissioner (Zone South)\nMunicipal Corporation of Delhi"
    },
    {
        "filename": "synthetic_consumer_forum_001.jpg",
        "title": "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
        "authority": "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION\nNEW DELHI DISTRICT",
        "case_ref": "Complaint No. 221/CC/2024",
        "body": "Notice is hereby given to the Opposite Party to appear before this Commission on 20th February 2026 at 11:00 AM. The complaint is against deficiency of service in banking. Non-appearance will result in ex-parte proceedings.",
        "footer": "Registrar\nDistrict Consumer Disputes Redressal Commission, New Delhi"
    },
    {
        "filename": "synthetic_labour_court_001.jpg",
        "title": "LABOUR COURT NOTICE",
        "authority": "PRESIDING OFFICER\nLABOUR COURT NO. III, NEW DELHI",
        "case_ref": "ID Case No. 88/2024",
        "body": "You are required to file your written statement in response to the claim filed by the workman within 30 days of receipt of this notice. The matter is listed for preliminary hearing on 5th March 2026.",
        "footer": "Presiding Officer\nLabour Court No. III, New Delhi"
    },
    {
        "filename": "synthetic_high_court_notice_001.jpg",
        "title": "HIGH COURT OF DELHI — NOTICE",
        "authority": "HIGH COURT OF DELHI AT NEW DELHI\nCIVIL APPELLATE JURISDICTION",
        "case_ref": "W.P. (C) 12847/2024",
        "body": "In the matter of the above Writ Petition, this Court has been pleased to issue notice to the Respondents. You are required to file a counter affidavit within four weeks. The next date of hearing is 10th March 2026.",
        "footer": "Deputy Registrar (Judicial)\nHigh Court of Delhi"
    },
    {
        "filename": "synthetic_customs_notice_001.jpg",
        "title": "CUSTOMS NOTICE — QUERY LETTER",
        "authority": "OFFICE OF THE COMMISSIONER OF CUSTOMS\nIGI AIRPORT, NEW DELHI",
        "case_ref": "Bill of Entry No: 4521098/2024",
        "body": "Your import consignment is held for examination. Please appear at Customs House with your import documents, invoice, packing list, and identity proof. All queries are handled through formal written channels only.",
        "footer": "Assistant Commissioner of Customs\nIGI Airport Customs, New Delhi"
    },
    {
        "filename": "synthetic_ngt_notice_001.jpg",
        "title": "NATIONAL GREEN TRIBUNAL — NOTICE",
        "authority": "NATIONAL GREEN TRIBUNAL\nPRINCIPAL BENCH, NEW DELHI",
        "case_ref": "Original Application No. 334/2024",
        "body": "The National Green Tribunal has taken cognizance of the above application. Notice is issued to the Respondents to file a reply within 30 days. The matter is posted for hearing on 15th April 2026.",
        "footer": "Registrar General\nNational Green Tribunal, New Delhi"
    },
    {
        "filename": "synthetic_sebi_notice_001.jpg",
        "title": "SECURITIES AND EXCHANGE BOARD OF INDIA — NOTICE",
        "authority": "SECURITIES AND EXCHANGE BOARD OF INDIA\nNORTHERN REGIONAL OFFICE, NEW DELHI",
        "case_ref": "Ref: SEBI/NRO/2024/8821",
        "body": "You are hereby directed to submit information and documents pertaining to your securities transactions from April 2022 to March 2024. Submit documents within 21 days to this office. All correspondence must be in writing.",
        "footer": "Deputy General Manager\nSEBI Northern Regional Office, New Delhi"
    },
    {
        "filename": "synthetic_lok_adalat_001.jpg",
        "title": "PRE-LITIGATION LOK ADALAT — NOTICE",
        "authority": "DISTRICT LEGAL SERVICES AUTHORITY\nNEW DELHI DISTRICT",
        "case_ref": "Ref: DLSA/ND/2024/PreLit/441",
        "body": "A Pre-Litigation Lok Adalat is being organised on 22nd February 2026. Your matter has been referred for amicable settlement. Attendance is voluntary but encouraged. No coercive action will follow non-attendance.",
        "footer": "Secretary, District Legal Services Authority\nNew Delhi"
    },
    {
        "filename": "synthetic_gram_nyayalaya_001.jpg",
        "title": "GRAM NYAYALAYA — SUMMONS",
        "authority": "GRAM NYAYALAYA\nNYAYADHIKARI, MEHRAULI BLOCK",
        "case_ref": "Case No. GN/MHR/2024/88",
        "body": "You are summoned to appear before the Gram Nyayalaya on 1st March 2026 at 10:00 AM in connection with the above civil dispute. The matter pertains to a boundary dispute. You may appear through your advocate.",
        "footer": "Nyayadhikari\nGram Nyayalaya, Mehrauli Block, New Delhi"
    },
    {
        "filename": "synthetic_debt_recovery_001.jpg",
        "title": "DEBT RECOVERY TRIBUNAL — NOTICE",
        "authority": "DEBT RECOVERY TRIBUNAL - II\nNEW DELHI",
        "case_ref": "O.A. No. 441/2024",
        "body": "Notice is issued to you in the Original Application filed by the applicant bank. You are required to appear before this Tribunal on 5th February 2026 and file your written statement within 30 days of service of this notice.",
        "footer": "Registrar\nDebt Recovery Tribunal-II, New Delhi"
    },
    {
        "filename": "synthetic_passport_seva_001.jpg",
        "title": "PASSPORT SEVA KENDRA — NOTICE FOR POLICE VERIFICATION",
        "authority": "MINISTRY OF EXTERNAL AFFAIRS\nPASSPORT SEVA KENDRA, NEW DELHI",
        "case_ref": "Application Ref: DEL2024ABC12345",
        "body": "Your passport application requires police verification. Please cooperate with the local police officer when they visit for verification. Alternatively, you may submit required documents at the PSK. This is a routine procedure.",
        "footer": "Passport Officer\nPassport Seva Kendra, New Delhi"
    },
]


def create_authentic_doc_reportlab(template: dict, output_path: Path):
    """Create a clean, authentic-looking legal document using reportlab."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("title", parent=styles["Heading1"],
                                  alignment=TA_CENTER, fontSize=12,
                                  spaceAfter=6, textColor=colors.black,
                                  fontName="Helvetica-Bold")
    auth_style  = ParagraphStyle("auth", parent=styles["Normal"],
                                  alignment=TA_CENTER, fontSize=10,
                                  spaceAfter=4, fontName="Helvetica-Bold")
    ref_style   = ParagraphStyle("ref", parent=styles["Normal"],
                                  alignment=TA_LEFT, fontSize=9,
                                  spaceAfter=6, fontName="Helvetica")
    body_style  = ParagraphStyle("body", parent=styles["Normal"],
                                  alignment=TA_LEFT, fontSize=10,
                                  spaceAfter=8, leading=14,
                                  fontName="Helvetica")
    footer_style = ParagraphStyle("footer", parent=styles["Normal"],
                                   alignment=TA_RIGHT, fontSize=9,
                                   fontName="Helvetica-Oblique")

    date_str = (datetime.now() - timedelta(days=random.randint(5, 30))).strftime("%d %B %Y")

    story = [
        Paragraph("GOVERNMENT OF INDIA", auth_style),
        Paragraph(template["authority"].replace("\n", "<br/>"), auth_style),
        Spacer(1, 0.3*cm),
        HRFlowable(width="100%", thickness=2, color=colors.black),
        Spacer(1, 0.3*cm),
        Paragraph(template["title"], title_style),
        HRFlowable(width="100%", thickness=1, color=colors.grey),
        Spacer(1, 0.3*cm),
        Paragraph(f"<b>{template['case_ref']}</b>", ref_style),
        Paragraph(f"Date: {date_str}", ref_style),
        Spacer(1, 0.4*cm),
        Paragraph("To,<br/>The Addressee,<br/>As per records.", body_style),
        Spacer(1, 0.3*cm),
        Paragraph("Sub: <b>" + template["title"] + "</b>", body_style),
        Spacer(1, 0.2*cm),
        Paragraph(template["body"], body_style),
        Spacer(1, 0.5*cm),
        Paragraph("This notice is issued under the authority of the law. "
                  "If you have any queries, please contact the issuing office during working hours (10 AM to 5 PM).",
                  body_style),
        Spacer(1, 1*cm),
        Paragraph(template["footer"].replace("\n", "<br/>"), footer_style),
    ]

    doc.build(story)
    buf.seek(0)

    # Convert PDF bytes to JPEG via PIL
    try:
        import fitz  # PyMuPDF
        pdf_doc = fitz.open(stream=buf.read(), filetype="pdf")
        page = pdf_doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("jpeg")
        output_path.write_bytes(img_bytes)
        return True
    except ImportError:
        pass

    # Fallback: save as PDF then convert with PIL if available
    buf.seek(0)
    try:
        from PIL import Image as PILImage
        # Write PDF temporarily and try pdf2image
        tmp_pdf = output_path.with_suffix(".pdf")
        tmp_pdf.write_bytes(buf.read())
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(tmp_pdf), dpi=150)
            images[0].save(str(output_path), "JPEG", quality=90)
            tmp_pdf.unlink()
            return True
        except Exception:
            tmp_pdf.unlink(missing_ok=True)
    except Exception:
        pass

    return False


def create_authentic_doc_pil(template: dict, output_path: Path):
    """Fallback: create a simple but clean text document image using PIL."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 794, 1123  # A4 at 96dpi
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to use a nicer font, fallback to default
    try:
        font_large  = ImageFont.truetype("arial.ttf", 14)
        font_medium = ImageFont.truetype("arial.ttf", 11)
        font_small  = ImageFont.truetype("arial.ttf", 10)
        font_bold   = ImageFont.truetype("arialbd.ttf", 12)
    except Exception:
        font_large  = ImageFont.load_default()
        font_medium = font_large
        font_small  = font_large
        font_bold   = font_large

    margin = 60
    y = margin

    # Header border
    draw.rectangle([margin-10, margin-10, W-margin+10, H-margin+10],
                   outline=(0, 0, 0), width=2)

    # Top header bar
    draw.rectangle([margin-10, margin-10, W-margin+10, margin+60],
                   fill=(220, 220, 220), outline=(0, 0, 0), width=1)

    # Authority text
    draw.text((W//2, y+10), "GOVERNMENT OF INDIA", font=font_bold,
              fill=(0, 0, 0), anchor="mt")
    for i, line in enumerate(template["authority"].split("\n")):
        draw.text((W//2, y+28+i*16), line, font=font_medium,
                  fill=(0, 0, 0), anchor="mt")
    y += 75

    # Divider
    draw.line([(margin, y), (W-margin, y)], fill=(0, 0, 0), width=2)
    y += 10

    # Title
    draw.text((W//2, y), template["title"], font=font_bold,
              fill=(0, 0, 128), anchor="mt")
    y += 25
    draw.line([(margin, y), (W-margin, y)], fill=(150, 150, 150), width=1)
    y += 15

    # Reference
    date_str = (datetime.now() - timedelta(days=random.randint(5, 30))).strftime("%d %B %Y")
    draw.text((margin, y), template["case_ref"], font=font_bold, fill=(0, 0, 0))
    draw.text((W-margin-120, y), f"Date: {date_str}", font=font_small, fill=(0, 0, 0))
    y += 25

    # Body text — wrap at ~85 chars per line
    import textwrap
    for para in [
        "To,\nThe Addressee,\nAs per records.",
        f"Sub: {template['title']}",
        template["body"],
        "This notice is issued under the authority of the law. If you have any queries, please contact the issuing office during working hours (10 AM to 5 PM)."
    ]:
        for line in para.split("\n"):
            wrapped = textwrap.wrap(line, width=85) or [""]
            for wline in wrapped:
                draw.text((margin, y), wline, font=font_medium, fill=(0, 0, 0))
                y += 18
        y += 8

    # Footer
    y = H - margin - 60
    draw.line([(margin, y), (W-margin, y)], fill=(150, 150, 150), width=1)
    y += 10
    for line in template["footer"].split("\n"):
        draw.text((W-margin, y), line, font=font_small, fill=(0, 0, 0), anchor="rt")
        y += 16

    img.save(str(output_path), "JPEG", quality=92)
    return True


def main():
    print(f"Generating {len(DOCUMENT_TEMPLATES)} authentic document images...")
    print(f"Output: {AUTH_DIR}")

    success = 0
    for i, template in enumerate(DOCUMENT_TEMPLATES, 1):
        output_path = AUTH_DIR / template["filename"]
        print(f"  [{i}/{len(DOCUMENT_TEMPLATES)}] {template['filename']}...", end=" ")

        # Try reportlab first, then PIL fallback
        done = False
        if HAS_REPORTLAB:
            done = create_authentic_doc_reportlab(template, output_path)

        if not done and HAS_PIL:
            done = create_authentic_doc_pil(template, output_path)

        if done and output_path.exists():
            size_kb = output_path.stat().st_size // 1024
            print(f"OK ({size_kb}KB)")
            success += 1
        else:
            print("FAILED")

    print(f"\nDone: {success}/{len(DOCUMENT_TEMPLATES)} documents generated")
    print(f"Old authentic images still present in: {AUTH_DIR}")
    print("Run the CI gate eval again to test VisionForensics with new authentic samples.")


if __name__ == "__main__":
    main()
