# Citations

Patterns, repos, and sources that shaped the toolkit. This includes external influences and original innovations developed through trial and error. Keeping provenance clear helps future sessions understand why things work the way they do.

## Repos

### caliber-ai-org/ai-setup
https://github.com/caliber-ai-org/ai-setup

TypeScript CLI that fingerprints projects and generates AI configs for Claude, Cursor, Codex, and GitHub Copilot. Studied for its deterministic scoring system, learning ROI tracking, and multi-platform writer abstraction.

**Patterns adopted:**
- Deterministic component scoring without LLM calls (ADR-031). Their 6-dimension scoring rubric for config quality proved that mechanical validation catches a class of errors LLM evaluation misses entirely.
- Learning staleness detection (ADR-033). Flagging learnings with zero activations over N sessions as prune candidates.
- PID-based lockfile with staleness detection (ADR-035). Their concurrent access pattern for preventing data corruption in shared files.
- Score regression guard concept (ADR-034). Comparing quality before and after changes, auto-reverting if score drops.

**Patterns noted but not adopted:**
- Token budget scoring (penalizing configs over 2000 tokens). Conflicts with our high-context agent philosophy.
- Multi-platform config generation (Claude + Cursor + Codex writers). We're Claude Code focused.
- Session event JSONL format for learning capture. Our SQLite + FTS5 approach serves better for search and graduation.

### Convergent Evolution

Repos that independently built similar routing patterns to our `/do` router. Discovered during ADR-040 landscape research (2026-03-22).

#### SethGammon/Citadel
https://github.com/SethGammon/Citadel

Agent orchestration harness for Claude Code with four-tier routing via `/do`. Routes by operational complexity (Skill -> Marshal -> Archon -> Fleet) rather than by domain. Built from running 198 autonomous agents across 32 fleet sessions.

**Routing mechanism:** Tier-based escalation ladder. `/do` classifies intent and dispatches to the "cheapest capable path." Tasks auto-escalate only when necessary.

**Patterns noted:**
- Four-tier escalation model (route by scale, not just domain) is orthogonal to our approach and could complement it
- Campaign persistence via markdown files for multi-session work survival
- Circuit breaker pattern (escalate after 3 tool failures)
- Fleet coordination with discovery compression (~500 tokens) relayed between parallel agent waves

#### userFRM/agent-dispatch
https://github.com/userFRM/agent-dispatch

Lightweight keyword-to-agent dispatch using a compact TOML index (~2k tokens). Just-in-time agent download mid-session from GitHub repos.

**Routing mechanism:** TOML keyword index maps keywords to agent names and categories. Agents fetched on demand rather than pre-installed.

**Patterns noted:**
- JIT download pattern solves context budget problem differently than load-on-trigger
- Platform-agnostic design (Claude Code, OpenClaw, Cursor, Codex) via environment variable abstraction
- Compact index format as alternative to our routing table embedded in skill markdown

#### anthroos/claude-code-orchestrator
https://github.com/anthroos/claude-code-orchestrator

Skill-based orchestration with a dispatcher that matches trigger phrases in SKILL.md frontmatter to route and chain skills sequentially.

**Routing mechanism:** Mapping table matches user requests against "When to use" trigger phrases. Multi-skill chaining for compound requests.

**Patterns noted:**
- Symlink bridge pattern (git repo with categorized skills, symlinked to flat discovery directory)
- Explicit multi-skill sequencing from a single user request
- Path variable abstraction for cross-machine portability

#### lst97/claude-code-sub-agents
https://github.com/lst97/claude-code-sub-agents

33 specialized subagents with an agent-organizer that performs project analysis and assembles minimal 1-3 agent teams per task.

**Routing mechanism:** Context-based auto-delegation via keyword/file-type detection, task classification, and domain expertise matching.

**Patterns noted:**
- Selective dispatching philosophy (minimal team, not maximum coverage) mirrors our Handyman Principle
- Honest trade-off documentation (acknowledges 2-5x token usage for comprehensive analysis)

#### carlrannaberg/claudekit
https://github.com/carlrannaberg/claudekit

Toolkit with 6-parallel code review agents, intelligent delegation based on file types, and invisible context injection via codebase mapping.

**Routing mechanism:** File-type and analysis-scope based agent delegation. Multi-agent research with breadth-first/depth-first strategy classification.

**Patterns noted:**
- Invisible context injection (codebase map injected transparently without user awareness)
- Session-based temporary hook control (disable per session without permanent config changes)
- 195+ security patterns across 12 categories for sensitive file protection

#### cexll/myclaude
https://github.com/cexll/myclaude

Multi-agent orchestration with intelligent routing across multiple backends (Codex, Claude, Gemini, OpenCode). Uses `/do` as entry point.

**Routing mechanism:** Two-tier orchestration. Claude Code orchestrates; codeagent-wrapper executes across backends. SPARV and BMAD methodologies for structured workflows.

