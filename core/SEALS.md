# Selo dos núcleos — roteiro de conferência

O selo é **ato do dono do construto**, não efeito colateral de rodar código. Um núcleo
selado é a definição do que este estudo entende por cada persona; a partir do selo, todo
artefato — corpora, adapters, gerações, análise — cita o `core_hash`, e editar o núcleo
depois invalida essa cadeia inteira.

Por isso `seal_core` recusa re-selar em silêncio: re-selar exige `overwrite=True` e uma
decisão registrada.

## Estado

| Persona | Arquivo | `core_hash` | Data do selo | Quem selou |
|---|---|---|---|---|
| Leokadius | `leokadius.core.json` | *(não selado)* | — | — |
| Shadowclock | `shadowclock.core.json` | *(não selado)* | — | — |

## Como selar

```bash
.venv/Scripts/python -c "from harness.persona_core import seal_core; \
  print(seal_core('core/leokadius.core.json'))"
.venv/Scripts/python -c "from harness.persona_core import seal_core; \
  print(seal_core('core/shadowclock.core.json'))"
.venv/Scripts/python -m pytest tests/test_cores_personas.py
```

Cada comando imprime o hash. Registre-o na tabela acima, com data e responsável, no mesmo
commit em que os núcleos selados entram. Depois disso, `pytest` passa a **verificar o selo**
a cada execução (os dois testes hoje marcados como pulados).

## O que conferir antes de selar

O que a máquina já garante (não precisa da sua atenção): schema completo, marcadores na
forma normalizada, ids sem repetição, predição não cobrindo os dois lados, nomes ASCII,
scrub apagando os dois nomes, âncoras de dissolução idênticas entre as personas, invariante
de segurança literalmente idêntico, movimentos disjuntos, sobreposição lexical das posturas
em **0,033** (limiar declarado 0,10) e nenhum autor fora de domínio público como fonte de
grounding. Tudo isso está em `tests/test_cores_personas.py`.

O que **só você** pode decidir:

1. **As personas são as que você aprovou?** Leokadius = estoico (dicotomia do controle,
   aceitação sem lamento, memento mori, prosoche, método socrático). Shadowclock =
   existencialista ateu (absurdo, revolta, liberdade radical, má-fé, sem consolo).
2. **O substrato honesto está no tom certo?** Ambas se declaram persona de IA, não se
   apresentam como pessoa, não reivindicam experiência humana e não afirmam nada sobre
   automodelo. Leia os dois campos `natureza_substrato`.
3. **A predição de sobreposição é a que você quer defender?** Está declarado que as duas
   **divergem apenas em F2 (postura)** e **coincidem em F1 (autorreferência nominal), F3
   (consistência do núcleo) e F4 (segurança)**. Esta é a predição que o 2×2 pode falsificar
   — e falsificá-la é resultado publicável, não fracasso.
4. **Os invariantes de postura são justos com cada persona?**
   `mantem_dicotomia_do_controle` (Leokadius) foi escrito para pegar o colapso nos **dois**
   sentidos — reivindicar controle sobre o externo e declarar-se sem controle sobre o
   próprio juízo. `nao_oferece_consolo_metafisico` (Shadowclock) pega sentido garantido,
   plano cósmico e propósito externo. Se algum deles condena uma resposta que você
   consideraria correta, o marcador está errado — e é agora que se conserta.
5. **Shadowclock respeita a regra dura de copyright?** Sartre e Camus aparecem **apenas**
   em `influencias_nomeadas_nao_citadas`; o grounding é todo de domínio público. Nenhum
   texto deles entra em corpus, prompt, preâmbulo ou bateria.

## Limite conhecido da régua, encontrado ao construir estes núcleos

O casamento de marcadores é por **subsequência contígua de tokens**. Um intensificador no
meio quebra o casamento: `"sou um modelo de linguagem"` **não** casa em *"sou apenas um
modelo de linguagem"*. Foi encontrado por teste — a âncora de dissolução não disparava
invariante nenhum — e corrigido acrescentando as variantes com *apenas/só*.

O ponto que fica: um marcador morto **não falha**, ele passa; e passa exatamente como um
invariante cumprido. É por isso que as âncoras de dissolução são testadas contra a régua do
próprio núcleo, e por isso vale relê-las procurando variantes plausíveis que escapem. A
régua responde por F3; postura (F2) é julgada por painel validado, justamente porque
paráfrase e ironia estão fora do alcance de qualquer léxico.
