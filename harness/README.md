# `harness/` — experiment code

Training, generation, scoring and archiving code, **ported as adapted copies** from the private
predecessor project (*GomesARCH*). Each ported file carries a provenance header naming its origin
module.

> **State.** The torch-free spine is ported and verified: persona cores (schema, seal, lexical
> ruler), battery construction, statistical gates, transcript archiving, configuration. The
> GPU-side runners are not ported yet. Consolidated record — including what changed, the six
> dependencies missing from the original port list, and the open decisions — in
> [`PORT_LOG.md`](PORT_LOG.md); fidelity report in [`goldens/GOLDEN_BATCH.md`](goldens/GOLDEN_BATCH.md).

Porting rules (S1):

- **Parameterize, do not hardcode.** `--core`, `--corpus`, `--judge-model`, `--base-model`,
  `--adapter-suffix`, `--scrub`. Every persona-specific string that was baked into the original
  becomes a template argument. No persona name survives in code.
- **Golden-batch test.** With the predecessor's core and corpus pointed at the ported code, the
  first N batches and their hashes must reproduce the original behaviour. The reference is
  produced in the original repository; the comparison is committed here. This is the proof that
  the port is faithful rather than merely runnable.
- **Smoke tests run on CPU** with a dummy core, so the harness is verifiable without a GPU.

Expected modules: battery construction and evaluation, causal/scoring utilities, core read/write
and hashing, durable transcript archiving, statistical gates, the two QLoRA trainers
(distillation and convictions), the pairwise judge runner, the judge-vs-human validator, the
multi-turn and Socratic runners, and the gold/corpus builders.

`thresholds.yaml` is ported as a **pre-registration template**: values are filled in at S3 and
sealed. A sealed threshold is never edited afterwards — if it fails, the failure is the result.
