import networkx as nx
from typing import List, Dict, Any, Tuple
from backend.app.models.schemas import VendorDetails, GNNNode, GNNEdge, CartelCluster, GNNGraphResponse

class GNNFraudDetectionService:
    """
    GNNFraudDetectionService orchestrates collusion and cartel detection using 
    NetworkX multi-relational graphs, PageRank centrality, and simulated GNN message-passing.
    
    ========================================================================================
    FUTURE SCOPE & SCALABILITY PATHWAY:
    1. Real-World GNN Architecture Integration (PyTorch Geometric / DGL):
       - Shift from heuristics to active GNN training. Migrate from PageRank and manual message 
         passing to GCN (Graph Convolutional Network) or GAT (Graph Attention Network) models, 
         using Node Classification and Link Prediction to identify fraudulent structures.
    2. Temporal Graph Analysis:
       - Incorporate dynamic timestamps on tender submissions to detect time-separated bid-rotation 
         schemes where cartel members take turns winning bids across consecutive months.
    3. Cross-Tender Correlation Engine:
       - Build a unified heterogeneous graph across multiple concurrent GeM tenders to identify 
         bidding rings operating syndicates across different government departments.
    4. Explainable AI (XAI) with GraphSAGE & LLMs:
       - Map GNN embedding vectors (e.g. GraphSAGE node embeddings) into an LLM context to automatically 
         generate natural language explanations detailing the exact rationale for flags (e.g., 
         why a set of bidders was flagged with cover bidding risk).
    ========================================================================================
    """
    def __init__(self):
        self.graph = nx.MultiGraph()

    def build_knowledge_graph(self, vendors: List[VendorDetails], tender_id: str = "GEM/2026/B/891204") -> nx.MultiGraph:
        """Constructs a Heterogeneous Graph connecting Vendors, Directors, IPs, Bank Accounts, and Tenders."""
        self.graph.clear()
        
        # Add Tender Node
        self.graph.add_node(f"TENDER:{tender_id}", label=f"Tender {tender_id}", type="TENDER", risk_score=0.0)

        for v in vendors:
            v_node = f"VENDOR:{v.vendor_id}"
            
            # Base risk from fake/corrupted attributes
            base_risk = 75.0 if v.is_fake_flag else 0.0
            
            self.graph.add_node(
                v_node,
                label=v.vendor_name,
                type="VENDOR",
                risk_score=base_risk,
                details={
                    "gst": v.gst_number,
                    "pan": v.pan_number,
                    "turnover": v.turnover_lakhs,
                    "exp": v.experience_years
                }
            )
            
            # Edge: Vendor -> Tender
            self.graph.add_edge(v_node, f"TENDER:{tender_id}", relation="BIDDED_ON")

            # Director Node
            if v.director_name:
                d_node = f"DIRECTOR:{v.director_name.replace(' ', '_')}"
                self.graph.add_node(d_node, label=f"Director: {v.director_name}", type="DIRECTOR", risk_score=0.0)
                self.graph.add_edge(v_node, d_node, relation="OWNED_BY")

            # IP Address Node
            if v.ip_address:
                ip_node = f"IP:{v.ip_address}"
                self.graph.add_node(ip_node, label=f"IP: {v.ip_address}", type="IP_ADDRESS", risk_score=0.0)
                self.graph.add_edge(v_node, ip_node, relation="SUBMITTED_FROM")

            # Bank Account Node
            if v.bank_account_no:
                bank_node = f"BANK:{v.bank_account_no}"
                self.graph.add_node(bank_node, label=f"Bank Acc: {v.bank_account_no}", type="BANK_ACC", risk_score=0.0)
                self.graph.add_edge(v_node, bank_node, relation="HAS_BANK_ACC")

        return self.graph

    def run_gnn_cartel_detection(self, vendors: List[VendorDetails], tender_id: str = "GEM/2026/B/891204") -> GNNGraphResponse:
        """
        Applies Graph Neural message passing / centrality algorithms to detect:
        1. Shared Director collusions (Cover bidding)
        2. Shared IP submissions (Same physical computer / office)
        3. Shared Bank accounts (Identical beneficiary entity)
        """
        self.build_knowledge_graph(vendors, tender_id)
        
        nodes_res: List[GNNNode] = []
        edges_res: List[GNNEdge] = []
        cartels: List[CartelCluster] = []
        
        # Track shared entity neighbors
        entity_vendor_map: Dict[str, List[str]] = {}

        for n, data in self.graph.nodes(data=True):
            node_type = data.get("type", "UNKNOWN")
            label = data.get("label", n)
            
            # Find vendor connections for non-vendor nodes
            if node_type in ["DIRECTOR", "IP_ADDRESS", "BANK_ACC"]:
                connected_vendors = [
                    self.graph.nodes[nbr].get("label", nbr)
                    for nbr in self.graph.neighbors(n)
                    if self.graph.nodes[nbr].get("type") == "VENDOR"
                ]
                if len(connected_vendors) > 1:
                    entity_vendor_map[label] = connected_vendors

        # Identify Cartel Clusters
        cartel_counter = 1
        suspicious_vendor_nodes = set()
        
        for entity_label, vendor_list in entity_vendor_map.items():
            if len(vendor_list) >= 2:
                collusion_type = "SHARED_INFRASTRUCTURE"
                if "Director" in entity_label:
                    collusion_type = "COVER_BIDDING"
                elif "IP" in entity_label or "Bank" in entity_label:
                    collusion_type = "SHARED_INFRASTRUCTURE"
                else:
                    collusion_type = "ROTATING_WINNER"

                cartels.append(CartelCluster(
                    cluster_id=f"CARTEL-{cartel_counter:02d}",
                    vendors=vendor_list,
                    shared_attributes=[entity_label],
                    risk_level="CRITICAL",
                    description=f"Bid Rigging Alert: Bidders {', '.join(vendor_list)} share identical {entity_label}.",
                    collusion_type=collusion_type
                ))
                cartel_counter += 1
                for v in vendor_list:
                    suspicious_vendor_nodes.add(v)

        # Compute graph metrics using networkx PageRank & Clustering
        simple_graph = nx.Graph(self.graph)
        density = nx.density(self.graph)
        
        try:
            pagerank = nx.pagerank(simple_graph, max_iter=200)
        except Exception:
            pagerank = {}
            
        try:
            clustering = nx.clustering(simple_graph)
        except Exception:
            clustering = {}

        # Initialize node risk scores
        node_risks = {n: 0.0 for n in self.graph.nodes}
        
        # Seed initial direct risks
        for n, data in self.graph.nodes(data=True):
            node_type = data.get("type", "UNKNOWN")
            label = data.get("label", n)
            
            if node_type == "VENDOR":
                if label in suspicious_vendor_nodes:
                    node_risks[n] = 95.0
                elif data.get("risk_score", 0.0) > 50:
                    node_risks[n] = 75.0
            elif node_type in ["DIRECTOR", "IP_ADDRESS", "BANK_ACC"]:
                if label in entity_vendor_map:
                    node_risks[n] = 90.0

        # Iterative risk propagation (Simulated 2-layer GNN Message Passing)
        # Collusion risks propagate to adjacent entities with a dampening factor of 0.85
        for _ in range(2):
            new_risks = dict(node_risks)
            for u, v in simple_graph.edges():
                if node_risks[u] > 0:
                    prop_val = node_risks[u] * 0.85
                    if prop_val > new_risks[v]:
                        new_risks[v] = prop_val
                if node_risks[v] > 0:
                    prop_val = node_risks[v] * 0.85
                    if prop_val > new_risks[u]:
                        new_risks[u] = prop_val
            node_risks = new_risks

        # Build output node list with propagated risk scores and scaled PageRank
        for n, data in self.graph.nodes(data=True):
            node_type = data.get("type", "UNKNOWN")
            label = data.get("label", n)
            
            final_risk = round(node_risks[n], 1)
            is_suspicious = final_risk > 50.0

            # Scale PageRank by 100 for readability (e.g. 0.05 -> 5.0)
            scaled_pr = round(pagerank.get(n, 0.0) * 100, 3)

            nodes_res.append(GNNNode(
                id=n,
                label=label,
                type=node_type,
                risk_score=final_risk,
                degree_centrality=scaled_pr, # Map PageRank here
                clustering_coef=round(clustering.get(n, 0.0), 3),
                is_suspicious=is_suspicious,
                details=data.get("details")
            ))

        # Build output edge list
        for u, v, data in self.graph.edges(data=True):
            edges_res.append(GNNEdge(
                source=u,
                target=v,
                relation=data.get("relation", "CONNECTED_TO")
            ))

        overall_network_risk = 85.0 if cartels else 10.0

        return GNNGraphResponse(
            nodes=nodes_res,
            edges=edges_res,
            detected_cartels=cartels,
            overall_network_risk=overall_network_risk,
            graph_density=round(density, 3)
        )
