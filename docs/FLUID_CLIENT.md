This is a draft for a general-purpose Fluid API Python Client Documentation. It illustrates how to use a Python client to interact with the API and retrieve key information about Vaults and NFT positions.

---

# Fluid API Python Client Documentation

This documentation outlines how to use a conceptual Python client to interact with the Fluid API, focusing on retrieving and interpreting data related to Vaults and user-specific NFT positions. The Fluid API provides comprehensive data on lending and borrowing activities within the Fluid Protocol across various blockchain networks.

## Introduction

The Fluid API offers developers programmatic access to crucial on-chain data, including detailed information about lending vaults, available tokens, historical statistics, and individual user positions represented by NFTs. This allows for building applications, analytics dashboards, monitoring tools, and more.

A Python client library serves as an abstraction layer, handling the complexities of HTTP requests, response parsing, error handling, and data modeling, allowing developers to focus on utilizing the data.

## Core Concepts

Before diving into the API endpoints, it's helpful to understand some core concepts within the Fluid Protocol and how they are represented in the API:

*   **Chain ID:** Represents the specific blockchain network (e.g., `1` for Ethereum Mainnet, `42161` for Arbitrum). Most API endpoints require a `chainId`.
*   **Vaults:** These are the core smart contracts that manage lending and borrowing pools for specific asset pairs. They define the rules, available tokens, interest rate models, and risk parameters.
*   **NFT Positions:** When a user supplies collateral or borrows assets from a Fluid Vault, their position is often represented by a unique Non-Fungible Token (NFT). This NFT encapsulates the user's specific stake and debt within a vault.
*   **Shares:** Within a vault's liquidity pool, user deposits (supply) and borrows (debt) are tracked using a share system. The API often provides user positions in terms of shares (`supply`, `borrow` fields in NFT data) and total shares in the vault (`totalSupplyLiquidity`, `totalBorrowLiquidity` in Vault data). Converting shares to actual token amounts requires knowing the total token amount corresponding to the total shares in the pool.
*   **APY (Annual Percentage Yield):** Represents the effective annual rate of return or cost, taking into account compounding. The API provides various rate components (interest, trading, staking) often in basis points, which can be combined to estimate a total APY.
*   **TVL (Total Value Locked):** The total value of assets currently supplied within a vault. This can be derived from the total supply liquidity shares and the value of the underlying tokens.
*   **Health Factor:** A key metric for borrowed positions, indicating the risk of liquidation. It is typically calculated based on the value of collateral, the value of debt, and the vault's liquidation threshold.

## API Endpoints

The Fluid API is structured around different data domains. Here are some key endpoints for accessing vault and NFT position data:

### Vault Data

Endpoints to retrieve information about available vaults and their configurations and current market data.

*   **Get All Vaults on a Chain:**
    *   **Endpoint:** `/v2/{chainId}/vaults`
    *   **Method:** `GET`
    *   **Parameters:**
        *   `chainId` (Path Parameter): The ID of the blockchain network.
    *   **Description:** Retrieves a list of all active vaults on the specified chain. Each entry provides extensive details about the vault's configuration, supported tokens, current liquidity, and various interest rates.
    *   **Key Data Points Available (from response object, e.g., `VaultData`):**
        *   `id`, `address`: Unique identifier and smart contract address of the vault.
        *   `type`: The type of vault (e.g., indicating the collateral/borrow asset pair structure).
        *   `supplyToken`, `borrowToken`: Details about the tokens involved (address, symbol, decimals, current price).
        *   `totalSupplyLiquidity`, `totalBorrowLiquidity`: Total shares representing supplied and borrowed liquidity in the vault.
        *   `supplyRate`, `borrowRate`: Objects containing different rate components (liquidity interest, DEX trading fees, etc.) for both supply and borrow sides, often in basis points.
        *   `liquiditySupplyData`, `liquidityBorrowData`: Raw amounts of `token0` and `token1` currently in the vault's liquidity pools, corresponding to the total supply/borrow shares.
        *   `collateralFactor`, `liquidationThreshold`: Risk parameters for positions using this vault, typically in basis points.
    *   **Derivable Metrics:**
        *   **TVL:** Can be estimated by summing the USD value of `token0` and `token1` amounts available in `liquiditySupplyData` (scaled by decimals and priced using `supplyToken`/`borrowToken` price).
        *   **APYs:** Calculated by combining relevant rate components from `supplyRate` and `borrowRate` (converting basis points to decimal rates). This might include interest yield, staking yield (if applicable to the collateral token), and trading fee yield.

### NFT Position Data

Endpoints to retrieve information about specific user positions represented by NFTs.

*   **Get a Specific NFT Position:**
    *   **Endpoint:** `/v2/{chainId}/nfts/{nftId}`
    *   **Method:** `GET`
    *   **Parameters:**
        *   `chainId` (Path Parameter): The ID of the blockchain network.
        *   `nftId` (Path Parameter): The unique identifier of the NFT representing the position.
    *   **Description:** Retrieves detailed information about a single NFT position.
    *   **Key Data Points Available (from response object, e.g., `NFTData`):**
        *   `nft`: The NFT ID.
        *   `chainId`: The chain ID.
        *   `vault`: Basic information about the vault this NFT belongs to (often just the ID).
        *   `health_factor`: The current health factor of the position (may be provided directly by the API or require calculation).
        *   `supply`: The amount of supply shares held by this NFT position.
        *   `borrow`: The amount of borrow shares held by this NFT position.
    *   **Derivable Metrics:**
        *   **Position Value (USD):** Requires combining `supply` and `borrow` shares from the NFT data with the total shares and token amounts from the corresponding Vault data, and then using token prices.
        *   **Net Equity (USD):** Calculated as the USD value of supplied assets minus the USD value of borrowed assets.
        *   **LTV (Loan-to-Value):** Calculated as the USD value of borrowed assets divided by the USD value of supplied assets.
        *   **Health Factor:** Can be calculated using the USD values of collateral and debt, and the `liquidationThreshold` from the corresponding Vault data. If the API provides `health_factor` directly, it should ideally match this calculation.

