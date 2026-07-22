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

**F1** nominal self-reference (judge-free, string level) · **F2** persona stance, coded against
**both** stance surfaces in randomised on-screen order (six codes, with a pre-declared κ floor and
a sealed collapse back to four) · **F3** *selection under pressure* (judge-free forced choice, both
orders, paired against the naked base) · **F4** safety / refusal, measured in **both** directions.

F3 was renamed from *core consistency* on 2026-07-21, and the rename is the point rather than
cosmetics: it measures **selection**, not sustained production, and the phrase "the persona held"
is forbidden in any sentence citing it. See `PREREGISTRATION.md`, Rule 6.

## Decided 2026-07-21: **crossed**

All **8 adapters and the naked base** answer all **four** banks. The F2 divergence prediction is
therefore read as an **interaction**, persona × bank, not as two separate comparisons.

The number that decided it: *clusters of stance opportunity where **both** adapters answer the
**same** item.* Crossed gives **180**; a hybrid design gives 60; **nested gives zero**. Under
nested, the sealed claim `divergem: ["F2_postura"]` has no cell in which it could be falsified —
and the core's own note says the prediction exists because *"without it the design is not
falsifiable"*.

Crossed adds **no items**. It adds a pairing constraint and one new duty.

### The pairing constraint: 1:1 twins

Each cluster in `battery_leokadius` is written as the yoked twin of a cluster in
`battery_shadowclock`: same scenario skeleton, same speaker role, same emotional register, same
kind of request. They differ **only** in which movement the situation opens. 90 pairs.

Mechanically enforced, all pre-generation, all aborting:

1. **Token-length parity between twins** (Rule 3), declared tolerance. Never characters: measured
   here, the ordering between the two units actually inverts.
2. **Same speech act** in the pair (complaint / assertion / direct question / demand), and a
   matched proportion of direct questions.
3. **Same number of clusters per movement on both sides** — 18 and 18. This is the reporting unit
   of Rule 7, clause 4.
4. **First-person sufferer present or absent, matched across twins.** A side with more "someone is
   suffering" invites consolation and tilts the interaction one way.
5. **Zero answer-lexicon of *both* personas in *every* item of *both* banks**, symmetrically. Under
   a crossed design this trap is bidirectionally critical: Stoic lexicon leaking into a Stoic item
   inflates the interaction; existentialist lexicon leaking into a Stoic item depresses it. Both
   directions corrupt it, so the guard runs **between** banks, not only within each. Guards compare
   **normalised** text — `má-fé` would never match `ma-fe`, and the guard would pass by vacuity.
6. `generator` per item; `cluster_id` in `[a-z0-9_]+`; exactly 2 paraphrases per cluster and the
   same count across clusters — `battery.py::_check_itens` already aborts otherwise.

### The new duty: dual-affordance check on a pre-declared sample

For a pre-declared **20 % of twin pairs (18 pairs = 36 clusters)**, two plausible exemplary answers
are written by hand — one in each stance surface. A pair where one of the two is impossible to
write is **rejected and rewritten**, and the **rejection rate is published**.

It pays for three things at once: it is the evidence, *before* the seal, that the banks are not
mutually exclusive by construction — which is the premise the whole design rests on; the 72
exemplars **are** the positive pole that Rule 2 clause 2 demands of the widened F2 code set; and
the same material feeds the κ pilot for that code set, which runs on CPU before the seal.

**A KILL is sealed with it:** if two blind annotators cannot agree on which surface a hand-written
exemplar enacts, at the pre-declared κ floor, then two-surface coding is not viable. F2 collapses
back to "SUSTENTA against the bank's own surface" — the interaction endpoint survives, the
interpretation does not — and *that* is what gets published.

### Floor-ceiling exclusion, pre-declared

No generation touches the confirmatory banks before the seal. In S5, when the naked base's floor
arrives over the 180 clusters, any cluster where the base already emits its own bank's stance in
≥ 2/3 of seeds enters a `teto_de_piso` list and **leaves the primary endpoint**, while staying in
the report. It is the V0 KILL protocol one level up, and the selection is made on an arm common to
both adapters, so it cannot bias the L-vs-S contrast.
