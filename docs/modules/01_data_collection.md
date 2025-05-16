
# Module Specification: 01 - Data Collection Round

**Parent Document:** [Rate Rover Overview](../../README.md)

**Version:** 0.1.0

**Last Updated:** 2025-05-16

## 1. Purpose

The Data Collection Round is a core component of the DeFi Arbitrage Agent's FSM (Finite State Machine) AbciApp. Its primary responsibility is to systematically and reliably fetch raw market data from a configured set of DeFi protocols operating on the Arbitrum network. This data includes, but is not limited to, information on lending/borrowing vaults (or markets), token prices, liquidity levels, interest rates, and relevant risk parameters.

The output of this round—a collection of raw data from various sources, timestamped and tagged with its origin—is made available via `SynchronizedData` for consumption by the subsequent `PreprocessingRound`. This ensures the agent service operates on the freshest possible data to make informed decisions.

## 2. Role within the FSM Application (Open Autonomy Framework)

The Data Collection module is implemented as one or more `AbstractRound` subclasses within the agent's main FSM AbciApp. The operational logic for fetching data is encapsulated within one or more associated `AsyncBehaviour` classes.

*   **FSM Round Class (Example):** `DataCollectionRound(AbstractRound)`
    *   Responsible for defining the payload structure for collected data.
    *   Manages the consensus process for the collected data if multiple agents participate in fetching or verifying.
    *   Updates `SynchronizedData` with the agreed-upon raw data.
    *   Determines the transition to the next FSM state based on the outcome of the data collection (e.g., success, partial failure, timeout).
*   **Behaviour Class (Example):** `DataCollectionBehaviour(AsyncBehaviour, BaseBehaviour)`
    *   Contains the `async_act` method which orchestrates the asynchronous fetching of data from all configured external sources (Fluid API, The Graph Subgraphs).
    *   Handles HTTP requests, retries, and error logging for individual data sources.
    *   Prepares the `DataCollectionPayload` with the fetched data (or error statuses) to be submitted for consensus.

The cyclical execution of the FSM ensures that data collection occurs at intervals determined by the overall FSM loop time or specific logic within preceding rounds that trigger this collection phase.

## 3. Inputs

### 3.1. Skill Parameters (Defined in `skill.yaml`, accessed via `self.params`):

*   **`target_protocols_config`**: (JSON String or Dict) A list defining each protocol data source.
    *   Structure per entry:
        ```json
        {
            "protocol_name": "Fluid | AAVE_V3_Arbitrum | etc.",
            "source_type": "API | SUBGRAPH",
            "chain_id": 42161, // Example for Arbitrum
            "api_details": { // If source_type is API
                "base_url": "https://api.fluid.instadapp.io",
                "vaults_endpoint": "/v2/42161/vaults"
            },
            "subgraph_details": { // If source_type is SUBGRAPH
                "subgraph_id_or_url": "your_subgraph_id_or_full_url",
                "query_name": "get_protocol_markets_query" // Key to retrieve the actual GraphQL query string
            }
        }
        ```
*   **`graphql_queries`**: (JSON String or Dict) A dictionary mapping `query_name` (from `target_protocols_config`) to the actual GraphQL query strings.
    *   Example: `{"get_aave_markets_query": "query {...}"}`
*   **`collection_round_timeout_seconds`**: (Integer) Maximum duration for the `DataCollectionRound` before it times out. *Default: 600 seconds.*
*   **`api_keys`**: (JSON String or Dict) Stores API keys, e.g., `{"THE_GRAPH_API_KEY": "your_key"}`.
*   **`http_request_timeout_seconds`**: (Integer) Timeout for individual HTTP calls made by the behaviour. *Default: 30 seconds.*
*   **`http_request_retry_attempts`**: (Integer) Number of retries for failed HTTP calls. *Default: 3.*
*   **`http_request_retry_backoff_factor`**: (Float) Backoff factor for retries. *Default: 0.5.*

### 3.2. `SynchronizedData` (Input from previous FSM round):
*   `current_fsm_cycle_count`: (Integer, optional) Can be used for logging or conditional logic.
*   `last_collection_status`: (Dict, optional) Status of the previous data collection attempt, to potentially influence current attempt.

## 4. Core Logic & Responsibilities

### 4.1. `DataCollectionBehaviour` (`async_act` method):
1.  **Initialization:**
    *   Log the start of the data collection behaviour.
    *   Retrieve `target_protocols_config`, `graphql_queries`, `api_keys`, and HTTP request parameters from `self.params`.
