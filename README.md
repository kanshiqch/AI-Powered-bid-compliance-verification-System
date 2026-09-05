# AI-Powered Integrated Bid Compliance Verification & Fraud Detection for GeM

An advanced procurement auditing platform designed for the **Government e-Marketplace (GeM)**. The platform integrates natural language clause compliance verification, PDF forensic integrity checkers, duplicate bid scanners, and multi-relational Graph Neural Network (GNN) cartel detection to identify collusive bidding syndicates.

---

## 🚀 Core Features

The suite includes **eight advanced AI-driven verification engines** mapped across modular workspaces:

1.  **AI Document Chatbot**: An interactive QA auditor using local TF-IDF semantic keyword matching. Officials can chat directly with the bid metadata (e.g. *Why did BID-102 fail?* or *Compare turnover of all vendors*).
2.  **AI Risk Report**: Generates structured, exportable threat assessments detailing Financial, Operational, Forensic, and Network risk scores with automated mitigation advice.
3.  **Smart Document Checklist**: Extracts and validates required clauses (GST registration state codes, PAN validity, ISO expiry, experience timelines) showing OCR text snippets, confidence scores, and manual officer overrides.
4.  **Document Forgery Detection**: Audits PDF binary properties, detects text layer tampering, identifies template date chronological anomalies (e.g., creation timestamp overlaps), and reports structural metadata modifications.
5.  **Deadline & Expiry Alert System**: A real-time timeline center flagging critical certificate expirations (e.g. expired ISO 9001 certifications) and upcoming bid evaluation deadlines.
6.  **Vendor Risk Profile**: Details historical performance scoring, maps location risks, and lists overlapping sister concern entities.
7.  **Duplicate Bid Detection**: Cross-references exact PDF MD5 file hashes and metadata timestamps to identify plagiarized proposal uploads.
8.  **AI Recommendation System**: Ranks all compliant bidders using Multi-Criteria Decision Analysis (40% Compliance, 30% Experience, 20% Price, 10% Turnover) to highlight the optimal selection.

---

## 🛠️ Technology Stack

*   **Backend**: Python, FastAPI, Pydantic, PyPDF, ReportLab (PDF generator), NetworkX (knowledge graph mapping)
*   **Database**: Persistent SQLite engine for selection logs & in-memory cache for dynamic session state
*   **Frontend**: Vanilla HTML5, CSS3 Grid, D3.js (Force-Directed Collusion Graphs)

---

## 🕸️ GNN Collusion Mapping Architecture

The platform builds a heterogeneous knowledge graph connecting:
*   **Bidders (Vendors)**
*   **Managing Directors**
*   **Terminal IP Addresses**
*   **Primary Bank Accounts**
*   **Tenders**

Using simulated **2-layer Graph Neural Network (GNN) message passing**, risk ratings propagate from suspicious entities to connected nodes using a dampening factor of `0.85`, automatically identifying cover bidding and shared infrastructure networks.

---

## 📦 Getting Started

### 1. Installation

Ensure you have Python installed, then install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
Run the launch script. This will automatically generate the synthetic test bid PDFs with metadata and start the uvicorn development server:
```bash
py run.py
```

Open your browser and navigate to **`http://127.0.0.1:8000`** to access the platform interface.

---

## 📜 Verification Tests
You can verify the API endpoints programmatically by running:
```bash
py scratch/test_endpoints.py
```
This tests all custom API routes (checking PASS/FAIL checklists, GNN cartel clusters, chatbot queries, recommendations ranks, and risk profiles).
