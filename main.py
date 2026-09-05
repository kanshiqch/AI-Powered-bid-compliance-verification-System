import os
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.models.schemas import (
    TenderCriteria, VendorDetails, ComplianceResult, GNNGraphResponse, DashboardSummary,
    LoginRequest, RegisterRequest, AuthResponse, TerminalLogMessage,
    ChatbotQueryRequest, ChatbotQueryResponse, SmartChecklist, ChecklistItem,
    ChecklistOverrideRequest, RiskReport, ExpiryAlert, DuplicateBid, AIRecommendation,
    VendorHistoryProfile
)
from backend.app.document_generator import generate_all_sample_pdfs, SAMPLE_DIR
from backend.app.services.pdf_parser import PDFParserService
from backend.app.services.gnn_service import GNNFraudDetectionService
from backend.app.services.compliance_service import ComplianceVerificationEngine
from backend.app.services.database_service import DatabaseService
from backend.app.services.chatbot_service import ChatbotVerificationService
from backend.app.services.forensics_service import ForensicsVerificationService


app = FastAPI(
    title="AI GeM Bid Compliance & GNN Fraud Detection Engine",
    description="Automated Procurement Compliance Verification using Python, NLP, and Graph Neural Networks",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for active session
DB_TENDER: TenderCriteria = None
DB_VENDORS: List[VendorDetails] = []
DB_RESULTS: List[ComplianceResult] = []
DB_GNN_GRAPH: GNNGraphResponse = None
DB_LOGS: List[TerminalLogMessage] = []
DB_USERS: Dict[str, dict] = {}
DB_CHECKLIST_OVERRIDES: Dict[str, Dict[str, str]] = {}


gnn_service = GNNFraudDetectionService()
compliance_engine = ComplianceVerificationEngine()

def log_event(level: str, module: str, message: str):
    log_entry = TerminalLogMessage(
        timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        level=level,
        module=module,
        message=message
    )
    DB_LOGS.append(log_entry)
    if len(DB_LOGS) > 100:
        DB_LOGS.pop(0)

# Ensure sample PDFs exist on boot
if not any(SAMPLE_DIR.glob("*.pdf")):
    generate_all_sample_pdfs()

# Mount frontend directory for web UI
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

@app.on_event("startup")
def startup_seed():
    """Auto-seeds the application with sample data on startup."""
    seed_demo_data()

def seed_demo_data():
    global DB_TENDER, DB_VENDORS, DB_RESULTS, DB_GNN_GRAPH, DB_USERS
    
    # Seed default user accounts
    DB_USERS["gov"] = {
        "username": "gov",
        "email": "authority@gem.gov.in",
        "password": "gov123",
        "role": "government",
        "name": "Government Official",
        "organization": "Government e-Marketplace"
    }
    DB_USERS["vendor"] = {
        "username": "vendor",
        "email": "vendor@techcorp.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "Vendor Representative",
        "organization": "TechCorp Solutions"
    }
    DB_USERS["infotech"] = {
        "username": "infotech",
        "email": "bids@infotech.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "InfoTech Representative",
        "organization": "InfoTech Enterprise"
    }
    DB_USERS["globalsol"] = {
        "username": "globalsol",
        "email": "compliance@globalsol.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "Global Digital Representative",
        "organization": "Global Digital Solutions"
    }
    DB_USERS["alphasys"] = {
        "username": "alphasys",
        "email": "contact@alphasys.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "Alpha Network Representative",
        "organization": "Alpha Network Systems"
    }
    DB_USERS["betasys"] = {
        "username": "betasys",
        "email": "sales@betasys.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "Beta Systematics Representative",
        "organization": "Beta Systematics Pvt Ltd"
    }
    DB_USERS["cybertech"] = {
        "username": "cybertech",
        "email": "info@cybertech.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "CyberTech Representative",
        "organization": "CyberTech Innovations"
    }
    DB_USERS["apex"] = {
        "username": "apex",
        "email": "admin@apexhardware.com",
        "password": "vendor123",
        "role": "vendor",
        "name": "Apex Hardware Representative",
        "organization": "Apex Hardware Traders"
    }
    
    log_event("INFO", "OCR", "Initializing GeM Bid Compliance & GNN Fraud detection pipeline...")
    
    # 1. Parse Tender PDF
    tender_pdf = SAMPLE_DIR / "Tender_GeM_2026_Hardware.pdf"
    if not tender_pdf.exists():
        log_event("WARN", "OCR", "Sample Tender PDF missing. Re-generating...")
        generate_all_sample_pdfs()
    
    log_event("INFO", "OCR", f"Parsing Tender PDF: {tender_pdf.name}...")
    DB_TENDER = PDFParserService.parse_tender_pdf(str(tender_pdf))
    log_event("INFO", "NLP", f"Tender Specifications Loaded. ID: {DB_TENDER.tender_id}, Min Turnover: INR {DB_TENDER.minimum_turnover_lakhs} Lakhs, Exp: {DB_TENDER.min_experience_years} Years.")

    # 2. Parse Vendor Bid PDFs
    pdf_files = sorted([p for p in SAMPLE_DIR.glob("Vendor_*.pdf")])
    DB_VENDORS = []
    
    log_event("INFO", "OCR", f"Discovered {len(pdf_files)} vendor proposal PDFs. Initiating structural entity extraction...")
    
    for idx, p in enumerate(pdf_files, start=101):
        bid_id = f"BID-{idx}"
        v = PDFParserService.parse_vendor_bid_pdf(str(p), bid_id=bid_id)
        DB_VENDORS.append(v)
        log_event("INFO", "NLP", f"Extracted {v.vendor_name} ({bid_id}). GSTIN: {v.gst_number}, Turnover: INR {v.turnover_lakhs}L, MD: {v.director_name}.")

    # 3. Run GNN Fraud & Cartel Detection
    log_event("INFO", "GNN_CONV", "Building heterogeneous knowledge graph of entities (Vendors, Directors, IPs, Bank Accounts)...")
    DB_GNN_GRAPH = gnn_service.run_gnn_cartel_detection(DB_VENDORS, DB_TENDER.tender_id)
    log_event("GNN_EVENT", "GNN_CONV", f"Graph neural message passing complete. Node count: {len(DB_GNN_GRAPH.nodes)}, Edge count: {len(DB_GNN_GRAPH.edges)}, Density: {DB_GNN_GRAPH.graph_density}.")
    
    if DB_GNN_GRAPH.detected_cartels:
        log_event("ERROR", "GNN_CONV", f"DISCOVERED {len(DB_GNN_GRAPH.detected_cartels)} SUSPICIOUS BIDDING CARTELS / RING INFRASTRUCTURES!")
        for c in DB_GNN_GRAPH.detected_cartels:
            log_event("ERROR", "GNN_CONV", f"Cartel {c.cluster_id} Flagged: Bidders {', '.join(c.vendors)} share identical {c.shared_attributes[0]}. risk: {c.risk_level}.")
    else:
        log_event("INFO", "GNN_CONV", "GNN collusion scan finished: No anomalous shared entity clusters detected.")

    # 4. Run Compliance Verification Engine on all bids
    log_event("INFO", "AUDIT", "Executing Automated Compliance Evaluation Engine on all active bids...")
    DB_RESULTS = []
    red_count = 0
    yellow_count = 0
    green_count = 0
    
    for v in DB_VENDORS:
        res = compliance_engine.verify_bid(v, DB_TENDER, DB_GNN_GRAPH, DB_VENDORS)
        DB_RESULTS.append(res)

        if res.overall_status == "RED":
            red_count += 1
            log_event("ERROR", "AUDIT", f"Bid {res.bid_id} ({res.vendor_name}) DISQUALIFIED. Score: {res.overall_score}%. Issues: {', '.join(res.detected_issues)}")
        elif res.overall_status == "YELLOW":
            yellow_count += 1
            log_event("WARN", "AUDIT", f"Bid {res.bid_id} ({res.vendor_name}) requires MANUAL REVIEW. Score: {res.overall_score}%. Minor warnings.")
        else:
            green_count += 1
            log_event("INFO", "AUDIT", f"Bid {res.bid_id} ({res.vendor_name}) COMPLIANT & APPROVED. Score: {res.overall_score}%.")

    log_event("INFO", "AUDIT", f"Audit pipeline finalized: Compliant={green_count}, Review Needed={yellow_count}, Disqualified={red_count}.")

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "AI GeM Compliance Engine active"}

