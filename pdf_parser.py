import re
import hashlib
from pathlib import Path
from pypdf import PdfReader
from backend.app.models.schemas import VendorDetails, TenderCriteria

class PDFParserService:
    @staticmethod
    def extract_text_from_pdf(pdf_path: str) -> str:
        """Extract raw text from PDF file using PyPDF."""
        try:
            reader = PdfReader(pdf_path)
            full_text = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
            return "\n".join(full_text)
        except Exception as e:
            print(f"Error reading PDF {pdf_path}: {e}")
            return ""

    @classmethod
    def parse_vendor_bid_pdf(cls, pdf_path: str, bid_id: str = "BID-UNKNOWN") -> VendorDetails:
        """Parses vendor bid PDF using OCR/Regex pattern matching and structural entity extraction."""
        text = cls.extract_text_from_pdf(pdf_path)
        filename = Path(pdf_path).name

        # Calculate PDF file hash
        pdf_hash = "unknown"
        try:
            with open(pdf_path, "rb") as f:
                pdf_hash = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            print(f"Error computing hash for {pdf_path}: {e}")

        # Extract PDF metadata properties
        pdf_author = None
        pdf_producer = None
        pdf_created = None
        pdf_modified = None
        try:
            reader = PdfReader(pdf_path)
            meta = reader.metadata
            if meta:
                pdf_author = meta.author
                pdf_producer = meta.producer
                pdf_created = meta.get("/CreationDate")
                pdf_modified = meta.get("/ModDate")
        except Exception as e:
            print(f"Error reading metadata from {pdf_path}: {e}")

        # Extract Vendor Name
        vendor_name_match = re.search(r"(?:BID SUBMISSION|BID PROPOSAL):\s*(.+)", text, re.IGNORECASE)
        vendor_name = vendor_name_match.group(1).strip() if vendor_name_match else "Unknown Vendor"

        # Extract GSTIN (Format: 2 digits, 5 letters, 4 digits, 1 letter, 1 char, Z, 1 char)
        gst_match = re.search(r"GST Identification No \(GSTIN\)\s*([A-Z0-9]+)", text, re.IGNORECASE)
        if not gst_match:
            gst_match = re.search(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z0-9]\d\b", text)
        gst_number = gst_match.group(1).strip() if gst_match else "MISSING_GST"

        # Extract PAN
        pan_match = re.search(r"Permanent Account No \(PAN\)\s*([A-Z0-9]+)", text, re.IGNORECASE)
        pan_number = pan_match.group(1).strip() if pan_match else "MISSING_PAN"

        # Extract Turnover
        turnover_match = re.search(r"Annual Turnover \(Lakhs INR\)\s*INR\s*([\d\.]+)", text, re.IGNORECASE)
        turnover_lakhs = float(turnover_match.group(1)) if turnover_match else 0.0

        # Extract Bid Price
        price_match = re.search(r"Total Bid Price \(Lakhs INR\)\s*INR\s*([\d\.]+)", text, re.IGNORECASE)
        bid_price_lakhs = float(price_match.group(1)) if price_match else 0.0

        # Extract Experience
        exp_match = re.search(r"Technical Experience\s*(\d+)\s*Years", text, re.IGNORECASE)
        experience_years = int(exp_match.group(1)) if exp_match else 0

        # Extract ISO Expiry Year
        iso_match = re.search(r"ISO 9001 Certificate Expiry\s*(\d{4})", text, re.IGNORECASE)
        iso_expiry_year = int(iso_match.group(1)) if iso_match else 2000

        # Extract Director Name
        dir_match = re.search(r"Managing Director\s*(.+)", text, re.IGNORECASE)
        director_name = dir_match.group(1).strip() if dir_match else "Unknown Director"

        # Extract IP Address
        ip_match = re.search(r"Submission Terminal IP Address\s*([\d\.]+)", text, re.IGNORECASE)
        ip_address = ip_match.group(1).strip() if ip_match else "0.0.0.0"

        # Extract Bank Account
        bank_match = re.search(r"Primary Bank Account Number\s*(\d+)", text, re.IGNORECASE)
        bank_account_no = bank_match.group(1).strip() if bank_match else "0000000000"

        vendor_id = f"VEND-{abs(hash(vendor_name)) % 1000:03d}"

        return VendorDetails(
            bid_id=bid_id,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            gst_number=gst_number,
            pan_number=pan_number,
            turnover_lakhs=turnover_lakhs,
            experience_years=experience_years,
            iso_certified=iso_expiry_year >= 2026,
            iso_expiry_year=iso_expiry_year,
            director_name=director_name,
            ip_address=ip_address,
            bank_account_no=bank_account_no,
            pdf_filename=filename,
            is_fake_flag="INVALID" in gst_number or "MISSING" in gst_number or turnover_lakhs < 30.0,
            bid_price_lakhs=bid_price_lakhs,
            pdf_hash=pdf_hash,
            pdf_author=pdf_author,
            pdf_producer=pdf_producer,
            pdf_created=pdf_created,
            pdf_modified=pdf_modified
        )


    @classmethod
    def parse_tender_pdf(cls, pdf_path: str) -> TenderCriteria:
        """Parses tender PDF to extract mandatory eligibility rules."""
        text = cls.extract_text_from_pdf(pdf_path)
        
        tender_id_match = re.search(r"Tender ID:\s*([A-Z0-9\/]+)", text)
        tender_id = tender_id_match.group(1) if tender_id_match else "GEM/2026/DEFAULT"

        turnover_match = re.search(r"INR\s*([\d\.]+)\s*Lakhs", text, re.IGNORECASE)
        min_turnover = float(turnover_match.group(1)) if turnover_match else 50.0

        exp_match = re.search(r"Minimum\s*(\d+)\s*Years", text, re.IGNORECASE)
        min_exp = int(exp_match.group(1)) if exp_match else 3

        return TenderCriteria(
            tender_id=tender_id,
            title="GeM Tender for IT Hardware & Laptops Supply",
            minimum_turnover_lakhs=min_turnover,
            min_experience_years=min_exp,
            required_certifications=["ISO 9001:2015"],
            must_have_gst=True,
            must_have_pan=True,
            emd_amount_inr=50000.0
        )
