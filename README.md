# HAR Reverse Engineering Platform

An experimental, network-layer intelligence engine designed to autonomously reverse-engineer internal APIs from browser telemetry (HAR files) and compile them into deterministic, zero-dependency Python executors. 

This platform bypasses DOM parsing and browser instantiation entirely, focusing exclusively on the underlying HTTP transport layer. By leveraging Large Language Models (LLMs) to construct execution schemas from minified network traces, it bridges the gap between probabilistic intelligence and deterministic code execution.

---

## Architecture

The platform is structured into four primary computational stages: Telemetry Distillation, Probabilistic Inference, Code Generation, and Deterministic Execution.

### 1. Telemetry Distillation (HAR Analyzer)
Raw HTTP Archive (.HAR) files export significant noise, including tracking pixels, CSS, web fonts, and multimedia payloads. Passing this directly to an LLM exceeds context windows horizontally and incurs prohibitive token costs.

The `HarAnalyzer` performs aggressive byte-to-token condensation:
*   **MIME Type Filtering:** Drops all responses corresponding to `image/*`, `video/*`, `font/*`, `application/javascript`, and `text/css`.
*   **Domain Exclusion:** Excludes cross-origin requests matching known analytics and CDN heuristics.
*   **Header Compression:** Strips browser telemetry (e.g., `sec-ch-ua`, `User-Agent`, pseudo-headers) while preserving critical cryptographic and authentication variables (`Authorization`, `x-csrf-token`, internal API keys).
*   **JSON Minification:** Parses and minifies large JSON response payloads, truncating them to 600 characters to provide just enough topological context for the LLM without bloating the prompt.
*   **Size-Ranked Sorting:** Orders the remaining candidate requests by response body size descending, maximizing the probability that the core data payload appears at the top of the LLM context frame.

### 2. Probabilistic Inference (AI Reverse Engineer)
The system injects the distilled HAR context and a natural-language target objective into an LLM constraint boundary utilizing standard JSON object extraction (compatible with OpenAI structured outputs or DeepSeek standard JSON mode).

The model acts as an autonomous security engineer. It is forced to conform strictly to a predefined Pydantic schema: `GeneratedEndpoint`. This bounds the probabilistic nature of the LLM: it cannot hallucinate unbounded text, but must specifically map out the target URL template, HTTP method, pagination cursors, interpolation tokens, and exact authentication headers required to construct a valid request signature.

### 3. Code Generation (Abstract Syntax Tree Construction)
Rather than simply returning a JSON metadata object, the platform transitions the schema into an executable runtime artifact. `GeneratedEndpoint.to_python_function()` renders the extracted parameters into a fully self-contained, valid Python asynchronous function.

*   **Variable Interpolation:** Embeds dynamically generated `{variable}` injection logic into the URL and JSON payload bodies.
*   **Pagination:** Conditionally generates query parameter mutation logic if a pagination cursor was detected by the LLM.
*   **Zero-Dependency Scope:** The generated module requires only standard `json`/`asyncio` and `httpx`.

### 4. Deterministic Execution
The engine bifurcates into two execution modes to cater to different operational risk profiles:

*   **Direct Replay Mode:** Uses the JSON schema fields to construct an `httpx.request` procedurally within the engine's memory space. It is strictly deterministic and perfectly safe from arbitrary code execution.
*   **Code Sandbox Mode:** Executes the LLM-generated Python string via an `exec()` runtime compilation step. This mirrors the execution paradigm of platforms like Parse.bot, allowing for complex data mutation or chaining logic embedded by the LLM before the final network transmission.

---

## System Dynamics: Probabilistic vs. Deterministic

The core design philosophy is the isolation of non-determinism to the initialization phase. 

In traditional AI agent frameworks (e.g., Playwright + Vision LLM), the LLM is in the hotpath of every execution. This incurs massive latency, token costs, and compounding failure probabilities on every run. 

In this architecture, the LLM is relegated exclusively to the "compile time" phase. It runs once per target to synthesize a deterministic network signature. All subsequent executions occur at "runtime," leveraging standard HTTP protocols without invoking the LLM, resulting in sub-second data retrieval with zero ongoing token cost.

---

## API Reference

### Generate Endpoint Map
`POST /api/v1/scrapers/generate`
Ingests a multipart encoded `.HAR` file and target objective. Performs the distillation and inference stages.
*   **Payload:** `har_file` (Binary), `goal` (String), `name` (String)
*   **Response:** JSON metadata containing the `GeneratedEndpoint` schema, confidence score, and the compiled standalone Python code.

### Execute Compiled Module
`POST /api/v1/scrapers/{id}/run`
Replays a stored endpoint map against the original target infrastructure.
*   **Payload:** `{"variables": {"search_term": "example"}, "use_code_execution": false}`
*   **Response:** The raw JSON output extracted directly from the target's internal infrastructure layer.

---

## Infrastructure Requirements

*   **PostgreSQL:** Handles persistence for generated endpoints, execution telemetry, and RBAC authentication bindings.
*   **Redis:** Serves as a high-speed inference cache and rate-limiting bucket backend. (Gracefully defaults to an in-memory dictionary cache if a socket connection fails).
*   **LLM Provider:** Provider-agnostic design. Automatically routes via `OPENAI_API_KEY` (compatible with `gpt-4o`) or `DEEPSEEK_API_KEY` utilizing the DeepSeek `v1/chat/completions` REST interface.

### Deployment

Dependencies are pinned in `requirements.txt`. The application serves via Uvicorn/FastAPI with integrated JWT-based Bearer token validation matching HS256 cryptographic standards. 

```bash
pip install -r app/requirements.txt
```

A `.env` configuration file is required at the root directory containing minimum infrastructure credentials. Note that the codebase leverages Pydantic V2 definitions; extra configuration variables supplied in the environment file will be gracefully ignored rather than invoking a schema crash.

### Quality Assurance

The system maintains a comprehensive pytest suite covering:
*   Byte-to-token filtration efficiency in `HarAnalyzer`.
*   Sanitization of standard tracking domains and cross-origin resource sharing calls.
*   Compilation validation of LLM-generated ASTs within `test_engine.py`, guaranteeing that generated modules strictly adhere to Python syntax rules regardless of the target network complexity.

To validate local modifications:
```bash
python -m pytest tests/ -v
```

---

## Future Research Implementations

*   **Regenerative Self-Healing:** Implementing a closed loop where failed deterministic executions (e.g., due to expired JWT/Session parameters) automatically trigger a Puppeteer-headless recapture sequence, regenerating a fresh HAR file and reinvoking the compilation stage entirely autonomously.
*   **Constraint Optimization:** Migrating away from standard JSON extraction into deterministic constrained-grammar generation (e.g., using `llama.cpp` grammar rules) to structurally guarantee 100% schema compliance for local edge models.