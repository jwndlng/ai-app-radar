# adk-backend Specification

## Purpose
Provides a Google ADK-based LLM backend that replaces the `gemini` subprocess path. Routes prompts through `google.adk.models.lite_llm.LiteLlm`, supporting any LiteLLM model string and optional self-hosted proxy configuration.

## Requirements

### Requirement: ADK backend executes prompts via Google ADK LiteLlm wrapper
When `LLM_BACKEND=adk` is set, the LLM CLI layer SHALL invoke the model using `google.adk.models.lite_llm.LiteLlm` instead of the `gemini` subprocess. The model is identified by the value of `ADK_MODEL`, which SHALL accept any LiteLLM model string (e.g. `gemini/gemini-2.5-flash`, `openai/gpt-4o`, `ollama/llama3`).

#### Scenario: ADK backend invoked with default Gemini model
- **WHEN** `LLM_BACKEND=adk` is set and `ADK_MODEL` is unset
- **THEN** the backend SHALL use `gemini/gemini-2.5-flash` as the model and call the Google API

#### Scenario: ADK backend invoked with a non-Gemini model string
- **WHEN** `LLM_BACKEND=adk` and `ADK_MODEL=openai/gpt-4o` are set
- **THEN** the backend SHALL route the call through LiteLLM to the OpenAI API

#### Scenario: ADK backend invoked pointing at a local LiteLLM proxy
- **WHEN** `LLM_BACKEND=adk`, `ADK_MODEL=ollama/llama3`, and `LITELLM_BASE_URL=http://localhost:4000` are set
- **THEN** the backend SHALL route the call to the local proxy and return parsed JSON on success

### Requirement: ADK backend model and proxy endpoint are configurable via environment variables
The ADK backend SHALL read the following env vars at call time:
- `ADK_MODEL` — LiteLLM model string; defaults to `gemini/gemini-2.5-flash`
- `LITELLM_BASE_URL` — base URL of a self-hosted LiteLLM proxy; optional
- `LITELLM_API_KEY` — API key for the proxy; optional

No other configuration files or code changes SHALL be required to switch models or endpoints.

#### Scenario: All env vars set
- **WHEN** `ADK_MODEL`, `LITELLM_BASE_URL`, and `LITELLM_API_KEY` are all set
- **THEN** the backend SHALL construct the `LiteLlm` instance with all three values and route accordingly

#### Scenario: Only `ADK_MODEL` set
- **WHEN** only `ADK_MODEL` is set and proxy vars are absent
- **THEN** the backend SHALL call the model directly via LiteLLM without proxy configuration

### Requirement: ADK backend returns parsed JSON using shared extraction logic
The ADK backend SHALL pass the prompt requesting a JSON response, then apply `_extract_json` to the model output. If the result is non-`None`, it SHALL be returned. If `None`, the attempt SHALL be logged and retried per the retry policy.

#### Scenario: Model returns clean JSON
- **WHEN** the model output is valid JSON
- **THEN** `_extract_json` SHALL return the parsed dict and the backend SHALL return it

#### Scenario: Model returns JSON in a markdown code fence
- **WHEN** the model wraps its JSON in ` ```json ... ``` `
- **THEN** `_extract_json` SHALL extract and return the parsed dict

#### Scenario: Model returns unparseable output
- **WHEN** `_extract_json` returns `None` after all strategies
- **THEN** the attempt SHALL be logged with the raw output (truncated to 500 chars) and the retry loop SHALL continue

### Requirement: ADK backend honours the agent-native sentinel
When `CLAUDE_CODE_AGENT=1` is set, the ADK backend path SHALL return `None` immediately, identical to the existing `gemini-cli` behaviour.

#### Scenario: Agent-native mode active with ADK backend selected
- **WHEN** both `CLAUDE_CODE_AGENT=1` and `LLM_BACKEND=adk` are set
- **THEN** the function SHALL return `None` without making any network call

### Requirement: Async ADK invocation is non-blocking
The async variant (`async_call_gemini_cli`) SHALL run the synchronous ADK SDK call via `_agent_call_async` in a thread executor so it does not block the event loop.

#### Scenario: Async path with ADK backend
- **WHEN** `async_call_gemini_cli` is called with `LLM_BACKEND=adk`
- **THEN** `_agent_call_async` SHALL dispatch the call via `loop.run_in_executor(None, ...)` and `await`-ed
