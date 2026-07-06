# Changelog

## v2.2 — 2026-07-05 (protocol & ledger hardening)

Extends truth-by-replay from the commitment plane to the execution plane and
closes the ledger chain's two measured integrity holes. Backward compatible:
every v2.0/v2.1 ledger remains valid; new signal kinds and invariants are
additive and the hash algorithm is unchanged.

### Added
- **Chain integrity, canonical-ancestry** ([spec/LEDGER.md](spec/LEDGER.md) §Chain integrity, [spec/INVARIANTS.md](spec/INVARIANTS.md) §2): a `prevHash` is sound when it resolves to *any* earlier hashed row (not only the adjacent line). Rows classify as canonical/skip-link, genesis/import anchor, fork (concurrency artifact, non-fatal), break (missing ancestor, `E_CHAIN_BROKEN`), or out-of-chain lane. The reference verifier (`tools/verify_ledger.py`) was reconciled to this definition — on the live 12,186-signal ledger it now reports 0 breaks + 62 forks instead of 109 false "breaks", still 100% content integrity.
- **Typed chain markers** — `session_anchor` (documents an intentional re-anchor; head recorded in `semantic.entities[0]`) and `lane_cutover` (unhashed rows after it are chain violations). Emitted through the hashed merkle path via `mentu ledger anchor` / `mentu ledger cutover`.
- **Invariant 6 — Inputs Are Events** ([spec/INVARIANTS.md](spec/INVARIANTS.md) §6, [spec/EXECUTION.md](spec/EXECUTION.md) §Step): content injected into an execution primitive (starting with mid-run steer messages) MUST be recorded as a signal before consumption. New `steer_message` kind. The engine now writes the full steer text as a hashed ledger signal at both the sequence-step and loop-beat drain boundaries before folding it into context — a steered run is now auditable and replayable, not just counted.
- **Execution lane** ([spec/LEDGER.md](spec/LEDGER.md) §Execution Lane): new `model_call` / `tool_call` kinds record the engine's in-process model/tool calls as content-addressed events — `request_hash` over the canonical request keys a response blob at `.mentu/cache/model-responses/<hash>.json`; only the hash + `response_digest` enter the (chain-anchored) CIR signal, linked by `run_id` + step. The semantic gate and completion verifier are instrumented. Coverage boundary documented: a step's delegated child-agent process makes its own calls, which are out of lane (no child-process interception). Default on; `MENTU_NO_CALL_LANE=1` opts out.
- **Verification-replay** ([spec/PROTOCOL.md](spec/PROTOCOL.md) §Conformance / Run replay, new error `E_REPLAY_DIVERGED`): `mentu runs replay <runId> [--strict]` walks a run's recorded call lane and content-addressed blobs. Permissive reports coverage; strict recomputes each blob's digest against the recorded `response_digest` and exits non-zero at the first divergence (missing or mutated blob), naming the call. Read-only; a green strict replay is a proof about the recording's integrity and the mechanism that polices determinism. Wired as a non-blocking sequence-end advisory.
- **Fork lineage anchored in the chain** ([spec/LEDGER.md](spec/LEDGER.md) §Fork Lineage, [spec/EXECUTION.md](spec/EXECUTION.md) §Parallel): new `fork` kind records `{parent_run_id, fork_at_step, prefix_head_hash}` where `prefix_head_hash` is the chain head the fork branched from. Fork ancestry is now cryptographically verifiable against the shared chain, not mutable beacon metadata that can drift.
- **Projections discipline** ([spec/PROTOCOL.md](spec/PROTOCOL.md) §Projections): cached state is conformant only as a content-keyed projection that is discarded on key mismatch — the Sacred Invariant now names this explicitly. Fixes the stale-step-cache hazard: `StepStatus.cacheKey` records the inputs a completed step folds from, and resume + fork inheritance reuse a prior result only when a freshly recomputed key matches. Reuse by label alone is now non-conformant; pre-v2.2 keyless statuses re-run (the one-time migration cost).

