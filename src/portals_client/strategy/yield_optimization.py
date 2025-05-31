from typing import List, Dict, Any

class YieldOptimizer:
    """
    Implements yield optimization strategies for DeFi positions.
    """
    def optimize_yield(self, positions: List[Dict[str, Any]], market_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggests reallocation actions to maximize yield.
        - positions: list of current positions (each with 'symbol', 'platform', 'balance', 'apy', ...)
        - market_data: list of available opportunities (each with 'symbol', 'platform', 'apy', ...)
        Returns a list of actions: [{'from': ..., 'to': ..., 'amount': ...}]
        """
        # Sort current positions by APY ascending
        positions_sorted = sorted(positions, key=lambda x: x.get('apy', 0))
        # Sort market opportunities by APY descending
        opportunities_sorted = sorted(market_data, key=lambda x: x.get('apy', 0), reverse=True)
        actions = []
        # Naive: move from lowest-yielding position to highest-yielding opportunity
        for pos in positions_sorted:
            best_opp = next((opp for opp in opportunities_sorted if opp['symbol'] != pos['symbol'] or opp['platform'] != pos['platform']), None)
            if best_opp and best_opp['apy'] > pos.get('apy', 0):
                actions.append({
                    'from': pos,
                    'to': best_opp,
                    'amount': pos['balance']
                })
        return actions

    def suggest_allocations(self, capital: float, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggest capital allocations across available opportunities, proportional to APY.
        Returns a list of allocations: [{'opportunity': ..., 'amount': ...}]
        """
        total_apy = sum([opp.get('apy', 0) for opp in opportunities])
        if total_apy == 0:
            # Fallback: allocate all to first opportunity
            return [{'opportunity': opportunities[0], 'amount': capital}] if opportunities else []
        allocations = []
        for opp in opportunities:
            weight = opp.get('apy', 0) / total_apy
            allocations.append({
                'opportunity': opp,
                'amount': capital * weight
            })
        return allocations 