2.  **Asynchronous Data Fetching:**
    *   Create a list of asynchronous tasks, one for each protocol defined in `target_protocols_config`.
    *   Each task will execute a specific fetch function (e.g., `_fetch_fluid_data`, `_fetch_subgraph_data`).
    *   **`_fetch_fluid_data(protocol_config)`:**
        *   Construct the target URL using `api_details.base_url` and `api_details.vaults_endpoint`.
        *   Use `yield from self.get_http_response()` to make a GET request.
        *   Implement retry logic based on `http_request_retry_attempts` and `http_request_retry_backoff_factor` for transient errors or rate limits.
        *   On success, parse JSON and return `{"status": "SUCCESS", "data": response_json, "timestamp": utc_now()}`.
        *   On failure, return `{"status": "FAILURE", "error": error_details, "timestamp": utc_now()}`.
    *   **`_fetch_subgraph_data(protocol_config)`:**
        *   Retrieve the GraphQL query string from `self.params.graphql_queries` using `subgraph_details.query_name`.
        *   Construct the target Subgraph URL.
        *   Prepare the POST request payload (query, variables).
        *   Use `yield from self.get_http_response()` to make a POST request.
        *   Implement retry logic.
        *   On success, parse JSON. Check for `response_json.get("errors")`. If GraphQL errors exist, treat as failure. Otherwise, return `{"status": "SUCCESS", "data": response_json["data"], "timestamp": utc_now()}`.
        *   On failure (HTTP or GraphQL error), return `{"status": "FAILURE", "error": error_details, "timestamp": utc_now()}`.
    *   Execute all tasks concurrently using `asyncio.gather` (or equivalent pattern compatible with `yield from`).
3.  **Result Aggregation:**
    *   Collect results from all fetching tasks.
    *   Compile a `collected_data_summary_list`, where each item contains:
        *   `protocol_name`
        *   `chain_id`
        *   `source_type`
        *   `status` ("SUCCESS" or "FAILURE")
        *   `collection_time_utc`
        *   `raw_data` (if successful, otherwise `None` or minimal error info)
        *   `error_message` (if failed)
4.  **Payload Creation:**
    *   Create an instance of `DataCollectionPayload` (e.g., `DataCollectionPayload(sender=self.context.agent_address, collected_data=collected_data_summary_list)`).
5.  **A2A Transaction:**
    *   `yield from self.send_a2a_transaction(payload)`
    *   `yield from self.wait_until_round_end()`
6.  **Completion:** `self.set_done()`

### 4.2. `DataCollectionPayload(BaseTxPayload)`:
*   Defines a single attribute, e.g., `collected_data: Optional[List[Dict]]`, to carry the `collected_data_summary_list`.
*   Includes type hints for serialization and validation.

### 4.3. `DataCollectionRound(AbstractRound)`:
1.  **Configuration:**
    *   `payload_class = DataCollectionPayload`
    *   `payload_attribute = "data_collection_payload"` (matching attribute name in payload class).
    *   Set `round_timeout_seconds = self.params.collection_round_timeout_seconds`.
2.  **Consensus Logic (within `end_block`):**
    *   The exact consensus mechanism depends on the chosen base round class (e.g., `CollectSameUntilThresholdRound`, `CollectDifferentUntilAllRound`).
    *   If `CollectSameUntilThresholdRound` is used, all agents are expected to fetch and propose identical raw data (or at least a hash of it). This is unlikely given external API calls.
    *   More likely, `CollectDifferentUntilAllRound` (or a custom variant) will be used, where each agent submits its fetched data. The `end_block` logic would then need to:
        *   Iterate through received payloads from all participating agents.
        *   Implement a strategy for merging or selecting the "best" data if discrepancies exist (e.g., use data from the majority, use the first successful fetch for each source, or flag discrepancies for manual review). For Alpha, a simpler approach might be that each agent attempts all fetches, and the "agreed" payload in `SynchronizedData` could be a list of *all* agents' findings, with the Preprocessing round then taking on the task of deduplication/selection. Alternatively, a designated fetcher agent could be used if the service has >1 agent.
        *   **For simplicity in Alpha with a single or few agents:** Assume the round collects the payload from the agent(s) and the primary task is to get *a* version of the data into `SynchronizedData`.
3.  **Update `SynchronizedData`:**
    *   Store the agreed-upon (or processed) `collected_data_summary_list` into `self.synchronized_data` under a key like `raw_market_data_sources`. Example:
      `self.synchronized_data.update(raw_market_data_sources=most_voted_payload.get("collected_data"))`
    *   Update a timestamp like `self.synchronized_data.update(last_successful_collection_utc=utc_now())`.
