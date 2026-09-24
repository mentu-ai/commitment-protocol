#!/usr/bin/env python3
r"""Reference verifier for the Commitment Protocol ledger (spec/LEDGER.md).

Recomputes each signal's content hash and checks the merkle chain using the SAME
canonicalization the Mentu engine uses (EpistemicSignal.computeContentHash)
AND the same chain semantics the engine's own scanner uses
(Mentu engine: MerkleLedgerLineage.scan).

Content hash — SHA-256 over the signal serialized as JSON with:
  1. `hash` and `prevHash` set to "" — the KEYS ARE RETAINED (Swift zeroes the
     stored values before encoding), not removed;
  2. keys sorted recursively (JSONEncoder .sortedKeys);
  3. no insignificant whitespace (compact separators);
  4. forward slashes escaped as \/ (Swift JSONEncoder default), UTF-8 bytes.
The digest is lowercase hex, 64 chars.

Chain — CANONICAL-ANCESTRY, not naive adjacency. A signal's `prevHash` is sound
if it resolves to the hash of ANY earlier hashed row (the engine links each
append to the head it read under an exclusive lock, tolerating interleaved
unhashed rows and concurrency forks). Therefore:
  - BREAK  = a `prevHash` that resolves to no earlier hashed row (a genuinely
             missing ancestor — tampering or truncation). This is fatal.
  - FORK   = two or more rows sharing one parent hash. Legitimate on a ledger
             shared by concurrent workspaces; reported, never fatal.
  - UNHASHED = the out-of-chain hook lane (rows with no `hash`). Content-
             uncheckable. Grandfathered UNLESS they appear after a `lane_cutover`
             marker (kind == "lane_cutover"), after which they are violations.
  - session_anchor markers (kind == "session_anchor") document an intentional
             re-anchor and are exempt from break counting.
  - GENESIS/IMPORT ANCHOR = the FIRST hashed row of the file. On an imported or
             rotated ledger it legitimately links to the head of a prior file
             (a hash absent from this one). It is the file's genesis anchor, not
             a break. A missing-ancestor link on any LATER row — once the chain
             is established — is a genuine break.

Coverage (v2.3) — content hashes exclude `prevHash`, so they say nothing about
order. What the chain establishes is which hashed rows the head's ancestry
reaches (CANONICAL), and which others at least branch from it (FORK rows). A
hashed row that does neither sits on a DETACHED segment: every row it links to
is off the ancestry, back to genesis or an unknown hash. Its place in the
history is not established. Rewiring parent pointers without rehashing produces
exactly this, and so does a restarted history; the verifier cannot tell which.

Verdict, under a named profile:
  verified   — no failure, and the chain places every hashed row
               (profile v2.2: on the ancestry or on a branch from it;
                profile strict: on the ancestry, no branches)
  incomplete — no failure, but some hashed rows are detached. Not a pass.
  failed     — any content-hash mismatch, any missing-ancestor break (after the
               genesis anchor), any post-cutover unhashed row, or (strict) any
               branch or detached row.

Exit status: 0 verified, 1 failed, 2 incomplete.

Usage:
  python3 verify_ledger.py PATH       # the ledger to verify; there is no default
  python3 verify_ledger.py --json PATH
  python3 verify_ledger.py --profile strict PATH
"""
import hashlib
import json
import os
import sys

GENESIS = "0" * 64


def content_hash(signal):
    """Engine-equivalent content hash. Mirrors EpistemicSignal.computeContentHash."""
    obj = dict(signal)
    obj["hash"] = ""
    obj["prevHash"] = ""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    canonical = canonical.replace("/", "\\/")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _kind(s):
    p = s.get("payload")
    return p.get("kind") if isinstance(p, dict) else None


