from typing import Dict, Optional
from ..core.models import TokenMapping, AssetClass

# Comprehensive token mappings
TOKEN_MAPPINGS: Dict[str, TokenMapping] = {
    # Fluid tokens
    'fUSDT': TokenMapping('fUSDT', 'USDT', AssetClass.STABLECOIN, 6),
    'fUSDC': TokenMapping('fUSDC', 'USDC', AssetClass.STABLECOIN, 6),
    'fDAI': TokenMapping('fDAI', 'DAI', AssetClass.STABLECOIN, 18),
    'fWETH': TokenMapping('fWETH', 'WETH', AssetClass.ETH_CORRELATED, 18),
    'fwstETH': TokenMapping('fwstETH', 'wstETH', AssetClass.ETH_CORRELATED, 18),

    # AAVE v3 tokens
    'aArbUSDC': TokenMapping('aArbUSDC', 'USDC', AssetClass.STABLECOIN, 6),
    'aArbUSDCn': TokenMapping('aArbUSDCn', 'USDC', AssetClass.STABLECOIN, 6), # Native USDC
    'aArbUSDT': TokenMapping('aArbUSDT', 'USDT', AssetClass.STABLECOIN, 6),
    'aArbDAI': TokenMapping('aArbDAI', 'DAI', AssetClass.STABLECOIN, 18),
    'aArbGHO': TokenMapping('aArbGHO', 'GHO', AssetClass.STABLECOIN, 18),
    'aArbWETH': TokenMapping('aArbWETH', 'WETH', AssetClass.ETH_CORRELATED, 18),
    'aArbwstETH': TokenMapping('aArbwstETH', 'wstETH', AssetClass.ETH_CORRELATED, 18),
    'aArbWBTC': TokenMapping('aArbWBTC', 'WBTC', AssetClass.BTC_CORRELATED, 8),
    # TODO: Add more mappings as needed
}

# Token addresses on Arbitrum
ARBITRUM_TOKEN_ADDRESSES: Dict[str, str] = {
    'USDC': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', # Native USDC
    'USDC.e': '0xFF970A61A043b1cA14834A43f5dE4533EBDDb5CC', # Bridged USDC
    'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
    'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
    'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
    'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f',
    'GHO': '0x4071c95B0755292AcC48a28E708Ade63812099Ac', # Example, verify actual GHO address on Arbitrum if available
}

KNOWN_UNDERLYING = {'USDC', 'USDT', 'DAI', 'WETH', 'WBTC', 'GHO', 'wstETH', 'ETH'}
PREFIXES = ['aArb', 'a.e.', 'fwst', 'a', 'c', 'f', 'r', 'y']

def get_underlying_asset(platform_token: str) -> Optional[str]:
    """Get underlying asset from platform token symbol."""
    if platform_token in TOKEN_MAPPINGS:
        return TOKEN_MAPPINGS[platform_token].underlying_asset
    # Try to parse from token name
    for prefix in PREFIXES:
        if platform_token.startswith(prefix):
            potential_underlying = platform_token[len(prefix):]
            if potential_underlying.upper() in KNOWN_UNDERLYING or potential_underlying in KNOWN_UNDERLYING:
                return potential_underlying
    return None

def classify_asset(asset_symbol: str) -> AssetClass:
    """Classify asset into categories based on its symbol."""
    asset_upper = asset_symbol.upper()
    # Check token mapping first by underlying asset for direct classification
    for token_map in TOKEN_MAPPINGS.values():
        if token_map.underlying_asset.upper() == asset_upper:
            return token_map.asset_class
    # Manual classification as a fallback
    if asset_upper in ['USDC', 'USDT', 'DAI', 'FRAX', 'LUSD', 'GHO', 'USDD', 'TUSD', 'MIM']:
        return AssetClass.STABLECOIN
    elif asset_upper in ['ETH', 'WETH', 'STETH', 'WSTETH', 'RETH', 'WEETH', 'ARB']:
        return AssetClass.ETH_CORRELATED
    elif asset_upper in ['BTC', 'WBTC', 'TBTC']:
        return AssetClass.BTC_CORRELATED
    return AssetClass.OTHER

def get_token_decimals(symbol: str) -> int:
    """Get decimals for a given token symbol (platform or underlying)."""
    if symbol in TOKEN_MAPPINGS:
        return TOKEN_MAPPINGS[symbol].decimals
    for token_map in TOKEN_MAPPINGS.values():
        if token_map.underlying_asset.upper() == symbol.upper():
            return token_map.decimals
    return 18

def get_token_address(symbol: str) -> Optional[str]:
    """Get the canonical address for a given token symbol (platform or underlying)."""
    # Try underlying first
    addr = ARBITRUM_TOKEN_ADDRESSES.get(symbol)
    if addr:
        return addr
    # Try platform token (by underlying)
    if symbol in TOKEN_MAPPINGS:
        underlying = TOKEN_MAPPINGS[symbol].underlying_asset
        return ARBITRUM_TOKEN_ADDRESSES.get(underlying)
    return None

# Use get_underlying_asset directly for platform token → underlying asset translation.
# TODO: Add more tokens and edge case handling as needed 