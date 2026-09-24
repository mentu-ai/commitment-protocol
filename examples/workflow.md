# Example Workflow

A complete example showing the Commitment Protocol in action, using the `mentu` CLI (one implementation).

---

## Scenario

A customer reports a bug. An agent fixes it. A human approves. The hash chain grows. Trust is computed.

---

## Step 1: Capture Observation

Human sees a customer report:

```bash
mentu capture "Customer reported checkout fails on empty cart" --kind observation
```

This is the genesis signal. Its `prevHash` is 64 zeros — the start of the chain.

```json
{
  "id": "mem_a1b2c3d4",
  "op": "capture",
  "hash": "bed4c1c8...",
  "prevHash": "0000000000000000000000000000000000000000000000000000000000000000",
  "payload": { "body": "Customer reported checkout fails on empty cart", "kind": "observation" },
  "observationLevel": "explicit"
}
```

**Chain**: `genesis → bed4c1c8...`

---

## Step 2: Create Commitment

Human creates a commitment from the observation. The commitment **cites** the observation — traceability from obligation to origin.

```bash
mentu commit "Fix empty cart checkout bug" --source mem_a1b2c3d4 --tag bug --tag checkout
```

```json
{
  "id": "cmt_e5f6g7h8",
  "op": "commit",
  "hash": "56789c80...",
  "prevHash": "bed4c1c8...",
  "payload": { "body": "Fix empty cart checkout bug", "kind": "commitment", "source": "mem_a1b2c3d4" },
  "relations": [{ "type": "cites", "targetId": "mem_a1b2c3d4" }]
}
```

**Chain**: `genesis → bed4c1c8... → 56789c80...`

---

## Step 3: Agent Claims

An AI agent checks for work and claims the commitment:

```bash
mentu status
mentu claim cmt_e5f6g7h8
```

```json
{
  "id": "op_i9j0k1l2",
  "op": "claim",
  "hash": "c491a41c...",
  "prevHash": "56789c80...",
  "payload": { "body": "Claiming checkout bug fix", "kind": "claim", "commitment": "cmt_e5f6g7h8" }
}
```

**Chain**: `genesis → bed4c1c8... → 56789c80... → c491a41c...`

---

## Step 4: Agent Works

Agent fixes the bug in the codebase.

---

## Step 5: Agent Captures Evidence

Agent records what was done. The evidence **cites** the original observation and carries mechanical trust metadata:

```bash
mentu capture "Fixed null check in cart.ts:42, added test in cart.test.ts" \
  --kind evidence \
  --refs mem_a1b2c3d4
```

```json
{
  "id": "mem_m3n4o5p6",
  "op": "capture",
  "hash": "9b280af3...",
  "prevHash": "c491a41c...",
  "payload": { "body": "Fixed null check in cart.ts:42, added test in cart.test.ts", "kind": "evidence" },
  "semantic": { "entities": ["cart.ts", "cart.test.ts"], "intent": "fix_null_check", "domain": ["bug", "checkout"] },
  "trust": {
    "confidence": 0.85,
    "verification": "machine_verified",
    "chain": ["exit_code:1.0", "test_pass_rate:0.95", "context_utilization:0.72", "loop_complete:1.0", "duration_reasonable:0.80", "no_errors:1.0", "evidence_depth:0.40"]
  },
  "trace": { "parent": ["mem_a1b2c3d4"], "causalDepth": 1 },
  "relations": [{ "type": "cites", "targetId": "mem_a1b2c3d4" }]
}
```

**Trust breakdown**: The engine observed exit code 0 (1.0), 95% test pass rate (0.95), 72% context utilization (0.72), completion keyword detected (1.0), reasonable duration (0.80), no errors (1.0), and causal depth 1 (0.40). Weighted sum: **0.85**.

**Chain**: `genesis → bed4c1c8... → 56789c80... → c491a41c... → 9b280af3...`

---

## Step 6: Agent Submits

Agent submits for review:

```bash
mentu submit cmt_e5f6g7h8 --evidence mem_m3n4o5p6 --summary "Fixed null check in cart.ts:42"
```

Commitment state: `in_review`

---

## Step 7: Human Reviews

Human checks the review queue:

```bash
mentu status --in-review
```

```
In Review:
  cmt_e5f6g7h8: Fix empty cart checkout bug
    Submitted by: agent:claude
    Evidence: Fixed null check in cart.ts:42, added test in cart.test.ts
    Trust: 0.85 (machine_verified)
```

Human verifies the fix works.

---

## Step 8: Human Approves

Human approves with human-verified trust:

```bash
mentu approve cmt_e5f6g7h8 --comment "Verified fix works"
```

```json
{
  "id": "op_u1v2w3x4",
  "op": "approve",
  "hash": "7ddb5ab4...",
  "prevHash": "815fd202...",
  "trust": { "confidence": 0.95, "verification": "human_verified" }
}
```

Commitment state: `closed`

**What happened to trust**: The evidence signal `mem_m3n4o5p6` was cited by the approval. Its `effective_confidence` increases — being cited is evidence of utility. The original observation `mem_a1b2c3d4` is now two citations deep. Trust propagates up the chain.

---

## Final Chain

```
Signal 1: mem_a1b2c3d4  (capture, observation)     hash: bed4c1c8...
Signal 2: cmt_e5f6g7h8  (commit, commitment)       hash: 56789c80...  prevHash: bed4c1c8...
Signal 3: op_i9j0k1l2   (claim)                    hash: c491a41c...  prevHash: 56789c80...
Signal 4: mem_m3n4o5p6  (capture, evidence)         hash: 9b280af3...  prevHash: c491a41c...  trust: 0.85
Signal 5: op_q7r8s9t0   (submit)                    hash: 815fd202...  prevHash: 9b280af3...
Signal 6: op_u1v2w3x4   (approve)                   hash: 7ddb5ab4...  prevHash: 815fd202...  trust: 0.95
```

Six signals. One unbroken chain. Observation → obligation → claim → evidence → submission → approval. Every link is hash-chained. Trust is mechanical.

---

## Key Points

1. **Observation came first** — The commitment traces to a memory
2. **Agent claimed before working** — No collision with others
3. **Evidence cites its source** — `trace.parent` links evidence to the original observation
4. **Trust is mechanical** — 0.85 from seven weighted observations, not self-reported
5. **Human approval is human-verified** — Different trust level than machine verification
6. **Hash chain is unbroken** — Every signal links to the one before it
7. **Everything recorded** — Full audit trail, tamper-evident

---

*Observe. Commit. Claim. Work. Evidence. Close. Every link in the chain.*
