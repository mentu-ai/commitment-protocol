# Protocol Invariants

**Version**: 2.2
**Status**: Stable

---

## Overview

Five invariants govern every operation on the ledger. Break any one and the system's guarantees fail.

---

## 1. Append-Only

Signals are never updated or deleted.

Once written, a signal exists forever. Corrections are new signals — a `contradicts` relation, not an edit. Retractions are new signals — an `annotate` with `kind: "retraction"`, not a deletion.

This is what makes the ledger an audit trail. If entries can change, history is negotiable.

---

## 2. Merkle Integrity

Every hashed signal's `prevHash` resolves to the `hash` of an earlier hashed row.

The chain starts at genesis (64 zeros) and grows with every append. Integrity is
defined by **canonical ancestry**, not line adjacency: each append links to the
head the writer read under an exclusive lock, so interleaved rows from concurrent
writers or the out-of-chain lane mean the linked head is often not the previous
line. A conforming implementation MUST verify the chain on read.

```
signal[0].prevHash = "0000...0000"         # genesis, OR a prior-file head on import
signal[k].prevHash ∈ { hash of some earlier hashed row }
```

A **break** — a non-genesis, non-`session_anchor` `prevHash` that resolves to no
earlier hashed row — is `E_CHAIN_BROKEN` (tampering or truncation). A **fork**
(two rows sharing one parent) is a legitimate concurrency artifact on a shared
ledger and is not a break. The engine keys its append lock on the symlink-resolved
real ledger path, so one physical ledger has one writer lock. Unhashed rows are
the out-of-chain lane (grandfathered before a `lane_cutover` marker). See
[LEDGER.md](./LEDGER.md) §Chain integrity for the full classification, the typed
`session_anchor` / `lane_cutover` markers, and the reference verifier.

The hash excludes `hash` and `prevHash` from its own computation. See [LEDGER.md](./LEDGER.md) for the algorithm.

---

## 3. Citation Gate (K1)

Signals of kind `finding`, `step_result`, or `learning` MUST have at least one entry in `trace.parent`.

Evidence must cite its source. A finding without provenance is an assertion, not evidence. An implementation MUST reject signals of these kinds that lack a parent reference.

**Why:** Without citation, the graph has no edges. Without edges, there is no provenance traversal, no contradiction detection, no trust propagation. The citation gate is what makes the ledger epistemically useful, not just a log.

**Execution lane (v2.2):** `model_call` and `tool_call` signals link to the step
that made them via `run_id` + the step label (they live on the CIR lane, keyed to
the run). Should such a signal ever be written to the chained ledger directly, it
too MUST carry `trace.parent` naming the step's claim/commitment. See
[LEDGER.md](./LEDGER.md) §Execution Lane.

---

## 4. Mechanical Trust

Trust scores derive from observation, not self-report.

An agent cannot declare `confidence: 0.95` on its own output. The seven-weight model computes confidence from exit codes, test results, context utilization, completion signals, duration, and evidence depth. See [TRUST.md](./TRUST.md).

**Why:** Self-reported trust is meaningless. A confident hallucination scores itself highly. Mechanical trust removes the agent from its own evaluation.

---

## 5. Read-Before-Act (RECOMMENDED)

Query prior evidence before acting.

An agent without epistemic context is epistemically blind — it may contradict existing evidence, duplicate completed work, or ignore known constraints. This invariant is RECOMMENDED, not REQUIRED. Enforcement is implementation-specific.

**Why:** The value of the ledger scales with how much it is read. A ledger that is only written to is a log. A ledger that is read before every action is a substrate.

---

## 6. Inputs Are Events

Content injected into an execution primitive — content the primitive did not
derive from the ledger itself — MUST be recorded as a signal before it is
consumed.

The canonical case is **mid-run steering**: a steer message (in Mentu, `mentu steer`)
alters the model input of the next step or beat. Recording only that a steer
occurred (a count) is not enough; the message *content* changed what the agent
saw, so the content is durable evidence. An implementation MUST append the full
steer text as a hashed signal (`payload.kind: "steer_message"`) before folding it
into the step's context.

**Why:** Without this the run is not auditable ("what did this step actually
see?") and not soundly replayable — a steered step whose input was destroyed
after consumption cannot be reproduced. Steering is the "rule change mid-run"
case; the protocol's answer is that a rule change is itself an event. Gate
decisions, human decisions, and injected context briefs are governed by the same
invariant; where an implementation already records those as signals it satisfies
Invariant 6 for them.

Recording happens at a boundary (step or beat start), never mid-flight, and a
ledger failure MUST NOT abort the running work (warn and proceed) — availability
of the run outranks completeness of the audit at this boundary.

---

## Enforcement

| Invariant | Level | Failure |
|-----------|-------|---------|
| Append-only | MUST | Implementation rejects mutations |
| Merkle integrity | MUST | `E_CHAIN_BROKEN` on verification failure |
| Citation gate (K1) | MUST | `E_CITATION_REQUIRED` on applicable kinds |
| Mechanical trust | MUST | Implementation computes trust, rejects self-reported values |
| Read-before-act | SHOULD | Implementation logs warning on blind writes |
| Inputs are events | MUST | Injected content recorded as a signal before consumption |

---

*Five rules. The ledger is only as strong as its weakest invariant.*