**Patterns noted:**
- Backend-agnostic execution across multiple AI coding agents
- SPARV workflow (Specify -> Plan -> Act -> Review -> Vault) with explicit archive phase
- Configuration-driven module enable/disable

### Novel Patterns

Repos with architecturally distinct ideas worth studying. Discovered during ADR-040 landscape research (2026-03-22).

#### BugRoger/beastmode
https://github.com/BugRoger/beastmode

Referenced as prior art for the retro knowledge system. Our implementation has diverged significantly from this approach.

**Patterns noted:**
- Original inspiration for session-level learning and knowledge accumulation concepts
- Our implementation (SQLite + FTS5, confidence scoring, graduation pipeline) bears little resemblance to the current state of beastmode
- Layered autonomy model (individually configurable trust per gate type, progressive from supervised to autonomous)
- Phase-based workflow gates (/design -> /plan -> /implement -> /validate -> /release)

#### parcadei/Continuous-Claude-v3
https://github.com/parcadei/Continuous-Claude-v3

Context management system with daemon-driven learning extraction, pgvector semantic recall, and 5-layer code analysis that reduces token consumption by 95%.

**Routing mechanism:** Natural language activation via hook-injected context. Prioritized skill suggestions (CRITICAL, RECOMMENDED, SUGGESTED) rather than deterministic keyword matching.

**Patterns noted:**
- Daemon-driven post-session learning extraction (headless Claude instances extract thinking blocks after sessions end)
- 5-layer TLDR code analysis (AST, call graphs, control flow, data flow, program dependence graphs) for radical token reduction
- "Compound, don't compact" philosophy aligns with our PreCompact hook but goes further with structured YAML handoffs
- BGE embeddings into PostgreSQL + pgvector for semantic recall

#### ShunsukeHayashi/agent-skill-bus
https://github.com/ShunsukeHayashi/agent-skill-bus

Self-improving task orchestration with DAG-based task queue, automatic skill quality monitoring, and external change detection. Framework-agnostic.

**Routing mechanism:** DAG-based task queue with topological sorting for dependency resolution. File-level locking with TTL-based deadlock prevention.

**Patterns noted:**
- Self-improving skill loop (OBSERVE -> ANALYZE -> DIAGNOSE -> PROPOSE -> EVALUATE -> APPLY -> RECORD) claimed 57% reduction in skill failures
- Three-tier knowledge watcher monitoring dependency versions, community patterns, and industry trends at different cadences
- Execution scoring (0.0-1.0) with anomaly detection through trend analysis
- Framework-agnostic design (OpenClaw, Claude Code, Codex, LangGraph, CrewAI)

#### jayminwest/overstory
https://github.com/jayminwest/overstory

Multi-agent orchestration with SQLite-based inter-agent mail, pluggable runtime adapters, and FIFO merge queue with 4-tier conflict resolution.

**Routing mechanism:** Persistent Coordinator agent decomposes objectives and dispatches via SQLite mail system. Capability-based routing with declared roles and access levels.

**Patterns noted:**
- SQLite inter-agent mail system (WAL mode, ~1-5ms per query) replacing pub/sub with durable offline messaging
- FIFO merge queue with 4-tier conflict resolution for integrating parallel agent work
- Multi-tier watchdog (mechanical daemon + AI triage + monitor agent) for fleet health
- Runtime-agnostic through pluggable adapters (Claude Code, Sapling, Pi, Cursor, Codex, Gemini, OpenCode)
- Honest warning about compounding error rates as the normal case in multi-agent systems

#### ruvnet/ruflo
https://github.com/ruvnet/ruflo

Enterprise-scale agent orchestration with Q-Learning router, Mixture of Experts classification, HNSW vector memory, and knowledge graphs.

**Routing mechanism:** Q-Learning Router + 8-expert MoE with cosine similarity matching. Claims 89% accuracy in agent selection. Supports hierarchical, mesh, ring, and star topologies.

**Patterns noted:**
- ML-based routing (Q-Learning + MoE) as the philosophical opposite of our deterministic keyword matching
- HNSW vector memory with sub-millisecond retrieval and EWC++ preventing catastrophic forgetting
- Agent Booster (WASM) that skips LLM calls for simple code transforms, claimed 352x faster
- 5 consensus algorithms (Raft, Byzantine, Gossip, CRDT, weighted voting) for multi-agent coordination

#### wshobson/agents
https://github.com/wshobson/agents

Plugin-based multi-agent system with 72 plugins, three-tier progressive disclosure for skills, and strategic model assignment across tiers.

**Routing mechanism:** Plugin-specific slash commands. Conductor plugin for structured workflows. Agent Teams for parallel multi-agent execution with preset configurations.

**Patterns noted:**
- Three-tier progressive disclosure for skills (metadata always loaded, instructions on activation, resources on demand) -- more granular than our binary loading
- Four-tier model assignment strategy (Opus for critical, inherit for complex, Sonnet for support, Haiku for operational)
- Plugin architecture that bundles agents + commands + skills into installable units

