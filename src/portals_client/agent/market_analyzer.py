from typing import List, Optional, Callable, Any
from statistics import mean, median
from api_client import PortalsAPIClient
from ..core.models import LendingOpportunity
from ..utils.token_mappings import classify_asset

class MarketAnalyzer:
    """
    MarketAnalyzer discovers and analyzes DeFi opportunities using PortalsAPIClient.
    Provides filtering, sorting, and advanced market analysis utilities.
    """
    def __init__(self, api_client: Optional[PortalsAPIClient] = None):
        self.api_client = api_client or PortalsAPIClient()

    def fetch_opportunities(self, **filters) -> List[LendingOpportunity]:
        """
        Fetch and parse opportunities from Portals API, applying optional filters.
        """
        return self.api_client.fetch_tokens(**filters)

    def filter_opportunities(self, opportunities: List[LendingOpportunity], filter_fn: Optional[Callable[[LendingOpportunity], bool]] = None) -> List[LendingOpportunity]:
        """
        Filter opportunities using a custom filter function.
        """
        if filter_fn is None:
            return opportunities
        return [opp for opp in opportunities if filter_fn(opp)]

    def sort_opportunities(self, opportunities: List[LendingOpportunity], key: Callable[[LendingOpportunity], Any], reverse: bool = True) -> List[LendingOpportunity]:
        """
        Sort opportunities by a given key function (e.g., APY, liquidity).
        """
        return sorted(opportunities, key=key, reverse=reverse)

    def analyze_market_conditions(self, opportunities: List[LendingOpportunity]) -> dict:
        """
        Analyze overall market conditions (e.g., average APY, liquidity distribution).
        """
        apys = [opp.apy for opp in opportunities]
        liquidities = [opp.liquidity for opp in opportunities]
        return {
            'apy_stats': self.calculate_apy_stats(opportunities),
            'liquidity_stats': self.analyze_liquidity(opportunities),
            'total_opportunities': len(opportunities),
        }

    def find_arbitrage_opportunities(self, opportunities: List[LendingOpportunity]) -> List[dict]:
        """
        Identify potential arbitrage opportunities across protocols.
        (Stub: complex logic, not implemented here.)
        """
        return []

    def calculate_apy_stats(self, opportunities: List[LendingOpportunity]) -> dict:
        """
        Calculate APY statistics (mean, median, max, min).
        """
        apys = [opp.apy for opp in opportunities]
        if not apys:
            return {'mean': None, 'median': None, 'max': None, 'min': None}
        return {
            'mean': mean(apys),
            'median': median(apys),
            'max': max(apys),
            'min': min(apys),
        }

    def analyze_liquidity(self, opportunities: List[LendingOpportunity]) -> dict:
        """
        Analyze liquidity distribution and identify deep pools.
        """
        liquidities = [opp.liquidity for opp in opportunities]
        if not liquidities:
            return {'total': 0, 'mean': None, 'max': None, 'min': None}
        return {
            'total': sum(liquidities),
            'mean': mean(liquidities),
            'max': max(liquidities),
            'min': min(liquidities),
        } 