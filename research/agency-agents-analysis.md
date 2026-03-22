# agency-agents Repository Analysis

Analysis of [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) for claude-code-toolkit coverage gaps and novel patterns.

## Repo Overview

**Repository**: msitarzewski/agency-agents (MIT License)
**Description**: "A complete AI agency at your fingertips" -- a community-driven collection of AI agent personalities organized into divisions, designed primarily for Claude Code but with conversion scripts for Cursor, Aider, Windsurf, Gemini CLI, OpenCode, and others.

**Structure**: Agents are organized into category directories (not a flat `agents/` folder like ours):
- `engineering/`, `design/`, `marketing/`, `sales/`, `product/`, `project-management/`, `testing/`, `support/`, `spatial-computing/`, `specialized/`, `game-development/`, `academic/`, `paid-media/`

**Philosophy**: Personality-driven agents with "strong character and voice." Each agent has identity, mission, critical rules, deliverables, and communication style. The emphasis is on breadth of domain coverage and human-like persona.

**Orchestration**: A `strategy/` directory contains the NEXUS operating model -- a seven-phase pipeline (Discover, Strategize, Scaffold, Build, Harden, Launch, Operate) with quality gates, agent coordination matrix, and handoff protocols. The `specialized/agents-orchestrator.md` agent manages dev-QA loops.

**Quality enforcement**: A bash lint script (`scripts/lint-agents.sh`) validates YAML frontmatter (name, description, color required) and checks for recommended sections (Identity, Core Mission, Critical Rules). Minimal compared to our deterministic scoring pipeline.

---

## Architecture Comparison

| Dimension | agency-agents | claude-code-toolkit |
|-----------|--------------|---------------------|
| **Agent structure** | YAML frontmatter (name, description, color, emoji, vibe) + markdown body | YAML frontmatter (name, version, description, color, hooks, routing, memory) + markdown body |
| **Context depth** | Medium -- Identity, Mission, Critical Rules, Deliverables, Communication Style | High -- Operator context, hardcoded/default/optional behaviors, phase gates, anti-patterns, error handling, reference files, retro topics |
| **Routing** | None in agent files; NEXUS strategy doc describes manual activation | Built into frontmatter: `routing.triggers`, `routing.pairs_with`, `routing.complexity`, `routing.category` |
| **Skill pairing** | None -- agents are standalone | Agents pair with methodology skills via `pairs_with` |
| **Hooks** | None in agent files | PostToolUse hooks embedded in frontmatter (e.g., go-agent suggests `go vet` after build) |
| **Learning integration** | "Memory" section describes what to remember (aspirational) | SQLite + FTS5 retro knowledge injection, confidence scoring, graduation pipeline |
| **Validation** | Bash lint script (frontmatter + section presence) | Deterministic component scoring (20-point rubric), LLM evaluation, 3-wave review |
| **Orchestration** | NEXUS 7-phase pipeline in strategy docs; Agents Orchestrator agent | Pipeline-first architecture with gates, artifacts, parallelization; `/do` router |
| **Personality** | Strong -- each agent has a distinct voice, persona, and communication style | Functional -- operator context focuses on behaviors and constraints, not persona |
| **Breadth** | Very wide -- sales, marketing, game dev, academic, spatial computing, paid media | Focused -- engineering, DevOps, review, research, documentation |

### Key Architectural Differences

1. **Low-context vs. high-context**: Their agents lack routing metadata, hooks, version fields, retro-topic integration, and behavior classification (hardcoded/default/optional). They compensate with personality and broader domain coverage.

2. **Personality vs. procedure**: Their agents invest heavily in persona ("You are...") and communication style. Our agents invest in operational procedure (phase gates, anti-patterns, error handling checklists).

3. **Breadth vs. depth**: They cover ~144 domains with medium-depth agents (2-26 KB each). We cover fewer domains but with deeper operational context per agent.

4. **Orchestration model**: Their NEXUS is a document-level strategy (humans read and follow it). Our `/do` router and pipeline orchestrator are executable infrastructure (routing happens automatically).

---

## Agent-by-Agent Classification

