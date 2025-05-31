import requests
import logging
from typing import Any, Dict, Optional, List
from ..config import PortalsConfig
from .exceptions import PortalsAPIError, RateLimitError
from .models import LendingOpportunity, TransactionResponse # TransactionResponse was unused, kept for consistency

logger = logging.getLogger(__name__)

class PortalsAPIClient:
    """Core API client for Portals Finance interactions"""

    def __init__(self, config: Optional[PortalsConfig] = None):
        self.config = config or PortalsConfig.from_env()
        self.base_url = self.config.api_base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        })

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, retry_count: int = 3) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        for attempt in range(retry_count):
            try:
                response = self.session.request(method=method, url=url, params=params, json=data)
                if response.status_code == 429:
                    logger.warning(f"Rate limit hit for {method} {url}, retrying...")
                    if attempt == retry_count - 1:
                        raise RateLimitError(f"Rate limit persisted after {retry_count} attempts for {method} {url}.")
                    import time; time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as http_err:
                logger.error(f"HTTP error: {http_err} for {method} {url}")
                if attempt == retry_count - 1:
                    raise PortalsAPIError(f"HTTP error after {retry_count} attempts: {http_err}", status_code=http_err.response.status_code, response_data=http_err.response.text) from http_err
                import time; time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e} for {method} {url}")
                if attempt == retry_count - 1:
                    raise PortalsAPIError(f"Request failed after {retry_count} attempts: {e}") from e
                import time; time.sleep(2 ** attempt)
        # This line should ideally not be reached if exceptions are raised correctly.
        # Adding a default raise to satisfy static analysis and ensure an error is always propagated.
        raise PortalsAPIError(f"API request failed for {method} {url} after all retries without returning a valid response or specific error.")

    def fetch_tokens(self, networks: str = "arbitrum", platforms: Optional[List[str]] = None, min_liquidity: Optional[float] = None, min_apy: Optional[float] = None, limit: int = 500) -> List[LendingOpportunity]:
        """
        Fetch token opportunities from Portals API and return as LendingOpportunity objects.
        """
        params: Dict[str, Any] = { # Explicitly type params
            "networks": networks,
            "limit": str(limit), # API might expect string
            "sortBy": "apy",
            "sortDirection": "desc"
        }
        if platforms and isinstance(platforms, list):
            params["platforms"] = platforms  # requests will encode as repeated params
        elif platforms and isinstance(platforms, str):
            params["platforms"] = [platforms]
        if min_liquidity is not None:
            params["minLiquidity"] = str(min_liquidity)
        if min_apy is not None:
            params["minApy"] = str(min_apy)
        
        logger.debug(f"Fetching tokens with params: {params}")
        api_response_data = self._make_request("GET", "/tokens", params=params)
        
        results = []
        # Corrected: API response uses "tokens" key for the list of opportunities
        for item_data in api_response_data.get("tokens", []): 
            if not isinstance(item_data, dict):
                logger.warning(f"Skipping non-dictionary item in API response: {item_data}")
                continue
            try:
                # Pass self or a utility to from_dict if it needs access to token_mappings for underlying_asset
                opportunity = LendingOpportunity.from_api_dict(item_data)
                if opportunity: # from_api_dict might return None if parsing fails critically
                    results.append(opportunity)
            except Exception as e:
                logger.warning(f"Failed to parse LendingOpportunity from item: {item_data}. Error: {e}", exc_info=True)
        return results

    def build_portal_transaction(self, sender: str, input_token: str, input_amount: str, output_token: str, slippage_tolerance: float = 0.5, gas_price: Optional[int] = None, gas_limit: Optional[int] = None) -> TransactionResponse:
        """
        Build a portal transaction for token swaps/deposits and return as TransactionResponse object.
        """
        data = {
            "sender": sender,
            "network": self.config.network, # Use network from config
            "inputToken": input_token,
            "inputAmount": input_amount, # Expected in wei string
            "outputToken": output_token,
            "slippageTolerance": str(slippage_tolerance),
            "validate": True
        }
        if gas_price is not None:
            data["gasPrice"] = str(gas_price)
        if gas_limit is not None:
            data["gasLimit"] = str(gas_limit)
        
        logger.debug(f"Building portal transaction with data: {data}")
        resp_data = self._make_request("POST", "/portal", data=data)
        
        try:
            # Ensure critical fields are present in the response
            if "tx" not in resp_data or "outputAmount" not in resp_data or "gasEstimate" not in resp_data:
                logger.error(f"Incomplete response from /portal endpoint: {resp_data}")
                raise PortalsAPIError("Incomplete response from /portal transaction building.", response_data=resp_data)
            
            # Use the TransactionResponse.from_dict for parsing if it's robust
            # Otherwise, parse manually here
            return TransactionResponse(
                tx_data=resp_data["tx"],
                estimated_output=float(resp_data.get("outputAmount", 0.0) or 0.0), # Handle None or empty string
                gas_estimate=int(resp_data.get("gasEstimate", 0) or 0), # Handle None or empty string
                protocol_route=resp_data.get("route", []),
                simulation_success=resp_data.get("success", True) # Default to True if not specified
            )
        except (ValueError, TypeError, KeyError) as e: # Catch parsing errors or missing keys
            logger.error(f"Failed to parse TransactionResponse from /portal data: {resp_data}. Error: {e}", exc_info=True)
            raise PortalsAPIError(f"Failed to parse TransactionResponse from /portal: {e}", response_data=resp_data) from e

    def fetch_account_balances(self, owner: str, networks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch account balances for the given owner address and list of networks using the Portals API /account endpoint.
        """
        if not owner:
            raise ValueError("Owner address is required for fetching account balances.")
        if networks is None:
            networks = [self.config.network]
        network_params = ','.join(networks)
        params = {
            "owner": owner,
            "networks": network_params
        }
        return self._make_request("GET", "/account", params=params)