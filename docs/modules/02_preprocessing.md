# Module Specification: 02 - Preprocessing Round

**Parent Document:** [Rate Rover Overview](../README.md)

**Version:** 0.1.0

**Last Updated:** 2025-05-16

## 1. Purpose

The Preprocessing Round is responsible for transforming the raw market data—collected by the `DataCollectionRound` from various DeFi protocols—into a clean, validated, standardized, and enriched format. This standardized format is defined by the **Unified Market Data Schema**.

This round performs several key functions:
*   Validates the incoming raw data for completeness and freshness.
*   Normalizes diverse data structures and value representations (e.g., APYs, token amounts) from different protocols.
*   Maps the protocol-specific raw data to the fields of the Unified Market Data Schema.
*   Enriches the data by calculating derived metrics such as net APYs (accounting for operational fees) and estimating potential transaction costs for entering/exiting positions.

The output of this round is a consistent and reliable dataset that the `OpportunityRankingRound` can use to identify and evaluate arbitrage opportunities.

## 2. Role within the FSM Application (Open Autonomy Framework)

The Preprocessing module is implemented as one or more `AbstractRound` subclasses within the agent's main FSM AbciApp. The core data transformation and calculation logic is executed within one or more associated `BaseBehaviour` classes (asynchronous operations might be less prevalent here, but `AsyncBehaviour` can be used if needed for parts like on-demand oracle calls).

*   **FSM Round Class (Example):** `PreprocessingRound(AbstractRound)`
    *   Defines the payload structure for the processed (unified) data.
    *   Manages the consensus process for the processed data.
    *   Updates `SynchronizedData` with the agreed-upon list of `UnifiedMarketData` objects.
    *   Determines the transition to the next FSM state.
*   **Behaviour Class (Example):** `PreprocessingBehaviour(BaseBehaviour)`
    *   Contains the `act` method which retrieves the `raw_market_data_sources` from `SynchronizedData`.
    *   Iterates through each raw data entry, applying validation, normalization, mapping, and enrichment logic.
    *   Prepares the `PreprocessingPayload` with the list of `UnifiedMarketData` objects.

## 3. Inputs

### 3.1. `SynchronizedData` (Input from `DataCollectionRound`):
*   **`raw_market_data_sources`**: (List[Dict]) The primary input. A list where each dictionary represents a data source's fetch attempt from the previous round, structured as:
    ```json
    [
        {
            "protocol_name": "Fluid",
            "chain_id": 42161,
            "source_type": "API",
            "status": "SUCCESS", // or "FAILURE"
            "collection_time_utc": "2023-10-27T10:00:00Z",
            "raw_data": { /* ... actual JSON data from Fluid API ... */ },
            "error_message": null // or error details
        },
        // ... more entries
    ]
    ```
*   **`last_successful_collection_utc`**: (Timestamp)
*   **`data_collection_cycle_status`**: (String)

### 3.2. Skill Parameters (Defined in `skill.yaml`, accessed via `self.params`):
*   **`preprocessing_round_timeout_seconds`**: (Integer) Maximum duration for the `PreprocessingRound`. *Default: 300 seconds.*
*   **`stale_data_threshold_seconds`**: (Integer) Maximum age for raw data to be considered fresh and processed. Data older than `utcnow() - stale_data_threshold_seconds` might be flagged or discarded. *Default: 900 seconds (15 minutes).*
*   **`gas_price_oracle_config`**: (JSON String or Dict, optional) Configuration for fetching current gas prices on Arbitrum if needed for dynamic cost estimation.
*   **`dex_slippage_estimation_config`**: (JSON String or Dict, optional) Parameters for slippage estimation (e.g., default slippage percentage, list of preferred DEXs for liquidity checks).
*   **`protocol_operational_fees`**: (JSON String or Dict, optional) Configuration defining known, ongoing operational fees for specific protocols that need to be factored into net APY calculations (e.g., `{ "AAVE_V3_Arbitrum": {"supply_fee_bps": 5} }`).

### 3.3. Unified Market Data Schema Definition:
*   The structure and field definitions of the target `UnifiedMarketData` object (as defined in `docs/schemas/unified_schema.md` or similar). This schema guides the mapping process.

## 4. Core Logic & Responsibilities