### Engineering Division

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| Frontend Developer | React/Vue/Angular UI | ~9 KB | Already covered | Our `typescript-frontend-engineer` and `react-portfolio-engineer` cover this |
| Backend Architect | API design, DB architecture | ~10 KB | Already covered | Our `nodejs-api-engineer` + `database-engineer` cover this |
| Mobile App Builder | iOS/Android, React Native | ~10 KB | Gap filler | We have no mobile development agent |
| AI Engineer | ML models, deployment | ~10 KB | Gap filler | We have no ML/AI engineering agent |
| DevOps Automator | CI/CD, cloud ops | ~13 KB | Already covered | Our `ansible-automation-engineer` + `kubernetes-helm-engineer` cover this |
| Rapid Prototyper | Fast POC, MVPs | ~8 KB | Low value | Too generic -- "build fast" is not a specialization |
| Senior Developer | Laravel/Livewire | ~10 KB | Low value | Framework-specific, not relevant to our stack |
| Security Engineer | Threat modeling, secure code | ~12 KB | Already covered | Our `reviewer-security` covers code security review |
| Autonomous Optimization Architect | LLM routing, cost optimization | ~12 KB | Novel pattern | Interesting domain: optimizing LLM API selection and cost |
| Embedded Firmware Engineer | Bare-metal, RTOS, ESP32/STM32 | ~12 KB | Gap filler | We have no embedded/IoT agent |
| Incident Response Commander | Incident management | ~10 KB | Gap filler | We have no incident response agent |
| Solidity Smart Contract Engineer | EVM, DeFi | ~10 KB | Low value | Niche blockchain domain |
| Technical Writer | Developer docs, tutorials | ~8 KB | Already covered | Our `technical-documentation-engineer` covers this |
| Threat Detection Engineer | SIEM, ATT&CK mapping | ~10 KB | Gap filler | Security operations domain we don't cover |
| WeChat Mini Program Developer | WeChat ecosystem | ~10 KB | Low value | China-market specific |
| Code Reviewer | Constructive PR reviews | ~3 KB | Already covered | We have 20+ specialized reviewer agents |
| Database Optimizer | Schema, query optimization | ~8 KB | Already covered | Our `database-engineer` covers this |
| Git Workflow Master | Branching, conventional commits | ~4 KB | Already covered | Git workflow is built into our CLAUDE.md |
| Software Architect | System design, DDD | ~4 KB | Already covered | Covered across multiple agents |
| SRE | SLOs, error budgets, chaos eng | ~4 KB | Novel pattern | SLO/error budget framework is well-structured |
| AI Data Remediation Engineer | Self-healing pipelines | ~10 KB | Gap filler | Interesting niche: data remediation at scale |
| Data Engineer | Pipelines, lakehouse | ~8 KB | Already covered | Our `data-engineer` covers this |
| Feishu Integration Developer | Feishu/Lark platform | ~10 KB | Low value | China-market specific |

### Design Division

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| UI Designer | Visual design, component libraries | ~10 KB | Already covered | Our `ui-design-engineer` covers this |
| UX Researcher | User testing, behavior analysis | ~10 KB | Gap filler | We have no UX research agent |
| UX Architect | CSS systems, implementation | ~10 KB | Already covered | Covered by our frontend agents |
| Brand Guardian | Brand identity, consistency | ~8 KB | Low value | Non-engineering domain |
| Visual Storyteller | Visual narratives | ~8 KB | Low value | Non-engineering domain |
| Whimsy Injector | Personality, delight, micro-interactions | ~16 KB | Novel pattern | Unique concept: systematic delight injection |
| Image Prompt Engineer | AI image generation prompts | ~8 KB | Low value | Prompt engineering for image generation |
| Inclusive Visuals Specialist | Representation, bias mitigation | ~10 KB | Low value | Non-engineering domain |

### Testing Division

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| Evidence Collector | Screenshot-based QA | ~8 KB | Novel pattern | Evidence-based QA with visual proof requirements |
| Reality Checker | Production readiness gates | ~10 KB | Novel pattern | "Default to NEEDS WORK" anti-fantasy-approval pattern |
| Test Results Analyzer | Test evaluation, metrics | ~8 KB | Already covered | Our `reviewer-test-analyzer` covers this |
| Performance Benchmarker | Load testing, performance | ~10 KB | Already covered | Our `performance-optimization-engineer` covers this |
| API Tester | API validation | ~8 KB | Already covered | Our `reviewer-api-contract` covers this |
| Tool Evaluator | Technology assessment | ~8 KB | Low value | Too generic |
| Workflow Optimizer | Process analysis | ~8 KB | Low value | Too generic |
| Accessibility Auditor | WCAG, assistive tech | ~15 KB | Gap filler | We have no accessibility testing agent |

