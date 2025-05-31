class DecisionEngine:
    """
    High-level decision engine for orchestrating strategy, risk, and rebalancing.
    """
    def evaluate(self, state):
        """
        Evaluate current state and determine next actions.
        Expects state dict with keys: optimizer, rebalancer, positions, market_data, capital
        Returns: list of actions (deposit/withdraw)
        """
        try:
            optimizer = state['optimizer']
            rebalancer = state['rebalancer']
            positions = state['positions']
            market_data = state['market_data']
            capital = state.get('capital', None)
            # Suggest allocations (list of dicts with 'opportunity', 'amount')
            target_allocations = optimizer.suggest_allocations(capital, market_data)
            actions = rebalancer.compute_rebalance(positions, target_allocations)
            return actions
        except Exception as e:
            print(f"[DecisionEngine] Error in evaluate: {e}")
            return []

    def act(self, actions, agent):
        """
        Execute decided actions using the provided agent.
        Returns: list of results from execution
        """
        from ..strategy.rebalancing import RebalancingEngine
        try:
            # Use agent.rebalancer if present, else instantiate
            rebalancer = getattr(agent, 'rebalancer', None) or RebalancingEngine()
            results = rebalancer.execute_rebalance(actions, agent)
            return results
        except Exception as e:
            print(f"[DecisionEngine] Error in act: {e}")
            return [] 