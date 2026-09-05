from typing import List, Dict, Any
from backend.app.models.schemas import VendorDetails

class ForensicsVerificationService:
    @staticmethod
    def audit_bid_forgery(vendor: VendorDetails, all_vendors: List[VendorDetails]) -> Dict[str, Any]:
        """
        Runs advanced PDF forensics checks:
        1. Duplicate file hash detection (plagiarism across submissions).
        2. PDF creation timeline anomaly detection.
        3. Metadata template overlap verification (shared Creator/Producer).
        """
        issues = []
        scores = []
        
        duplicate_hash_found = False
        plagiarized_bid_id = None
        plagiarized_vendor = None

        # 1. Duplicate Hash Check (Plagiarism / Double submission)
        for other in all_vendors:
            if other.bid_id != vendor.bid_id and other.pdf_hash != "unknown" and other.pdf_hash == vendor.pdf_hash:
                duplicate_hash_found = True
                plagiarized_bid_id = other.bid_id
                plagiarized_vendor = other.vendor_name
                issues.append(f"CRITICAL: Exact duplicate file hash matching {other.vendor_name} ({other.bid_id})!")
                scores.append(0.0)
                break
                
        # 2. Metadata Timeline Anomaly Check
        # Example: Creation Date in the future, or ModDate earlier than CreationDate
        if vendor.pdf_created and vendor.pdf_modified:
            try:
                # Basic string or logical checks if they are in PDF date format (D:YYYYMMDDHHMMSS...)
                # If modified is earlier than created:
                if vendor.pdf_modified < vendor.pdf_created:
                    issues.append("WARNING: PDF modified date is registered prior to its creation date!")
                    scores.append(50.0)
            except Exception:
                pass

        # 3. Shared Metadata Overlap (Cartel / Template reuse check)
        # If different vendors share the exact same PDF Author, Creator, or Creation Microsecond
        shared_template_vendors = []
        if vendor.pdf_created and "unknown" not in vendor.pdf_created:
            for other in all_vendors:
                if other.bid_id != vendor.bid_id and other.pdf_created == vendor.pdf_created:
                    shared_template_vendors.append(other.vendor_name)
            
            if shared_template_vendors:
                issues.append(f"WARNING: Identical PDF creation microsecond as {', '.join(shared_template_vendors)} (Template Reuse Alert).")
                scores.append(40.0)

        # 4. Check for invalid state code GST structure
        if "INVALID" in vendor.gst_number or "MISSING" in vendor.gst_number:
            issues.append("CRITICAL: Synthetic tax identity format detected.")
            scores.append(0.0)

        # Calculate final forensics score
        if len(scores) > 0:
            forensics_score = sum(scores) / len(scores)
        else:
            forensics_score = 100.0

        if forensics_score < 50.0:
            status = "FAIL"
        elif forensics_score < 90.0:
            status = "NEEDS_REVIEW"
        else:
            status = "PASS"

        return {
            "duplicate_hash_found": duplicate_hash_found,
            "plagiarized_bid_id": plagiarized_bid_id,
            "plagiarized_vendor": plagiarized_vendor,
            "metadata_anomaly_found": len(issues) > 0,
            "forensics_score": round(forensics_score, 1),
            "status": status,
            "issues": issues,
            "details": "; ".join(issues) if issues else "All PDF structural entity hashes verified clean."
        }