### Product Division

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| Sprint Prioritizer | Agile planning | ~8 KB | Low value | Non-engineering domain |
| Trend Researcher | Market intelligence | ~8 KB | Already covered | Our `research-coordinator-engineer` covers research |
| Feedback Synthesizer | User feedback analysis | ~8 KB | Low value | Non-engineering domain |
| Behavioral Nudge Engine | Behavioral psychology | ~5 KB | Novel pattern | Interesting: behavioral science applied to UX |
| Product Manager | Full lifecycle PM | ~23 KB | Low value | Non-engineering domain; their largest agent |

### Sales Division (8 agents)

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| All 8 agents | Sales methodology | 8-14 KB each | Low value | Entirely non-engineering; sales coaching, pipeline analysis, proposals |

**Exception**: Discovery Coach (~14 KB) has a genuinely excellent Socratic questioning framework (SPIN, Gap Selling, Sandler) that could inform how we structure diagnostic/debugging skills. Worth studying as a **novel pattern** for methodology transfer, not as an agent to adopt.

### Marketing Division (27 agents)

| Classification | Notes |
|----------------|-------|
| All: Low value | Non-engineering domain. Heavy China-market focus (Xiaohongshu, WeChat, Douyin, Baidu, Bilibili, Kuaishou, Weibo, Zhihu). Reddit Community Builder is well-written but marketing-focused. |

### Paid Media Division (7 agents)

| Classification | Notes |
|----------------|-------|
| All: Low value | Non-engineering domain. PPC, ad creative, programmatic buying. |

### Project Management Division (6 agents)

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| Studio Producer | Portfolio management | ~10 KB | Low value | Non-engineering |
| Project Shepherd | Cross-functional coordination | ~10 KB | Already covered | Our `project-coordinator-engineer` covers this |
| Senior Project Manager | Spec-to-task conversion | ~10 KB | Low value | Non-engineering |
| Jira Workflow Steward | Git-Jira discipline | ~8 KB | Low value | Tool-specific |
| Others | Operations, experiments | ~8 KB each | Low value | Non-engineering |

### Support Division (6 agents)

| Classification | Notes |
|----------------|-------|
| All: Low value | Customer support, finance, legal compliance. Non-engineering. |

### Spatial Computing Division (6 agents)

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| visionOS Spatial Engineer | Apple Vision Pro | ~10 KB | Gap filler | Novel platform, no equivalent |
| XR Interface Architect | Spatial UX | ~10 KB | Low value | Too niche for general toolkit |
| macOS Spatial/Metal Engineer | Swift, Metal, 3D | ~10 KB | Low value | Too niche |
| Others | WebXR, cockpit controls, terminal | ~8 KB each | Low value | Too niche |

### Game Development Division (18 agents)

| Classification | Notes |
|----------------|-------|
| Mostly: Low value | Engine-specific agents (Unity, Unreal, Godot, Roblox, Blender). Not relevant to our engineering focus. |

**Exception**: Game Designer (~8 KB) has an excellent **gameplay loop framework** (moment-to-moment, session, long-term) that could inform how we think about developer experience loops. Worth studying as a **novel pattern**.

### Academic Division (5 agents)

| Classification | Notes |
|----------------|-------|
| All: Low value | Scholarly agents for world-building (Anthropologist, Geographer, Historian, Narratologist, Psychologist). Creative writing support. |

**Exception**: Narratologist (~7 KB) has strong framework-grounded analysis (Propp, Campbell, Genette, Barthes). Demonstrates how to cite theoretical frameworks in agent instructions. Worth studying as a **novel pattern** for methodology grounding.

### Specialized Division (27 agents)

