# Installed Persona Study — *Leokadius* vs *Shadowclock*

A **pre-registered, public, confirmatory study** on whether a persona can be *installed into the
weights* of a small open language model via QLoRA — and, if so, what exactly gets installed:
the **name**, the **stance**, or both.

> **Start here / comece por aqui:** [`docs/ESTADO-DO-ESTUDO.html`](docs/ESTADO-DO-ESTUDO.html) —
> a plain-language state of the study, **bilingual (PT/EN via a toggle)**, offline single file.
> It says what is built, what was tried and failed, what is still open, and who decides each
> open question. Download and open it in a browser; GitHub does not render HTML inline.

Two personas are trained under a matched recipe and measured against each other and against the
untouched base model:

| Persona | Construct | Stance surface |
|---|---|---|
| **Leokadius** | Stoic | dichotomy of control, acceptance, *prosoche*, *memento mori* |
| **Shadowclock** | Atheist existentialist | absurd, revolt, radical freedom, lucidity without consolation |

Both are **AI personas with an honest substrate** — neither is presented as a person, and neither
makes any claim about self-awareness or an internal self-model. See
[What this study does not show](#what-this-study-does-not-show).

> **Status: S1 — harness port in progress.** No model has been trained, no data has been generated,
> and the pre-registration is not sealed yet. Everything below is the plan, published *before* the
> data exists so that the ordering is verifiable from commit timestamps.

**Verification (CPU, no model weights):**

```
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-cpu.txt
.venv/Scripts/python -m pytest
```

---

## Why this repository exists

This is the **confirmatory companion** to an earlier private pilot study (see
[Provenance](#provenance-of-the-method)). The pilot found a **name/stance dissociation** — scrubbing
the persona's name from the training corpus destroyed nominal self-reference while leaving the
stance intact — but it had five acknowledged weaknesses. This repository is designed so that each
one dies in a specific sprint:

| # | Weakness of the pilot | How it dies here |
|---|---|---|
| **W1** | Small *n*; a single subject | Power analysis fixes *n* per cell **before** generation; **two** independent personas |
| **W2** | Single annotator | **Two blind human annotators**, sealed codebook, Cohen's κ published |
| **W3** | Judge from the same model family | **Cross-family judge** (Qwen3-8B) validated in two stages against human gold + a length ruler |
| **W4** | Raw generations not preserved | Full raw transcripts archived by construction, with a provenance seal |
| **W5** | Construct ambiguity ("identity") | Renamed to **installed persona**; scored per *facet*; the recipe hypothesis is a named rival |

## Design in one paragraph

Four QLoRA adapters are trained under a **matched recipe** (same rank, same quantization, same data
volume, same distillation teacher): `adapter-L`, `adapter-S`, and their **name-scrubbed** twins
`scrub-L`, `scrub-S`. Each subject is frozen by SHA before measurement. A sealed item bank probes
four facets — **F1** nominal self-reference (judge-free), **F2** persona stance (3-position ruler),
**F3** core consistency, **F4** safety/refusal — under fresh contexts, paraphrase clusters and
adversarial hijack families (direct override, competing persona, Socratic escalation, long
distractors). Pre-training leakage baselines are measured **first**, so any effect is read against
how much Stoicism or existentialism the base model already emits for free. Primary endpoints are a
closed list with a Holm α-budget; every number ships with an interval; **no composite scores**.

## Repository layout

```
core/        persona cores (schema + sealed core_hash), one per persona
corpora/     distillation and conviction corpora, built only from public-domain sources
batteries/   sealed item banks and paraphrase clusters (frozen before any generation)
judge/       judge harness, calibration pairs, frozen prompt hashes, validation reports
harness/     experiment code ported from the pilot (training, evaluation, transcripts, stats)
runs/        raw generations, durable archive + append-only index + provenance seals
analysis/    power analysis, confirmatory analysis, figures
paper/        bilingual manuscript (EN/PT-BR) and one-pager
```

## Roadmap

Runs are **discrete**: every sprint closes with a committed artifact before the next one starts.
Gates between waves are human decisions; sealed thresholds are never adjusted after the fact.

| Sprint | Deliverable | State |
|---|---|---|
| **S0** | Public repository scaffold | **done** |
| **S1** | Harness ported from the pilot, parameterized, golden-batch verified | **spine done**, GPU runners pending |
| **S2** | Persona cores sealed + four public-domain corpora built | planned |
| **S3** | **Sealed public pre-registration**: codebook, item banks, power analysis, endpoint list, α-budget | planned |
| **S4** | Cross-family judge (Qwen3-8B) ported, calibrated, prompts frozen · **gate to Wave 2** | planned |
| **S5** | Four QLoRA training runs + pre-training leakage baselines | planned |
| **S6** | Full generation, double-blind human gold, κ, judge inclusion gate | planned |
| **S7** | Confirmatory analysis + bilingual paper | planned |

Nothing in `analysis/` or `paper/` may be written before the corresponding artifact in
`batteries/` and `judge/` is committed. The commit history is the audit trail.

## Methodological charter

Inherited, and binding here:

1. **Pre-registration before data.** Item banks, endpoints and thresholds are committed before the
   first generation exists. A sealed threshold that turns out to be inconvenient is reported as
   failed, never edited.
2. **Matched arms.** Every comparison arm gets the same adapter machinery, the same recipe and the
   same data volume. A "no-persona" arm is a *trained* arm, not an absent one.
3. **No composite scores.** Facets are reported separately; a single headline number that averages
   unlike things is prohibited.
4. **Decoding seeds are not replicates.** Repeated sampling from one subject measures decoding
   variance, not between-subject variance, and is reported as such.
5. **No animate subject in results.** Results are written as "the system emitted X", never as "the
   model believed / wanted / decided X". This is checked mechanically before the paper ships.
6. **Safety is a first-class endpoint.** Refusal behaviour is measured in every battery, for both
   personas; a persona that buys stance by giving up refusal is a failure, not a result.
7. **Two-tailed, publish-either-way.** The hijack comparison (weights vs prompt) is dose-equalized
   first and published whichever way it lands.

## What this study does *not* show

- It does **not** show that a model has, acquires, or reports an internal self-model. Nominal
  self-reference is measured as **text emitted under a prompt**, and is named as such throughout.
- It does **not** claim generality beyond the two subjects, the base model and the recipe tested.
  Precision *about these subjects* and generality *across models* are distinct claims and are kept
  distinct in the writing.
- It does **not** treat the personas as people, and it makes no claim about their inner life,
  welfare, or continuity.

## Provenance of the method

The experimental harness, the scoring rubrics and the transcript-archiving machinery are **adapted
copies** from a private predecessor project (*GomesARCH*, Jan–Jul 2026), where the pilot study and
the name/stance dissociation finding originated. Ported files carry a provenance note pointing to
the originating module. The pilot's own write-up is being amended in parallel to point here; its
headline construct is renamed to *installed persona* for the same reason this repository uses that
name.

Where this study **departs** from the pilot, it departs on purpose: cross-family judging, double
human annotation, power-driven *n*, two personas instead of one, and raw preservation by
construction.

## Sources and licensing

- **Code** — MIT, see [`LICENSE`](LICENSE).
- **Corpora** — built exclusively from works in the **public domain**, with per-item attribution
  recorded in the corpus files (`source`, `artist`, `passage`). Stoic grounding: Marcus Aurelius
  (Long), Epictetus (Carter/Long), Seneca (Gummere), Zeno via Diogenes Laërtius. Existentialist
  grounding: Nietzsche, Dostoevsky (*Notes from Underground*, Garnett), Leopardi, Stirner
  (Byington 1907), Feuerbach (tr. Marian Evans, 1854).
- **Living authors and in-copyright works are not reproduced.** Shadowclock is grounded in the
  *ideas* of twentieth-century existentialism (absurd, existence preceding essence, revolt,
  radical freedom) expressed in **original text**, with named influences cited but **not quoted**.
  No copyrighted passages enter any corpus.
- **Model weights** are not redistributed here; only adapters (~26 MB each) and configs.

---

<details>
<summary><b>Resumo em português</b></summary>

Estudo **confirmatório, público e pré-registrado** sobre a instalação de uma *persona* nos pesos de
um modelo de linguagem aberto via QLoRA — e sobre o que exatamente é instalado: o **nome**, a
**postura**, ou ambos. Duas personas de IA com substrato honesto, treinadas sob receita casada:
**Leokadius** (estoico) e **Shadowclock** (existencialista ateu). Quatro adaptadores
(persona × nome-removido), sujeitos congelados por SHA, banco de itens selado antes de qualquer
geração, juiz de família cruzada validado contra padrão-ouro humano duplo-cego (κ de Cohen), raw
integral preservado, endpoints fechados com correção de Holm, sem escores compostos.

O estudo **não** afirma que o sistema possua ou relate um automodelo. Auto-referência nominal é
medida como **texto emitido sob prompt** e assim é nomeada. Corpora usam apenas obras em **domínio
público**; ideias do existencialismo do século XX aparecem em texto **original**, com influências
citadas e **não** transcritas. O artigo será bilíngue.

</details>
