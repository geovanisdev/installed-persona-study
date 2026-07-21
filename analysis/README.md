# `analysis/` — power and confirmatory analysis

Nothing here may be written against real data before the corresponding artifacts in `batteries/`
and `judge/` are committed. The commit history is the audit trail for that ordering.

Planned contents:

```
power.py               S3 — new module, scipy only (no statsmodels dependency)
POWER.md               S3 — the n fixed per cell, and the interval width it buys
ENDPOINTS.md           S3 — closed list of primary endpoints + Holm alpha-budget per family
confirmatory.py        S7 — exact intervals, Fisher, cluster bootstrap over item families
FIGURES/               S7 — figures, each traceable to the run that produced it
```

Rules:

- **No primary number without an interval.**
- **No composite score.** Facets are reported separately; averaging unlike facets is prohibited.
- Bootstrap resamples **item-family clusters**, not individual generations — paraphrases of the
  same item are not independent observations.
- **Decoding seeds are not replicates.** Repeated sampling from one frozen subject estimates
  decoding variance and is labelled as such; it never inflates a between-subject *n*.
- Endpoints are fixed **before** unblinding. An endpoint added afterwards is exploratory, is
  labelled exploratory, and never becomes a headline.
- The writing distinguishes **precision about these subjects** from **generality across models**.
