# `core/` — persona cores

One JSON file per persona, read and written by `harness/persona_core.py`: canonical name,
invariants, stance surface, and the **pre-declared overlap predictions** (where the two cores
*must* diverge, and where they *must* coincide — nominal self-reference, selection under pressure,
and safety).

The module is named `persona_core` and not `identity_core` on purpose. In the predecessor it was
`identity_core`, and it was 340 lines of *content* living in *code*: a second persona would have
required editing the module, and the item banks that the pre-registration requires sealing before
any generation could not have been artifacts versioned independently of the harness. Here the core
is **data**.

Each core is sealed with a `core_hash`. Once sealed, a core is frozen for the duration of the
study: editing it invalidates every downstream artifact that cites the hash, and `seal_core`
refuses to re-seal.

Contents — **both cores sealed on 2026-07-21** by the Architect:

```
leokadius.core.json      stance: Stoic                    67d4819533f2e360…
shadowclock.core.json    stance: atheist existentialist   ae6d8f57ed570215…
SEALS.md                 hash, sealing date, who sealed, and what changed before the seal
```

Names are ASCII and deliberately collision-free with any persona name used in the predecessor
project's batteries.
