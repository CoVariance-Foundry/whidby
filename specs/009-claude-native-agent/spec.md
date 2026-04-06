# Feature Specification: Claude-Native Research Agent with Plugin Registry and Real Experiment Runner

**Feature Branch**: `009-claude-native-agent`
**Created**: 2026-04-04
**Status**: Draft
**Input**: User description: "Replace the dead LangChain/DeepAgents orchestration with a Claude-native tool-use agent built on the Anthropic Python SDK. Build a Python plugin registry so DataForSEO, MetroDB, LLM, and scoring tools are modular and loadable. Implement a real experiment runner that leverages the existing M5 (collect_data), M6 (extract_signals), and M7 (compute_batch_scores) pipeline to produce real candidate scores. Support two experiment modes: fast (parameter-only re-scoring via M7, zero API cost) and full (data refresh via M5/M6/M7 with real DataForSEO cost tracking). Remove unused deepagents/langgraph/langchain dependencies. Keep the Ralph loop, memory stores, hypothesis generator, evaluator, recommender, and all API/UI surfaces unchanged."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a Real Scoring Experiment (Priority: P1)

A scoring engine developer wants to test whether adjusting a scoring parameter (e.g. domain authority ceiling, review count barrier) actually improves the composite opportunity score across metros. Today the experiment runner is a stub that returns zero deltas, making the entire research loop inert. The developer needs experiments that produce real, comparable candidate scores so the loop can validate or invalidate hypotheses with actual evidence.

**Why this priority**: This is the core value unlock. Without real experiments, the research agent cannot fulfill its primary purpose of improving the scoring algorithm. Every other capability (plugin system, agent reasoning) exists to support this outcome.

**Independent Test**: Can be tested by running a research session with demo scoring data and verifying that experiment results contain non-zero candidate scores, meaningful score deltas, and accurate cost tracking.

**Acceptance Scenarios**:

1. **Given** a hypothesis that modifies only scoring parameters (e.g. "lower DA ceiling from 60 to 50"), **When** an experiment runs, **Then** the system re-scores the baseline data with modified parameters and returns candidate scores with real per-proxy values and a composite opportunity score for each metro.
2. **Given** a hypothesis that requires fresh data collection (e.g. "expand keyword set"), **When** an experiment runs, **Then** the system gathers new data, extracts signals, scores the result, and returns candidate scores with an accurate cumulative API cost in USD.
3. **Given** a completed experiment with positive score deltas, **When** the research loop evaluates it, **Then** the hypothesis is marked "validated" and promoted to the knowledge graph with the real delta as confidence weight.
4. **Given** a completed experiment with negative or zero score deltas, **When** the research loop evaluates it, **Then** the hypothesis is marked "invalidated" and the learning is recorded with per-proxy breakdown.

---

### User Story 2 - Modular Tool Registration (Priority: P2)

A developer extending the research agent wants to add a new data source (e.g. a new API, a custom analysis function) without modifying the core agent loop. They need a plugin system where tools are self-contained modules that declare their capabilities and can be loaded, swapped, or disabled independently.

**Why this priority**: Modularity enables team velocity and experimentation. Without it, adding any new tool requires modifying the agent core, increasing coupling and regression risk. This is the architectural foundation that makes the agent extensible.

**Independent Test**: Can be tested by creating a minimal test plugin that registers a single tool, loading it into the registry, and verifying the agent can discover and execute that tool.

**Acceptance Scenarios**:

1. **Given** a new tool plugin module, **When** it is registered with the plugin registry, **Then** its tools become available to the agent for invocation without any changes to the agent core.
2. **Given** the existing DataForSEO, MetroDB, LLM, and scoring capabilities, **When** the system starts, **Then** each is loaded as a separate plugin with independently discoverable tools.
3. **Given** a plugin that fails to load (e.g. missing credentials), **When** the registry initializes, **Then** other plugins still load successfully and the failure is logged with a clear error message.

---

### User Story 3 - AI-Powered Experiment Reasoning (Priority: P3)

A scoring engine developer wants the research agent to intelligently decide which tools to call and in what order when running an experiment, rather than following a hardcoded sequence. For example, given a hypothesis about review count barriers, the agent should reason that it needs to fetch review data for the target metros, extract local competition signals, and re-score -- without the developer specifying these steps manually.

**Why this priority**: This differentiates the system from a simple scripted pipeline. AI-powered reasoning allows the agent to handle novel hypothesis types without code changes and to optimize data gathering (e.g. skip unnecessary API calls). However, the system provides value even with deterministic tool selection (P1 + P2), making this an enhancement.

**Independent Test**: Can be tested by providing the agent with a hypothesis and verifying it selects appropriate tools, calls them in a reasonable order, and produces a valid experiment result without explicit tool-call instructions.

**Acceptance Scenarios**:

1. **Given** a hypothesis targeting a specific scoring proxy, **When** the agent plans its experiment, **Then** it selects only the tools relevant to that proxy's signals (e.g. review data tools for local competition, SERP tools for organic competition).
2. **Given** a budget constraint, **When** the agent is mid-experiment, **Then** it tracks cumulative tool costs and stops gracefully if the budget would be exceeded by the next tool call.
3. **Given** a tool call that fails (e.g. API timeout), **When** the agent encounters the error, **Then** it logs the failure, decides whether to retry or skip, and continues the experiment with available data.

---

### User Story 4 - Dependency Cleanup (Priority: P4)

