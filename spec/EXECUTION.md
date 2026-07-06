# Execution Algebra

**Version**: 2.2
**Status**: Stable

---

## What an Execution Primitive Is

An execution primitive is a unit of computation that:

1. **Accepts an intent.** Not just a command. An intent carries context — what is known, what was tried, what constraints apply.
2. **Produces evidence.** Not just output. Evidence is trust-scored and causally chained.
3. **Records both.** The ledger captures the intent, the execution, and the evidence as a single hash-chained sequence.

If a unit of work lacks any of these, it is not an execution primitive.

---

## The Ten Primitives

| Primitive | Signature | Purpose |
|-----------|-----------|---------|
| **Step** | `S: (Intent, Context) → (Evidence, Trust)` | Irreducible atom. One agent, one intent, one execution boundary. |
| **Formula** | `F = fold(S₁, S₂, …, Sₙ)` | Ordered step composition. Each step's output feeds the next step's context. |
| **Pipeline** | `P = F₁ ;c F₂ ;c … ;c Fₙ` | Sequential formula chain. Each formula's output feeds the next formula's context. |
| **Parallel** | `‖{F₁, F₂, …, Fₙ}` | Concurrent execution in isolation. Each formula runs independently. |
| **Compound** | `G = (V, E)` | Dependency graph. Layers declare dependencies, independent layers run concurrently. |
| **Adversarial** | `A(F_blue, F_red)` | Red/Blue self-correction. Blue defends. Red attacks. Trust adjusts. |
| **Convergent** | `C({F₁, …, Fₙ}, σ)` | N strategies, one goal. Selector σ picks the winner. Losers are negative evidence. |
| **Temporal** | `T(F, cron, ttl)` | Scheduled execution with cooldown and evidence TTL. |
| **Sentinel** | `W(condition, escalation)` | Continuous monitoring with progressive escalation. |
| **Substrate** | `Ω(config)` | Meta-operations on trust weights, configuration, and infrastructure. |

---

## Step — The Atom

A step is the irreducible unit. One agent, one intent, one execution boundary.

```
S: (Intent, Context) → (Evidence, Trust)
```

Four mechanical guards prevent runaway execution:

| Guard | Default | Purpose |
|-------|---------|---------|
| Completion keyword | — | Agent signals when done. Engine halts. |
| Max iterations | 12 | Hard cap on execution cycles. |
| Max runtime | 1 hour | Wall clock timeout. |
| Circuit breaker | 3 consecutive failures | Stop retrying what cannot succeed. |

Trust computation is per-step, always. Higher primitives aggregate but never override.

Content injected into a step between boundaries — a mid-run steer message, a
human/gate decision, an injected context brief — is governed by **Invariant 6
(Inputs Are Events)**: it MUST be recorded as a signal (e.g. `steer_message`)
before the step consumes it, so a step's actual input is auditable and replayable.
See [INVARIANTS.md](./INVARIANTS.md) §6.

---

## Formula — The Sequence

A formula is an ordered composition of steps. Knowledge accumulates — step 5 starts with the context of steps 1 through 4.

```
F = fold(S₁, S₂, …, Sₙ)
```

Two execution modes:
- **Sequential.** Steps execute in order.
- **DAG-parallel.** Steps declare dependencies. Independent steps run concurrently.

---

## Pipeline — The Chain

A pipeline chains formulas sequentially. Each formula can target a different workspace, a different model, a different prompt.

```
P = F₁ ;c F₂ ;c … ;c Fₙ
```

Where `;c` is conditional sequencing:

| Condition | Meaning |
|-----------|---------|
| `success` | Run if previous succeeded (default) |
| `failure` | Run if previous failed |
| `always` | Run regardless |

Resume is built in. `--from N` resumes from any step across all formulas.

---

## Parallel — The Fleet

A parallel runs multiple formulas concurrently, each in isolation.

```
‖{F₁, F₂, …, Fₙ}
```

Formulas cannot interfere with each other. The ledger is shared and write-locked. Rate limits are coordinated — one limit affects everyone.

A run forked from another (fork-at-step) records its lineage as a chain-anchored
`fork` signal carrying `prefix_head_hash` — the chain head it branched from — so
the branch relationship is cryptographically verifiable, not mutable metadata.
See [LEDGER.md](./LEDGER.md) §Fork Lineage (v2.2).

---

## Compound — The Graph

A compound is a dependency graph of layers. Each layer can be any primitive. Independent layers run concurrently. The scheduler uses topological sort.

