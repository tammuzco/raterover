class RebalancingEngine:
    """
    Handles portfolio rebalancing logic for DeFi strategies.
    """
    def compute_rebalance(self, positions, target_allocations):
        """Compute required actions to reach target allocations."""
        # positions: list of dicts with 'symbol', 'platform', 'balance', ...
        # target_allocations: list of dicts with 'opportunity' (dict), 'amount' (float)
        actions = []
        # Build a lookup for current positions by (symbol, platform)
        pos_lookup = {(p['symbol'], p['platform']): p for p in positions}
        # For each target allocation, compare to current position
        for alloc in target_allocations:
            opp = alloc['opportunity']
            key = (opp['symbol'], opp['platform'])
            target_amt = alloc['amount']
            current_amt = pos_lookup.get(key, {}).get('balance', 0)
            delta = target_amt - current_amt
            if abs(delta) < 1e-8:
                continue  # No action needed
            if delta > 0:
                # Need to deposit more into this opportunity
                actions.append({
                    'type': 'deposit',
                    'to': opp,
                    'amount': delta
                })
            elif delta < 0:
                # Need to withdraw from this position
                actions.append({
                    'type': 'withdraw',
                    'from': pos_lookup[key],
                    'amount': -delta
                })
        return actions

    def execute_rebalance(self, actions, agent):
        """Execute rebalance actions using the provided agent."""
        results = []
        for action in actions:
            if action['type'] == 'deposit':
                # agent.deposit(to_opportunity, amount)
                res = agent.deposit(action['to'], action['amount'])
                results.append({'action': action, 'result': res})
            elif action['type'] == 'withdraw':
                # agent.withdraw(from_position, amount)
                res = agent.withdraw(action['from'], action['amount'])
                results.append({'action': action, 'result': res})
            else:
                results.append({'action': action, 'result': 'unknown action type'})
        return results 