@app.post("/api/auth/register", response_model=AuthResponse)
def register_user(req: RegisterRequest):
    username_lower = req.username.strip().lower()
    if username_lower in DB_USERS:
        return AuthResponse(
            success=False,
            message="Username is already registered."
        )
    
    user_data = {
        "username": req.username.strip(),
        "email": req.email.strip(),
        "password": req.password,
        "role": req.role,
        "name": req.username.strip().capitalize(),
        "organization": req.organization
    }
    DB_USERS[username_lower] = user_data
    log_event("INFO", "AUTH", f"New user registered: {req.username} ({req.role})")
    
    return AuthResponse(
        success=True,
        message="Registration successful! You can now log in.",
        username=user_data["username"],
        role=user_data["role"],
        name=user_data["name"]
    )

@app.post("/api/auth/login", response_model=AuthResponse)
def login_user(req: LoginRequest):
    username_lower = req.username.strip().lower()
    if username_lower not in DB_USERS:
        return AuthResponse(
            success=False,
            message="Invalid username or password."
        )
    
    user_data = DB_USERS[username_lower]
    if user_data["password"] != req.password:
        return AuthResponse(
            success=False,
            message="Invalid username or password."
        )
        
    log_event("INFO", "AUTH", f"User {user_data['username']} logged in successfully as {user_data['role']}")
    return AuthResponse(
        success=True,
        message="Login successful!",
        username=user_data["username"],
        role=user_data["role"],
        name=user_data["name"]
    )

