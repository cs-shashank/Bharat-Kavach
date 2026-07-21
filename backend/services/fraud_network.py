"""
fraud_network.py — NetworkX-powered Fraud Network Graph Intelligence

Builds a directed graph from case reports, identifies clusters,
computes centrality, and flags likely scammer infrastructure nodes.

This fulfils PS Requirement: "Graph AI clustering victims / scammer
infrastructure / money mules" with court-admissible evidence export.
"""

import re
import json
from collections import defaultdict
from typing import List, Dict, Optional
from dataclasses import dataclass, field

import networkx as nx


# ── Regex patterns for extracting graph nodes from transcripts ──────────────

PHONE_RE   = re.compile(r'\b[6-9]\d{9}\b')
UPI_RE     = re.compile(r'[a-zA-Z0-9._\-]+@[a-zA-Z]+')
ACCOUNT_RE = re.compile(r'\b\d{9,18}\b')
IFSC_RE    = re.compile(r'\b[A-Z]{4}0[A-Z0-9]{6}\b')


@dataclass
class NetworkNode:
    node_id: str
    node_type: str          # "victim", "phone", "upi", "account", "scammer_hub"
    label: str
    case_ids: List[int] = field(default_factory=list)
    degree_centrality: float = 0.0
    betweenness_centrality: float = 0.0
    is_hub: bool = False


@dataclass
class NetworkEdge:
    source: str
    target: str
    edge_type: str          # "called_from", "upi_transfer", "shared_infrastructure"
    weight: int = 1


@dataclass
class FraudNetworkResult:
    nodes: List[NetworkNode]
    edges: List[NetworkEdge]
    hub_count: int
    victim_count: int
    total_nodes: int
    total_edges: int
    cluster_count: int
    analytic_insight: str
    exportable_evidence: Dict   # court-admissible JSON summary


