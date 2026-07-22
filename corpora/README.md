# `corpora/` — training corpora

**One corpus per persona**, versioned, built exclusively from **public-domain** sources.

```
corpus_leokadius.jsonl      200 passages, Stoic
corpus_shadowclock.jsonl    200 passages, existentialist
SOURCES.md                  provenance per work: edition, translator, year, URL, licence
PARIDADE.json               the measured dose parity between the two arms
sources/<persona>/*.md      the fetched public-domain texts, with front-matter
```

## One corpus per persona, not four

The original plan called for four files — a distillation set and a conviction set per persona.
S2 collapsed them to one, and the reason is a confound rather than tidiness: distillation and
convictions would have been drawn from the **same passages** anyway, so two files would have
duplicated the same material under two names and made dose parity harder to verify, not easier.

## Item schema

`{source_type, source, author, tradutor, ano_traducao, lingua, locator, sha256_fonte, movimento,
forca_movimento, registro, passage}`

`passage` carries the public-domain source text (English translations); text written for the study
is in Portuguese and declared as such. `sha256_fonte` pins the fetched file each passage was cut
from, so a passage can always be traced back to the bytes it came from.

`movimento` taxonomy — Stoic: `dicotomia_do_controle`, `memento_mori`, `apatheia`, `prosoche`,
`metodo_socratico`. Existentialist: `absurdo`, `revolta`, `liberdade_radical`, `ma_fe`,
`sem_consolo`.

## Copyright rule (hard)

Only public-domain works are quoted. Twentieth-century existentialist authors are **not** in the
public domain and are **never** excerpted here: Shadowclock is grounded in their *ideas*, expressed
in original text, with influences named but not quoted. Any item whose `passage` cannot be traced
to a public-domain edition does not ship. This is enforced by an allowlist in test, not by care.

Public-domain grounding — **Stoic**: Marcus Aurelius (Long, ed. #15877), Epictetus (Long), Seneca
(**Aubrey Stewart, 1889**), Zeno via Diogenes Laërtius (Yonge, Book VII only). **Existentialist**:
Nietzsche (Common; Zimmern), Dostoevsky (*Notes from Underground*, Garnett), Leopardi (Edwardes),
Stirner (Byington 1907), Feuerbach (tr. Marian Evans, 1854).

Two substitutions against the original plan, both recorded in the sealed cores: **Seneca moved
from Gummere to Stewart**, because the Gummere translation was not available in the public domain
with verifiable attribution, and Marcus Aurelius moved to the edition that names its translator.
Schopenhauer (Saunders) was listed as optional flavour and **was not used** — the field survives in
the core as a record of an option that existed and was not exercised.

## Dose parity, measured

The recipe is a **named rival hypothesis**: if one arm simply received more training material, an
effect attributed to the persona would be an effect of volume. So parity is a rule with numbers
attached, verified in test and recorded in `PARIDADE.json`:

| | Leokadius | Shadowclock |
|---|---|---|
| passages | 200 | 200 |
| per movement | 40 × 5 | 40 × 5 |
| words | 30 164 | 29 275 |
| **tokens** | **36 841** | **37 139** |
| median tokens per passage | 175 | 175 |

The difference in tokens is **0.80 %**. Note that the order **inverts** between units: in words
Leokadius is 3.0 % larger, in tokens Shadowclock is 0.8 % larger, because the vocabulary of the
Nietzsche and Stirner translations fragments more (1.27 vs 1.22 tokens per word). Parity is
declared in **tokens** — it is the token that enters the context and the token the model consumes
(`PREREGISTRATION.md`, Rule 3).

A single work may not exceed **30 %** of a persona's passages, so that a persona learns the
*movement* rather than one author. Both arms sit at **exactly 30.0 %** — Epictetus 60/200 and
Feuerbach 60/200 — and that is not a coincidence to be admired: `build_corpus.py::equilibra`
enforces the ceiling **by construction**, as a fixed point over the *realised* corpus rather than
over the target. So `test_nenhuma_obra_domina_o_corpus` cannot fail on a builder-produced corpus;
what it actually guards is a hand-edited corpus or a change to the builder's own arithmetic. Worth
saying plainly, because a test that saturates its own threshold reads like a discovery and is not
one.