@app.post("/api/demo/seed")
def reseed_demo_endpoint():
    """Endpoint to re-seed and execute full AI verification pipeline."""
    generate_all_sample_pdfs()
    seed_demo_data()
    return {"status": "success", "message": f"Successfully processed {len(DB_VENDORS)} bids against Tender {DB_TENDER.tender_id}"}

@app.get("/api/dashboard/stats", response_model=DashboardSummary)
def get_dashboard_summary():
    """Returns real-time dashboard analytics, compliance scorecards, and GNN graph payload."""
    if not DB_RESULTS:
        seed_demo_data()

    green_count = sum(1 for r in DB_RESULTS if r.overall_status == "GREEN")
    yellow_count = sum(1 for r in DB_RESULTS if r.overall_status == "YELLOW")
    red_count = sum(1 for r in DB_RESULTS if r.overall_status == "RED")
    cartel_count = len(DB_GNN_GRAPH.detected_cartels) if DB_GNN_GRAPH else 0

    return DashboardSummary(
        total_tenders=1,
        total_bids=len(DB_RESULTS),
        compliant_bids=green_count,
        review_needed_bids=yellow_count,
        rejected_bids=red_count,
        flagged_cartels=cartel_count,
        network_risk_index=DB_GNN_GRAPH.overall_network_risk if DB_GNN_GRAPH else 0.0,
        bids=DB_RESULTS,
        graph_data=DB_GNN_GRAPH,
        recent_logs=DB_LOGS
    )

@app.get("/api/fraud/collusion-graph", response_model=GNNGraphResponse)
def get_collusion_graph():
    """Returns GNN Heterogeneous Knowledge Graph for D3 rendering."""
    if not DB_GNN_GRAPH:
        seed_demo_data()
    return DB_GNN_GRAPH

@app.post("/api/upload/bid")
async def upload_custom_bid(file: UploadFile = File(...)):
    """Allows manual upload of vendor bid PDF for OCR parsing and compliance audit."""
    if not file.filename.endswith(".pdf"):
        log_event("WARN", "OCR", f"Attempted upload of unsupported file type: {file.filename}")
        raise HTTPException(status_code=400, detail="Only PDF files supported.")
    
    save_path = SAMPLE_DIR / f"Upload_{file.filename}"
    log_event("INFO", "OCR", f"Receiving custom bid PDF '{file.filename}', saving to local staging...")
    with open(save_path, "wb") as f:
        content = await file.read()
        f.write(content)

    new_bid_id = f"BID-UPL-{len(DB_VENDORS)+1:03d}"
    log_event("INFO", "OCR", f"OCR parsing and layout structural entity analysis on: {save_path.name}")
    parsed_vendor = PDFParserService.parse_vendor_bid_pdf(str(save_path), bid_id=new_bid_id)
    
    DB_VENDORS.append(parsed_vendor)
    log_event("INFO", "NLP", f"Custom Bid extracted -> {parsed_vendor.vendor_name} ({new_bid_id}). GSTIN: {parsed_vendor.gst_number}, Turnover: INR {parsed_vendor.turnover_lakhs}L.")
    
    # Re-run GNN graph and compliance evaluation
    global DB_GNN_GRAPH, DB_RESULTS
    log_event("INFO", "GNN_CONV", "Re-running GNN fraud message passing collusion check with new bid inclusion...")
    DB_GNN_GRAPH = gnn_service.run_gnn_cartel_detection(DB_VENDORS, DB_TENDER.tender_id)
    log_event("GNN_EVENT", "GNN_CONV", f"GNN check done. Current Graph density: {DB_GNN_GRAPH.graph_density}.")
    
    # Preserve selected status of previously selected bids
    selected_bid_ids = {r.bid_id for r in DB_RESULTS if r.selected}
    
    DB_RESULTS = []
    for v in DB_VENDORS:
        res = compliance_engine.verify_bid(v, DB_TENDER, DB_GNN_GRAPH, DB_VENDORS)
        if v.bid_id in selected_bid_ids:
            res.selected = True
        DB_RESULTS.append(res)


    uploaded_result = next(r for r in DB_RESULTS if r.bid_id == new_bid_id)
    log_event("INFO", "AUDIT", f"Custom compliance verification finished for {uploaded_result.vendor_name}. Status: {uploaded_result.overall_status}, Score: {uploaded_result.overall_score}%.")
    return uploaded_result

