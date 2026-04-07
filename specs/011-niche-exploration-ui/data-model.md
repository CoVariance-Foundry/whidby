# Data Model: Niche Finder Exploration Interface

## Entities

### 1) NicheQuery

- **Purpose**: Canonical input shared across standard and exploration surfaces.
- **Fields**:
  - `query_id` (string): Unique request/session query identifier
  - `city_input` (string): User-provided city text
  - `service_input` (string): User-provided service text
  - `normalized_city` (string): Normalized city token used for scoring parity
  - `normalized_service` (string): Normalized service token used for scoring parity
  - `requested_at` (datetime): Submission timestamp
- **Validation Rules**:
  - `city_input` and `service_input` are required and non-empty
  - Normalized fields must be derived before score retrieval
- **Relationships**:
  - One `NicheQuery` has one or more `ScoreResult` entries (by mode/run)
  - One `NicheQuery` belongs to one `ExplorationSession`

### 2) ScoreResult

- **Purpose**: Canonical score output displayed on both surfaces.
- **Fields**:
  - `score_id` (string): Unique score record ID
  - `query_id` (string): Reference to `NicheQuery`
  - `opportunity_score` (number): Composite score value
  - `classification_label` (string): Human-readable score class
  - `generated_at` (datetime): Score generation timestamp
  - `surface` (enum): `standard` or `exploration`
- **Validation Rules**:
  - `opportunity_score` must be numeric and bounded by existing scoring contract
  - `surface` is required for parity comparison audits
- **Relationships**:
  - One `ScoreResult` is supported by zero or more `EvidenceRecord` entries

### 3) EvidenceRecord

- **Purpose**: Raw or derived evidence shown for score transparency.
- **Fields**:
  - `evidence_id` (string): Unique evidence item ID
  - `query_id` (string): Reference to `NicheQuery`
  - `category` (string): Evidence class (for example, demand, competition, monetization, resilience)
  - `label` (string): User-facing evidence label
  - `value` (string | number | boolean): Evidence value shown in UI
  - `source` (string): Origin of evidence data
  - `is_available` (boolean): Explicit missing/available marker
- **Validation Rules**:
  - `category`, `label`, and `source` are required
  - Missing evidence must set `is_available=false` with a user-visible fallback message
- **Relationships**:
  - Many `EvidenceRecord` entries map to one `ScoreResult` through shared `query_id`

### 4) ExplorationSession

- **Purpose**: Tracks user context while switching between surfaces and follow-up queries.
- **Fields**:
  - `session_id` (string): Session identifier
  - `active_query_id` (string): Current query in context
  - `started_at` (datetime): Session start time
  - `last_updated_at` (datetime): Last interaction timestamp
  - `surface_state` (enum): `standard` or `exploration`
- **Validation Rules**:
  - `active_query_id` must always reference an existing `NicheQuery`
  - Session transitions must preserve query context when switching surfaces
- **Relationships**:
  - One `ExplorationSession` has many `AssistantExplorationResponse` entries

### 5) AssistantExplorationResponse

- **Purpose**: Represents follow-up assistant output for deeper exploration.
- **Fields**:
  - `response_id` (string): Unique response ID
  - `session_id` (string): Reference to `ExplorationSession`
  - `query_id` (string): Reference to `NicheQuery`
  - `prompt_text` (string): User’s follow-up question
  - `response_text` (string): Assistant answer
  - `evidence_refs` (array[string]): Referenced evidence IDs/categories
  - `status` (enum): `success`, `partial`, `unsupported`
  - `responded_at` (datetime): Response timestamp
- **Validation Rules**:
  - `prompt_text` and `response_text` are required
  - `status=unsupported` must include next-step guidance in `response_text`
- **Relationships**:
  - Many responses belong to one `ExplorationSession` and one `NicheQuery`

## State Transitions

1. User creates `NicheQuery` from city/service input.
2. System generates `ScoreResult` for standard or exploration surface.
3. Exploration path enriches score with `EvidenceRecord` entries.
4. User asks follow-up question; system appends `AssistantExplorationResponse`.
5. Session remains active with preserved `active_query_id` across surface switches.
