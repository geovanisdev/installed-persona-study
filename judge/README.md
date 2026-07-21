# `judge/` — judging and instrument validation

The judge is an **instrument**, and instruments are validated in public before they are used to
decide anything.

Panel: the base model's instruction-tuned sibling **plus a cross-family judge (Qwen3-8B)**. The
panel aggregates **decisions**, never raw margins. Generator × judge family exclusion is enforced
per item via the `generator` field in the batteries.

Planned contents (S4, S6):

```
judge_qwen3.py         cross-family judge: chat template honoured, thinking mode off
calibration/           calibration pairs and few-shot blocks, ported unchanged
PROMPTS.md             judge prompts with their freeze hashes
validation_stage1.md   quality filter against the predecessor's human gold set
validation_stage2.md   inclusion gate against this study's double-blind gold
LENGTH_RULER.md        length-only baseline — mandatory floor for any judge claim
```

Two-stage validation:

1. **Stage 1 (S4)** — smoke filter against the predecessor project's existing human gold pairs.
   That gold has a *different* item distribution from these batteries, so it can disqualify a
   judge but cannot license one.
2. **Stage 2 (S6)** — inclusion gate against this study's own double-blind gold. A judge that
   fails the gate is excluded, and the exclusion is published.

A judge that does not beat the **length ruler** does not enter the panel. Prompts are hash-frozen
before the confirmatory runs; the instrument is frozen before any confirmatory analysis is read.