@app.post("/api/bids/{bid_id}/select")
def select_bid(bid_id: str, officer: str = "anonymous"):
    """Awards the tender bid, persists selection, and simulates email dispatch to the registered vendor."""
    global DB_RESULTS
    
    # 1. Locate the compliance result matching the bid ID
    bid_result = None
    for r in DB_RESULTS:
        if r.bid_id == bid_id:
            bid_result = r
            break
            
    if not bid_result:
        log_event("WARN", "AUDIT", f"Failed to select bid: ID {bid_id} not found.")
        raise HTTPException(status_code=404, detail="Bid not found")
        
    bid_result.selected = True
    vendor_name = bid_result.vendor_name
    registered_email = None
    matched_user = None
    
    # 2. Match with registered user account in DB_USERS by organization name
    for username, user_data in DB_USERS.items():
        if user_data.get("role") == "vendor" and user_data.get("organization"):
            org = user_data["organization"].lower().strip()
            v_name = vendor_name.lower().strip()
            # Perform substring match to account for "Pvt Ltd" vs "Solutions" etc.
            if org in v_name or v_name in org:
                matched_user = user_data
                registered_email = user_data["email"]
                break
                
    # 3. Fallback email format if the vendor is not pre-registered
    if not registered_email:
        clean_name = "".join(c for c in vendor_name if c.isalnum()).lower()
        registered_email = f"contact@{clean_name[:15] or 'vendor'}.com"
        log_event("WARN", "EMAIL", f"No registered user account found for '{vendor_name}'. Dispatching to fallback email address.")
        
    # 4. Build formal selection email content
    subject = f"Government e-Marketplace (GeM) - Tender Award Notification: Bid {bid_id}"
    email_body = f"""Dear {vendor_name} Team,

We are pleased to inform you that your bid (Bid ID: {bid_id}) submitted for the GeM Tender (ID: {DB_TENDER.tender_id}) has been formally reviewed and selected by our procurement panel.

Award Details:
- Tender ID: {DB_TENDER.tender_id}
- Selected Vendor: {vendor_name}
- Reviewing Officer: {officer}
- Notification Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

A formal service order agreement will be sent shortly. Please ensure your contact details remain up to date.

Regards,
Procurement Office
Government e-Marketplace (GeM)
"""
    full_email_content = f"Subject: {subject}\n\n{email_body}"
    
    # 5. Persist selection to SQLite database
    try:
        DatabaseService.save_selection(
            bid_id=bid_id,
            vendor_name=vendor_name,
            officer_username=officer,
            registered_email=registered_email,
            email_content=full_email_content
        )
        log_event("INFO", "EMAIL", f"Sent selection notification to registered email: {registered_email} (Saved to persistent DB)")
    except Exception as e:
        log_event("ERROR", "AUDIT", f"Failed to persist selection in DB: {str(e)}")
        
    return {
        "status": "success",
        "message": f"Bid {bid_id} selected. Notification email dispatched to registered address: {registered_email}",
        "registered_email": registered_email,
        "matched_user": matched_user.get("username") if matched_user else None
    }

@app.get("/api/selections")
def get_selection_history():
    """Retrieves all officer selections and email notification records from the persistent database."""
    try:
        return DatabaseService.get_selections()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database retrieval failed: {str(e)}")

