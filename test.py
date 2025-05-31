#!/usr/bin/env python3

import os
import sys
from unittest.mock import MagicMock

from portals_client.config import PortalsConfig
from portals_client.core.api_client import PortalsAPIClient

from dotenv import load_dotenv
load_dotenv()

# --- STRATEGY/AGENT IMPORTS ---
# Adjust import paths as needed for your project structure
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))  # If needed for local imports
from portals_client.strategy.yield_optimization import YieldOptimizer
from portals_client.strategy.rebalancing import RebalancingEngine
from portals_client.strategy.risk_management import RiskManager
from portals_client.agent.decision_engine import DecisionEngine
# from portals_client.agent.execution_agent import ExecutionAgent  # Uncomment for real/forked chain tests

def main():
    # Load config from env or defaults
    config = PortalsConfig.from_env()
    api_key = config.api_key
    if not api_key:
        raise RuntimeError("PORTALS_API_KEY not set in environment.")

    # Only query Aave and Fluid, only stablecoins
    platforms = ['aavev3', 'fluid']
    min_liquidity = 50000  # USD
    min_apy = 0.01         # 1%
    network = "arbitrum"

    client = PortalsAPIClient(config)
    print(f"Querying opportunities on {platforms} for stablecoins...")

    # Fetch all opportunities
    data = client.fetch_tokens(
        networks=network,
        platforms=platforms,
        min_liquidity=min_liquidity,
        min_apy=min_apy,
        limit=100
    )

    # Filter for stablecoins (by underlying asset)
    stablecoins = {'USDC', 'USDC.e', 'USDT', 'DAI', 'GHO', 'FRAX', 'LUSD', 'TUSD', 'MIM'}
    results = []
    for opp in data:
        print(vars(opp))  # Debug: show all fields of the LendingOpportunity
        underlying = opp.underlying_asset.upper()
        if underlying in stablecoins:
            results.append({
                'protocol': opp.protocol,
                'platform': opp.protocol,
                'symbol': opp.asset,
                'underlying': underlying,
                'apy': opp.apy,
                'liquidity': opp.liquidity,
                'address': opp.asset_address,
            })

    print(f"Found {len(results)} stablecoin opportunities:")
    for r in results:
        print(f"{r['protocol']:8} | {r['symbol']:10} | {r['underlying']:8} | APY: {r['apy']:.2f}% | Liquidity: ${r['liquidity']:,.0f} | {r['address']}")

    # --- EXTENDED TESTS ---
    test_strategy_unit()
    test_strategy_integration(results, dry_run=True)
    test_decision_engine(results)

# --- UNIT TEST: STRATEGY LOGIC WITH MOCK DATA ---
def test_strategy_unit():
    print("\n[UNIT] Testing YieldOptimizer with mock data...")
    optimizer = YieldOptimizer()
    mock_positions = [
        {'symbol': 'aArbUSDC', 'platform': 'aavev3', 'balance': 1000, 'apy': 2.0},
        {'symbol': 'fUSDT', 'platform': 'fluid', 'balance': 500, 'apy': 1.0},
    ]
    mock_market = [
        {'symbol': 'aArbUSDC', 'platform': 'aavev3', 'apy': 2.0},
        {'symbol': 'fUSDT', 'platform': 'fluid', 'apy': 8.0},
        {'symbol': 'aArbGHO', 'platform': 'aavev3', 'apy': 3.0},
    ]
    actions = optimizer.optimize_yield(mock_positions, mock_market)
    print("YieldOptimizer actions:", actions)
    assert any(a['to']['apy'] > a['from']['apy'] for a in actions), "Should suggest moving to higher APY"

# --- INTEGRATION TEST: LIVE DATA, DRY RUN ---
def test_strategy_integration(live_opps, dry_run=True):
    print("\n[INTEGRATION] Testing strategy logic with live data (dry_run={})...".format(dry_run))
    optimizer = YieldOptimizer()
    rebalancer = RebalancingEngine()
    risk = RiskManager()
    # Simulate a portfolio: all cash, no positions
    portfolio = {'positions': [], 'cash': 10000}
    # Suggest allocations
    allocations = optimizer.suggest_allocations(portfolio['cash'], live_opps)
    print("Suggested allocations:", allocations)
    # Risk management: enforce limits
    risk_profile = {'max_per_protocol': 0.3}
    safe_allocs = risk.enforce_limits(allocations, risk_profile)
    print("Risk-adjusted allocations:", safe_allocs)
    # Simulate current positions (empty)
    positions = []
    actions = rebalancer.compute_rebalance(positions, safe_allocs)
    print("Rebalance actions:", actions)
    # Dry run: do not execute, just print what would happen
    if not dry_run:
        print("[WARNING] Real execution not implemented in this test.")

# --- AGENT/DECISION ENGINE SIMULATION ---
def test_decision_engine(live_opps):
    print("\n[SIMULATION] Testing DecisionEngine with live data...")
    optimizer = YieldOptimizer()
    rebalancer = RebalancingEngine()
    decision_engine = DecisionEngine()
    # Simulate a portfolio: all cash, no positions
    state = {
        'optimizer': optimizer,
        'rebalancer': rebalancer,
        'positions': [],
        'market_data': live_opps,
        'capital': 10000,
    }
    actions = decision_engine.evaluate(state)
    print("DecisionEngine actions:", actions)
    # Optionally, simulate agent.act(actions, agent) with a mock agent
    agent = MagicMock()
    agent.deposit = MagicMock(return_value='tx_hash_dummy')
    agent.withdraw = MagicMock(return_value='tx_hash_dummy')
    results = decision_engine.act(actions, agent)
    print("Simulated agent act results:", results)

if __name__ == "__main__":
    main()