| Agent | Domain | Size | Classification | Notes |
|-------|--------|------|----------------|-------|
| Agents Orchestrator | Pipeline management | ~16 KB | Already covered | Our `pipeline-orchestrator-engineer` covers this |
| LSP/Index Engineer | LSP, code intelligence | ~11 KB | Gap filler | Unique: building semantic code graphs |
| MCP Builder | MCP server development | ~3 KB | Already covered | Our `mcp-local-docs-engineer` covers this |
| Workflow Architect | Workflow mapping | ~26 KB | Novel pattern | Their deepest agent -- exhaustive workflow discovery methodology |
| ZK Steward | Zettelkasten knowledge mgmt | ~11 KB | Novel pattern | Luhmann-inspired knowledge base management |
| Model QA Specialist | ML model auditing | ~12 KB | Gap filler | Comprehensive ML audit framework |
| Compliance Auditor | SOC 2, ISO, HIPAA | ~10 KB | Gap filler | We have no compliance agent |
| Agentic Identity & Trust | Agent authentication | ~10 KB | Novel pattern | Multi-agent identity and trust verification |
| Document Generator | PDF, PPTX, DOCX from code | ~8 KB | Low value | Utility agent |
| Automation Governance Architect | n8n, workflow auditing | ~10 KB | Low value | Tool-specific |
| Blockchain Security Auditor | Smart contract audits | ~10 KB | Low value | Niche |
| Others | Various business domains | 8-10 KB each | Low value | Non-engineering (recruitment, supply chain, training, etc.) |

---

## Summary Classification

| Classification | Count | Percentage |
|---------------|-------|------------|
| Already covered | ~25 | ~17% |
| Gap filler | ~12 | ~8% |
| Novel pattern | ~10 | ~7% |
| Low value | ~97 | ~68% |

The majority of agents are in non-engineering domains (sales, marketing, paid media, game development, academic) that fall outside our toolkit's scope.

---

## Detailed Analysis: Gap Fillers

### 1. Accessibility Auditor
**What they have**: WCAG 2.1/2.2 compliance testing, screen reader testing methodology, ARIA pattern validation, color contrast checking, keyboard navigation testing.
**What we lack**: No accessibility-focused reviewer or testing agent.
**Adaptation needed**: Convert personality-driven format to high-context with reviewer behavior patterns (hardcoded: must cite WCAG criteria; default: test with screen reader; optional: color contrast ratios). Add as a reviewer agent in our 3-wave review system.
**Effort**: Low -- their content is solid, needs structural conversion.
**Recommendation**: **Adopt** as `reviewer-accessibility.md` in Wave 1 or Wave 2.

### 2. Incident Response Commander
**What they have**: Incident severity classification, communication templates, post-mortem frameworks, runbook patterns.
**What we lack**: No incident response workflow.
**Adaptation needed**: Convert to skill rather than agent. Incident response is a methodology (like debugging), not a domain specialty.
**Effort**: Medium -- needs restructuring from agent to skill format.
**Recommendation**: **Study** -- consider as a skill if we expand into production operations.

### 3. Mobile App Builder
**What they have**: React Native/Flutter patterns, platform-specific considerations, app store deployment.
**What we lack**: No mobile development agent.
**Adaptation needed**: Full high-context conversion with routing triggers, skill pairing, hooks.
**Effort**: Medium -- their content is generic; would need framework-specific depth.
**Recommendation**: **Skip** for now -- create only when a user needs mobile development support.

### 4. AI Engineer / Model QA Specialist
**What they have**: ML pipeline design (AI Engineer), comprehensive model audit framework with PSI, SHAP, calibration testing (Model QA).
**What we lack**: No ML/AI development or QA agents.
**Adaptation needed**: High-context conversion. Model QA is particularly strong and could become a reviewer agent.
**Effort**: Medium for AI Engineer, Low for Model QA (already well-structured).
**Recommendation**: **Study** AI Engineer. **Adopt** Model QA patterns if we add ML support.

### 5. Compliance Auditor
**What they have**: SOC 2, ISO 27001, HIPAA, PCI-DSS frameworks. Evidence collection, control mapping, gap analysis.
**What we lack**: No compliance-focused agent.
**Adaptation needed**: Convert to high-context with compliance-specific routing triggers.
**Effort**: Medium -- solid content but needs our structural format.
**Recommendation**: **Study** -- adopt when compliance work arises.

