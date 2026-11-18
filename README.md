# CortensorOps — OpenMinion 0.1 DePIN Node & Inference Audit Copilot

**Hackathon Submission:** Cortensor Hackathon #5 (`$1,150` Prize Pool)  
**Runtime:** `openminion` `0.1.23` Python SDK (`Agent`, `APIRuntime`, `@tool`, `OpenMinionConfig`, `AgentOutputValidationError`)  
**License:** Apache-2.0

---

## 1. Overview & OpenMinion SDK Workflow
**CortensorOps** is a reproducible, local-first AI operations agent built on the **OpenMinion 0.1 Python SDK** for auditing Cortensor decentralized GPU miner nodes and Proof-of-Inference (PoI) execution receipts.

### Workflow Architecture
```
[ CortensorOps CLI / Script ]
            │
            ▼
[ OpenMinion APIRuntime (agents.json) ] ──► [ SQLite Session & Memory Store ]
            │
            ├──► Turn 1: Agent(..., output_type=NodeAuditSummary, forced_tools=["inspect_cortensor_node"])
            │       ├──► READ_ONLY Tool (auto-approved by action_policy)
            │       └──► Pydantic Validation (NodeAuditSummary)
            │
            └──► Turn 2: Agent(..., forced_tools=["archive_audit_receipt"])
                    ├──► Write-Scoped Tool ──► Operator approval_callback Gate
                    └──► Persists audit_logs/miner-sol-gpu-042_receipt.json
```

---

## 2. Quick Setup & Reproducible Run (Zero Secrets Required)
1. Clone repository & install `openminion` (`>=0.1.23`):
   ```bash
   pip install -r requirements.txt
   ```
2. Run the full end-to-end model-backed workflow (starts a local OpenAI-compatible Cortensor inference server on `127.0.0.1:11435` so judges can run and verify tool calls + Pydantic validation with zero external API keys):
   ```bash
   python cortensor_ops_agent.py
   ```
   *(To point at a live Cortensor Router/Portal instead, export `CORTENSOR_API_KEY` and select the `cortensor` provider preset in `agents.json`.)*
3. Run automated unit + integration tests:
   ```bash
   python -m unittest discover -s tests -v
   ```

---

## 3. Building Blocks Tested
| OpenMinion Building Block | How Exercised in CortensorOps | Result |
| :--- | :--- | :--- |
| **Agent Execution & APIRuntime** | Shared `APIRuntime.from_config_path("agents.json")` across multi-turn `Agent` runs | **Worked cleanly** — clean lifecycle start/shutdown |
| **Structured Tools (`@tool`)** | Registered `READ_ONLY` tools (`inspect_cortensor_node`, `verify_poi_receipt`) and write tool (`archive_audit_receipt`) | **Worked cleanly** — Pydantic args validated automatically |
| **Action Policy & Approval Gates** | `allow_read_only_without_prompt: true` vs `approval_callback` for write tool | **Worked cleanly** — READ_ONLY ran silently; write tool fired `approval_callback` with `approval_id` |
| **Typed Structured Output (`output_type`)** | `NodeAuditSummary(BaseModel)` validated on Turn 1 | **Worked cleanly** — caught invalid non-JSON with `AgentOutputValidationError` |
| **Sessions & SQLite Storage** | Reused `session_id="cortensor-audit-session-01"` across Turn 1 and Turn 2 | **Worked cleanly** — Alembic auto-applied 10 SQLite migrations (`v10_capture_bundle_receipts`) |
| **Diagnostics & CLI (`status readiness`)** | Tested `openminion config init --provider echo`, `openminion run`, and `openminion status readiness` | **Worked cleanly** — reported `overall=demo checks=8 blocked=0` |

---

## 4. What We Learned (Actionable Product Feedback for OpenMinion)
Real engineering findings observed while testing `openminion 0.1.23` on Windows (Python 3.14):

1. **Multi-step Internal LLM Sub-calls During a Single `Agent.run()` Turn:**
   - During a single `Agent.run()` turn with `forced_tools` + `output_type`, OpenMinion dispatches multiple HTTP `/chat/completions` calls (context composition, tool execution, and final formatting). Local mock/test harnesses or custom routers must inspect the current-turn slice after the latest `user` message rather than assuming 1 HTTP request per turn.
2. **Helpful `ProviderError` & `AgentOutputValidationError` Ergonomics:**
   - Explicit exception hierarchy (`AgentOutputValidationError.raw_text`) immediately exposed why malformed output failed Pydantic parsing without silent swallowing.
3. **Lazy Root Imports vs Missing Dependency Errors:**
   - Root `openminion/__init__.py` uses `_LAZY_EXPORTS`, so `import openminion` succeeds even if runtime dependencies (`sqlalchemy`, `alembic`) are missing, deferring `ModuleNotFoundError` until `openminion.Agent` is accessed. Adding a fast preflight dependency check in `openminion doctor` or import hints improves onboarding.
4. **Windows Path & Stderr Logging:**
   - When isolating workspace state via `OPENMINION_HOME` / `OPENMINION_DATA_ROOT`, `openminion` emits `INFO` logs to `stderr`, which causes PowerShell `2>&1` pipelines with `$ErrorActionPreference` strict wrappers to treat `INFO` lines as non-zero remote exceptions unless directed to a log file. Supporting `--quiet` or structured JSON logging on SDK runtime initialization would streamline CI/CD pipelines.
