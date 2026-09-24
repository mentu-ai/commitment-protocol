# Instructions for AI Agents

This workspace uses the Commitment Protocol for work coordination, through `mentu`, one implementation of it.

**Before doing any work, read this file completely.**

---

## What is the Commitment Protocol

The Commitment Protocol is an accountability ledger for agent work. Append-only. Hash-chained. It tracks what needs to be done, who is doing it, and proof that it was done. The commands below use the `mentu` CLI.

- **Observations** become **commitments**
- **Commitments** require **evidence** to close
- **Evidence** is trust-scored and causally chained
- Everything is recorded. Nothing is edited. Nothing is deleted.

You are working inside a governed workspace. Your actions are tracked.

---

## Your First Action

Read the ledger before acting. Check for existing work:

```bash
mentu status
```

This shows:
- Open commitments (available to claim)
- Your claimed commitments (resume these first)
- Commitments in review (awaiting approval)

**If you have claimed commitments, resume them before taking new work.**

Reading the ledger is not optional. An agent without epistemic context is epistemically blind — you may contradict existing evidence, duplicate completed work, or ignore known constraints.

---

## The Workflow

### 1. Claim Before Starting

Before working on any commitment:

```bash
mentu claim <commitment_id>
```

This prevents collision with other agents or humans. You are now the owner.

### 2. Do the Work

Complete the task described in the commitment.

### 3. Capture Evidence

When you finish, capture what you did:

```bash
mentu capture "Fixed null check in payment.ts:42, added test" --kind evidence
```

Be specific. Include:
- What files you changed
- What you fixed or built
- What tests you ran

### 4. Submit for Review

Submit your work with evidence:

```bash
mentu submit <commitment_id> --evidence <memory_id> --summary "Fixed payment bug"
```

The commitment enters `in_review` state.

### 5. Wait for Approval

A human or validator will review your submission. They may:
- **Approve** — Work is complete, commitment closes
- **Reopen** — Work needs revision, you continue

---

## Citation Requirements

When your work produces findings, step results, or learnings, **cite the source**:

```bash
mentu capture "JWT validation is missing expiry check" \
  --kind finding \
  --refs <source_signal_id>
```

Findings without provenance are assertions, not evidence. The protocol requires that signals of kind `finding`, `step_result`, or `learning` reference their source.

---

## What You Cannot Do

- **Cannot close without evidence** — Every closure needs proof
- **Cannot claim what's claimed** — Another agent/human owns it
- **Cannot close directly** — Use `submit`, not `close`
- **Cannot work on closed commitments** — They're done
- **Cannot self-report trust** — Trust is computed from your work, not your claim

---

## When Stuck

If you cannot complete a commitment:

```bash
mentu release <commitment_id> --reason "Blocked on external API access"
```

This gives up ownership. Someone else will take it.

---

## Creating New Commitments

If you observe something that needs to be done:

```bash
# Capture the observation
mentu capture "Found bug: checkout fails on empty cart" --kind observation

# Create commitment from observation
mentu commit "Fix empty cart checkout bug" --source <memory_id>

# Claim it
mentu claim <commitment_id>
```

---

## Commands Reference

```bash
# Check status
mentu status
mentu status --mine       # Just your work

# Work with commitments
mentu claim <id>          # Take ownership
mentu release <id>        # Give up ownership
mentu submit <id> --evidence <mem_id> --summary "..."

# Capture observations
mentu capture "What happened" --kind <kind>

# Annotate
mentu annotate <target_id> "Note text" --kind <kind>

# Query
mentu show <id>           # Details of any signal
mentu log                 # Recent operations
```

---

## Evidence Guidelines

Good evidence is:
- **Specific** — "Fixed null check in auth.ts:42"
- **Verifiable** — Mentions files, lines, tests
- **Connected** — References the source signal it derives from
- **Mechanically checkable** — Build passes, tests pass

Bad evidence is:
- **Vague** — "Fixed the issue"
- **Missing details** — "Made changes"
- **Unrelated** — Doesn't address the commitment
- **Untestable** — No build, no tests, no verification

---

## The Sacred Rule

**Read ledger, write ops.**

You don't store state. You read the ledger and perform operations. The ledger is truth.

---

*You are accountable. Your work is tracked. Cite your sources. Produce evidence.*
