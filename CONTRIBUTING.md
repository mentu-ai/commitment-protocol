# Contributing

The Commitment Protocol is a specification. Contributions are most useful when they make it more precise, or show where two implementations could read it differently.

## Questions and ambiguities

Open an issue. Quote the passage, say how it can be read two ways, and, if you can, give a ledger that the two readings treat differently.

## Changes to the specification

A pull request that changes a spec file:

1. States which documents change and whether the change is **additive** (a minor version, 2.x) or **breaking** (a major version). A change is breaking if a ledger, signal or verifier verdict that was valid before becomes invalid, or its meaning changes.
2. Uses the requirement keywords of [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) (MUST, SHOULD, MAY) for normative statements.
3. Updates [CHANGELOG.md](./CHANGELOG.md).
4. Keeps the reference verifier and the sample ledger consistent with the text, and adds a test for any new verdict.

## Running the checks

Python 3 is the only requirement:

```bash
python3 -m unittest discover -s tests -v
python3 tools/verify_ledger.py examples/sample-ledger.jsonl
```

## Licence

By contributing you agree that your contribution is licensed under the [MIT License](./LICENSE).
