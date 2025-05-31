from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AssetClass(Enum):
    """Asset classification for risk management and strategy selection"""
    STABLECOIN = "stablecoin"
    ETH_CORRELATED = "eth_correlated"
    BTC_CORRELATED = "btc_correlated"
    OTHER = "other"

def classify_asset(symbol: str) -> AssetClass:
    symbol = symbol.upper()
    if symbol in {"USDC", "USDT", "DAI"}:
        return AssetClass.STABLECOIN
    if symbol in {"ETH", "WETH", "STETH", "WSTETH"}:
        return AssetClass.ETH_CORRELATED
    if symbol in {"WBTC", "TBTC"}:
        return AssetClass.BTC_CORRELATED
    return AssetClass.OTHER

@dataclass
class TokenMapping:
    """Maps platform-specific tokens to underlying assets"""
    platform_token: str
    underlying_asset: str
    asset_class: AssetClass
    decimals: int = 18

    def validate(self):
        assert isinstance(self.platform_token, str) and self.platform_token, "platform_token must be a non-empty string"
        assert isinstance(self.underlying_asset, str) and self.underlying_asset, "underlying_asset must be a non-empty string"
        assert isinstance(self.asset_class, AssetClass), "asset_class must be an AssetClass"
        assert isinstance(self.decimals, int) and self.decimals > 0, "decimals must be a positive integer"

    def to_dict(self):
        return {
            "platform_token": self.platform_token,
            "underlying_asset": self.underlying_asset,
            "asset_class": self.asset_class.value,
            "decimals": self.decimals,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            platform_token=d["platform_token"],
            underlying_asset=d["underlying_asset"],
            asset_class=AssetClass(d["asset_class"]),
            decimals=d.get("decimals", 18),
        )