@app.post("/api/chatbot/query", response_model=ChatbotQueryResponse)
def run_chatbot_query(req: ChatbotQueryRequest):
    if not DB_RESULTS:
        seed_demo_data()
    res = ChatbotVerificationService.answer_query(
        question=req.question,
        tender=DB_TENDER,
        bids=DB_RESULTS,
        gnn=DB_GNN_GRAPH,
        selected_bid_id=req.bid_id
    )
    return ChatbotQueryResponse(
        answer=res["answer"],
        context_sources=res["context_sources"],
        timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    )

@app.get("/api/compliance/checklist/{bid_id}", response_model=SmartChecklist)
def get_bid_checklist(bid_id: str):
    if not DB_RESULTS:
        seed_demo_data()
    
    res = next((r for r in DB_RESULTS if r.bid_id == bid_id), None)
    if not res:
        raise HTTPException(status_code=404, detail="Bid not found")
        
    checklist = compliance_engine.generate_smart_checklist(
        vendor=res.vendor_details,
        tender=DB_TENDER,
        compliance_res=res,
        gnn_response=DB_GNN_GRAPH
    )
    
    # Apply overrides if they exist
    if bid_id in DB_CHECKLIST_OVERRIDES:
        overrides = DB_CHECKLIST_OVERRIDES[bid_id]
        for item in checklist.items:
            if item.name in overrides:
                item.status = overrides[item.name]
                item.manual_override = True
                item.verified_by = "Manual Officer Override"
                
    return checklist

@app.post("/api/compliance/checklist/{bid_id}/verify")
def override_checklist_status(bid_id: str, req: ChecklistOverrideRequest):
    if not DB_RESULTS:
        seed_demo_data()
        
    if bid_id not in DB_CHECKLIST_OVERRIDES:
        DB_CHECKLIST_OVERRIDES[bid_id] = {}
        
    DB_CHECKLIST_OVERRIDES[bid_id][req.item_name] = req.status
    log_event("WARN", "AUDIT", f"Manual override registered by officer '{req.officer}' on Bid {bid_id} item '{req.item_name}' status set to '{req.status}'")
    
    # Recalculate Compliance score dynamically based on overrides
    for idx, r in enumerate(DB_RESULTS):
        if r.bid_id == bid_id:
            res = compliance_engine.verify_bid(r.vendor_details, DB_TENDER, DB_GNN_GRAPH, DB_VENDORS)
            for check in res.itemized_checks:
                mapped_name = ""
                if "GST" in check.check_name:
                    mapped_name = "GSTIN Registration"
                elif "PAN" in check.check_name:
                    mapped_name = "PAN Card Check"
                elif "Turnover" in check.check_name:
                    mapped_name = "Annual Turnover Threshold"
                elif "Experience" in check.check_name:
                    mapped_name = "Technical Work Experience"
                elif "ISO" in check.check_name:
                    mapped_name = "ISO 9001:2015 Accreditation"
                    
                if mapped_name and mapped_name in DB_CHECKLIST_OVERRIDES[bid_id]:
                    override_val = DB_CHECKLIST_OVERRIDES[bid_id][mapped_name]
                    check.status = override_val
                    check.score = 100.0 if override_val == "PASS" else 0.0
                    check.details = f"Manual override by {req.officer}: set to {override_val}."
            
            total_score = sum(c.score for c in res.itemized_checks) / len(res.itemized_checks)
            res.overall_score = round(total_score, 1)
            has_critical_fail = any(c.status == "FAIL" and c.category in ["Tax & Identity", "Fraud & Forensics", "GNN Collusion"] for c in res.itemized_checks)
            
            if has_critical_fail or total_score < 60.0:
                res.overall_status = "RED"
            elif total_score < 85.0 or any(c.status == "FAIL" for c in res.itemized_checks):
                res.overall_status = "YELLOW"
            else:
                res.overall_status = "GREEN"
                
            res.selected = r.selected
            DB_RESULTS[idx] = res
            break
            
    return {"status": "success", "message": f"Overrode checklist item '{req.item_name}' to '{req.status}' successfully."}