### 6. LSP/Index Engineer
**What they have**: Multi-language LSP client orchestration, semantic graph construction, performance contracts.
**What we lack**: No code intelligence or LSP-focused agent. Highly relevant to developer tooling.
**Adaptation needed**: Full high-context conversion with routing, hooks, and gopls integration awareness.
**Effort**: Medium -- niche but well-specified.
**Recommendation**: **Study** -- relevant if we build code intelligence features.

---

## Detailed Analysis: Novel Patterns

### 1. Workflow Architect (~26 KB) -- Most Valuable Discovery
**What's novel**: The most thorough agent in their entire repo. A four-view workflow registry (by Workflow, by Component, by User Journey, by State) that ensures every path through a system is mapped before code is written. The "Missing" status concept (workflow exists in code but has no spec = liability) is powerful.
**What we can learn**: The workflow registry structure could inform a skill for system design reviews. The four-view cross-referencing pattern (component -> workflows, user journey -> workflows, state -> workflows) is a genuinely novel contribution.
**Adaptation**: Create a `workflow-mapping` skill using their registry structure as a template.
**Effort**: Medium.
**Recommendation**: **Adopt the registry pattern** as a skill template for system design reviews.

### 2. Reality Checker -- "Default to NEEDS WORK"
**What's novel**: The explicit anti-fantasy-approval stance. "No more 98/100 ratings for basic dark themes." Automatic fail triggers for perfect scores, zero-issues claims, or production-ready certifications without evidence. Default to skepticism.
**What we can learn**: We already have `reviewer-skeptical-senior` and `reviewer-contrarian`, but their "automatic fail triggers" list is a useful pattern: specific conditions that invalidate a review result regardless of other findings.
**Adaptation**: Add automatic-fail-trigger patterns to our review aggregation.
**Effort**: Low.
**Recommendation**: **Study** for integration into review pipeline.

### 3. Evidence Collector -- Visual Proof Requirements
**What's novel**: Screenshot-based QA with mandatory visual evidence for every claim. Not "I checked and it works" but "here is the screenshot proving it works." Evidence hierarchy: automated screenshots > manual screenshots > text descriptions.
**What we can learn**: Evidence requirements as a structural constraint, not a suggestion. Could enhance our review pipeline's artifact requirements.
**Adaptation**: Add evidence-requirement patterns to testing/review skills.
**Effort**: Low.
**Recommendation**: **Study** for review pipeline enhancement.

### 4. ZK Steward -- Zettelkasten for Knowledge Management
**What's novel**: Luhmann's Zettelkasten principles applied to AI knowledge management. Four-principle validation gate (Atomicity, Connectivity, Organic growth, Continued dialogue). Expert-switching based on domain (Feynman for physics, Munger for analysis). Note linking and registry maintenance.
**What we can learn**: The validation gate concept (four binary checks before a knowledge artifact is accepted) could inform our learning graduation pipeline. The "connectivity" check (does this learning connect to at least 2 others?) is particularly useful for detecting isolated learnings.
**Adaptation**: Add connectivity checks to learning graduation criteria.
**Effort**: Low.
**Recommendation**: **Study** for learning pipeline enhancement.

### 5. SRE -- SLO/Error Budget Framework
**What's novel**: Well-structured SLO definition format with burn-rate alerts. "Error budgets fund velocity -- spend them wisely." The framing of reliability as a budget rather than a target is a useful mental model.
**What we can learn**: The SLO YAML template and golden signals framework are good reference material for production operations work.
**Adaptation**: Could inform an SRE skill or monitoring agent.
**Effort**: Low.
**Recommendation**: **Study** as reference material.

### 6. Behavioral Nudge Engine -- Psychology in UX
**What's novel**: Applying behavioral psychology (cognitive load reduction, default biases, momentum building, variable-reward loops) to software interaction design. The "never show 50 tasks, show the 1 most critical" principle.
**What we can learn**: The micro-sprint pattern and cognitive load awareness could inform how our agents present information to users (e.g., review findings prioritization).
**Adaptation**: Not an agent to adopt, but principles to study for our agent communication patterns.
**Effort**: N/A.
**Recommendation**: **Study** for UX principles in agent output design.

