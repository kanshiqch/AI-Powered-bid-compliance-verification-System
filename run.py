import sys
import uvicorn
from backend.app.document_generator import generate_all_sample_pdfs

if __name__ == "__main__":
    print("==========================================================================")
    print("  AI GeM Bid Compliance & GNN Fraud Detection Platform Platform Launcher  ")
    print("==========================================================================")
    
    # Generate sample test PDFs if missing
    generate_all_sample_pdfs()
    
    print("\nStarting FastAPI Application Server at http://127.0.0.1:8000 ...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