@dataclass
class LendingOpportunity:
    """Core data model for lending opportunities"""
    protocol: str
    protocol_key: str
    asset: str
    underlying_asset: str
    asset_address: str
    apy: float
    liquidity: float
    utilization_rate: float = 0.0
    collateral_factor: float = 0.0
    chain: str = "arbitrum"
    platform_id: str = ""
    pool_address: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def validate(self):
        assert isinstance(self.protocol, str) and self.protocol, "protocol must be a non-empty string"
        assert isinstance(self.protocol_key, str) and self.protocol_key, "protocol_key must be a non-empty string"
        assert isinstance(self.asset, str) and self.asset, "asset must be a non-empty string"
        assert isinstance(self.underlying_asset, str) and self.underlying_asset, "underlying_asset must be a non-empty string"
        assert isinstance(self.asset_address, str) and self.asset_address, "asset_address must be a non-empty string"
        assert isinstance(self.apy, (int, float)), "apy must be a number"
        assert isinstance(self.liquidity, (int, float)), "liquidity must be a number"
        assert 0.0 <= self.utilization_rate <= 1.0, "utilization_rate must be between 0 and 1"
        assert 0.0 <= self.collateral_factor <= 1.0, "collateral_factor must be between 0 and 1"
        assert isinstance(self.chain, str) and self.chain, "chain must be a non-empty string"
        assert isinstance(self.last_updated, datetime), "last_updated must be a datetime"

    @property
    def asset_class(self) -> AssetClass:
        return classify_asset(self.underlying_asset)

    @property
    def risk_adjusted_apy(self) -> float:
        util_rate = self.utilization_rate if 0 <= self.utilization_rate <= 1 else 0.0
        cf = self.collateral_factor if 0 <= self.collateral_factor <= 1 else 0.0
        
        utilization_penalty_factor = max(0, (util_rate - 0.8)) * 2.5
        adjusted_apy = self.apy * (1 - utilization_penalty_factor)
        return max(0, adjusted_apy)

    @classmethod
    def from_api_dict(cls, api_data: Dict[str, Any]) -> Optional['LendingOpportunity']:
        """
        Creates a LendingOpportunity instance from a dictionary (single item from API response).
        Handles nested metrics and derives underlying_asset.
        Returns None if essential data is missing or invalid.
        """
        from ..utils.token_mappings import get_underlying_asset

        try:
            platform_token_symbol = api_data.get("symbol")
            if not platform_token_symbol:
                logger.warning(f"Missing 'symbol' in API data item: {api_data}")
                return None

            derived_underlying_asset = get_underlying_asset(platform_token_symbol)
            if not derived_underlying_asset:
                logger.warning(f"Could not derive underlying asset for platform token '{platform_token_symbol}'. Using symbol itself as underlying.")
                derived_underlying_asset = platform_token_symbol

            metrics = api_data.get("metrics", {})
            
            apy_str = metrics.get("apy")
            apy_val = float(apy_str) if apy_str is not None and apy_str != "" else 0.0

            liquidity_str = api_data.get("liquidity")
            liquidity_val = float(liquidity_str) if liquidity_str is not None and liquidity_str != "" else 0.0
            
            util_str = metrics.get("utilization")
            util_val = float(util_str) if util_str is not None and util_str != "" else 0.0

            cf_str = metrics.get("collateralFactor")
            cf_val = float(cf_str) if cf_str is not None and cf_str != "" else 0.0

            return cls(
                protocol=api_data.get("platform", "UnknownProtocol"),
                protocol_key=api_data.get("platformKey", api_data.get("platform", "unknown_protocol_key")),
                asset=platform_token_symbol,
                underlying_asset=derived_underlying_asset,
                asset_address=api_data.get("address", ""),
                apy=apy_val,
                liquidity=liquidity_val,
                utilization_rate=util_val,
                collateral_factor=cf_val,
                chain=api_data.get("network", "arbitrum"),
                platform_id=api_data.get("key", ""),
                pool_address=api_data.get("address", ""),
                last_updated=datetime.now(timezone.utc)
            )
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error parsing LendingOpportunity from API dict: {api_data}. Error: {e}", exc_info=True)
            return None
        except ImportError:
            logger.critical("Failed to import token_mappings for LendingOpportunity parsing. Ensure utils are accessible.")
            return None

    def to_dict(self):
        return {
            "protocol": self.protocol,
            "protocol_key": self.protocol_key,
            "asset": self.asset,
            "underlying_asset": self.underlying_asset,
            "asset_address": self.asset_address,
            "apy": self.apy,
            "liquidity": self.liquidity,
            "utilization_rate": self.utilization_rate,
            "collateral_factor": self.collateral_factor,
            "chain": self.chain,
            "platform_id": self.platform_id,
            "pool_address": self.pool_address,
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            protocol=d["protocol"],
            protocol_key=d["protocol_key"],
            asset=d["asset"],
            underlying_asset=d["underlying_asset"],
            asset_address=d["asset_address"],
            apy=d["apy"],
            liquidity=d["liquidity"],
            utilization_rate=d.get("utilization_rate", 0.0),
            collateral_factor=d.get("collateral_factor", 0.0),
            chain=d.get("chain", "arbitrum"),
            platform_id=d.get("platform_id", ""),
            pool_address=d.get("pool_address", ""),
            last_updated=datetime.fromisoformat(d["last_updated"]),
        )