### 7. Discovery Coach -- Socratic Questioning Framework
**What's novel**: Three complementary frameworks (SPIN, Gap Selling, Sandler) for structured questioning. The insight that "Implication questions do the heavy lifting because they activate loss aversion" is directly applicable to debugging methodologies.
**What we can learn**: The question escalation pattern (Situation -> Problem -> Implication -> Need-Payoff) maps directly to debugging (Context -> Symptom -> Impact -> Resolution). Could enhance our `systematic-debugging` skill.
**Adaptation**: Extract the questioning framework and apply to diagnostic skills.
**Effort**: Low.
**Recommendation**: **Study** for debugging skill enhancement.

### 8. Agentic Identity & Trust Architect
**What's novel**: Addresses multi-agent identity, authentication, and trust verification. As agent ecosystems grow, this becomes increasingly relevant.
**What we can learn**: Trust verification patterns for multi-agent coordination.
**Adaptation**: Relevant if we build multi-agent orchestration features.
**Effort**: Medium.
**Recommendation**: **Study** for future multi-agent work.

### 9. NEXUS Operating Model (strategy/ directory)
**What's novel**: A comprehensive multi-agent orchestration doctrine with seven phases, quality gates, agent coordination matrix, handoff protocols, and three deployment modes (Full, Sprint, Micro). More prescriptive than our pipeline architecture.
**What we can learn**: The activation modes concept (Full/Sprint/Micro) for right-sizing pipeline complexity to task size. Their handoff protocol templates are well-structured.
**Adaptation**: The activation modes concept could inform our pipeline architecture.
**Effort**: Low to study, Medium to adopt.
**Recommendation**: **Study** the activation modes and handoff protocols.

---

## Recommended Adoptions

### Immediate (Low Effort, Clear Value)

1. **Accessibility Reviewer Agent** -- Convert their Accessibility Auditor into a `reviewer-accessibility.md` for our review pipeline. WCAG compliance checking is a genuine gap.

2. **Workflow Registry Pattern** -- Extract the four-view registry concept from Workflow Architect into a skill template for system design reviews.

### Study for Future Integration

3. **Automatic Fail Triggers** -- From Reality Checker. Add to review aggregation: specific conditions that invalidate a review regardless of other scores.

4. **Connectivity Checks for Learnings** -- From ZK Steward. Require learnings to connect to at least 2 existing learnings before graduation.

5. **Questioning Framework for Debugging** -- From Discovery Coach. The SPIN escalation pattern adapted for diagnostic workflows.

6. **Evidence Requirements** -- From Evidence Collector. Structural requirement for proof artifacts in review and testing pipelines.

### Skip (Not Relevant to Our Scope)

- All sales, marketing, paid media, game development, academic, and support agents
- China-market-specific agents (WeChat, Douyin, Xiaohongshu, Baidu, etc.)
- Laravel/Senior Developer (framework-specific)
- Blockchain/Solidity agents

---

## Key Takeaways

1. **Breadth vs. depth trade-off confirmed**: Their repo validates our hypothesis. They have ~144 agents across 12 divisions, but most are medium-depth personality prompts without routing, hooks, learning integration, or deterministic validation. Our smaller set of high-context agents with operational infrastructure is a fundamentally different architecture.

2. **Personality is not depth**: Their agents have strong personas ("You are Backend Architect, a senior architect who...") but lack the operational infrastructure that makes agents effective in practice: routing triggers, skill pairing, PostToolUse hooks, retro knowledge injection, behavior classification.

3. **Non-engineering domains dominate**: ~68% of their agents cover domains outside our scope (sales, marketing, game dev, etc.). This makes the repo look large but most content is irrelevant to engineering-focused toolkits.

4. **Orchestration philosophy differs**: Their NEXUS model is documentation-as-strategy (humans read and follow the plan). Our pipeline architecture is infrastructure-as-strategy (routing and gates execute automatically). Both have merit, but ours is more deterministic.

5. **Genuine contributions exist**: The Workflow Architect's four-view registry, the Reality Checker's anti-fantasy-approval stance, the ZK Steward's knowledge validation gates, and the Discovery Coach's questioning frameworks are genuinely novel patterns worth studying regardless of agent architecture.

6. **Conversion cost is real**: Converting a low-context agent to high-context requires adding routing metadata, hook definitions, behavior classification, anti-patterns, phase gates, error handling, reference files, and retro topics. This typically doubles or triples the content size and requires domain expertise to do well. Adopting agents should be demand-driven, not speculative.
