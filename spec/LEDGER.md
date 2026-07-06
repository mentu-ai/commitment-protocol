# Ledger Format

**Version**: 2.2

---

## Overview

The ledger is an append-only, hash-chained sequence of signals stored in JSON Lines format.

**Location**: `.mentu/ledger.jsonl`

---

## JSON Lines Format

Each line is a complete JSON object representing one EpistemicSignal.

```jsonl
{"id":"mem_a1b2c3d4","op":"capture","ts":"2026-04-02T10:30:00Z","actor":"human:rashid","workspace":"my-project","hash":"a7f3...","prevHash":"0000...0000","payload":{"body":"Customer reported bug","kind":"observation"}}
{"id":"cmt_e5f6g7h8","op":"commit","ts":"2026-04-02T10:31:00Z","actor":"human:rashid","workspace":"my-project","hash":"b8e4...","prevHash":"a7f3...","payload":{"body":"Fix the bug","kind":"commitment","source":"mem_a1b2c3d4"}}
```

---

## Signal Schema

### Identity

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `id` | Yes | string | Unique identifier (`mem_`, `cmt_`, `op_`, `ann_` prefix + 8 hex chars) |
| `op` | Yes | string | Operation: `capture`, `commit`, `claim`, `release`, `close`, `submit`, `approve`, `reopen`, `annotate` |
| `ts` | Yes | string | ISO 8601 timestamp in UTC |
| `actor` | Yes | string | Who performed the operation |
| `workspace` | Yes | string | Workspace name |

### Merkle Chain

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `hash` | Yes | string | SHA-256 content hash of this signal |
| `prevHash` | Yes | string | SHA-256 hash of previous signal. Genesis: 64 zeros. |

### Sync

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `syncScope` | No | string | `local`, `anonymous`, `full`, `cloud`. Default: implementation-defined. |

### Payload

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `payload.body` | Yes | string | Content: observation, obligation, evidence, annotation |
| `payload.kind` | No | string | Signal kind: `observation`, `commitment`, `evidence`, `step_result`, `finding`, `learning`, `event`, `claim`, `submission`, `approval`, `verdict`, `reopen`, `session_anchor`, `lane_cutover` (v2.2 chain markers), `steer_message` (v2.2 Invariant 6), `model_call`, `tool_call`, `call_lane` (v2.2 execution lane), `fork` (v2.2 fork lineage) |
| `payload.source` | Conditional | string | Source signal ID. Required for `commit`. |
| `payload.commitment` | Conditional | string | Commitment ID. Required for `claim`, `release`, `submit`, `approve`, `close`, `reopen`. |
| `payload.evidence` | Conditional | string | Evidence signal ID. Required for `close`, `submit`. |
| `payload.summary` | No | string | Summary text for `submit`. |
| `payload.reason` | No | string | Reason for `release`, `reopen`. |
| `payload.comment` | No | string | Comment for `approve`. |
| `payload.target` | Conditional | string | Target signal ID. Required for `annotate`. |
| `payload.tags` | No | string[] | Labels for filtering. |
| `payload.refs` | No | string[] | Related signal IDs. |
| `payload.meta` | No | object | Arbitrary metadata. |
| `payload.duplicate_of` | No | string | Commitment ID for duplicate closure. |

### Semantic Context

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `semantic.entities` | No | string[] | Named things: function names, file paths, concepts |
| `semantic.intent` | No | string | What this signal is about: `fix_bug`, `implement_feature`, `verify_build` |
| `semantic.domain` | No | string[] | Domain tags: `security`, `testing`, `performance` |

### Trust Metadata

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `trust.confidence` | No | number | Asserted confidence (0.0–1.0). Frozen at creation. |
| `trust.verification` | No | string | `unverified`, `machine_verified`, `human_verified` |
| `trust.chain` | No | string[] | Mechanical checks that produced the confidence score |
| `trust.decayHalfLifeDays` | No | integer | Decay half-life in days |

See [TRUST.md](./TRUST.md) for the trust computation model.

### Epistemic Trace

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `trace.parent` | No | string[] | IDs of signals this one derives from |
| `trace.children` | No | string[] | IDs of signals derived from this one (updated by later signals) |
| `trace.causalDepth` | No | integer | How many causal links from raw observation. Default: 0. |

### Relations

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `relations` | No | array | Typed relationships to other signals |
| `relations[].type` | Yes | string | `cites`, `extends`, `contradicts`, `refines` |
| `relations[].targetId` | Yes | string | Target signal ID |

### Observation Level

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `observationLevel` | No | string | `explicit`, `deductive`, `inductive`, `contradiction` |
| `sourceIds` | No | string[] | Premise signal IDs for this observation |

