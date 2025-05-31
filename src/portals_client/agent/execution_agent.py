import os
from web3 import Web3, HTTPProvider
from typing import Optional, Dict, Any
import logging
from ..core.api_client import PortalsAPIClient
from ..config import PortalsConfig

logger = logging.getLogger(__name__)

class ExecutionAgent:
    """
    Handles wallet management, transaction signing, position tracking, balance checking,
    token approvals, gas estimation, and transaction monitoring for DeFi operations.
    """
    def __init__(self, rpc_url: str, private_key: Optional[str] = None, api_client: Optional[PortalsAPIClient] = None):
        self.web3 = Web3(HTTPProvider(rpc_url))
        self.private_key = private_key or os.getenv('WALLET_PRIVATE_KEY')
        if not self.private_key:
            raise ValueError("Private key must be provided for ExecutionAgent.")
        self.account = self.web3.eth.account.from_key(self.private_key)
        logger.info(f"ExecutionAgent initialized for address: {self.account.address}")
        self.api_client = api_client or PortalsAPIClient(PortalsConfig.from_env())

    # 1. Wallet management
    def get_address(self) -> str:
        return self.account.address

    # 2. Transaction signing
    def sign_transaction(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        signed = self.web3.eth.account.sign_transaction(tx, self.private_key)
        return signed

    # 3. Position tracking
    def get_positions(self, networks: Optional[list] = None) -> dict:
        """
        Fetch positions/balances for the agent's address using the Portals API.
        """
        owner = self.get_address()
        return self.api_client.fetch_account_balances(owner, networks)

    # 4. Balance checking
    def get_balance(self, token_address: Optional[str] = None) -> int:
        if token_address:
            # ERC20 balance
            erc20 = self.web3.eth.contract(address=token_address, abi=[
                {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}
            ])
            return erc20.functions.balanceOf(self.account.address).call()
        else:
            # Native ETH balance
            return self.web3.eth.get_balance(self.account.address)

    # 5. Token approvals
    def approve_token(self, token_address: str, spender: str, amount: int) -> str:
        """
        Approve the spender to spend a given amount of the ERC20 token on behalf of the agent.
        Returns the transaction hash.
        """
        from web3.exceptions import ContractLogicError
        ERC20_ABI = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [
                    {"name": "", "type": "bool"}
                ],
                "type": "function"
            }
        ]
        try:
            contract = self.web3.eth.contract(address=token_address, abi=ERC20_ABI)
            tx = contract.functions.approve(spender, amount).build_transaction({
                'from': self.account.address,
                'nonce': self.web3.eth.get_transaction_count(self.account.address),
                'gas': 0,  # placeholder, will estimate below
                'gasPrice': self.web3.eth.gas_price
            })
            # Estimate gas
            tx['gas'] = self.web3.eth.estimate_gas({
                'from': self.account.address,
                'to': token_address,
                'data': tx['data']
            })
            # Sign
            signed = self.sign_transaction(tx)
            # Send
            tx_hash = self.web3.eth.send_raw_transaction(signed.rawTransaction)
            logger.info(f"Sent approve tx: {tx_hash.hex()}")
            # Wait for receipt
            receipt = self.wait_for_tx_receipt(tx_hash)
            if receipt and receipt.get('status') == 1:
                logger.info(f"Approve successful: {tx_hash.hex()}")
            else:
                logger.error(f"Approve failed: {tx_hash.hex()} | receipt: {receipt}")
            return tx_hash.hex()
        except ContractLogicError as e:
            logger.error(f"Contract logic error during approve: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in approve_token: {e}")
            raise

    # 6. Gas estimation
    def estimate_gas(self, tx: Dict[str, Any]) -> int:
        return self.web3.eth.estimate_gas(tx)

    # 7. Transaction monitoring (stub)
    def wait_for_tx_receipt(self, tx_hash: str, timeout: int = 120) -> Optional[Dict[str, Any]]:
        try:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            return dict(receipt)
        except Exception as e:
            logger.error(f"Error waiting for tx receipt: {e}")
            return None

    def get_all_positions_flat(self, networks: Optional[list] = None) -> list:
        """
        Return a flat list of all assets/positions (including nested tokens) with platform, symbol, balance, and network.
        Useful for tracking all supplied assets across protocols and networks.
        """
        def _walk_tokens(tokens, parent_platform=None, parent_network=None):
            flat = []
            for t in tokens:
                entry = {
                    'platform': t.get('platform', parent_platform),
                    'symbol': t.get('symbol'),
                    'balance': t.get('balance'),
                    'network': t.get('network', parent_network),
                    'raw': t  # keep full original for reference
                }
                flat.append(entry)
                # Recurse into nested tokens if present
                if t.get('tokens'):
                    flat.extend(_walk_tokens(t['tokens'], entry['platform'], entry['network']))
            return flat

        positions = self.get_positions(networks)
        balances = positions.get('balances', [])
        flat = []
        for b in balances:
            entry = {
                'platform': b.get('platform'),
                'symbol': b.get('symbol'),
                'balance': b.get('balance'),
                'network': b.get('network'),
                'raw': b
            }
            flat.append(entry)
            if b.get('tokens'):
                flat.extend(_walk_tokens(b['tokens'], entry['platform'], entry['network']))
        return flat

    def send_transaction(self, signed_tx: Any, wait: bool = True, timeout: int = 120) -> dict:
        """
        Send a signed transaction to the network.
        Accepts either a signed transaction object (from sign_transaction) or raw bytes.
        Returns a dict with tx_hash and receipt (if wait=True).
        """
        try:
            raw = signed_tx.rawTransaction if hasattr(signed_tx, 'rawTransaction') else signed_tx
            tx_hash = self.web3.eth.send_raw_transaction(raw)
            logger.info(f"Sent transaction: {tx_hash.hex()}")
            receipt = None
            if wait:
                receipt = self.wait_for_tx_receipt(tx_hash, timeout=timeout)
                if receipt and receipt.get('status') == 1:
                    logger.info(f"Transaction successful: {tx_hash.hex()}")
                else:
                    logger.error(f"Transaction failed: {tx_hash.hex()} | receipt: {receipt}")
            return {"tx_hash": tx_hash.hex(), "receipt": receipt}
        except Exception as e:
            logger.error(f"Error sending transaction: {e}")
            raise

    def deposit(self, opportunity, amount, slippage_tolerance=0.5):
        """
        Deposit into a supported protocol using Portals API (for MVP: only protocols supported by Portals).
        Args:
            opportunity: LendingOpportunity (or dict with required fields)
            amount: float (human units)
            slippage_tolerance: float (percent)
        Returns: tx hash or result dict
        """
        logger.info(f"Deposit: protocol={opportunity.protocol}, asset={opportunity.asset}, amount={amount}")
        if opportunity.protocol.lower() in ["fluid", "aave", "aavev3"]:
            # Use Portals API for deposit
            from ..core.models import TransactionRequest
            from ..utils.token_mappings import get_token_address, get_token_decimals
            sender = self.get_address()
            input_token = get_token_address(opportunity.underlying_asset)
            output_token = opportunity.asset_address
            decimals = get_token_decimals(opportunity.underlying_asset)
            input_amount = str(int(amount * (10 ** decimals)))
            req = TransactionRequest(
                sender=sender,
                input_token=input_token,
                input_amount=input_amount,
                output_token=output_token,
                slippage_tolerance=slippage_tolerance,
            )
            tx_resp = self.api_client.build_portal_transaction(req)
            tx = tx_resp.tx_data
            signed = self.sign_transaction(tx)
            return self.send_transaction(signed)
        else:
            raise NotImplementedError(f"Deposit not supported for protocol: {opportunity.protocol}")

    def withdraw(self, position, amount):
        """
        Withdraw from a supported protocol. For MVP: direct contract call for Aave v3 and Fluid.
        Args:
            position: Position (or dict with required fields)
            amount: float (human units)
        Returns: tx hash or result dict
        """
        logger.info(f"Withdraw: protocol={position.opportunity.protocol}, asset={position.opportunity.asset}, amount={amount}")
        protocol = position.opportunity.protocol.lower()
        if protocol in ["aave", "aavev3"]:
            # Aave v3 Pool contract withdraw(address asset, uint256 amount, address to)
            POOL_ADDRESS = "0xC9e9fda9dC5A44fA3C2A8eA7e7e1C0b2b8cA5b5c"  # Canonical Arbitrum v3 Pool
            POOL_ABI = [
                {
                    "inputs": [
                        {"internalType": "address", "name": "asset", "type": "address"},
                        {"internalType": "uint256", "name": "amount", "type": "uint256"},
                        {"internalType": "address", "name": "to", "type": "address"}
                    ],
                    "name": "withdraw",
                    "outputs": [
                        {"internalType": "uint256", "name": "", "type": "uint256"}
                    ],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            asset_addr = position.opportunity.asset_address
            from ..utils.token_mappings import get_token_decimals
            decimals = get_token_decimals(position.opportunity.underlying_asset)
            withdraw_amount = int(amount * (10 ** decimals))
            contract = self.web3.eth.contract(address=POOL_ADDRESS, abi=POOL_ABI)
            tx = contract.functions.withdraw(
                asset_addr,
                withdraw_amount,
                self.get_address()
            ).build_transaction({
                'from': self.get_address(),
                'nonce': self.web3.eth.get_transaction_count(self.get_address()),
                'gas': 0,  # will estimate below
                'gasPrice': self.web3.eth.gas_price
            })
            tx['gas'] = self.web3.eth.estimate_gas({
                'from': self.get_address(),
                'to': POOL_ADDRESS,
                'data': tx['data']
            })
            signed = self.sign_transaction(tx)
            logger.info(f"Aave withdraw tx built and signed for {withdraw_amount} of {asset_addr}")
            return self.send_transaction(signed)
        elif protocol == "fluid":
            # Fluid fToken contract redeem(uint256 amount)
            FLUID_ABI = [
                {
                    "inputs": [
                        {"internalType": "uint256", "name": "amount", "type": "uint256"}
                    ],
                    "name": "redeem",
                    "outputs": [],
                    "stateMutability": "nonpayable",
                    "type": "function"
                }
            ]
            ftoken_addr = position.opportunity.asset_address
            from ..utils.token_mappings import get_token_decimals
            decimals = get_token_decimals(position.opportunity.asset)
            withdraw_amount = int(amount * (10 ** decimals))
            contract = self.web3.eth.contract(address=ftoken_addr, abi=FLUID_ABI)
            tx = contract.functions.redeem(withdraw_amount).build_transaction({
                'from': self.get_address(),
                'nonce': self.web3.eth.get_transaction_count(self.get_address()),
                'gas': 0,
                'gasPrice': self.web3.eth.gas_price
            })
            tx['gas'] = self.web3.eth.estimate_gas({
                'from': self.get_address(),
                'to': ftoken_addr,
                'data': tx['data']
            })
            signed = self.sign_transaction(tx)
            logger.info(f"Fluid redeem tx built and signed for {withdraw_amount} of {ftoken_addr}")
            return self.send_transaction(signed)
        else:
            raise NotImplementedError(f"Withdraw not supported for protocol: {protocol}") 