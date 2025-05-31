from typing import List, Dict, Any

class RiskManager:
    """
    Implements risk assessment and management for DeFi strategies.
    """
    def assess_risk(self, positions: List[Dict[str, Any]], market_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Assess risk of current positions and market conditions.
        Returns a list of risk assessments: [{'position': ..., 'risk_score': ...}]
        """
        # Example: assign risk score based on asset class and protocol
        risk_scores = {
            'stablecoin': 1,
            'eth_correlated': 2,
            'btc_correlated': 2,
            'other': 3
        }
        protocol_risk = {
            'aave': 1,
            'compound': 2,
            'fluid': 2,
            'radiant': 2,
            'unknown': 3
        }
        assessments = []
        for pos in positions:
            asset_class = pos.get('asset_class', 'other').lower()
            protocol = pos.get('platform', 'unknown').lower()
            score = risk_scores.get(asset_class, 3) + protocol_risk.get(protocol, 3)
            assessments.append({'position': pos, 'risk_score': score})
        return assessments

    def enforce_limits(self, allocations: List[Dict[str, Any]], risk_profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Adjust allocations to comply with risk limits (e.g., max per protocol/asset).
        Returns adjusted allocations.
        """
        max_per_protocol = risk_profile.get('max_per_protocol', 0.3)  # 30% default
        protocol_totals = {}
        total = sum(a['amount'] for a in allocations)
        adjusted = []
        for alloc in allocations:
            protocol = alloc['opportunity'].get('platform', 'unknown')
            protocol_totals.setdefault(protocol, 0)
            allowed = max_per_protocol * total
            amount = min(alloc['amount'], allowed - protocol_totals[protocol])
            if amount > 0:
                protocol_totals[protocol] += amount
                adjusted.append({'opportunity': alloc['opportunity'], 'amount': amount})
        return adjusted 