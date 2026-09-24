# Trust Computation

**Version**: 2.3
**Status**: Stable

---

## The Principle

Trust is computed, never self-reported.

An agent cannot declare its own confidence. A signal cannot assert its own trustworthiness. Trust is the ledger's judgment, based on mechanical observation of what actually happened.

---

## Three Confidence Values

| Value | When Set | Mutable | Description |
|-------|----------|---------|-------------|
| `asserted_confidence` | Creation | Never | What the mechanical model computed at insertion time. Frozen. |
| `effective_confidence` | Recomputed | On citation, contradiction, reinforcement | Current trust accounting for downstream signals. |
| `current_confidence` | Read time | Never stored | Effective confidence × temporal decay. |

`asserted_confidence` is a fact about creation. `effective_confidence` is a fact about the graph. `current_confidence` is a fact about now.

---

## The Seven-Weight Model

Asserted confidence is computed from seven mechanical observations:

| Weight | Component | Measures |
|--------|-----------|----------|
| 0.20 | `exit_code` | Process exited 0 |
| 0.20 | `test_pass_rate` | Tests passed / tests run |
| 0.20 | `context_utilization` | 1.0 − tokens_used / context_window |
| 0.15 | `loop_complete` | Completion keyword detected |
| 0.10 | `duration_reasonable` | Within timeout, not instant |
| 0.10 | `no_errors` | Exit 0 AND loop complete |
| 0.05 | `evidence_depth` | Causal depth from parent signals |

Each component produces a value between 0.0 and 1.0. The asserted confidence is:

```
asserted_confidence = Σ (weight_i × component_i)
```

Components are binary or continuous:
- **Binary**: `exit_code` (0 or 1), `loop_complete` (0 or 1), `no_errors` (0 or 1)
- **Continuous**: `test_pass_rate` (0.0–1.0), `context_utilization` (0.0–1.0), `duration_reasonable` (0.0–1.0), `evidence_depth` (normalized 0.0–1.0)

**Weights are configurable.** A workspace's Genesis Key can override the default weights. The seven components are fixed. The weights are not.

---

## Temporal Decay

Evidence fades. Recent evidence weighs more than old evidence.

```
current_confidence = effective_confidence × 2^(−age_days / half_life_days)
```

Default `half_life_days`: 90. Configurable per signal via `trust.decayHalfLifeDays`.

| Age | Decay Factor (90-day half-life) |
|-----|------|
| 0 days | 1.000 |
| 30 days | 0.794 |
| 90 days | 0.500 |
| 180 days | 0.250 |
| 365 days | 0.059 |

Decay is applied at read time. Stored values do not change.

---

## Effective Confidence

Effective confidence starts at asserted confidence and changes as the graph evolves:

### Citation

When signal B cites signal A, A's effective confidence increases. Being cited is evidence of utility.

### Contradiction

When signal C contradicts signal A, A's effective confidence decreases. Being contradicted is evidence of doubt.

### Reinforcement

When multiple independent signals cite A, the reinforcement compounds. The more downstream signals depend on A, the more the graph trusts it.

### Cascade

Trust changes propagate. If A's effective confidence drops due to contradiction, every signal that cites A re-evaluates. This is not a loop — it is a directed acyclic traversal of the citation graph.

---

## Trust Events

Every confidence change is an explainable event:

| Event Type | Trigger | Direction |
|------------|---------|-----------|
| `citation_added` | Signal B cites signal A | A ↑ |
| `contradiction_detected` | Signal C contradicts signal A | A ↓ |
| `reinforcement_update` | Multiple citations accumulate | A ↑ |
| `decay_applied` | Time passes | A ↓ |

Each event records: signal ID, event type, old confidence, new confidence, cause signal ID, reason, timestamp.

---

## Verification Levels

| Level | Meaning |
|-------|---------|
| `unverified` | Not verified. From the trust computer: a check the run reported failed, named in `chain` (`exit_code:1`, `tests:fail`). As a default: no trust was computed |
| `partially_verified` | No check failed, but one the run expects was not established — for example, no test report (v2.3) |
| `machine_verified` | Passed automated checks. From the trust computer: exit status 0, completion detected, and a passing test report |
| `human_verified` | Explicitly reviewed by a human actor |

**Per-check components (v2.3).** A label summarizes; `chain` carries each check
as passed, failed or absent. Tests are `tests:pass`, `tests:fail` or
`tests:no_evidence`. A failed check and a missing one are different facts, and
the trust computer MUST NOT give them the same label: a run whose tests failed is
`unverified`, a run with no test report is at most `partially_verified`, and only
a passing test report can yield `machine_verified`. A successful build is not
test evidence.

**Reading earlier records.** Before v2.3 the reference engine wrote
`tests:inferred_from_build` for a run with no test report and still labelled it
`machine_verified`. Records are append-only, so readers map instead of
rewriting: a `machine_verified` record whose chain contains
`tests:inferred_from_build` reads as `partially_verified`.

Verification level is set at creation and can only increase — `unverified` → `partially_verified` → `machine_verified` → `human_verified`. It never decreases.

---

## Trust in the Signal

Trust metadata lives in the signal's `trust` field:

```json
{
  "trust": {
    "confidence": 0.85,
    "verification": "machine_verified",
    "chain": ["exit_code:1.0", "test_pass_rate:0.95", "context_utilization:0.72", "loop_complete:1.0", "duration_reasonable:0.80", "no_errors:1.0", "evidence_depth:0.40"],
    "decayHalfLifeDays": 90
  }
}
```

The `chain` array is the explainability trail — exactly which checks produced the score.

---

## Conformance

A conforming implementation that supports trust MUST:

1. Compute asserted confidence mechanically, never accept self-reported values
2. Freeze asserted confidence at creation — never update it
3. Apply temporal decay at read time, not at write time
4. Record trust events for every effective confidence change
5. Propagate trust changes through the citation graph

A conforming implementation MAY:
1. Override default weights via Genesis Key
2. Define additional components beyond the seven defaults
3. Implement custom decay functions

---

*Trust is earned by observation. Not claimed by assertion.*