@app.get("/api/alerts/expiry", response_model=List[ExpiryAlert])
def get_document_expiry_alerts():
    if not DB_RESULTS:
        seed_demo_data()
        
    alerts = []
    current_year = 2026
    
    for r in DB_RESULTS:
        v = r.vendor_details
        if v.iso_expiry_year < current_year:
            alerts.append(ExpiryAlert(
                title="ISO Certificate Expired",
                description=f"ISO 9001 certification expired in {v.iso_expiry_year}.",
                vendor_name=v.vendor_name,
                expiry_date=f"{v.iso_expiry_year}-12-31",
                days_remaining=-(current_year - v.iso_expiry_year) * 365,
                severity="CRITICAL"
            ))
        elif v.iso_expiry_year == current_year:
            alerts.append(ExpiryAlert(
                title="ISO Certificate Expiring Soon",
                description=f"ISO 9001 certification expires this year ({v.iso_expiry_year}).",
                vendor_name=v.vendor_name,
                expiry_date=f"{v.iso_expiry_year}-12-31",
                days_remaining=120,
                severity="WARNING"
            ))
            
    alerts.append(ExpiryAlert(
        title="Bid Evaluation Window Closing",
        description="Tender GEM/2026/B/891204 bid review period expires in 7 days.",
        vendor_name="Government e-Marketplace",
        expiry_date="2026-08-30",
        days_remaining=7,
        severity="WARNING"
    ))
    
    return alerts

@app.get("/api/fraud/duplicate-bids", response_model=List[DuplicateBid])
def get_duplicate_bids():
    if not DB_RESULTS:
        seed_demo_data()
        
    duplicates = []
    for i in range(len(DB_VENDORS)):
        for j in range(i + 1, len(DB_VENDORS)):
            v1 = DB_VENDORS[i]
            v2 = DB_VENDORS[j]
            
            if v1.pdf_hash != "unknown" and v1.pdf_hash == v2.pdf_hash:
                duplicates.append(DuplicateBid(
                    bid_id_1=v1.bid_id,
                    vendor_1=v1.vendor_name,
                    bid_id_2=v2.bid_id,
                    vendor_2=v2.vendor_name,
                    similarity_score=100.0,
                    duplicate_type="EXACT_HASH"
                ))
            elif v1.ip_address == v2.ip_address and v1.creation_timestamp == v2.creation_timestamp:
                duplicates.append(DuplicateBid(
                    bid_id_1=v1.bid_id,
                    vendor_1=v1.vendor_name,
                    bid_id_2=v2.bid_id,
                    vendor_2=v2.vendor_name,
                    similarity_score=95.0,
                    duplicate_type="HIGH_TEXT_SIMILARITY"
                ))
    return duplicates

@app.get("/api/recommendations/rankings", response_model=List[AIRecommendation])
def get_ai_recommendations():
    if not DB_RESULTS:
        seed_demo_data()
        
    compliant_bids = [r for r in DB_RESULTS if r.overall_status != "RED"]
    rankings = []
    
    for r in compliant_bids:
        v = r.vendor_details
        compliance_score = r.overall_score
        exp_score = min(100.0, (v.experience_years / 7.0) * 100.0)
        turnover_score = min(100.0, (v.turnover_lakhs / 120.0) * 100.0)
        
        price_score = min(100.0, (100.0 - v.bid_price_lakhs) * 2.0) if v.bid_price_lakhs > 0 else 50.0
        
        overall_score = (compliance_score * 0.4) + (exp_score * 0.3) + (turnover_score * 0.1) + (price_score * 0.2)
        
        criteria = {
            "Compliance & Credentials": round(compliance_score, 1),
            "Technical Experience": round(exp_score, 1),
            "Financial Capacity": round(turnover_score, 1),
            "Price Competitiveness": round(price_score, 1)
        }
        
        rationale = f"Highly competitive bid at ₹{v.bid_price_lakhs} Lakhs, presenting {v.experience_years} years of operational credentials with a compliance rating of {r.overall_score}%."
        if compliance_score >= 90:
            rationale += " Zero fraud networks flagged on GNN scan."
        else:
            rationale += " Minor technical documentation reviews pending."
            
        rankings.append((overall_score, r, criteria, rationale))
        
    rankings.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for rank, (score, r, crit, rat) in enumerate(rankings, 1):
        results.append(AIRecommendation(
            rank=rank,
            bid_id=r.bid_id,
            vendor_name=r.vendor_name,
            score=round(score, 1),
            bid_price_lakhs=r.vendor_details.bid_price_lakhs,
            criteria_scores=crit,
            rationale=rat
        ))
    return results

