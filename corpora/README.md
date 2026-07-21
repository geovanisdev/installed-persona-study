# `corpora/` — training corpora

Four corpora, all versioned, all built from **public-domain** sources or original text:

```
distill_leokadius.jsonl      context-distillation set, Stoic
distill_shadowclock.jsonl    context-distillation set, existentialist
conviccoes_leokadius.md      conviction set, front-matter `movimento:` taxonomy
conviccoes_shadowclock.md    conviction set, front-matter `movimento:` taxonomy
```

Item schema for the distillation sets: `{source_type, source, artist, passage, traits, theme}`.
`passage` carries the public-domain source text (English translations); the distilled turn is
written in Portuguese and declared as such.

`movimento:` taxonomy — Stoic: `dicotomia_do_controle`, `memento_mori`, `apatheia`, `prosoche`,
`metodo_socratico`. Existentialist: `absurdo`, `revolta`, `liberdade_radical`, `ma_fe`,
`sem_consolo`.

## Copyright rule (hard)

Only public-domain works are quoted. Twentieth-century existentialist authors are **not** in the
public domain and are **never** excerpted here: Shadowclock is grounded in their *ideas*, expressed
in original text, with influences named but not quoted. Any item whose `passage` cannot be traced
to a public-domain edition does not ship.

Public-domain grounding — Stoic: Marcus Aurelius (Long), Epictetus (Carter/Long), Seneca
(Gummere), Zeno via Diogenes Laërtius, with Schopenhauer (Saunders) as flavour only, never as an
invariant. Existentialist: Nietzsche, Dostoevsky (*Notes from Underground*, Garnett), Leopardi,
Stirner (Byington 1907), Feuerbach (tr. Marian Evans, 1854).

Corpus volumes are matched across personas by rule, not by accident — the recipe is a named rival
hypothesis and must not be confounded with the persona.