#### SuperClaude-Org/SuperClaude_Framework
https://github.com/SuperClaude-Org/SuperClaude_Framework

Meta-programming framework that transforms Claude Code through behavioral instruction injection. 7 behavioral modes, ReflexionMemory, and Deep Research with multi-hop reasoning.

**Routing mechanism:** Implicit context-based agent activation. Behavioral modes modify Claude's operating style rather than loading different agents.

**Patterns noted:**
- Behavioral modes as an alternative to agent switching (Token-Efficiency, Deep Research, Orchestration modes)
- ReflexionMemory for error learning and case-based pattern recognition across sessions
- Deep Research with multi-hop reasoning, adaptive strategies, and confidence thresholds (min 0.6, target 0.8)

### Model Routers

Repos that route at the API/model level rather than the agent/skill level. Included for completeness but architecturally distinct from domain routing.

#### 0xrdan/claude-router
https://github.com/0xrdan/claude-router

Complexity-based model routing (Haiku/Sonnet/Opus) with hybrid classification: rule-based first, LLM fallback if uncertain.

**Routing mechanism:** Pattern matching for instant classification, escalating to Haiku-based evaluation for ambiguous requests. Token-optimized agent definitions.

**Patterns noted:**
- Hybrid classification (rules first, LLM fallback) could complement our deterministic keyword matching for ambiguous requests
- `/learn` command for extracting session insights into persistent knowledge -- conceptually similar to our retro system
- Opus Orchestrator that delegates subtasks to cheaper models for cost optimization

## Blog Posts

### vexjoy.com
https://vexjoy.com

The toolkit author's blog. Posts that crystallized design decisions:

- **Everything That Can Be Deterministic, Should Be** - The four-layer architecture (Router, Agent, Skill, Script) and the division of labor between LLMs and programs.
- **The /do Router** - Specialist selection over generalism. Why keyword-matching routing produces more consistent results than generalist improvisation.
- **The Handyman Principle** - Context as a scarce resource. Why specialized agents beat one giant system prompt.
- **I Was Excited to See Someone Else Build a /do Router** - Convergent evolution in AI tooling and the case for open sharing.

## Original Innovations

Patterns developed through trial and error in this toolkit, not derived from external sources.

### The /do Router and Specialist Selection
Keyword-matching routing to domain-specific agents. The insight that "which agent has the right mental scaffolding" matters more than "which agent is smartest." Developed over months of observing inconsistent results from generalist prompts.

### Anti-Rationalization as Infrastructure
Auto-injected anti-rationalization tables that make it structurally difficult to skip verification. Not a policy doc that gets ignored. Infrastructure that fires on every code modification, review, and security task. Born from repeated incidents where "should work" turned out to be wrong.

### Learning Graduation Pipeline
Record at 0.7 confidence, boost on validation, graduate into agent/skill markdown, ship together. The insight that review findings should be immediately embedded as permanent behavior changes, not passively recorded for "multiple observations." Developed after noticing that deferred learnings never got acted on.

### Three-Wave Comprehensive Review
20+ specialized reviewer agents in 3 cascading waves: per-package deep review (Wave 0), cross-cutting foundation (Wave 1, 11 agents), context-aware deep-dive (Wave 2, 10 agents). Each wave's findings enrich the next. Evolved from single-agent reviews that kept missing cross-cutting concerns.

### Pipeline-First Architecture
The principle that any task with 3+ phases should be a pipeline with gates, artifacts, and parallelization. Emerged from observing that ad-hoc execution skips steps under time pressure but pipelines with explicit phase gates don't.

### Two-Tier Evaluation (Deterministic + LLM)
Deterministic scoring (file existence, frontmatter validity, path checking) as a fast, free first pass, with LLM evaluation for nuanced quality. Neither replaces the other. Adopted after analyzing how mechanical failures wasted LLM evaluation tokens.

### Retro Knowledge Injection
SQLite + FTS5 database of operational learnings, auto-injected into relevant agent prompts via hook. Benchmarked at +5.3 avg score improvement, 67% win rate. The cross-session memory that makes each session smarter than the last.

### The Handyman Principle
"Context is a scarce resource, not a dumpster." Specialized agents loaded only when their triggers match, rather than one giant system prompt. Named and articulated through blog writing that forced clarity on why large prompts degrade performance.

### Manifest + Undo for Upgrades
SHA-256 snapshot before modification, backup storage, score regression detection, and rollback capability. Created after an upgrade broke agent references and required manual git archaeology to recover.

## Principles

### Claude Code Documentation
https://docs.anthropic.com/en/docs/claude-code

Official documentation for hooks, settings.json schema, slash commands, and MCP server configuration. The event-driven hook architecture (PostToolUse, UserPromptSubmit, SessionStart) is the foundation for error learning, retro knowledge injection, and auto-plan detection.

### Conventional Commits
https://www.conventionalcommits.org

Commit message format used throughout: `feat:`, `fix:`, `refactor:`, `docs:`. Enables automated changelog generation and semantic versioning.