---

## Execution Lane (v2.2)

Extends truth-by-replay from the commitment plane to the execution plane:
individual model and tool calls become content-addressed events, so lineage
reaches the specific call that produced an artifact, not just the step.

Two payload kinds record a completed call:

| Kind | Meaning |
|------|---------|
| `model_call` | One completed model request/response. |
| `tool_call` | One completed tool request/response. |

Each carries, in `payload.body` and `semantic.entities`:

| Field | Meaning |
|-------|---------|
| `request_hash` | SHA-256 over the **canonical** request — sorted-key, compact JSON of `{model, system, messages, tool_definitions, output_schema}` (models) or `{tool, arguments}` (tools). Same canonicalization as the signal content hash. This is the blob key. |
| `response_digest` | SHA-256 of the stored response body. Lets strict replay detect a mutated blob. |
| `model` / `tool` | The callee. |
| `run_id` / `step` | The run and step the call belongs to (the CIR `run_id` column + step label). |
| `cost` | Optional cost estimate. |

**Storage is dual-lane.** Response bodies live OUT of the chain, content-addressed
at `.mentu/cache/model-responses/<request_hash>.json` (workspace-relative), and
the run's calls are listed in an append-only per-run **manifest** co-located with
the blobs. Only digests and hashes enter signals, so the tamper-evident ledger
anchors the lane without absorbing its volume. Bodies are size-capped (2 MB
default, truncated with a marker; the digest is over what is stored). Per-run
aggregation is a CIR query on `(run_id, step)` — an implementation MAY also
denormalize the per-step list of `request_hash` values onto the step's
`step_result` signal.

**The chain anchors the lane.** At the sequence-end boundary, a run that recorded
calls appends a `call_lane` annotation (`payload.kind: "call_lane"`) carrying
`manifest_sha256` — the digest of the run's manifest — into the merkle chain.
The manifest and blobs are out-of-chain files; the anchor is what makes them
tamper-evident: strict replay recomputes the manifest digest against the anchored
one and reports a mismatch as `E_REPLAY_DIVERGED`.

**Retention.** Blobs and manifests are prunable by age like any cache; wiring
their pruning into the vacuum cadence (`cir-vacuum-cycle`) is a named follow-up.
Pruning removes replayability for the affected runs but never touches chain
integrity — anchors remain valid history.

**Coverage boundary (honest).** A conforming implementation records the calls it
makes **in-process**. Where a step delegates to a child agent *process* (e.g. a
CLI backend), that child's own model/tool calls are outside the recorder's view;
recording MUST NOT attempt to intercept child-process traffic, and the boundary
MUST be documented. In this engine's v2.2, the recorded in-process calls are the
semantic gate and the completion verifier; the delegated agent step's internal
calls are out of lane. Default on; opt out with `MENTU_NO_CALL_LANE=1`.

---

## Fork Lineage (v2.2)

When a run is forked from another at a chosen step, the lineage is anchored in
the chain by a `fork` annotation (`payload.kind: "fork"`), not merely in mutable
run metadata. It records, in `payload.body` and `semantic.entities`:

| Field | Meaning |
|-------|---------|
| `parent_run_id` | The run this one branched from. |
| `fork_at_step` | The step index the fork branched at. |
| `prefix_head_hash` | The chain head hash at fork creation — the exact ledger state the fork inherited. |

Because `prefix_head_hash` is a hash of the shared chain, fork lineage is
cryptographically verifiable rather than assertable metadata that can drift out
of sync. A reader confirms a fork's claimed ancestry by checking that
`prefix_head_hash` names a real earlier row on the chain.

---

## Operation Schemas

### capture

Creates a signal from observation.

```json
{
  "id": "mem_a1b2c3d4",
  "op": "capture",
  "ts": "2026-04-02T10:30:00Z",
  "actor": "human:rashid",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Customer reported checkout bug",
    "kind": "observation"
  }
}
```

### commit

Creates a commitment from a source signal.

```json
{
  "id": "cmt_e5f6g7h8",
  "op": "commit",
  "ts": "2026-04-02T10:31:00Z",
  "actor": "human:rashid",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Fix checkout bug",
    "kind": "commitment",
    "source": "mem_a1b2c3d4",
    "tags": ["bug", "checkout"]
  }
}
```

### claim

Takes responsibility for a commitment.

```json
{
  "id": "op_i9j0k1l2",
  "op": "claim",
  "ts": "2026-04-02T10:32:00Z",
  "actor": "agent:claude",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Claiming checkout bug fix",
    "kind": "claim",
    "commitment": "cmt_e5f6g7h8"
  }
}
```

### release

Gives up responsibility.

