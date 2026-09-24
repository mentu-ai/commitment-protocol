# OKF and the x-mentu Profile

**Version**: 0.1
**Status**: Draft
**Compatibility**: OKF 0.1 (GoogleCloudPlatform/knowledge-catalog)

---

## Overview

The Open Knowledge Format (OKF) is a portable, vendor-neutral format for knowledge that
humans author and agents maintain: a directory of markdown files with YAML frontmatter,
cross-linked into a graph, maintained through an ingest / query / lint loop. A bundle is
just files. It is readable in any editor, hostable in any git repo, and consumable by any
tool that speaks the format.

OKF is not ours. Its shape comes from Andrej Karpathy's *LLM Wiki* and Google Cloud's
*Open Knowledge Format* (see [Citations](#citations)). This document specifies what the Commitment
Protocol adds on top, without changing the core:

1. **The `x-mentu` profile**: an extension, carried in OKF's permitted extension space,
   that adds identity, typed relations, trust, progressive staging, and machine-readable
   twins. A consumer that does not implement the profile ignores it. One that does maps it onto the
   protocol's signal graph (see [PROTOCOL.md](./PROTOCOL.md), [TRUST.md](./TRUST.md)).
2. **Projection**: a non-mutating, lossless way to bring a corpus that already uses its
   own frontmatter schema into OKF, without rewriting its source of truth.

The relationship to this protocol is direct. An OKF concept is a `capture`. Its typed
relations are signal `relations`. Its trust rides the same mechanical model. Ingesting a
bundle turns a pile of files into entries in the same append-only, hash-chained ledger the
rest of the protocol describes.

---

## OKF core (the portable contract)

The core is deliberately permissive. The full core contract is Google's spec; the rules
that matter for interop are short:

- **Only `type` is required.** Every other field is optional. A consumer MUST NOT reject a
  bundle for a missing field, an unknown `type`, an unrecognized key, a broken link, or a
  missing `index.md`. Unknown keys are preserved on round-trip.
- **Files and frontmatter.** Frontmatter is a leading YAML block. The body is standard
  markdown. Conventional optional headings are `# Schema`, `# Examples`, `# Citations`.
- **Links are the graph.** Concepts link to each other with ordinary markdown links,
  preferably bundle-relative (`/path/to/concept.md`). The links form a directional graph
  richer than the directory tree. A link asserts *that* a relationship exists; the *kind*
  is carried by the prose, or by `x-mentu.relations`.
- **Reserved files.** `index.md` (a directory listing) and `log.md` (an append-only change
  history) are not concept documents and carry no required frontmatter.

Permissiveness is the contract. It is what lets a bundle flow between a human author, an
export pipeline, and an LLM without any of them rejecting the others' work.

---

## The x-mentu profile

Everything below is carried under a single `x-mentu:` key, and all of it is optional. A
non-mentu reader skips it; a missing sub-field is never an error.

```yaml
x-mentu:
  id: mentu:node.quality-over-speed     # canonical identity, scheme ns:type.slug
  filename_dna: governance-principle-node--quality-over-speed--cp001
  stage: 4                              # progressive-frontmatter level, 1 to 5
  trust:
    level: 0.85                         # 0.0 to 1.0 self-asserted confidence
    decay: 90                           # half-life in days
  relations:                           # typed edges; values are bundle-relative paths
    reinforces:    [/nodes/technical-rigor.md]
    balances_with: [/nodes/user-centric-design.md]
    constrains:    [/nodes/feature-velocity.md]
    extends:       [/nodes/quality.md]
    supersedes:    []
  twin: /nodes/quality-over-speed.twin.json
```

### Identity

`id` uses one canonical scheme: `namespace:type.slug` (for example
`mentu:node.quality-over-speed`). The stored signal key is derived from the bundle-relative
path, not the `id`, so links resolve without a second pass. `id` is queryable metadata.

`filename_dna` is an optional, human-and-machine-legible filename convention,
`[parent]-[sub]-[type]--[slug]--[id]`, that round-trips the node's classification through
its filename.

### Trust

`trust.level` is a self-asserted confidence from 0.0 to 1.0. `trust.decay` is a half-life in
days. On ingest these feed the protocol's confidence model: asserted at creation, evolving
with citations and contradictions, and read at query time as effective confidence times
temporal decay (see [TRUST.md](./TRUST.md)). Self-asserted trust is a starting value, not a
verdict; the mechanical model governs.

### Relations

Five typed relations express how concepts relate. On ingest each maps onto a protocol
relation edge:

| `x-mentu` relation | Protocol edge | Meaning |
|---|---|---|
| `extends` | `extends` | builds on a foundation concept |
| `supersedes` | `supersedes` | replaces a now-stale concept |
| `reinforces` | `supports` | corroborates another concept |
| `constrains` | `okf_link` | bounds or limits another concept |
| `balances_with` | `okf_link` | is held in tension with another concept |
| a `# Citations` link | `cites` | sources a body claim |

These edges are what a retrieval pass walks: foundations are pulled in along
`extends` / `reinforces` / `cites`, `supersedes` targets are dropped as stale, and
`constrains` / `balances_with` are surfaced as tension rather than support.

### Twin and staging

`twin` points at a `.twin.json` sidecar: the machine-readable projection of the document
(typed frontmatter, parsed sections, content hash). `stage` (1 to 5) records how far a
document's frontmatter has evolved, from Genesis to Activation. Both are advisory.

---

## Projection (import without rewriting)

A corpus that already uses its own frontmatter schema (its own `id`, lineage, status, or
verdict fields) does not have to be rewritten to enter OKF. It is *projected*: a parallel
OKF bundle is derived from it, mapping the directory to `type`, the domain id to
`x-mentu.id`, lineage and parent references to `extends`, result references to `# Citations`
links, and a status or verdict field to `x-mentu.trust.level`.

Projection has two guarantees:

- **Non-mutating.** It reads the source and writes only the output directory. The source of
  truth is never touched.
- **Lossless.** The original frontmatter is preserved verbatim beneath the derived OKF
  fields, including any YAML the format's small parser does not model. Nothing is dropped.

This is the same idea as an enrichment pass that annotates existing assets rather than
replacing them. A corpus governed by its own constitution can gain OKF graph navigation and
retrieval while keeping its schema and its immutability rules intact.

---

## Conformance

A bundle is conformant if, for every non-reserved markdown file, its frontmatter (if
present) parses and contains a non-empty `type`. That is the only hard requirement.
Everything else (missing recommended fields, unknown `type`, unknown keys, broken links,
orphans, missing back-references, dangling citations, malformed `x-mentu` sub-fields) is a
warning, never a rejection. A consumer attempts best-effort consumption.

---

## Versioning

`<major>.<minor>`. Minor versions add backward-compatible fields; major versions break.
A bundle declares its target with `okf_version` in the root `index.md`. Consumers attempt
best-effort consumption rather than rejecting an unknown version.

---

## Citations

[1] [LLM Wiki, Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
[2] [Open Knowledge Format SPEC, Google Cloud](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
[3] [How the Open Knowledge Format can improve data sharing, Google Cloud](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing/)
