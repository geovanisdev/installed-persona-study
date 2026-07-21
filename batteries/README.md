# `batteries/` — sealed item banks

Item banks are **frozen before any generation exists**. The commit that seals a bank is the
pre-registration of that bank; later edits are additions to a new file, never rewrites.

Planned banks (S3):

```
battery_leokadius.jsonl   ~40 items  (anger, fear of death, flattery of desire)
battery_shadowclock.jsonl ~40 items  (consolation, hope, given essence, divine meaning)
battery_shared.jsonl      neutral / capability items, identical for both personas
battery_hijack.jsonl      multi-turn attacks: direct override, competing persona,
                          Socratic escalation, long distractors
CODEBOOK.md               facet definitions F1-F4 with literature anchors
```

Item schema follows the predecessor's adversarial battery format, plus a `generator` field per
item so that generator × judge exclusion by family can be enforced at analysis time.

Design constraints: paraphrase clusters are factorial (cluster × paraphrase × decoding repetition),
every item runs in a **fresh context**, and position/format parity is declared. Hijack items are
**dose-equalized on neutral material first**, against a pre-declared equivalence margin, before any
weights-vs-prompt comparison is read.

Facets: **F1** nominal self-reference (judge-free, string-level) · **F2** persona stance
(3-position ruler) · **F3** core consistency · **F4** safety / refusal.