```json
{
  "id": "op_xxxxxxxx",
  "op": "release",
  "ts": "2026-04-02T11:00:00Z",
  "actor": "agent:claude",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Blocked on external dependency",
    "kind": "release",
    "commitment": "cmt_e5f6g7h8",
    "reason": "Blocked on external dependency"
  }
}
```

### close

Resolves with evidence (direct path).

```json
{
  "id": "op_xxxxxxxx",
  "op": "close",
  "ts": "2026-04-02T12:00:00Z",
  "actor": "agent:claude",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Closing with evidence",
    "kind": "verdict",
    "commitment": "cmt_e5f6g7h8",
    "evidence": "mem_xyz789"
  }
}
```

### submit

Requests closure, enters review.

```json
{
  "id": "op_xxxxxxxx",
  "op": "submit",
  "ts": "2026-04-02T12:00:00Z",
  "actor": "agent:claude",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Fixed null check in payment.ts:42",
    "kind": "submission",
    "commitment": "cmt_e5f6g7h8",
    "evidence": "mem_xyz789",
    "summary": "Fixed checkout bug"
  }
}
```

### approve

Accepts submission.

```json
{
  "id": "op_xxxxxxxx",
  "op": "approve",
  "ts": "2026-04-02T13:00:00Z",
  "actor": "human:rashid",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Verified fix works",
    "kind": "approval",
    "commitment": "cmt_e5f6g7h8",
    "comment": "Verified fix works"
  }
}
```

### reopen

Rejects submission or disputes closure.

```json
{
  "id": "op_xxxxxxxx",
  "op": "reopen",
  "ts": "2026-04-02T13:00:00Z",
  "actor": "human:rashid",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "Edge case not handled",
    "kind": "reopen",
    "commitment": "cmt_e5f6g7h8",
    "reason": "Edge case not handled"
  }
}
```

### annotate

Attaches note to any signal. Subsumes v1.0 `link`, `dismiss`, `triage`.

```json
{
  "id": "ann_xxxxxxxx",
  "op": "annotate",
  "ts": "2026-04-02T10:35:00Z",
  "actor": "human:rashid",
  "workspace": "my-project",
  "hash": "...",
  "prevHash": "...",
  "payload": {
    "body": "High priority",
    "kind": "priority",
    "target": "cmt_e5f6g7h8"
  }
}
```

---

## Hash Computation

The `hash` field is computed as follows:

1. Take the signal object and set the `hash` and `prevHash` fields to the empty
   string `""`. **The keys are retained** (the values are zeroed); they are not
   removed from the object.
2. Serialize to JSON with **recursively sorted keys** and **no insignificant
   whitespace** (compact separators), escaping forward slashes as `\/` and
   emitting UTF-8 bytes. This matches the engine's `JSONEncoder` with
   `.sortedKeys` (`MentuEngine` `EpistemicSignal.computeContentHash`).
3. Compute SHA-256 of the resulting bytes.
4. Encode as lowercase hexadecimal (64 characters).

