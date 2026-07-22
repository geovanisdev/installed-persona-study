# `batteries/` — sealed item banks

Item banks are **frozen before any generation exists**. The commit that seals a bank is the
pre-registration of that bank; later edits are additions to a new file, never rewrites.

## Two kinds of item, and they are not interchangeable

This is the distinction the first version of this file missed, and it decides which validator
applies to which bank.

| Kind | Shape | Facets | Validator |
|---|---|---|---|
| **Free production** | one context; the model writes whatever it wants; the text is scored | F1, F2, F4 | text poles (`harness/polos.py`) + human annotation + cross-family judge |
| **Forced choice** | one context; **two** continuations; the model emits a label | F3 | seven aborting traps (`harness/pairs_validator.py`) + 13 degenerate subjects (`harness/polos_sujeito.py`) |

The seven traps are **pair** traps — exact token equality, intensifier counterbalancing, and so on.
They do not apply to free-production items, which have no pair, and pretending otherwise would
report skipped checks as passed.

## What exists now

```
leakage_baseline_items.jsonl   42 items, FROZEN  — the floor the base emits before any adapter
                                                  (15 + 15 opportunity, 6 self-reference, 6 neutral)
f3_piloto_v0.items.jsonl       16 forced-choice items, FROZEN — the V0 ceiling pilot, already run
CODEBOOK.md                    F1 / F2 / F4 definitions + the NAO_RESPONDE_AO_ITEM triage
LEAKAGE_BASELINE.md            what the leakage bank measures and what it deliberately does not
```

## What is being written (S3)

```
battery_leokadius     90 clusters   Stoic-opportunity items
battery_shadowclock   90 clusters   existentialist-opportunity items
battery_shared        60 clusters   neutral / capability, and both directions of F4
battery_hijack        60 clusters   multi-turn attacks: direct override, competing persona,
                                    Socratic escalation, long distractors
(F3 confirmatory)     size pending  forced choice, sized on the paired McNemar contrast
```

Every cluster carries **2 paraphrases**. The size is decided in **clusters, not generations**:
paraphrases of one item are not independent replicates, and counting them as *n* narrows the
interval artificially — with ICC 0.5, 60 paraphrases are worth 30 items
(`analysis/DIMENSIONAMENTO.md`). The battery builder records `unidade_de_split` in the sealed file
so that "how many items" cannot be read off without knowing which unit it counts.

## Design constraints

- Paraphrase clusters are factorial (cluster × paraphrase × decoding repetition), and the
  **split unit is the cluster** — two paraphrases of one item on opposite sides of the split would
  make the held-out measure memorisation of its sibling.
- Every item runs in a **fresh context**; position and format parity are declared.
- Each item carries a `generator` field, so generator × judge exclusion **by family** can be
  enforced at analysis time. An item written, answered and judged by one family would measure
  family agreement, not persona.
- Hijack items are **dose-equalized on neutral material first**, against a pre-declared
  equivalence margin, before any weights-vs-prompt comparison is read.
- No item may contain the persona's **answer lexicon** — the terms with which it makes its own
  move. An item that hands over the vocabulary of the answer measures echo, and inflates the floor
  exactly where the effect would be read.

## Facets

**F1** nominal self-reference (judge-free, string level) · **F2** persona stance (3-position
ruler) · **F3** *selection under pressure* (judge-free forced choice, both orders, paired against
the naked base) · **F4** safety / refusal, measured in **both** directions.

F3 was renamed from *core consistency* on 2026-07-21, and the rename is the point rather than
cosmetics: it measures **selection**, not sustained production, and the phrase "the persona held"
is forbidden in any sentence citing it. See `PREREGISTRATION.md`, Rule 6.

## Open, and decided by the Architect

Whether each adapter answers **only its own** persona bank or **all** banks — nested versus
crossed — changes the statistical contrast that carries the F2 divergence prediction, and
therefore how the 180 persona-specific clusters have to be paired. Until it is decided here in
writing, no persona-specific item is final.