### Other Relevant Endpoints

*   **Vault Oracle Data:**
    *   **Endpoint:** `/v2/{chainId}/vaults/{idOrAddress}/oracle`
    *   **Method:** `GET`
    *   **Parameters:** `chainId`, `idOrAddress` (Vault ID or Address).
    *   **Description:** Get information about the price oracle used by a specific vault. Essential for determining the USD value of assets.
*   **Historical Data:** The API also provides endpoints for historical data (e.g., `/v2/{chainId}/dexes/{address}/historical-stats`, `/v2/{chainId}/vaults/{id}/apr-history`). These are useful for trend analysis but require separate fetching and processing.

## Combining Data for Position Analysis

To get a complete view of a specific NFT position, including its value, risk, and estimated yield, you need to combine data from the NFT endpoint and the corresponding Vault endpoint:

1.  **Fetch NFT Data:** Call `/v2/{chainId}/nfts/{nftId}` to get the user's shares (`supply`, `borrow`) and the associated `vaultId`.
2.  **Fetch Vaults Data:** Call `/v2/{chainId}/vaults` to get the configurations and current state of all vaults on the chain.
3.  **Find Matching Vault:** Locate the specific `VaultData` object from the `/vaults` response that matches the `vaultId` from the NFT data.
4.  **Calculate User Token Amounts:** Use the user's `supply` shares, the vault's `totalSupplyLiquidity` shares, and the raw token amounts in `liquiditySupplyData` to determine the user's actual token balance for supplied assets. Repeat for `borrow` shares, `totalBorrowLiquidity`, and `liquidityBorrowData` for borrowed assets. Remember to use the correct token `decimals` to scale the raw amounts.
5.  **Calculate USD Values:** Multiply the calculated user token amounts by the corresponding token `price` obtained from the `VaultData`. Sum these values for total collateral value and total debt value.
6.  **Calculate Health Factor:** Use the total collateral value, total debt value, and the vault's `liquidationThreshold` (converted from basis points) to calculate the health factor.
7.  **Estimate Net APY on Equity:** This is a more complex calculation that involves:
    *   Calculating the annual yield generated by supplied assets (combining interest yield, staking yield from `TokenInfo`, and the vault's supply-side trading yield from `supplyRate.dex`).
    *   Calculating the annual cost of borrowed assets (combining interest cost and the vault's borrow-side trading yield from `borrowRate.dex`).
    *   Determining the Net Annual Yield in USD (Total Yield from Supply - Total Cost from Borrow).
    *   Calculating Net Equity (Total Collateral Value - Total Debt Value).
    *   Finally, dividing the Net Annual Yield (USD) by the Net Equity (USD) to get the Net APY on Equity. Careful handling of zero or negative equity is required.

## Using a Python Client Library

A well-designed Python client library would encapsulate the API request logic, Pydantic data parsing, and potentially some of the common calculation logic (like converting basis points or scaling values).

**Example (Conceptual Python Code):**

```python
from fluid_api_client import FluidAPIClient # TODO: Define this client
from fluid_models import NFTData, VaultData, AnalysisResult # TODO: Define these models

async def analyze_user_position(chain_id: int, nft_id: int):
    """Fetches data and analyzes a Fluid NFT position."""
    client = FluidAPIClient()
    try:
        # Fetch NFT data
        nft_position: NFTData = await client.get_nft_position(chain_id, nft_id)

        # Fetch all vaults data (needed to find the specific vault info)
        all_vaults: list[VaultData] = await client.get_vaults_data(chain_id)

        # Find the specific vault data for this NFT
        vault_info = next((v for v in all_vaults if v.id == nft_position.vault.id), None)

        if not vault_info:
            print(f"Error: Vault {nft_position.vault.id} not found.")
            return None

        # Perform analysis calculations (shares, USD values, health factor, APY)
        # This logic would typically be in a separate service or method within the client
        analysis_result: AnalysisResult = calculate_position_metrics(nft_position, vault_info)

        # Display or return the result
        print(f"Analysis for NFT {nft_id} on Chain {chain_id}:")
        print(f"  Net Equity: ${analysis_result.net_equity_usd:,.2f}")
        print(f"  Health Factor: {analysis_result.health_factor:.4f}")
        print(f"  Estimated Net APY on Equity: {analysis_result.net_apy_estimate_on_equity:.2%}")
        # ... print other details

        return analysis_result

    except DataNotFoundError as e:
        print(f"Error: Required data not found - {e}")
    except FluidAPIError as e:
        print(f"API Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        await client.close() # Ensure the client session is closed

# Example usage (requires an async environment like asyncio)
# import asyncio
# asyncio.run(analyze_user_position(1, 4547))
```

## Error Handling

A robust client should implement error handling for common API issues:

*   `404 Not Found`: The requested resource (e.g., a specific NFT or Vault) does not exist.
*   `429 Too Many Requests`: Rate limiting is in effect. The client should implement retry logic with exponential backoff.
*   `5xx Server Errors`: Indicates an issue on the API side. Retry logic is also appropriate here.
*   **Data Validation Errors:** If the API response does not match the expected data model (e.g., Pydantic validation fails), this indicates a potential issue with the API or the client's models.