@app.get("/api/vendor/profile/{vendor_id}", response_model=VendorHistoryProfile)
def get_vendor_profile(vendor_id: str):
    if not DB_RESULTS:
        seed_demo_data()
        
    r = next((res for res in DB_RESULTS if res.vendor_details.vendor_id == vendor_id), None)
    if not r:
        raise HTTPException(status_code=404, detail="Vendor not found")
        
    v = r.vendor_details
    perf_score = 92.5 if r.overall_status == "GREEN" else (82.0 if r.overall_status == "YELLOW" else 45.0)
    is_blacklisted = r.overall_status == "RED" and "Fake" in r.vendor_name
    
    sister_concerns = []
    for other in DB_VENDORS:
        if other.vendor_id != vendor_id:
            if other.ip_address == v.ip_address or other.director_name == v.director_name or other.bank_account_no == v.bank_account_no:
                sister_concerns.append(other.vendor_name)
                
    location_risk = "LOW"
    if "Delhi" in v.gst_number or v.ip_address.startswith("192.168."):
        location_risk = "MODERATE"
        
    return VendorHistoryProfile(
        vendor_id=v.vendor_id,
        vendor_name=v.vendor_name,
        performance_score=perf_score,
        blacklisted=is_blacklisted,
        sister_concerns=sister_concerns,
        location_risk=location_risk
    )

@app.get("/api/analysis/risk-report/{bid_id}", response_model=RiskReport)
def get_bid_risk_report(bid_id: str):
    if not DB_RESULTS:
        seed_demo_data()
        
    res = next((r for r in DB_RESULTS if r.bid_id == bid_id), None)
    if not res:
        raise HTTPException(status_code=404, detail="Bid not found")
        
    v = res.vendor_details
    fin_risk = "LOW" if v.turnover_lakhs >= 80.0 else ("MEDIUM" if v.turnover_lakhs >= 50.0 else "HIGH")
    op_risk = "LOW" if v.experience_years >= 5 else "MEDIUM"
    cred_risk = "LOW" if res.category_scores.tax_identity >= 90.0 else "HIGH"
    
    forens_check = next((c for c in res.itemized_checks if c.category == "Fraud & Forensics"), None)
    foren_risk = "LOW"
    if forens_check:
        if forens_check.status == "FAIL":
            foren_risk = "CRITICAL"
        elif forens_check.status == "NEEDS_REVIEW":
            foren_risk = "HIGH"
            
    net_check = next((c for c in res.itemized_checks if c.category == "GNN Collusion"), None)
    net_risk = "LOW"
    if net_check and net_check.status == "FAIL":
        net_risk = "CRITICAL"
        
    risk_rating = "LOW"
    risk_score = 10.0
    
    if net_risk == "CRITICAL" or foren_risk == "CRITICAL":
        risk_rating = "CRITICAL"
        risk_score = 95.0
    elif cred_risk == "HIGH" or fin_risk == "HIGH":
        risk_rating = "HIGH"
        risk_score = 75.0
    elif fin_risk == "MEDIUM" or op_risk == "MEDIUM":
        risk_rating = "MEDIUM"
        risk_score = 45.0
        
    recs = []
    if fin_risk == "HIGH":
        recs.append("Request bank guarantee and audited statements to ensure financial capability.")
    if op_risk == "MEDIUM":
        recs.append("Confirm historical performance on GeM portal via client references.")
    if foren_risk == "CRITICAL":
        recs.append("DISQUALIFY: Fraudulent document uploads or plagiarized submissions detected.")
    if net_risk == "CRITICAL":
        recs.append("FLAG FOR AUDIT: Anti-collusion bidding ring identified by GNN engine.")
    if not recs:
        recs.append("Approved for standard fast-track procurement award.")
        
    return RiskReport(
        bid_id=bid_id,
        vendor_name=res.vendor_name,
        risk_rating=risk_rating,
        risk_score=risk_score,
        financial_risk=fin_risk,
        operational_risk=op_risk,
        credential_risk=cred_risk,
        forensic_risk=foren_risk,
        network_risk=net_risk,
        detailed_recommendations=recs
    )


@app.get("/sample-pdfs/{filename}")
def download_sample_pdf(filename: str):
    pdf_path = SAMPLE_DIR / filename
    if pdf_path.exists():
        return FileResponse(str(pdf_path), media_type="application/pdf", filename=filename)
    raise HTTPException(status_code=404, detail="File not found")

# Serve frontend static assets
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