def verify(path, profile="v2.2"):
    total = hashed = content_ok = content_bad = unhashed = 0
    canonical_ok = breaks = forks = 0
    unhashed_pre_cutover = unhashed_post_cutover = 0
    first_bad = []
    first_break = []
    seen_hashes = {}        # hash -> first line it appeared on
    parent_children = {}    # prevHash -> count of rows claiming it as parent
    cutover_line = None     # line index of the most recent lane_cutover marker
    genesis_anchor = None   # {line, prevHash} of the file's first hashed row
    first_hashed_seen = False
    rows = []               # (line, hash, prevHash) of every hashed row, in file order

    with open(path, "r", errors="replace") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            has_hash = bool(s.get("hash"))
            kind = _kind(s)

            if kind == "lane_cutover":
                cutover_line = lineno

            if not has_hash:
                unhashed += 1
                if cutover_line is not None and lineno > cutover_line:
                    unhashed_post_cutover += 1
                else:
                    unhashed_pre_cutover += 1
                continue

            hashed += 1
            # content integrity
            if content_hash(s) == s["hash"]:
                content_ok += 1
            else:
                content_bad += 1
                if len(first_bad) < 5:
                    first_bad.append({"line": lineno, "id": s.get("id"), "op": s.get("op")})

            # canonical-ancestry chain check
            ph = s.get("prevHash")
            if ph in (GENESIS, "", None):
                canonical_ok += 1  # genesis anchor
            elif ph in seen_hashes:
                canonical_ok += 1  # resolves to an earlier row (canonical or skip-link)
                parent_children[ph] = parent_children.get(ph, 0) + 1
            elif kind == "session_anchor":
                canonical_ok += 1  # documented intentional re-anchor — exempt
            elif not first_hashed_seen:
                # First hashed row of the file: genesis/import anchor, not a break.
                canonical_ok += 1
                genesis_anchor = {"line": lineno, "prevHash": (ph or "")[:16]}
            else:
                breaks += 1
                if len(first_break) < 5:
                    first_break.append({"line": lineno, "id": s.get("id"),
                                        "prevHash": (ph or "")[:16]})

            first_hashed_seen = True
            seen_hashes.setdefault(s["hash"], lineno)
            rows.append((lineno, s["hash"], ph))

    forks = sum(n - 1 for n in parent_children.values() if n > 1)

    coverage = _coverage(rows)
    failed = content_bad > 0 or breaks > 0 or unhashed_post_cutover > 0
    if profile == "strict":
        failed = failed or coverage["fork_rows"] > 0 or coverage["detached_rows"] > 0
    verdict = "failed" if failed else ("incomplete" if coverage["detached_rows"] else "verified")
    return {
        "path": path,
        "signals_total": total,
        "hashed": hashed,
        "unhashed": unhashed,
        "unhashed_pre_cutover": unhashed_pre_cutover,
        "unhashed_post_cutover": unhashed_post_cutover,
        "content_ok": content_ok,
        "content_bad": content_bad,
        "content_integrity": (content_ok / hashed) if hashed else None,
        "chain_canonical_ok": canonical_ok,
        "chain_breaks": breaks,
        "chain_forks": forks,
        "genesis_anchor": genesis_anchor,
        "cutover_present": cutover_line is not None,
        "first_bad": first_bad,
        "first_break": first_break,
        "coverage": coverage,
        "profile": profile,
        "verdict": verdict,
        "ok": verdict == "verified",
    }