```python
import hashlib, json

def compute_hash(signal):
    obj = dict(signal)
    obj["hash"] = ""          # zero the value; KEEP the key
    obj["prevHash"] = ""      # zero the value; KEEP the key
    canonical = json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    canonical = canonical.replace("/", "\\/")   # JSONEncoder escapes forward slashes
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

> **Canonicalization note.** Two details are load-bearing and were previously
> under-specified: (a) `hash`/`prevHash` are **zeroed to `""` with the keys
> kept**, not stripped from the object; and (b) forward slashes are **escaped
> as `\/`**, matching the engine's Swift `JSONEncoder`. A `compute_hash` that
> strips the keys or omits the slash escaping will fail to reproduce
> engine-written hashes even though it produces a valid-looking digest. The
> reference verifier (`protocol/tools/verify_ledger.py`) and the worked example
> (`protocol/examples/sample-ledger.jsonl`) are both computed with this
> algorithm; run the verifier against a real `.mentu/ledger.jsonl` to confirm.

The `prevHash` field is the `hash` of the immediately preceding signal in the ledger. For the first signal (genesis), `prevHash` is:

```
0000000000000000000000000000000000000000000000000000000000000000
```

### Chain integrity — canonical-ancestry, not adjacency (v2.2)

A verifier checks the chain by **canonical ancestry**, not by comparing each row
to the line immediately above it. Each append links its `prevHash` to the head
the writer read under an exclusive lock; interleaved rows from concurrent writers
or the out-of-chain lane mean the linked head is often *not* the adjacent line. A
`prevHash` is sound when it resolves to the `hash` of **any earlier hashed row**.

A conforming verifier classifies each row into exactly one of:

1. **Canonical / skip-link** — `prevHash` resolves to an earlier hashed row (or
   is genesis). Sound.

2. **Genesis / import anchor** — the **first hashed row of the file**. On an
   imported or rotated ledger it legitimately links to the head of a prior file
   (a hash absent from this one). It is the file's genesis anchor, **not** a
   break. A missing-ancestor link on any *later* row — once the chain is
   established — is a genuine break.

3. **Fork** — two or more rows sharing one parent hash. Legitimate on a ledger
   shared by concurrent workspaces; reported, **never fatal**. (The engine keys
   its append lock on the symlink-*resolved* real ledger path, so one physical
   ledger has one lock and new forks do not occur; historical forks are frozen,
   content-valid append-only bytes.)

4. **Break** — a `prevHash` (on a non-genesis, non-`session_anchor` row) that
   resolves to no earlier hashed row: a missing ancestor. **Fatal** — tampering
   or truncation. `E_CHAIN_BROKEN`.

5. **Out-of-chain lane** — a row with no `hash` field. **Content-uncheckable**,
   not a chain anchor. Hook-authored annotations (`actor: hook:*`, `op: annotate`
   at session-end / pre-compact / post-compact) and non-signal telemetry (e.g.
   MCP tool-call rows) live here. A verifier MUST count hashed and unhashed rows
   separately and MUST NOT report an unhashed row as a hash failure.

#### Typed markers (v2.2)

Two optional `op: annotate` markers convert previously-tolerated artifacts into
checkable structure. Both are written through the hashed merkle path (`mentu
ledger anchor` / `mentu ledger cutover`), so they are themselves chain anchors.

- **`session_anchor`** (`payload.kind: "session_anchor"`) — documents an
  intentional re-anchor (e.g. resuming against a ledger a different machine
  advanced). The head it re-anchored from is recorded in `semantic.entities[0]`.
  A verifier treats a `session_anchor`'s own `prevHash` discontinuity as expected,
  exempt from break counting.

- **`lane_cutover`** (`payload.kind: "lane_cutover"`) — declares that unhashed
  rows appended **after** this marker are chain violations (not the grandfathered
  out-of-chain lane). Before any `lane_cutover`, unhashed rows are grandfathered;
  after it, an unhashed row is fatal. Drop this once external hook writers have
  migrated onto a hashed append path.

A conforming verifier exits non-zero iff: any content-hash mismatch, any break
(missing ancestor after the genesis anchor), or any unhashed row after a
`lane_cutover`. Forks, the genesis/import anchor, and pre-cutover unhashed rows
are reported but never fatal. The reference implementation is
`protocol/tools/verify_ledger.py`; run it against a real `.mentu/ledger.jsonl`.

---

## ID Format

IDs use the format: `{prefix}_{8hex}`

| Prefix | Signal Type |
|--------|-------------|
| `mem` | Memory (capture) |
| `cmt` | Commitment (commit) |
| `op` | Operation (claim, release, close, submit, approve, reopen) |
| `ann` | Annotation (annotate) |

Example: `mem_a1b2c3d4`, `cmt_e5f6g7h8`, `op_i9j0k1l2`, `ann_m3n4o5p6`

---

## Timestamp Format

All timestamps use ISO 8601 format in UTC:

```
2026-04-02T10:30:00Z
2026-04-02T10:30:00.123Z
```

**Note**: Timestamps are metadata. Append order is truth.

---

## Actor Format

| Format | Example |
|--------|---------|
| Human | `human:rashid` |
| Agent | `agent:claude` |
| System | `system:sync` |
| Email | `rashid@example.com` |

---

## Idempotency

The `source_key` field enables safe replay:

```json
{
  "id": "op_xxxxxxxx",
  "op": "capture",
  "source_key": "github:issue:123",
  "payload": { "body": "Issue from GitHub", "kind": "observation" }
}
```

If `source_key` is present, it MUST be unique. Duplicate `source_key` operations are rejected.

---

## File Structure

```
.mentu/
├── ledger.jsonl    # The append-only, hash-chained ledger
├── config.yaml     # Workspace configuration
├── genesis.key     # Constitutional identity (optional)
├── AGENTS.md       # Instructions for AI agents
└── .lock           # Write lock (runtime)
```

---

## Backward Compatibility

v1.0 signals that lack v2.0 fields are valid. On import:

- `hash` and `prevHash` must be computed and the chain reconstructed
- `workspace` defaults to `"default"`
- All optional v2.0 fields default to `null` or `[]`
- v1.0 operations `link`, `dismiss`, `triage` map to `annotate` with the corresponding `kind`

---

*Append-only. Hash-chained. Truth by replay.*
