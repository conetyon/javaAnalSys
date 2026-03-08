## MODIFIED Requirements

### Requirement: AI Code Explanation
The system SHALL provide AI-powered code explanation for ALL matching result types.

#### Scenario: List mode explanation
- **WHEN** user clicks "AI 解释" on a list mode result card
- **THEN** the CodeExplainer component opens with correct snippet and KP context

#### Scenario: Matrix mode explanation
- **WHEN** user clicks "AI 解释" on a matrix mode result card (easy/medium/hard)
- **THEN** the CodeExplainer component opens with correct snippet and KP context

#### Scenario: Composite list mode explanation
- **WHEN** user clicks "AI 解释" on a composite list mode result card
- **THEN** the CodeExplainer component opens with the primary KP context

#### Scenario: Composite matrix mode explanation
- **WHEN** user clicks "AI 解释" on a composite matrix mode result card
- **THEN** the CodeExplainer component opens with the primary KP context

### Requirement: Prompt Completeness
The AI explanation prompt SHALL include complete knowledge point context.

#### Scenario: Knowledge point context in prompt
- **WHEN** ExplainService builds the system prompt
- **THEN** the prompt includes: kp.name, kp.name_zh, kp.keywords, kp.ast_template

#### Scenario: Code snippet context in prompt
- **WHEN** ExplainService builds the user prompt
- **THEN** the prompt includes: snippet.content, snippet.file_path (if available)

## ADDED Requirements

### Requirement: LLM Fallback Streaming
The system SHALL continue streaming content to frontend when switching to fallback endpoint.

#### Scenario: Fallback streaming continuity
- **WHEN** primary LLM endpoint fails mid-request
- **AND** system switches to fallback endpoint
- **THEN** fallback response chunks are streamed to frontend in real-time
- **AND** frontend displays content progressively (not blocked)

#### Scenario: Fallback error handling
- **WHEN** both primary and fallback endpoints fail
- **THEN** the system returns user-friendly error via SSE: `{"type": "error", "error": "..."}`
- **AND** frontend displays error message immediately

#### Scenario: Fallback transition logging
- **WHEN** system switches from primary to fallback
- **THEN** logs include: `[LLMClient] Fallback triggered`, fallback endpoint, model name

### Requirement: LLM Performance Monitoring
The system SHALL track and report LLM response performance metrics.

#### Scenario: Response time logging
- **WHEN** an AI explanation request completes
- **THEN** the system logs: total_time_ms, first_byte_time_ms, token_count

#### Scenario: Slow request detection
- **WHEN** an AI explanation request exceeds 30 seconds
- **THEN** the system logs a warning with request details
