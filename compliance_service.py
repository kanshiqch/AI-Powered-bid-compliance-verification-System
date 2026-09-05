from typing import List, Dict, Tuple
from backend.app.models.schemas import (
    VendorDetails, TenderCriteria, ComplianceResult, ComplianceCheckItem, CategoryScores, GNNGraphResponse, SmartChecklist, ChecklistItem
)
from backend.app.services.nlp_service import NLPService
from backend.app.services.gnn_service import GNNFraudDetectionService
from backend.app.services.forensics_service import ForensicsVerificationService

class ComplianceVerificationEngine:
    def __init__(self):
        self.gnn_service = GNNFraudDetectionService()

    def verify_bid(
        self,
        vendor: VendorDetails,
        tender: TenderCriteria,
        gnn_response: GNNGraphResponse,
        all_vendors: List[VendorDetails] = []
    ) -> ComplianceResult:
        """Verifies vendor bid compliance using NLP checks, GNN fraud, and PDF Forensics."""
        # Run NLP compliance checks
        checks = NLPService.run_nlp_compliance_checks(vendor, tender)
        
        detected_issues: List[str] = []

        # Run Forensic Fraud Detection check
        forensics_res = ForensicsVerificationService.audit_bid_forgery(vendor, all_vendors)
        forensic_status = forensics_res["status"]
        forensic_score = forensics_res["forensics_score"]
        forensic_details = forensics_res["details"]
        
        for issue in forensics_res["issues"]:
            detected_issues.append(issue)

        checks.append(ComplianceCheckItem(
            check_name="Forensic Document Integrity Audit",
            category="Fraud & Forensics",
            status=forensic_status,
            score=forensic_score,
            details=forensic_details
        ))
        
        # Check GNN Collusion Flags for this vendor
        vendor_cartels = [
            c for c in gnn_response.detected_cartels
            if vendor.vendor_name in c.vendors
        ]
        
        if vendor_cartels:
            for cartel in vendor_cartels:
                issue_text = f"CRITICAL GNN FRAUD FLAG: Cartel / Cover Bidding detected! Shared attributes: {', '.join(cartel.shared_attributes)}"
                detected_issues.append(issue_text)
                checks.append(ComplianceCheckItem(
                    check_name="GNN Collusion Network Analysis",
                    category="GNN Collusion",
                    status="FAIL",
                    score=0.0,
                    details=issue_text
                ))
        else:
            checks.append(ComplianceCheckItem(
                check_name="GNN Collusion Network Analysis",
                category="GNN Collusion",
                status="PASS",
                score=100.0,
                details="No covert bidding ring or shared infrastructure detected on GNN Knowledge Graph."
            ))

        # Collect failed checks for issues list
        for chk in checks:
            if chk.status == "FAIL" and chk.details not in detected_issues:
                detected_issues.append(chk.details)

        # Calculate overall score
        total_score = sum(c.score for c in checks) / len(checks) if checks else 0.0

        # Categorize Overall Status
        has_critical_fail = any(c.status == "FAIL" and c.category in ["Tax & Identity", "Fraud & Forensics", "GNN Collusion"] for c in checks)
        
        if has_critical_fail or total_score < 60.0 or vendor_cartels:
            overall_status = "RED"  # Rejected / Fraud Alert
        elif total_score < 85.0 or any(c.status == "FAIL" for c in checks):
            overall_status = "YELLOW"  # Needs Manual Review
        else:
            overall_status = "GREEN"  # Fully Compliant

        # Calculate CategoryScores averages
        tax_vals = [c.score for c in checks if c.category == "Tax & Identity"]
        fin_vals = [c.score for c in checks if c.category == "Financial"]
        exp_vals = [c.score for c in checks if c.category in ["Experience & Certificate", "Experience & Quality"]]
        forensic_vals = [c.score for c in checks if c.category == "Fraud & Forensics"]
        gnn_vals = [c.score for c in checks if c.category == "GNN Collusion"]

        category_scores = CategoryScores(
            tax_identity=round(sum(tax_vals) / len(tax_vals), 1) if tax_vals else 100.0,
            financial=round(sum(fin_vals) / len(fin_vals), 1) if fin_vals else 100.0,
            experience_quality=round(sum(exp_vals) / len(exp_vals), 1) if exp_vals else 100.0,
            forensics=round(sum(forensic_vals) / len(forensic_vals), 1) if forensic_vals else 100.0,
            gnn_collusion=round(sum(gnn_vals) / len(gnn_vals), 1) if gnn_vals else 100.0
        )

        return ComplianceResult(
            bid_id=vendor.bid_id,
            vendor_name=vendor.vendor_name,
            overall_score=round(total_score, 1),
            overall_status=overall_status,
            category_scores=category_scores,
            itemized_checks=checks,
            detected_issues=detected_issues,
            vendor_details=vendor
        )

    def generate_smart_checklist(
        self,
        vendor: VendorDetails,
        tender: TenderCriteria,
        compliance_res: ComplianceResult,
        gnn_response: GNNGraphResponse
    ) -> SmartChecklist:
        """Helper to generate Smart checklist items with individual confidence metrics."""
        items = []
        
        # 1. GST Identification
        gst_item = next((c for c in compliance_res.itemized_checks if "GST" in c.check_name), None)
        gst_status = gst_item.status if gst_item else "NEEDS_REVIEW"
        items.append(ChecklistItem(
            name="GSTIN Registration",
            category="Tax",
            status=gst_status,
            confidence=99.2 if gst_status == "PASS" else 0.0,
            extracted_text=f"GSTIN: {vendor.gst_number}"
        ))

        # 2. PAN Verification
        pan_item = next((c for c in compliance_res.itemized_checks if "PAN" in c.check_name), None)
        pan_status = pan_item.status if pan_item else "NEEDS_REVIEW"
        items.append(ChecklistItem(
            name="PAN Card Check",
            category="Tax",
            status=pan_status,
            confidence=98.8 if pan_status == "PASS" else 0.0,
            extracted_text=f"PAN: {vendor.pan_number}"
        ))

        # 3. Minimum Turnover Verification
        turnover_item = next((c for c in compliance_res.itemized_checks if "Turnover" in c.check_name), None)
        turnover_status = turnover_item.status if turnover_item else "NEEDS_REVIEW"
        items.append(ChecklistItem(
            name="Annual Turnover Threshold",
            category="Financial",
            status=turnover_status,
            confidence=99.5 if turnover_status == "PASS" else 50.0,
            extracted_text=f"Declared Turnover: INR {vendor.turnover_lakhs} Lakhs (Threshold: {tender.minimum_turnover_lakhs} Lakhs)"
        ))

        # 4. Work Experience Audit
        exp_item = next((c for c in compliance_res.itemized_checks if "Experience" in c.check_name), None)
        exp_status = exp_item.status if exp_item else "NEEDS_REVIEW"
        items.append(ChecklistItem(
            name="Technical Work Experience",
            category="Technical",
            status=exp_status,
            confidence=97.4 if exp_status == "PASS" else 40.0,
            extracted_text=f"Extracted Experience: {vendor.experience_years} Years (Required: {tender.min_experience_years} Years)"
        ))

        # 5. ISO 9001 Certificate
        iso_item = next((c for c in compliance_res.itemized_checks if "ISO" in c.check_name), None)
        iso_status = iso_item.status if iso_item else "NEEDS_REVIEW"
        items.append(ChecklistItem(
            name="ISO 9001:2015 Accreditation",
            category="Legal",
            status=iso_status,
            confidence=96.8 if iso_status == "PASS" else 20.0,
            extracted_text=f"ISO Expiry Year: {vendor.iso_expiry_year} (Accreditation Required: ISO 9001:2015)"
        ))

        # Calculate average confidence
        total_conf = sum(i.confidence for i in items) / len(items) if items else 100.0

        return SmartChecklist(
            bid_id=vendor.bid_id,
            vendor_name=vendor.vendor_name,
            items=items,
            overall_confidence=round(total_conf, 1)
        )
