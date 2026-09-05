from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class TenderCriteria(BaseModel):
    tender_id: str
    title: str
    issuing_authority: str = "Government e-Marketplace (GeM)"
    minimum_turnover_lakhs: float = 50.0
    min_experience_years: int = 3
    required_certifications: List[str] = ["ISO 9001:2015", "MSME Registration"]
    must_have_gst: bool = True
    must_have_pan: bool = True
    emd_amount_inr: float = 50000.0

class VendorDetails(BaseModel):
    bid_id: str
    vendor_id: str
    vendor_name: str
    gst_number: str
    pan_number: str
    turnover_lakhs: float
    experience_years: int
    iso_certified: bool
    iso_expiry_year: int
    director_name: str
    ip_address: str
    bank_account_no: str
    creation_timestamp: str = "2026-01-15T14:30:00"
    document_hash: str = "abc123hash"
    pdf_filename: Optional[str] = None
    is_fake_flag: bool = False
    bid_price_lakhs: float = 0.0
    pdf_hash: str = "unknown"
    pdf_author: Optional[str] = None
    pdf_producer: Optional[str] = None
    pdf_created: Optional[str] = None
    pdf_modified: Optional[str] = None


class ComplianceCheckItem(BaseModel):
    check_name: str
    category: str  # "Tax & Identity", "Financial", "Experience & Quality", "Fraud & Forensics", "GNN Collusion"
    status: str    # "PASS", "FAIL", "NEEDS_REVIEW"
    score: float   # 0 to 100
    details: str

class CategoryScores(BaseModel):
    tax_identity: float
    financial: float
    experience_quality: float
    forensics: float
    gnn_collusion: float

class ComplianceResult(BaseModel):
    bid_id: str
    vendor_name: str
    overall_score: float
    overall_status: str  # "GREEN", "YELLOW", "RED"
    category_scores: CategoryScores
    itemized_checks: List[ComplianceCheckItem]
    detected_issues: List[str]
    vendor_details: Optional[VendorDetails] = None
    selected: bool = False

class GNNNode(BaseModel):
    id: str
    label: str
    type: str  # "VENDOR", "DIRECTOR", "IP_ADDRESS", "BANK_ACC", "TENDER"
    risk_score: float = 0.0
    degree_centrality: float = 0.0
    clustering_coef: float = 0.0
    is_suspicious: bool = False
    details: Optional[Dict[str, Any]] = None

class GNNEdge(BaseModel):
    source: str
    target: str
    relation: str  # "OWNED_BY", "SUBMITTED_FROM", "HAS_BANK_ACC", "BIDDED_ON"

class CartelCluster(BaseModel):
    cluster_id: str
    vendors: List[str]
    shared_attributes: List[str]
    risk_level: str  # "CRITICAL", "HIGH", "MODERATE"
    description: str
    collusion_type: str  # "COVER_BIDDING", "ROTATING_WINNER", "SHARED_INFRASTRUCTURE"

class GNNGraphResponse(BaseModel):
    nodes: List[GNNNode]
    edges: List[GNNEdge]
    detected_cartels: List[CartelCluster]
    overall_network_risk: float
    graph_density: float = 0.0

class TerminalLogMessage(BaseModel):
    timestamp: str
    level: str  # "INFO", "WARN", "ERROR", "GNN_EVENT"
    module: str # "OCR", "NLP", "GNN_CONV", "AUDIT"
    message: str

class DashboardSummary(BaseModel):
    total_tenders: int
    total_bids: int
    compliant_bids: int
    review_needed_bids: int
    rejected_bids: int
    flagged_cartels: int
    network_risk_index: float
    bids: List[ComplianceResult]
    graph_data: GNNGraphResponse
    recent_logs: List[TerminalLogMessage]

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str  # "vendor" or "government"
    organization: Optional[str] = None

class AuthResponse(BaseModel):
    success: bool
    message: str
    username: Optional[str] = None
    role: Optional[str] = None
    name: Optional[str] = None

class ChatbotQueryRequest(BaseModel):
    question: str
    bid_id: Optional[str] = None

class ChatbotQueryResponse(BaseModel):
    answer: str
    context_sources: List[str]
    timestamp: str

class ChecklistItem(BaseModel):
    name: str
    category: str  # "Legal", "Tax", "Financial", "Technical"
    status: str    # "PASS", "FAIL", "NEEDS_REVIEW"
    confidence: float
    extracted_text: str
    manual_override: bool = False
    verified_by: Optional[str] = None

class SmartChecklist(BaseModel):
    bid_id: str
    vendor_name: str
    items: List[ChecklistItem]
    overall_confidence: float

class ChecklistOverrideRequest(BaseModel):
    item_name: str
    status: str
    officer: str

class RiskReport(BaseModel):
    bid_id: str
    vendor_name: str
    risk_rating: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    risk_score: float  # 0 to 100
    financial_risk: str
    operational_risk: str
    credential_risk: str
    forensic_risk: str
    network_risk: str
    detailed_recommendations: List[str]

class ExpiryAlert(BaseModel):
    title: str
    description: str
    vendor_name: str
    expiry_date: str
    days_remaining: int
    severity: str  # "CRITICAL", "WARNING", "SAFE"

class DuplicateBid(BaseModel):
    bid_id_1: str
    vendor_1: str
    bid_id_2: str
    vendor_2: str
    similarity_score: float
    duplicate_type: str  # "EXACT_HASH", "HIGH_TEXT_SIMILARITY"

class AIRecommendation(BaseModel):
    rank: int
    bid_id: str
    vendor_name: str
    score: float
    bid_price_lakhs: float
    criteria_scores: Dict[str, float]
    rationale: str

class VendorHistoryProfile(BaseModel):
    vendor_id: str
    vendor_name: str
    performance_score: float
    blacklisted: bool
    sister_concerns: List[str]
    location_risk: str

