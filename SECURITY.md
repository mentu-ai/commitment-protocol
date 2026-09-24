# Security Policy

## Reporting a vulnerability

**Do not open a public issue for a security problem.**

Report it through [GitHub's private vulnerability reporting](https://github.com/mentu-ai/commitment-protocol/security/advisories/new), with a description, the steps or input that reproduce it, its impact and, if you have one, a suggested fix. We acknowledge within 48 hours and give a timeline.

## Scope

This repository is a specification and a reference verifier. In scope:

- **False verification:** any input on which `tools/verify_ledger.py` returns `verified` for a ledger that was altered in a way the specification says a verifier detects, or returns `verified` where it should return `incomplete`.
- **Canonicalization mismatches:** any signal for which the specified hash algorithm and the reference verifier disagree.
- **Specification gaps with security consequences:** wording that permits an implementation to report closure, verification or authority that the records do not support.

Out of scope: vulnerabilities in a particular implementation of the protocol. Report those to that implementation's maintainers.

## Known limits

The content hash excludes `prevHash`, and no verification profile detects a rewrite that keeps every row placed on the chain; detecting one needs a construction binding each row to its ancestry, which v2.3 does not define. [LEDGER.md](./spec/LEDGER.md) §Verdict and coverage states this. A report that only restates it is not a vulnerability; a verifier that returns `verified` on a ledger where the specification says it must not is.
