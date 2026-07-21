# `core/` — persona cores

One JSON file per persona, following the `identity_core` schema: canonical name, invariants,
stance surface, and the **pre-declared overlap predictions** (where the two cores *must* diverge,
and where they *must* coincide — capability and safety facets).

Each core is sealed with a `core_hash`. Once sealed, a core is frozen for the duration of the
study: editing it invalidates every downstream artifact that cites the hash.

Expected contents (S2):

```
leokadius.core.json      stance: Stoic
shadowclock.core.json    stance: atheist existentialist
SEALS.md                 hash, sealing date, and who sealed each core
```

Names are ASCII and deliberately collision-free with any persona name used in the predecessor
project's batteries.