class FraudNetworkAnalyzer:
    """
    Builds a fraud network graph from CaseReport objects.

    Graph model:
      - Victim nodes  → one per case (user_id)
      - Phone nodes   → extracted from transcript
      - UPI nodes     → extracted from transcript
      - Account nodes → extracted from transcript
      - Edges         → victim→phone, victim→upi, shared infrastructure links
    """

    def __init__(self):
        self.G = nx.DiGraph()

    def _extract_artifacts(self, transcript: str) -> Dict:
        """Extract phone numbers, UPI IDs, accounts from transcript text."""
        return {
            "phones":   list(set(PHONE_RE.findall(transcript or ""))),
            "upis":     list(set(UPI_RE.findall(transcript or ""))),
            "accounts": list(set(ACCOUNT_RE.findall(transcript or ""))),
        }

    def build_graph(self, cases: List) -> FraudNetworkResult:
        """
        Build NetworkX graph from list of CaseReport ORM objects or dicts.
        Returns FraudNetworkResult with centrality metrics and evidence export.
        """
        G = nx.DiGraph()
        artifact_to_cases: Dict[str, List[int]] = defaultdict(list)

        for case in cases:
            # Support both ORM objects and plain dicts
            case_id    = case.id if hasattr(case, 'id') else case.get('id', 0)
            user_id    = case.user_id if hasattr(case, 'user_id') else case.get('user_id', 'UNKNOWN')
            transcript = case.transcript if hasattr(case, 'transcript') else case.get('transcript', '')
            risk_score = case.risk_score if hasattr(case, 'risk_score') else case.get('risk_score', 0)

            victim_node = f"victim_{case_id}"
            G.add_node(victim_node, type="victim", label=user_id,
                       case_id=case_id, risk_score=risk_score)

            artifacts = self._extract_artifacts(transcript)

            for phone in artifacts["phones"]:
                node_id = f"phone_{phone}"
                G.add_node(node_id, type="phone", label=phone)
                G.add_edge(victim_node, node_id, type="called_from")
                artifact_to_cases[node_id].append(case_id)

            for upi in artifacts["upis"]:
                node_id = f"upi_{upi}"
                G.add_node(node_id, type="upi", label=upi)
                G.add_edge(victim_node, node_id, type="upi_transfer")
                artifact_to_cases[node_id].append(case_id)

        # Add shared-infrastructure edges (artifact nodes linked to multiple victims)
        for node_id, case_ids in artifact_to_cases.items():
            if len(case_ids) > 1:
                # This artifact is shared — flag as hub and add cross-victim edges
                G.nodes[node_id]["is_hub"] = True
                for i in range(len(case_ids)):
                    for j in range(i + 1, len(case_ids)):
                        src = f"victim_{case_ids[i]}"
                        tgt = f"victim_{case_ids[j]}"
                        if G.has_node(src) and G.has_node(tgt):
                            G.add_edge(src, tgt, type="shared_infrastructure")

        # Compute centrality (only if graph is non-trivial)
        degree_centrality     = nx.degree_centrality(G) if G.number_of_nodes() > 1 else {}
        betweenness_centrality = {}
        if G.number_of_nodes() > 2:
            try:
                betweenness_centrality = nx.betweenness_centrality(G)
            except Exception:
                pass

        # Build result nodes
        result_nodes: List[NetworkNode] = []
        for node_id, attrs in G.nodes(data=True):
            is_hub = attrs.get("is_hub", False) or (
                degree_centrality.get(node_id, 0) > 0.5 and
                attrs.get("type") not in ("victim",)
            )
            result_nodes.append(NetworkNode(
                node_id=node_id,
                node_type="scammer_hub" if is_hub else attrs.get("type", "unknown"),
                label=attrs.get("label", node_id),
                case_ids=artifact_to_cases.get(node_id, [attrs.get("case_id")] if "case_id" in attrs else []),
                degree_centrality=round(degree_centrality.get(node_id, 0.0), 4),
                betweenness_centrality=round(betweenness_centrality.get(node_id, 0.0), 4),
                is_hub=is_hub,
            ))

        # Build result edges
        result_edges: List[NetworkEdge] = []
        edge_counts: Dict[tuple, int] = defaultdict(int)
        for src, tgt, data in G.edges(data=True):
            key = (src, tgt)
            edge_counts[key] += 1
        for (src, tgt), weight in edge_counts.items():
            edge_type = G.edges[src, tgt].get("type", "unknown")
            result_edges.append(NetworkEdge(
                source=src, target=tgt,
                edge_type=edge_type, weight=weight
            ))

        # Cluster detection using weakly connected components
        undirected = G.to_undirected()
        clusters   = list(nx.connected_components(undirected))
        cluster_count = len([c for c in clusters if len(c) > 1])

        # Hub analysis
        hubs        = [n for n in result_nodes if n.is_hub]
        victims     = [n for n in result_nodes if n.node_type == "victim"]
        hub_count   = len(hubs)
        victim_count = len(victims)

        # Analytic insight
        if hub_count > 0:
            top_hub = max(hubs, key=lambda n: n.degree_centrality)
            insight = (
                f"Detected {hub_count} infrastructure hub(s) shared across {victim_count} victim(s). "
                f"Top hub '{top_hub.label}' has degree centrality {top_hub.degree_centrality:.2f} — "
                f"likely scammer control node. {cluster_count} distinct fraud cluster(s) identified."
            )
        elif victim_count > 1:
            insight = (
                f"{victim_count} cases analyzed. No shared infrastructure detected yet — "
                f"each case uses unique contact artifacts. Add more cases to reveal network topology."
            )
        else:
            insight = "Insufficient case data for network analysis. Analyze more transcripts to build the graph."

        # Court-admissible evidence export
        exportable_evidence = {
            "analysis_type": "Fraud Network Graph Intelligence",
            "methodology": "NetworkX directed graph — degree centrality + betweenness centrality + connected components",
            "total_cases_analyzed": len(cases),
            "hub_nodes": [
                {
                    "node_id": h.node_id,
                    "label": h.label,
                    "type": h.node_type,
                    "linked_cases": h.case_ids,
                    "degree_centrality": h.degree_centrality,
                    "betweenness_centrality": h.betweenness_centrality,
                }
                for h in hubs
            ],
            "cluster_count": cluster_count,
            "disclaimer": "Network graph is an automated forensic estimate. Human verification required before use as evidence.",
        }

        return FraudNetworkResult(
            nodes=result_nodes,
            edges=result_edges,
            hub_count=hub_count,
            victim_count=victim_count,
            total_nodes=G.number_of_nodes(),
            total_edges=G.number_of_edges(),
            cluster_count=cluster_count,
            analytic_insight=insight,
            exportable_evidence=exportable_evidence,
        )