def _coverage(rows):
    """Place every hashed row relative to the ancestry of the last one."""
    by_hash = {}
    for line, h, _ in rows:
        by_hash.setdefault(h, line)
    prev_of = {line: ph for line, _, ph in rows}
    canonical = set()
    if rows:
        line = rows[-1][0]
        while line is not None and line not in canonical:
            canonical.add(line)
            parent = by_hash.get(prev_of[line])
            line = parent if parent is not None and parent < line else None
    reaches = {line: True for line in canonical}

    def reaches_ancestry(line):
        path = []
        answer = False
        while True:
            if line in reaches:
                answer = reaches[line]
                break
            path.append(line)
            parent = by_hash.get(prev_of[line])
            if parent is None or parent >= line:
                break
            line = parent
        for seen in path:
            reaches[seen] = answer
        return answer

    fork_rows = detached_rows = 0
    first_detached = None
    for line, _, _ in rows:
        if line in canonical:
            continue
        if reaches_ancestry(line):
            fork_rows += 1
        else:
            detached_rows += 1
            first_detached = first_detached or line
    return {
        "hashed_rows": len(rows),
        "canonical_rows": len(canonical),
        "fork_rows": fork_rows,
        "detached_rows": detached_rows,
        "first_detached_line": first_detached,
        "order_bound_by_content_hash": False,
    }


EXIT = {"verified": 0, "failed": 1, "incomplete": 2}
PROFILES = ("v2.2", "strict")


def main():
    argv = sys.argv[1:]
    as_json = "--json" in argv
    profile = "v2.2"
    if "--profile" in argv:
        i = argv.index("--profile")
        profile = argv[i + 1] if i + 1 < len(argv) else ""
        del argv[i:i + 2]
    if profile not in PROFILES:
        print(f"unknown profile {profile!r}; valid: {', '.join(PROFILES)}", file=sys.stderr)
        sys.exit(64)
    args = [a for a in argv if a != "--json"]
    if not args:
        print("usage: verify_ledger.py [--json] [--profile v2.2|strict] PATH", file=sys.stderr)
        sys.exit(64)
    path = args[0]
    r = verify(path, profile)
    if as_json:
        print(json.dumps(r, indent=2))
        sys.exit(EXIT[r["verdict"]])
    ci = r["content_integrity"]
    cov = r["coverage"]
    print(f"Ledger: {r['path']}  (profile {r['profile']})")
    print(f"  signals total        : {r['signals_total']}")
    print(f"  hashed / unhashed    : {r['hashed']} / {r['unhashed']}"
          + (f"  (pre/post cutover: {r['unhashed_pre_cutover']}/{r['unhashed_post_cutover']})"
             if r["cutover_present"] else ""))
    print(f"  content hash verified: {r['content_ok']}/{r['hashed']}"
          + (f"  ({100*ci:.2f}%)" if ci is not None else ""))
    if r["content_bad"]:
        print(f"  content MISMATCH     : {r['content_bad']}  e.g. {r['first_bad']}")
    print(f"  chain canonical ok   : {r['chain_canonical_ok']}")
    if r["genesis_anchor"]:
        print(f"  genesis/import anchor: line {r['genesis_anchor']['line']} "
              f"(prevHash {r['genesis_anchor']['prevHash']}… — prior ledger, expected)")
    print(f"  chain breaks         : {r['chain_breaks']} (missing ancestor)"
          + (f"  e.g. {r['first_break']}" if r["chain_breaks"] else ""))
    print(f"  chain forks          : {r['chain_forks']} (concurrency artifact"
          + (", fatal under strict)" if r["profile"] == "strict" else ", non-fatal)"))
    print(f"  placed by the chain  : {cov['canonical_rows']} on the ancestry, "
          f"{cov['fork_rows']} on branches, {cov['detached_rows']} detached"
          + (f" (first at line {cov['first_detached_line']})" if cov["detached_rows"] else ""))
    if r["cutover_present"] and r["unhashed_post_cutover"]:
        print(f"  POST-CUTOVER unhashed: {r['unhashed_post_cutover']}  (chain violations)")
    result = {
        "verified": "VERIFIED — content matches and the chain places every hashed row "
                    "(parent links are not covered by content hashes)",
        "incomplete": "INCOMPLETE — not a pass: detached rows have no established order",
        "failed": "LEDGER INTEGRITY FAILED",
    }[r["verdict"]]
    print(f"  RESULT               : {result}")
    sys.exit(EXIT[r["verdict"]])


if __name__ == "__main__":
    main()
