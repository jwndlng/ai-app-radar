# llm-cli Specification

## Purpose
Defines the LLM invocation layer (`BaseAgent`) used by all flows that call an LLM backend. Covers the class interface and JSON extraction strategies.

## Requirements

### Requirement: Class-based BaseAgent interface
The LLM invocation layer SHALL be exposed as a class `BaseAgent` in `src/core/agent.py`. It uses pydantic-ai's `run_sync()` (synchronous) and `run()` (async) methods. All internal helpers SHALL remain module-private.

#### Scenario: Caller instantiates and calls synchronously
- **WHEN** a caller invokes `run_sync()` on the agent
- **THEN** the pydantic-ai backend is invoked synchronously and a result is returned

#### Scenario: Caller instantiates and calls asynchronously
- **WHEN** a caller invokes `await run()` on the agent
- **THEN** the pydantic-ai backend is invoked asynchronously and a result is returned

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
Retry logic (if any) is handled at the pydantic-ai / caller level, not inside `BaseAgent` itself.