A developer maintaining the project wants to remove unused dependencies that add install complexity, binary compatibility issues (especially on Apple Silicon), and security surface area. The LangChain/DeepAgents dependencies are entirely dead code and should be removed.

**Why this priority**: Reduces install time, eliminates ARM64/x86 binary mismatch issues in Docker, and shrinks the attack surface. Low effort, high hygiene value, but does not directly deliver user-facing functionality.

**Independent Test**: Can be tested by removing the dependencies, running the full test suite, and verifying all tests pass. Then building the Docker image and confirming it starts successfully.

**Acceptance Scenarios**:

1. **Given** the unused LangChain-related dependencies are removed, **When** the full unit test suite runs, **Then** all tests pass without import errors.
2. **Given** the Docker image is rebuilt without the removed dependencies, **When** the API starts, **Then** all endpoints respond correctly.

---

### Edge Cases

- What happens when the DataForSEO API returns an error (rate limit, auth failure, timeout) during a full-mode experiment? The system should record partial results, mark the experiment as failed, and allow the loop to continue with the next hypothesis.
- What happens when baseline signal data is missing or incomplete for a fast-mode experiment? The system should fall back to full mode (gather fresh data) or mark the hypothesis as un-testable.
- What happens when the budget is exceeded mid-experiment (e.g. a single data collection call uses most of the remaining budget)? The system should complete the current tool call, record accumulated cost, and let the loop's budget check prevent the next iteration.
- What happens when a plugin declares a tool with a name that conflicts with another plugin's tool? The registry should detect the collision at load time and raise a clear error.
- What happens when no plugins are registered? The agent should report that no tools are available and the experiment cannot proceed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a plugin registry where tool capabilities are registered as self-contained modules with declared names, descriptions, and input/output schemas.
- **FR-002**: The system MUST include plugins for the existing DataForSEO data gathering, geographic scope expansion, keyword/intent classification, and scoring pipeline capabilities.
- **FR-003**: The system MUST provide an AI-powered agent that reasons about which tools to call and in what order to execute a given experiment, using the registered plugin tools.
- **FR-004**: The system MUST support a "fast mode" experiment path where only scoring parameters are modified and the scoring pipeline is re-run without external API calls, producing candidate scores at zero cost.
- **FR-005**: The system MUST support a "full mode" experiment path where fresh data is gathered via external APIs, signals are extracted, and scoring is performed, with accurate cumulative API cost tracking.
- **FR-006**: Experiment results MUST contain per-metro candidate scores with both the composite opportunity score and individual proxy dimension scores (demand, organic competition, local competition, monetization, AI resilience).
- **FR-007**: Experiment results MUST include the total cost in USD incurred during the experiment.
- **FR-008**: The system MUST remove all unused orchestration framework dependencies that are not called by any live code path.
- **FR-009**: The agent MUST respect the session budget limit and stop making cost-incurring tool calls when the budget would be exceeded.
- **FR-010**: Plugin loading failures MUST be isolated -- a single plugin failure must not prevent other plugins from loading or the system from starting.
- **FR-011**: The system MUST log all tool invocations with their inputs, outputs, cost, and latency for auditability.
- **FR-012**: All existing API endpoints, CLI commands, and dashboard proxy routes MUST continue to function without changes to their request/response contracts.

### Key Entities

- **Plugin**: A self-contained module that declares one or more tools with their names, descriptions, and input schemas. Responsible for executing tool calls and returning structured results.
- **Plugin Registry**: The central catalog of all loaded plugins and their tools. Resolves tool names to the appropriate plugin for execution. Enforces uniqueness of tool names across plugins.
- **Agent**: The AI reasoning component that receives a hypothesis and baseline data, decides which tools to invoke, executes them via the registry, and assembles the experiment result.
- **Experiment Result**: The output of a single experiment run. Contains candidate scores per metro, cumulative API cost, parameter modifications applied, and any tool call logs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Research sessions produce experiments with non-zero score deltas -- at least 60% of experiments in a demo session must produce a measurable (non-zero) composite score change.
- **SC-002**: Fast-mode experiments (parameter-only) complete in under 5 seconds and report zero API cost.
- **SC-003**: Full-mode experiments report accurate API cost that matches the sum of individual tool call costs to within 1%.
- **SC-004**: The plugin registry loads all default plugins (DataForSEO, MetroDB, LLM, Scoring) successfully on system startup, verified by a health check or startup log.
- **SC-005**: Removing unused dependencies reduces the install footprint -- the Docker image builds successfully without the removed packages and all unit tests pass.
- **SC-006**: The agent selects contextually appropriate tools for a given hypothesis type at least 80% of the time (validated via unit tests with representative hypothesis types).
- **SC-007**: All existing API endpoints return the same response shapes as before the change, verified by the existing test suite passing without modification.

## Assumptions

- The existing M5 (data collection), M6 (signal extraction), and M7 (scoring) pipeline modules are stable and their public interfaces will not change during this feature's development.
- DataForSEO API credentials are available in the environment for full-mode experiments; fast-mode experiments work without any API credentials.
- The existing Ralph loop, hypothesis generator, experiment planner, evaluator, and recommender modules are correct and do not need modification -- only the experiment runner callback is replaced.
- The existing FilesystemStore and ResearchGraphStore persistence layers handle the new experiment result data without schema changes (they accept arbitrary dicts).
- The agent's AI reasoning operates within the existing session budget constraints (default $50 USD) and does not require additional cost controls beyond what the loop already provides.
- The Docker build environment supports the remaining dependencies after cleanup (no new binary compatibility issues introduced).
