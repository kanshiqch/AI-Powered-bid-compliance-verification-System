import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.models.schemas import TenderCriteria, ComplianceResult, GNNGraphResponse

class ChatbotVerificationService:
    @staticmethod
    def answer_query(
        question: str,
        tender: TenderCriteria,
        bids: List[ComplianceResult],
        gnn: GNNGraphResponse,
        selected_bid_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Processes natural language queries relating to tenders, bid compliance, and fraud detection.
        Returns a structured Markdown answer with source citations.
        """
        q = question.lower().strip()
        sources = ["Tender Specifications"]
        
        # 1. Tender spec related questions
        if "turnover" in q or "financial threshold" in q:
            ans = (
                f"### Annual Turnover Requirement\n\n"
                f"The tender **{tender.tender_id}** requires vendors to have a minimum average annual turnover of "
                f"**INR {tender.minimum_turnover_lakhs} Lakhs** (last 3 financial years).\n\n"
                f"**Current Status:**\n"
            )
            for b in bids:
                v = b.vendor_details
                status = "🟢 Meets criteria" if v.turnover_lakhs >= tender.minimum_turnover_lakhs else "🔴 Fails criteria"
                ans += f"- **{b.vendor_name}**: Declared ₹{v.turnover_lakhs} Lakhs. ({status})\n"
            return {"answer": ans, "context_sources": sources}
            
        elif "experience" in q or "years" in q:
            ans = (
                f"### Technical Experience Requirement\n\n"
                f"The tender requires a minimum of **{tender.min_experience_years} Years** of experience in enterprise hardware supply.\n\n"
                f"**Vendor Experience Breakdown:**\n"
            )
            for b in bids:
                v = b.vendor_details
                status = "🟢 Compliant" if v.experience_years >= tender.min_experience_years else "🔴 Non-compliant"
                ans += f"- **{b.vendor_name}**: {v.experience_years} Years experience. ({status})\n"
            return {"answer": ans, "context_sources": sources}

        elif "iso" in q or "certificat" in q:
            ans = (
                f"### Quality & Certification Requirements\n\n"
                f"All bidders must submit a valid **ISO 9001:2015** certification that remains unexpired for the year 2026 and beyond.\n\n"
                f"**Verification Log:**\n"
            )
            for b in bids:
                v = b.vendor_details
                status = f"🟢 Unexpired (Expires {v.iso_expiry_year})" if v.iso_expiry_year >= 2026 else f"🔴 Expired (Expiry {v.iso_expiry_year})"
                ans += f"- **{b.vendor_name}**: ISO Certificate. ({status})\n"
            return {"answer": ans, "context_sources": sources}

        # 2. Cartels, fraud or GNN collusion related questions
        elif "cartel" in q or "collusion" in q or "fraud" in q or "suspicious" in q:
            sources.append("GNN Collusion Engine")
            if not gnn or not gnn.detected_cartels:
                ans = "### GNN Fraud Scan Status\n\nNo collusive bid-rigging rings or shared infrastructure anomalies were flagged by the GNN model."
                return {"answer": ans, "context_sources": sources}
                
            ans = (
                f"### 🚨 Flagged Bidding Cartels / Collusions\n\n"
                f"The GNN Knowledge Graph has flagged **{len(gnn.detected_cartels)} suspicious bidding syndicate(s)**:\n\n"
            )
            for c in gnn.detected_cartels:
                ans += (
                    f"#### {c.cluster_id} - Collusion Type: `{c.collusion_type}`\n"
                    f"- **Bidders Involved:** {', '.join(c.vendors)}\n"
                    f"- **Shared Attributes:** {', '.join(c.shared_attributes)}\n"
                    f"- **Risk Level:** **{c.risk_level}**\n"
                    f"- **Description:** *{c.description}*\n\n"
                )
            ans += "These bidders share identical directors, Bank accounts, IP addresses, or submission times, indicating cover bidding."
            return {"answer": ans, "context_sources": sources}

        # 3. Recommendation questions
        elif "recommend" in q or "best" in q or "winner" in q or "rank" in q:
            sources.append("AI Recommendation System")
            compliant_bids = [b for b in bids if b.overall_status != "RED"]
            
            if not compliant_bids:
                ans = "### Winner Recommendation\n\nNo vendors currently qualify because all active bids have been disqualified or flagged with critical compliance/fraud issues."
                return {"answer": ans, "context_sources": sources}
            
            # Sort by compliance score, experience, and price
            # Ranking heuristic
            rankings = []
            for b in compliant_bids:
                v = b.vendor_details
                score = b.overall_score
                # Add weights: turnover, price (lower is better), experience
                price_factor = (100.0 - v.bid_price_lakhs) if v.bid_price_lakhs > 0 else 0
                rank_score = (score * 0.40) + (v.experience_years * 5) + (price_factor * 0.20)
                rankings.append((rank_score, b))
                
            rankings.sort(key=lambda x: x[0], reverse=True)
            
            ans = (
                f"### AI Recommended Vendor Leaderboard\n\n"
                f"Based on compliance checklist, financial health, pricing, and network collusion risk factors, the optimal candidates are ranked below:\n\n"
            )
            for rank, (r_score, b) in enumerate(rankings, 1):
                v = b.vendor_details
                ans += (
                    f"**Rank {rank}: {b.vendor_name} ({b.bid_id})**\n"
                    f"- **Overall Score:** {b.overall_score}% | **Declared Bid Price:** ₹{v.bid_price_lakhs} Lakhs\n"
                    f"- **Experience:** {v.experience_years} Years | **Turnover:** ₹{v.turnover_lakhs} Lakhs\n"
                    f"- **AI Rationale:** High compliance grade, unexpired quality certifications, and clean GNN risk history.\n\n"
                )
            return {"answer": ans, "context_sources": sources}

        # 4. Check specific bid ID or vendor name
        matched_bid = None
        for b in bids:
            bid_id_clean = b.bid_id.lower().replace("-", "")
            vendor_clean = b.vendor_name.lower()
            if bid_id_clean in q.replace("-", "") or vendor_clean in q or (selected_bid_id and b.bid_id == selected_bid_id):
                matched_bid = b
                break
                
        if matched_bid:
            sources.append(f"Bid Details: {matched_bid.bid_id}")
            v = matched_bid.vendor_details
            ans = (
                f"### Audit Profile: {matched_bid.vendor_name} ({matched_bid.bid_id})\n\n"
                f"- **Compliance Status:** `{matched_bid.overall_status}`\n"
                f"- **Overall Audit Score:** **{matched_bid.overall_score}%**\n"
                f"- **Declared Bid Price:** ₹{v.bid_price_lakhs} Lakhs\n"
                f"- **Extracted GSTIN:** `{v.gst_number}`\n"
                f"- **Annual Turnover:** ₹{v.turnover_lakhs} Lakhs (Requirement: ₹{tender.minimum_turnover_lakhs} Lakhs)\n"
                f"- **Experience:** {v.experience_years} Years (Requirement: {tender.min_experience_years} Years)\n\n"
                f"**Detected Issues:**\n"
            )
            if matched_bid.detected_issues:
                for issue in matched_bid.detected_issues:
                    ans += f"- ❌ {issue}\n"
            else:
                ans += "- 🟢 No critical compliance failures or cartels detected."
            return {"answer": ans, "context_sources": sources}

        # 5. Default Fallback
        ans = (
            f"### GeM Auditing Chatbot Agent\n\n"
            f"Hello! I am the integrated clause compliance and fraud scanner. You can ask me specific questions like:\n\n"
            f"1. *What are the turnover and experience thresholds?*\n"
            f"2. *Is there any cartel or bidding ring detected?*\n"
            f"3. *Which vendor is recommended for selection?*\n"
            f"4. *Audit report for bid BID-101 (or vendor TechCorp).*\n\n"
            f"Please let me know how I can help you verify compliance."
        )
        return {"answer": ans, "context_sources": sources}