### 4.1. `PreprocessingBehaviour` (`act` method):
1.  **Initialization:**
    *   Log the start of the preprocessing behaviour.
    *   Retrieve `raw_market_data_sources` from `self.synchronized_data`.
    *   Retrieve relevant parameters from `self.params`.
2.  **Data Iteration and Processing:**
    *   Initialize an empty list: `processed_unified_markets = []`.
    *   For each `source_entry` in `raw_market_data_sources`:
        *   **a. Validation:**
            *   If `source_entry["status"]` is "FAILURE", log it and skip to the next source.
            *   Check data freshness: If `utcnow() - source_entry["collection_time_utc"] > self.params.stale_data_threshold_seconds`, log a warning and potentially skip or flag the data.
            *   Perform basic completeness checks on `source_entry["raw_data"]` (e.g., does it contain the expected 'markets' list or equivalent structure?).
        *   **b. Protocol-Specific Mapping & Normalization:**
            *   Based on `source_entry["protocol_name"]`, select the appropriate mapping function (e.g., `_map_fluid_to_unified`, `_map_aave_to_unified`).
            *   These mapping functions will:
                *   Iterate through individual markets/vaults within `source_entry["raw_data"]`.
                *   Extract relevant fields.
                *   Normalize values:
                    *   Convert string numbers to `Decimal`.
                    *   Scale token amounts using their `decimals`.
                    *   Convert APYs/rates from basis points or percentage strings to decimal ratios (e.g., 5% -> 0.05).
                *   Populate a new `UnifiedMarketData` object (or a list of them, e.g., for Fluid's dual-asset vaults).
                *   Set the `last_updated_at` field in the `UnifiedMarketData` object to `source_entry["collection_time_utc"]`.
        *   **c. Enrichment (per `UnifiedMarketData` object):**
            *   **Calculate Net APYs:**
                *   `supply_apy_net`: Start with the protocol's reported supply APY. Subtract any known ongoing operational fees defined in `self.params.protocol_operational_fees`.
                *   `borrow_apy_net`: Start with the protocol's reported borrow APY. Add any known ongoing operational fees. (Note: Fluid's `borrow_rate.dex.trading_rate` *reduces* cost, so it's handled during the initial APY calculation from raw rates).
            *   **Estimate Transaction Costs (for entering/exiting this *specific market*):**
                *   This is a complex step. It might involve:
                    *   Estimating gas costs for typical operations (deposit, borrow, withdraw, repay) on this specific protocol on Arbitrum.
                    *   Estimating potential slippage if a swap is *implicitly* required to interact with this market (e.g., if the agent only holds USDC but this market is for DAI). This is more relevant for the "Opportunity Chooser" when evaluating *pairs* of markets. For now, focus on costs for direct interaction.
                *   Store this as an indicative cost or a set of cost components within or alongside the `UnifiedMarketData` object.
                *   `TODO`: Clarify if this cost estimation is per individual market action or for a typical arbitrage "round trip" involving this market as one leg. For preprocessing, individual action costs might be more appropriate.
            *   **Calculate Utilization Rate:** If not directly provided by the protocol, calculate as `total_borrowed_usd / total_value_locked_usd` (or using raw token amounts if USD values are not yet reliable).
        *   Append the processed `UnifiedMarketData` object(s) to `processed_unified_markets`.
3.  **Payload Creation:**
    *   Create an instance of `PreprocessingPayload` (e.g., `PreprocessingPayload(sender=self.context.agent_address, unified_market_data=processed_unified_markets)`).
4.  **A2A Transaction & Completion:**
    *   `yield from self.send_a2a_transaction(payload)`
    *   `yield from self.wait_until_round_end()`
    *   `self.set_done()`

### 4.2. `PreprocessingPayload(BaseTxPayload)`:
*   Defines an attribute, e.g., `unified_market_data: Optional[List[Dict]]`, to carry the list of processed `UnifiedMarketData` objects (serialized to dicts for the payload).

### 4.3. `PreprocessingRound(AbstractRound)`:
1.  **Configuration:**
    *   `payload_class = PreprocessingPayload`
    *   `payload_attribute = "preprocessing_payload"`
    *   Set `round_timeout_seconds = self.params.preprocessing_round_timeout_seconds`.
2.  **Consensus Logic (within `end_block`):**
    *   Similar to `DataCollectionRound`, the consensus mechanism will depend on the base round class.
    *   If agents perform preprocessing independently, their `unified_market_data` lists might differ slightly due to floating-point arithmetic or minor variations in cost estimations if those involve external calls.
    *   A strategy for agreeing on a canonical list of `UnifiedMarketData` will be needed (e.g., using data from a majority, averaging numerical values where appropriate and discrepancies are small, or a designated processor agent).
    *   **For Alpha:** A simpler approach might involve each agent performing the preprocessing and the round ensuring a consistent *count* or hash of the resulting list, with the actual list taken from one agent or merged carefully.
3.  **Update `SynchronizedData`:**
    *   Store the agreed-upon list of `UnifiedMarketData` objects into `self.synchronized_data` under a key like `unified_markets`.
    *   Update a timestamp like `self.synchronized_data.update(last_preprocessing_utc=utc_now())`.
4.  **Transition Event Determination:**
    *   If preprocessing is successful and a sufficient number of markets are processed: `return self.synchronized_data, Event.DONE`
    *   If significant errors occurred during preprocessing (e.g., unable to map critical data): `return self.synchronized_data, Event.PREPROCESSING_FAILED`
    *   On timeout or internal error: `return self.synchronized_data, Event.ERROR` or `Event.TIMEOUT`.

## 5. Outputs

### 5.1. Data written to `SynchronizedData` (by `PreprocessingRound`):
*   **`unified_markets`**: (List[Dict]) A list of `UnifiedMarketData` objects (serialized as dictionaries), representing all successfully processed and standardized market opportunities. Each object conforms to the Unified Market Data Schema.
*   **`last_preprocessing_utc`**: (Timestamp)
*   **`preprocessing_cycle_status`**: (String: e.g., "COMPLETED", "ERRORS_ENCOUNTERED")

### 5.2. FSM Events (from `PreprocessingRound`):
*   `Event.DONE`: Preprocessing successful.
*   `Event.PREPROCESSING_FAILED`: Significant errors occurred.
*   `Event.ERROR`: Internal error.
*   `Event.TIMEOUT`: Round execution exceeded timeout.

## 6. Interactions with Other Rounds/Behaviours

*   **Receives Control From:** `DataCollectionRound` (on `Event.DONE` or `Event.DONE_WITH_WARNINGS`).
*   **Passes Control To:**
    *   `OpportunityRankingRound` (on `Event.DONE`).
    *   An Error Handling Round or back to `ResetRound` (on `Event.PREPROCESSING_FAILED`, `Event.ERROR`, `Event.TIMEOUT`).

## 7. TODOs & Open Questions

*   **`TODO`**: Finalize and document the complete Unified Market Data Schema (`docs/schemas/unified_schema.md`). This is a critical dependency for the mapping functions.
*   **`TODO`**: Implement the protocol-specific mapping functions (`_map_fluid_to_unified`, `_map_aave_to_unified`, etc.) within the `PreprocessingBehaviour`. These functions must handle the nuances of each protocol's raw data structure.
*   **`TODO`**: Develop the detailed methodology and implement the logic for calculating `supply_apy_net` and `borrow_apy_net`, including how to access and apply `self.params.protocol_operational_fees`.
*   **`TODO`**: Design and implement the transaction cost estimation logic. Determine if this is a simple estimation per market (e.g., typical deposit gas) or a more complex estimation for an arbitrage "leg" involving this market. Clarify where this estimated cost is stored or how it's passed to the Opportunity Ranking Round.
*   **`TODO`**: Define the exact validation rules for raw data (completeness, freshness criteria based on `stale_data_threshold_seconds`).
*   **`TODO`**: Implement the `PreprocessingPayload` class.
*   **`TODO`**: Implement the `PreprocessingRound` class, including the consensus strategy for the processed `unified_market_data` list if multiple agents are involved in preprocessing. Define the FSM `Event` enum for this round's outcomes.
*   **`TODO`**: If gas/slippage estimation requires external calls (e.g., to a gas oracle, or DEX for liquidity), ensure `PreprocessingBehaviour` uses `AsyncBehaviour` and `yield from self.get_http_response()` for these calls.
*   **`TODO`**: Clarify how to handle cases where essential data for a market is missing from the raw input (e.g., token price missing, preventing USD value calculations). Should the market be dropped, or included with missing fields?
*   **`TODO`**: Update `skill.yaml` examples to show how parameters like `stale_data_threshold_seconds`, `protocol_operational_fees`, etc., would be structured.

