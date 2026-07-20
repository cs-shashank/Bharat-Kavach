"""
Regenerate authentic documents with consistent dates throughout.
Fixes the issue where issued date and appearance date were contradictory.
"""
from pathlib import Path
from datetime import datetime, timedelta
import random, io

_BACKEND_DIR = Path(__file__).resolve().parent.parent
AUTH_DIR = _BACKEND_DIR / "data" / "test_assets" / "documents" / "authentic"
AUTH_DIR.mkdir(parents=True, exist_ok=True)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    HAS_RL = True
except ImportError:
    HAS_RL = False

from PIL import Image, ImageDraw, ImageFont
import textwrap


def make_dates():
    """Return consistent issued_date and hearing_date (hearing always after issued)."""
    issued = datetime.now() - timedelta(days=random.randint(5, 20))
    hearing = issued + timedelta(days=random.randint(30, 60))
    return issued.strftime("%d %B %Y"), hearing.strftime("%d %B %Y")


TEMPLATES = [
    ("synthetic_court_summons_001.jpg",
     "SUMMONS TO APPEAR BEFORE COURT",
     "IN THE COURT OF CIVIL JUDGE (SENIOR DIVISION)\nDISTRICT COURT, SAKET, NEW DELHI",
     "Case No. 442/2024",
     "You are hereby summoned to appear before this Court on {hearing} at 10:30 AM in the matter of the above case. Please bring all relevant documents and identity proof. This is a civil proceeding.",
     "Civil Judge (Senior Division)\nDistrict Court, Saket, New Delhi"),

    ("synthetic_police_notice_001.jpg",
     "NOTICE FROM POLICE STATION",
     "MUMBAI POLICE\nANDHERI (WEST) POLICE STATION",
     "FIR No. 123/2024",
     "Your statement is required in connection with the above FIR. Please appear at the station on {hearing} between 10 AM and 4 PM with your identity proof.",
     "Sub-Inspector\nAndheri West Police Station, Mumbai"),

    ("synthetic_income_tax_notice_001.jpg",
     "NOTICE UNDER SECTION 139(9) OF THE INCOME TAX ACT",
     "OFFICE OF THE INCOME TAX OFFICER\nWARD 4(3), NEW DELHI",
     "PAN: ABCDE1234F | AY: 2024-25",
     "Your Income Tax Return for AY 2024-25 has a defect. Please rectify within 15 days by {hearing} by submitting a revised return. Defect: Missing computation of income from house property.",
     "Income Tax Officer, Ward 4(3)\nCR Building, IP Estate, New Delhi"),

    ("synthetic_consumer_forum_001.jpg",
     "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
     "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION\nNEW DELHI DISTRICT",
     "Complaint No. 221/CC/2024",
     "Notice is issued to the Opposite Party to appear before this Commission on {hearing} at 11:00 AM. Non-appearance will result in ex-parte proceedings.",
     "Registrar\nDistrict Consumer Disputes Redressal Commission, New Delhi"),

    ("synthetic_high_court_notice_001.jpg",
     "HIGH COURT OF DELHI — NOTICE",
     "HIGH COURT OF DELHI AT NEW DELHI\nCIVIL APPELLATE JURISDICTION",
     "W.P. (C) 12847/2024",
     "Notice is issued to the Respondents. File a counter affidavit within four weeks. Next date of hearing is {hearing}.",
     "Deputy Registrar (Judicial)\nHigh Court of Delhi"),

    ("synthetic_labour_court_001.jpg",
     "LABOUR COURT NOTICE",
     "PRESIDING OFFICER\nLABOUR COURT NO. III, NEW DELHI",
     "ID Case No. 88/2024",
     "File your written statement within 30 days. The matter is listed for preliminary hearing on {hearing}.",
     "Presiding Officer\nLabour Court No. III, New Delhi"),

    ("synthetic_sebi_notice_001.jpg",
     "SECURITIES AND EXCHANGE BOARD OF INDIA — NOTICE",
     "SECURITIES AND EXCHANGE BOARD OF INDIA\nNORTHERN REGIONAL OFFICE",
     "Ref: SEBI/NRO/2024/8821",
     "Submit information and documents pertaining to your securities transactions by {hearing}. All correspondence must be in writing.",
     "Deputy General Manager\nSEBI Northern Regional Office, New Delhi"),

    ("synthetic_ngt_notice_001.jpg",
     "NATIONAL GREEN TRIBUNAL — NOTICE",
     "NATIONAL GREEN TRIBUNAL\nPRINCIPAL BENCH, NEW DELHI",
     "O.A. No. 334/2024",
     "Notice is issued to the Respondents to file a reply within 30 days. The matter is posted for hearing on {hearing}.",
     "Registrar General\nNational Green Tribunal, New Delhi"),

    ("synthetic_municipal_notice_001.jpg",
     "MUNICIPAL CORPORATION — PROPERTY TAX NOTICE",
     "MUNICIPAL CORPORATION OF DELHI\nZONAL OFFICE — SOUTH",
     "File No: MCD/S/2024/441",
     "Property tax assessment notice for 2024-25. Assessed amount: Rs. 8,450. Please deposit by {hearing} at any MCD collection centre.",
     "Assistant Commissioner (Zone South)\nMunicipal Corporation of Delhi"),

    ("synthetic_debt_recovery_001.jpg",
     "DEBT RECOVERY TRIBUNAL — NOTICE",
     "DEBT RECOVERY TRIBUNAL - II\nNEW DELHI",
     "O.A. No. 441/2024",
     "Notice is issued to appear before this Tribunal on {hearing} and file your written statement within 30 days of service.",
     "Registrar\nDebt Recovery Tribunal-II, New Delhi"),

    ("synthetic_gram_nyayalaya_001.jpg",
     "GRAM NYAYALAYA — SUMMONS",
     "GRAM NYAYALAYA\nNYAYADHIKARI, MEHRAULI BLOCK",
     "Case No. GN/MHR/2024/88",
     "You are summoned to appear before the Gram Nyayalaya on {hearing} at 10:00 AM. You may appear through your advocate.",
     "Nyayadhikari\nGram Nyayalaya, Mehrauli Block"),

    ("synthetic_customs_notice_001.jpg",
     "CUSTOMS NOTICE — QUERY LETTER",
     "OFFICE OF THE COMMISSIONER OF CUSTOMS\nIGI AIRPORT, NEW DELHI",
     "Bill of Entry No: 4521098/2024",
     "Your import consignment is held for examination. Appear at Customs House by {hearing} with import documents, invoice, packing list, and identity proof.",
     "Assistant Commissioner of Customs\nIGI Airport Customs, New Delhi"),

    ("synthetic_lok_adalat_001.jpg",
     "PRE-LITIGATION LOK ADALAT — NOTICE",
     "DISTRICT LEGAL SERVICES AUTHORITY\nNEW DELHI DISTRICT",
     "Ref: DLSA/ND/2024/PreLit/441",
     "A Pre-Litigation Lok Adalat is being organised on {hearing}. Your matter has been referred for amicable settlement. Attendance is voluntary.",
     "Secretary, District Legal Services Authority\nNew Delhi"),

    ("synthetic_rto_notice_001.jpg",
     "REGIONAL TRANSPORT OFFICE — NOTICE",
     "REGIONAL TRANSPORT OFFICE\nDELHI (SOUTH WEST)",
     "Reference: RTO/DSW/2024/8821",
     "Your vehicle registration renewal is due by {hearing}. Please appear at the RTO office with: Pollution Certificate, Insurance, Previous RC, and identity proof.",
     "Regional Transport Officer\nDelhi South West"),

    ("synthetic_passport_seva_001.jpg",
     "PASSPORT SEVA KENDRA — POLICE VERIFICATION NOTICE",
     "MINISTRY OF EXTERNAL AFFAIRS\nPASSPORT SEVA KENDRA, NEW DELHI",
     "Application Ref: DEL2024ABC12345",
     "Your passport application requires police verification by {hearing}. Please cooperate with the local police officer. This is a routine procedure.",
     "Passport Officer\nPassport Seva Kendra, New Delhi"),
]