4.  **Transition Event Determination:**
    *   Analyze the `status` fields within the agreed `collected_data_summary_list`.
    *   If all critical data sources reported "SUCCESS": `return self.synchronized_data, Event.DONE`
    *   If some non-critical sources failed but critical ones succeeded: `return self.synchronized_data, Event.DONE_WITH_WARNINGS` (or just `Event.DONE` for Alpha).
    *   If critical data sources reported "FAILURE": `return self.synchronized_data, Event.FETCH_FAILED`
    *   If an internal error occurred or timeout: `return self.synchronized_data, Event.ERROR` or `Event.TIMEOUT`.

## 5. Outputs

### 5.1. Data written to `SynchronizedData` (by `DataCollectionRound`):
*   **`raw_market_data_sources`**: (List[Dict]) A list where each dictionary represents a data source's fetch attempt:
    ```json
    [
        {
            "protocol_name": "Fluid",
            "chain_id": 42161,
            "source_type": "API",
            "status": "SUCCESS",
            "collection_time_utc": "2023-10-27T10:00:00Z",
            "raw_data": { /* ... actual JSON data from Fluid API ... */ },
            "error_message": null
        },
        {
            "protocol_name": "AAVE_V3_Arbitrum",
            "chain_id": 42161,
            "source_type": "SUBGRAPH",
            "status": "FAILURE",
            "collection_time_utc": "2023-10-27T10:00:05Z",
            "raw_data": null,
            "error_message": "Subgraph request timed out after 3 retries."
        }
        // ... more entries for other protocols
    ]
    ```
*   **`last_successful_collection_utc`**: (Timestamp) Overall timestamp for the cycle.
*   **`data_collection_cycle_status`**: (String: e.g., "COMPLETED", "PARTIAL_FAILURE")

### 5.2. FSM Events (from `DataCollectionRound`):
*   `Event.DONE`: Data collection successful (or sufficiently successful).
*   `Event.DONE_WITH_WARNINGS`: Data collection completed, but some non-critical sources might have failed.
*   `Event.FETCH_FAILED`: Critical data source(s) failed.
*   `Event.ERROR`: Internal error in the round/behaviour.
*   `Event.TIMEOUT`: Round execution exceeded `collection_round_timeout_seconds`.

## 6. Interactions with Other Rounds/Behaviours

*   **Receives Control From:** Typically `ResetRound` or an initial `RegistrationRound`. Can also be re-triggered by a monitoring round if a data refresh is needed.
*   **Passes Control To:**
    *   `PreprocessingRound` (on `Event.DONE` or `Event.DONE_WITH_WARNINGS`).
    *   An Error Handling Round or back to `ResetRound` (on `Event.FETCH_FAILED`, `Event.ERROR`, `Event.TIMEOUT`).

## 7. TODOs & Open Questions

*   **`TODO`**: Apply the GraphQL query strings for each target subgraph (AAVE, Compound, Dolomite, Silo) and store them in the skill's configuration (e.g., `params.graphql_queries`). Ensure queries fetch all fields needed for the **Unified Schema** and subsequent APY/risk calculations.
*   **`TODO`**: Document the official rate limits for the Fluid API `/v2/{chainId}/vaults` endpoint to refine retry strategies.
*   **`TODO`**: Determine the FSM cycle time. This will directly influence the effective data collection interval. If specific sources need faster updates than the main FSM cycle, a separate, faster-looping background FSM or a specialized round might be needed (consider for post-Alpha).
*   **`TODO`**: Implement the `DataCollectionBehaviour` including concurrent asynchronous fetching for all configured sources using `yield from self.get_http_response()`, robust retry logic, and error handling for each source.
*   **`TODO`**: Implement the `DataCollectionPayload` class.
*   **`TODO`**: Implement the `DataCollectionRound` class, including the logic for processing submitted payloads (consensus strategy if multiple agents) and updating `SynchronizedData`. Define the FSM `Event` enum.
*   **`TODO`**: Establish a clear definition of "critical" vs. "non-critical" data sources to determine transitions (e.g., `Event.DONE` vs. `Event.FETCH_FAILED`). This should be configurable.
*   **`TODO`**: Confirm if all necessary token price data (e.g., `inputTokenPriceUSD`) is reliably available directly from the primary market data queries. If not, design the logic for supplementary price oracle calls (either within this behaviour or in Preprocessing).
*   **`TODO`**: Ensure secure handling and access of `api_keys` within the skill, loaded from service/agent configuration.
*   **`TODO`**: Update `skill.yaml` examples to show how `target_protocols_config`, `graphql_queries`, and other parameters for this round would be structured.