```
G = (V, E)   where V = {layers}, E = {depends_on edges}
```

The compound is the most general primitive. It can express any combination of the others. Use the simplest primitive that fits.

Compounds can embed other compounds — recursive execution with depth limiting and cycle detection.

---

## Adversarial — The Self-Correcting Pair

Blue runs first. Red attacks Blue's evidence. The verdict adjusts trust.

```
A(F_blue, F_red) → (Verdict, ΔTrust)
```

| Verdict | Trust Effect | Meaning |
|---------|-------------|---------|
| SURVIVED | Blue +0.1 | Evidence withstood scrutiny |
| COMPROMISED | Blue −0.3 (cascades) | Contradictions found, propagated through citation graph |
| INCONCLUSIVE | No change | Red failed to complete |

This is not testing. Testing verifies behavior. Adversarial verification challenges the evidence itself.

---

## Convergent — Selection Under Uncertainty

N formulas, same goal, different strategies. The selector picks the winner.

```
C({F₁, F₂, …, Fₙ}, σ) → F_winner
```

Three selector methods:

| Selector | Picks |
|----------|-------|
| `trust_score` | Highest mean effective confidence |
| `contradiction_min` | Fewest unresolved contradictions |
| `formula` | Evaluation formula re-ranks by trust |

The winner gets +0.1 trust. Losers get −0.05 — preserved as negative evidence, not deleted.

---

## Temporal — Scheduled Execution

Formulas on a schedule with evidence decay awareness.

```
T(F, cron, ttl) → repeated (Evidence, Trust)
```

Cooldown prevents re-execution before prior evidence has been processed. TTL marks evidence as stale after a window. The system re-executes when evidence expires.

---

## Sentinel — Continuous Monitoring

Heartbeat-driven monitoring with progressive escalation.

```
W(condition, escalation) → alerts
```

Watches for drift, contradictions, or formula-defined conditions. Escalates through configurable tiers. Auto-resolves when conditions clear.

---

## Substrate — Meta-Operations

Operations on the execution infrastructure itself — trust weights, configuration, routing.

```
Ω(config) → infrastructure change
```

Elevated permissions. Approval gates. Rollback support.

---

## The Composition Algebra

The ten primitives form a closed algebra under composition:

- `;` — sequential composition. `A ; B` means "run A, then run B."
- `‖` — parallel composition. `A ‖ B` means "run A and B concurrently."
- `ε` — identity. Empty step, no evidence, succeeds immediately.

**Properties:**
- Sequential is associative: `(A ; B) ; C = A ; (B ; C)`
- Parallel is commutative: `A ‖ B = B ‖ A`
- Identity is neutral: `A ; ε = ε ; A = A`

The algebra describes what the composition does. It is descriptive, not prescriptive.

---

## The Embedding Principle

Every higher primitive embeds lower primitives without modification.

- A step runs identically whether it is alone, one of 20 in a formula, or one of 200 in a compound.
- Trust computation is per-step, always. Higher primitives aggregate but never override.
- The ledger sees individual step signals regardless of which primitive invoked them.
- The step does not know what contains it. It does not need to know.

---

## Sequences as Protocol Compositions

A sequence is a composition of commitments, not a separate state machine. Every sequence concept maps to a protocol primitive:

| Sequence Concept | Protocol Primitive | Operation |
|------------------|--------------------|-----------|
| Sequence definition | Signal | `capture` with `kind: "sequence"` |
| Sequence instance | Commitment (parent) | `commit` referencing the definition |
| Step execution start | Child commitment | `commit` + `claim` |
| Step completed | Child closed | `close` with evidence |
| Step failed | Child annotated | `annotate` with failure details |
| Sequence progress | Computed | Count child commitment states |
| Sequence completed | Parent closed | `close` with summary evidence |

Sequence state is never stored. It is computed from child commitment states:

```
If any child is claimed/in_review/reopened → "running"
If all children are closed                 → "completed"
If no children are claimed and none closed → "pending"
```

This is the protocol's composition model: higher constructs are always reducible to signals and operations. State is always computed, never stored.

---

## The Law of Epistemic Acceleration

A formula's epistemic value exceeds the sum of its steps run independently:

```
V(F_n) > Σ V(S_i)   for i = 1..n
```

Step 5 in sequence is stronger than step 5 in isolation because it has the accumulated context of steps 1 through 4. Knowledge compounds. Evidence builds on evidence.

---

*Ten primitives. One algebra. Evidence in, evidence out.*