@dataclass
class Position:
    """Represents an active lending position"""
    opportunity: LendingOpportunity
    amount_deposited: float
    deposit_timestamp: datetime
    tx_hash: str
    current_value: Optional[float] = None
    earned_yield: Optional[float] = None
    last_updated: Optional[datetime] = None

    def validate(self):
        assert isinstance(self.opportunity, LendingOpportunity), "opportunity must be a LendingOpportunity"
        assert isinstance(self.amount_deposited, (int, float)) and self.amount_deposited > 0, "amount_deposited must be a positive number"
        assert isinstance(self.deposit_timestamp, datetime), "deposit_timestamp must be a datetime"
        assert isinstance(self.tx_hash, str) and self.tx_hash, "tx_hash must be a non-empty string"
        if self.current_value is not None:
            assert isinstance(self.current_value, (int, float)), "current_value must be a number if set"
        if self.earned_yield is not None:
            assert isinstance(self.earned_yield, (int, float)), "earned_yield must be a number if set"
        if self.last_updated is not None:
            assert isinstance(self.last_updated, datetime), "last_updated must be a datetime if set"

    def to_dict(self):
        return {
            "opportunity": self.opportunity.to_dict(),
            "amount_deposited": self.amount_deposited,
            "deposit_timestamp": self.deposit_timestamp.isoformat(),
            "tx_hash": self.tx_hash,
            "current_value": self.current_value,
            "earned_yield": self.earned_yield,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            opportunity=LendingOpportunity.from_dict(d["opportunity"]),
            amount_deposited=d["amount_deposited"],
            deposit_timestamp=datetime.fromisoformat(d["deposit_timestamp"]),
            tx_hash=d["tx_hash"],
            current_value=d.get("current_value"),
            earned_yield=d.get("earned_yield"),
            last_updated=datetime.fromisoformat(d["last_updated"]) if d.get("last_updated") else None,
        )

@dataclass
class TransactionRequest:
    """Request model for building transactions via Portals API"""
    sender: str
    input_token: str
    input_amount: str
    output_token: str
    slippage_tolerance: float = 0.5
    gas_price: Optional[int] = None
    gas_limit: Optional[int] = None

    def validate(self):
        assert isinstance(self.sender, str) and self.sender, "sender must be a non-empty string"
        assert isinstance(self.input_token, str) and self.input_token, "input_token must be a non-empty string"
        assert isinstance(self.input_amount, str) and self.input_amount, "input_amount must be a non-empty string"
        assert isinstance(self.output_token, str) and self.output_token, "output_token must be a non-empty string"
        assert isinstance(self.slippage_tolerance, (int, float)) and self.slippage_tolerance >= 0, "slippage_tolerance must be a non-negative number"
        if self.gas_price is not None:
            assert isinstance(self.gas_price, int) and self.gas_price > 0, "gas_price must be a positive integer if set"
        if self.gas_limit is not None:
            assert isinstance(self.gas_limit, int) and self.gas_limit > 0, "gas_limit must be a positive integer if set"

    def to_dict(self):
        return {
            "sender": self.sender,
            "input_token": self.input_token,
            "input_amount": self.input_amount,
            "output_token": self.output_token,
            "slippage_tolerance": self.slippage_tolerance,
            "gas_price": self.gas_price,
            "gas_limit": self.gas_limit,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            sender=d["sender"],
            input_token=d["input_token"],
            input_amount=d["input_amount"],
            output_token=d["output_token"],
            slippage_tolerance=d.get("slippage_tolerance", 0.5),
            gas_price=d.get("gas_price"),
            gas_limit=d.get("gas_limit"),
        )

@dataclass
class TransactionResponse:
    """Response model from Portals API transaction building"""
    tx_data: Dict[str, Any]
    estimated_output: float
    gas_estimate: int
    protocol_route: List[str]
    simulation_success: bool = True

    def validate(self):
        assert isinstance(self.tx_data, dict), "tx_data must be a dict"
        assert isinstance(self.estimated_output, (int, float)), "estimated_output must be a number"
        assert isinstance(self.gas_estimate, int) and self.gas_estimate > 0, "gas_estimate must be a positive integer"
        assert isinstance(self.protocol_route, list), "protocol_route must be a list"
        assert isinstance(self.simulation_success, bool), "simulation_success must be a boolean"

    def to_dict(self):
        return {
            "tx_data": self.tx_data,
            "estimated_output": self.estimated_output,
            "gas_estimate": self.gas_estimate,
            "protocol_route": self.protocol_route,
            "simulation_success": self.simulation_success,
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            tx_data=d["tx_data"],
            estimated_output=d["estimated_output"],
            gas_estimate=d["gas_estimate"],
            protocol_route=d["protocol_route"],
            simulation_success=d.get("simulation_success", True),
        )