def create_doc_pil(filename, title, authority, case_ref, body_template, footer, issued, hearing):
    W, H = 850, 1100
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    body = body_template.replace("{hearing}", hearing)

    try:
        font_b14 = ImageFont.truetype("arialbd.ttf", 14)
        font_b12 = ImageFont.truetype("arialbd.ttf", 12)
        font_r11 = ImageFont.truetype("arial.ttf", 11)
        font_r10 = ImageFont.truetype("arial.ttf", 10)
        font_i10 = ImageFont.truetype("ariali.ttf", 10)
    except Exception:
        font_b14 = font_b12 = font_r11 = font_r10 = font_i10 = ImageFont.load_default()

    M = 55  # margin
    y = M

    # Outer border
    draw.rectangle([M-5, M-5, W-M+5, H-M+5], outline=(0, 0, 0), width=2)

    # Header band
    draw.rectangle([M-5, M-5, W-M+5, M+75], fill=(230, 230, 245), outline=(0, 0, 0), width=1)
    draw.text((W//2, y+5), "GOVERNMENT OF INDIA", font=font_b14, fill=(0, 0, 100), anchor="mt")
    y += 22
    for line in authority.split("\n"):
        draw.text((W//2, y), line, font=font_b12, fill=(0, 0, 80), anchor="mt")
        y += 17
    y += 6

    # Title band
    draw.line([(M, y), (W-M, y)], fill=(0, 0, 0), width=2)
    y += 6
    draw.text((W//2, y), title, font=font_b12, fill=(0, 0, 128), anchor="mt")
    y += 20
    draw.line([(M, y), (W-M, y)], fill=(100, 100, 100), width=1)
    y += 12

    # Ref + Date row
    draw.text((M, y), case_ref, font=font_b12, fill=(0, 0, 0))
    draw.text((W-M, y), f"Date of Issue: {issued}", font=font_r10, fill=(0, 0, 0), anchor="ra")
    y += 22

    # Addressee
    draw.text((M, y), "To,", font=font_r11, fill=(0, 0, 0))
    y += 16
    draw.text((M, y), "The Addressee / Respondent,", font=font_r11, fill=(0, 0, 0))
    y += 16
    draw.text((M, y), "As per records.", font=font_r11, fill=(0, 0, 0))
    y += 22

    # Subject
    draw.text((M, y), f"Sub: {title}", font=font_b12, fill=(0, 0, 0))
    y += 22

    # Divider
    draw.line([(M, y), (W-M, y)], fill=(180, 180, 180), width=1)
    y += 12

    # Body
    for para in [body,
                 "This notice is issued under the authority of law. Please comply within the stipulated time period. "
                 "For queries, contact the issuing office during working hours (10:00 AM to 5:00 PM, Monday to Friday)."]:
        wrapped = textwrap.wrap(para, width=90)
        for line in wrapped:
            draw.text((M, y), line, font=font_r11, fill=(0, 0, 0))
            y += 17
        y += 8

    # Seal placeholder (circle)
    seal_x, seal_y, seal_r = M+40, H-M-80, 35
    draw.ellipse([seal_x-seal_r, seal_y-seal_r, seal_x+seal_r, seal_y+seal_r],
                 outline=(0, 0, 128), width=2)
    draw.ellipse([seal_x-seal_r+6, seal_y-seal_r+6, seal_x+seal_r-6, seal_y+seal_r-6],
                 outline=(0, 0, 128), width=1)
    draw.text((seal_x, seal_y), "SEAL", font=font_r10, fill=(0, 0, 128), anchor="mm")

    # Footer
    y = H - M - 70
    draw.line([(M, y), (W-M, y)], fill=(0, 0, 0), width=1)
    y += 8
    for line in footer.split("\n"):
        draw.text((W-M, y), line, font=font_i10, fill=(0, 0, 0), anchor="ra")
        y += 15

    out_path = AUTH_DIR / filename
    img.save(str(out_path), "JPEG", quality=93)
    return out_path


def main():
    print(f"Regenerating {len(TEMPLATES)} authentic documents with consistent dates...")

    success = 0
    for i, (fname, title, auth, ref, body, footer) in enumerate(TEMPLATES, 1):
        issued, hearing = make_dates()
        print(f"  [{i}/{len(TEMPLATES)}] {fname} (issued={issued}, hearing={hearing})...", end=" ")
        try:
            path = create_doc_pil(fname, title, auth, ref, body, footer, issued, hearing)
            sz = path.stat().st_size // 1024
            print(f"OK ({sz}KB)")
            success += 1
        except Exception as e:
            print(f"FAILED: {e}")

    print(f"\nDone: {success}/{len(TEMPLATES)} documents regenerated in {AUTH_DIR}")


if __name__ == "__main__":
    main()