- **Call-lane chain anchor** ([spec/LEDGER.md](spec/LEDGER.md) §Execution Lane): at sequence end a `call_lane` annotation carrying `manifest_sha256` anchors the run's out-of-chain manifest in the merkle chain; strict replay verifies the manifest against the anchor. Retention note added (blobs/manifests age-prunable; vacuum-cadence wiring is a named follow-up).

### Fixed
- **Concurrency-fork root cause** (engine `Ledger.appendPermissionless`): the append lock is now keyed by the symlink-*resolved* real ledger path, so all workspaces sharing one physical ledger contend on one lock. Per-symlink locking was the root cause of 108 historical chain forks.
- **Hook lane closed for real**: the three repo hook sources that still appended raw unhashed rows (`session-end.sh`, `pre-compact.sh`, `post-compact.sh`) now route through `mentu cir capture --ledger-anchor` (hashed merkle path); MCP telemetry moved off the signal ledger to `.mentu/mcp-telemetry.jsonl`; the `lane_cutover` marker is live (unhashed rows after it are chain violations).

## v2.1 — 2026-06-13

### Added
- **OKF profile** ([spec/OKF.md](spec/OKF.md)): the Open Knowledge Format (Andrej Karpathy's *LLM Wiki* and Google Cloud's *Open Knowledge Format*) with the `x-mentu` profile, which maps portable knowledge bundles onto the protocol's signal graph. Identity (`ns:type.slug`), trust (`level`/`decay`), five typed relations (`extends`, `supersedes`, `reinforces`, `constrains`, `balances_with`) mapping to protocol edges, and machine-readable twins.
- **Projection**: non-mutating, lossless import of a corpus that already uses its own frontmatter schema, deriving a parallel OKF bundle without rewriting the source.

## v2.0 — 2026-04-02

### Added
- **EpistemicSignal**: Unified signal type replaces Memory + Commitment as separate objects
- **Merkle chain**: SHA-256 hash chaining from genesis (64 zeros). Every signal links to the one before it.
- **Trust computation**: Seven-weight mechanical model, three confidence values (asserted, effective, current), temporal decay
- **Execution algebra**: Ten composable primitives (Step, Formula, Pipeline, Parallel, Compound, Adversarial, Convergent, Temporal, Sentinel, Substrate)
- **Typed relations**: `cites`, `extends`, `contradicts`, `refines` between signals
- **Observation levels**: `explicit`, `deductive`, `inductive`, `contradiction`
- **Semantic context**: Entities, intent, and domain tags on any signal
- **Sync scope**: `local`, `anonymous`, `full`, `cloud` per signal
- **Epistemic trace**: Parent/child causal links with causal depth
- **Invariants spec**: Append-only, Merkle integrity, citation gate (K1), mechanical trust, read-before-act
- **Trust spec**: Full specification of the seven-weight model and confidence lifecycle
- **Execution spec**: Ten primitives, composition algebra, embedding principle
- **CHANGELOG**: This file

### Changed
- **Operations**: Twelve → nine. `link`, `dismiss`, `triage` become annotation kinds.
- **Signal envelope**: Now includes `hash`, `prevHash`, `workspace`, optional `semantic`, `trust`, `trace`, `relations`, `observationLevel`, `sourceIds`, `syncScope`
- **Genesis Key**: Promoted from Draft to v1.0 Stable. Added `trust` section for weight overrides.
- **Agent instructions**: Added citation requirements, epistemic awareness, trust guidance
- **Sample ledger**: Full v2.0 signals with real SHA-256 hash chain
- **Workflow example**: Shows trust computation, hash chain growth, citation

### Backward Compatibility
- v1.0 ledgers are valid v2.0 ledgers. Missing fields default to null/empty.
- v1.0 operations `link`, `dismiss`, `triage` accepted as `annotate` with corresponding kind.
- `hash` and `prevHash` must be computed on v1.0 import.

## v1.0 — 2025-12-31

- Initial release
- Twelve operations: capture, commit, claim, release, close, annotate, submit, approve, reopen, link, dismiss, triage
- Two objects: Memory, Commitment
- JSONL ledger format
- Genesis Key (Draft)
- Agent instruction template
