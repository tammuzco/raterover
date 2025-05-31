from dataclasses import dataclass, field
import os
from typing import Optional, List, Dict, Any

@dataclass
class PortalsConfig:
    """Configuration for Portals Finance client"""

    # API Configuration
    api_key: str = os.getenv('PORTALS_API_KEY', '')
    api_base_url: str = "https://api.portals.fi/v2"

    # Network Configuration
    network: str = "arbitrum"
    rpc_url: str = os.getenv('ARBITRUM_RPC_URL', 'https://arbitrum.drpc.org')
    chain_id: int = 42161

    # Wallet Configuration
    private_key: str = os.getenv('WALLET_PRIVATE_KEY', '')

    # Target Platforms
    target_platforms: List[str] = ('aavev3', 'fluid')

    # Risk Parameters
    max_slippage: float = 0.5  # 0.5%
    min_liquidity_usd: float = 50000
    min_apy: float = 0.01  # 1%

    # Position Management
    min_position_size: float = 100  # $100
    max_position_size: float = 100000  # $100k
    max_positions: int = 10
    diversification_ratio: float = 0.2  # Max 20% per protocol

    # Monitoring
    position_check_interval: int = 3600  # 1 hour
    rebalance_threshold: float = 2.0  # 2% APY difference

    # Caching
    cache_ttl_minutes: int = 5

    # Logging
    log_level: str = "INFO"
    log_file: str = "portals_client.log"

    def __post_init__(self):
        if not self.api_key:
            raise ValueError('API key is required')
        if not self.rpc_url:
            raise ValueError('RPC URL is required')
        # Private key is optional, but warn if missing
        if not self.private_key:
            print('Warning: No private key set in config')

    def __repr__(self):
        priv = self.private_key
        if priv:
            priv = priv[:4] + '...' + priv[-4:]
        return f"<PortalsConfig api_key=*** rpc_url={self.rpc_url} private_key={priv}>"

    @classmethod
    def from_env(cls) -> 'PortalsConfig':
        """Create config from environment variables"""
        return cls()

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PortalsConfig':
        """Create config from dictionary"""
        return cls(**config_dict)
