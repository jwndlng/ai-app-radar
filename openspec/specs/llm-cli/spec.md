# llm-cli Specification

## Purpose
Defines the LLM invocation layer (`LLMAgent`) used by all flows that call an LLM backend. Covers the class interface, retry behaviour, and agent-native short-circuit.

## Requirements

### Requirement: Class-based LLMAgent interface
The LLM invocation layer SHALL be exposed as a class `LLMAgent` in `src/common/agent.py`. It SHALL provide two public methods: `call(prompt, attempts, base_delay)` (synchronous) and `async_call(prompt, attempts, base_delay)` (async). All internal helpers SHALL remain module-private.

#### Scenario: Caller instantiates and calls synchronously
- **WHEN** a caller does `LLMAgent().call(prompt)`
- **THEN** the ADK backend is invoked synchronously and a parsed JSON dict (or None) is returned

#### Scenario: Caller instantiates and calls asynchronously
- **WHEN** a caller does `await LLMAgent().async_call(prompt)`
- **THEN** the ADK backend is invoked asynchronously and a parsed JSON dict (or None) is returned

### Requirement: Agent-native execution path
When the environment variable `CLAUDE_CODE_AGENT=1` is set, `LLMAgent.call` and `LLMAgent.async_call` SHALL return `None` immediately without invoking any backend. The calling command documentation SHALL instruct the agent to handle this case.

#### Scenario: Agent-native mode is active
- **WHEN** `CLAUDE_CODE_AGENT=1` is set in the environment
- **THEN** `LLMAgent.call` and `LLMAgent.async_call` SHALL return `None` immediately

#### Scenario: Headless mode (no flag set)
- **WHEN** `CLAUDE_CODE_AGENT` is not set or is not `"1"`
- **THEN** the ADK backend SHALL be used as normal

### Requirement: Multi-strategy JSON extraction
The `_extract_json` function SHALL attempt extraction in order: (1) markdown code fence, (2) direct `json.loads`, (3) regex `\{.*\}` with DOTALL, (4) single-quote normalisation on the regex result. It SHALL return the first successfully parsed result or `None` if all strategies fail.

#### Scenario: Model wraps JSON in a code fence
- **WHEN** the LLM output contains ` ```json\n{...}\n``` `
- **THEN** the JSON object SHALL be extracted and parsed correctly

#### Scenario: Model returns clean JSON
- **WHEN** the LLM output is a bare JSON object with no surrounding text
- **THEN** `json.loads` on the full output SHALL succeed and be returned

#### Scenario: Model returns JSON with explanatory preamble
- **WHEN** the LLM output contains prose before the JSON object
- **THEN** the regex strategy SHALL extract the JSON object

#### Scenario: All strategies fail
- **WHEN** the LLM output cannot be parsed as JSON by any strategy
- **THEN** `_extract_json` SHALL return `None`

### Requirement: Retry with exponential backoff
Both `LLMAgent.call` and `LLMAgent.async_call` SHALL retry up to 3 attempts on failure (API error or `None` JSON result), with a delay of `2 * 2^(attempt-1)` seconds between attempts. Each attempt SHALL be logged with its attempt number.

#### Scenario: Transient failure then success
- **WHEN** the first attempt fails and the second attempt succeeds
- **THEN** the successful result SHALL be returned and both attempt logs SHALL be emitted

#### Scenario: All retries exhausted
- **WHEN** all 3 attempts fail
- **THEN** `None` SHALL be returned and the final error SHALL be logged

