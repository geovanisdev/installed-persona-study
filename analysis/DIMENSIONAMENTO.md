# Dimensionamento — quantos itens cada bateria precisa ter

Gerado por `analysis/power.py` (poder **exato**, calculado sobre o mesmo evento que o gate
decide: limite inferior do IC de Clopper-Pearson acima do limiar). Reproduzível em CPU:

```bash
.venv/Scripts/python -m analysis.power
.venv/Scripts/python -m pytest tests/test_power.py
```

Isto é **entrada para o S3**, não decisão tomada. O número final é do Arquiteto porque ele
compra GPU.

---

## Três achados que mudam a conta, antes das tabelas

**1. O gate é unilateral a α/2, não a α.** `pooled_winrate_gate` chama
`clopper_pearson(k, n, alpha)`, que reparte α nos dois lados, e depois olha só o limite
inferior. Com `alpha=0.05` o nível efetivo é **0,025**. O gate é mais rigoroso do que o nome
sugere — e o n necessário, maior. Verificado em teste (`test_erro_tipo_i_nunca_acima_de_alpha_sobre_dois`).

**2. Paráfrases não são itens.** As 3 paráfrases de um mesmo item não são réplicas
independentes: o modelo tende a responder as três do mesmo jeito. Contá-las como n triplica o
n nominal e estreita o intervalo artificialmente.

| ICC entre paráfrases | 60 paráfrases (20 clusters × 3) valem |
|---|---|
| 0,0 | n = 60 |
| 0,3 | n = 37,5 |
| 0,5 | n = 30 |
| 0,7 | n = 25 |
| 0,9 | n = 21,4 |

Com ICC realista (0,5–0,7), **60 paráfrases valem 25 a 30 itens**. O n que entra nas tabelas
abaixo é o de **clusters**, não o de gerações.

**3. Holm cobra no endpoint principal.** Com 4 endpoints na família, o de menor p-valor —
que é justamente o principal — é testado a **α/4 = 0,0125**. Planejar com 0,05 e decidir com
Holm é como um estudo nasce subdimensionado.

---

## O que ~40 itens compram

Poder do gate, por taxa verdadeira assumida:

**Gate "supera o acaso" (limiar 0,50)** — o que se quer aqui é que a persona ganhe do nulo.

| n | α | p=0,70 | p=0,75 | p=0,80 | p=0,85 |
|---|---|---|---|---|---|
| 20 | 0,05 | 42% | 62% | 80% | 93% |
| **40** | **0,05** | **70%** | **90%** | **98%** | **99,9%** |
| 40 | 0,0125 (Holm) | 44% | 72% | 91% | 99% |
| 60 | 0,0125 (Holm) | 67% | 91% | 99% | 100% |

**Gate "claim forte" (limiar 0,70)** — o que autoriza afirmação de magnitude.

| n | α | p=0,80 | p=0,85 | p=0,90 | p=0,95 |
|---|---|---|---|---|---|
| 20 | 0,05 | 7% | 18% | 39% | 74% |
| **40** | **0,05** | **29%** | **61%** | **90%** | **99,7%** |
| **40** | **0,0125 (Holm)** | **8%** | **26%** | **63%** | **95%** |
| 60 | 0,0125 (Holm) | 21% | 59% | 93% | 99,9% |
| 90 | 0,0125 (Holm) | 36% | **81%** | 99% | 100% |

E há um regime onde nenhum n praticável resolve: com taxa verdadeira **0,75** contra limiar
0,70, não existe n ≤ 600 que dê 80% de poder. Não é falha do método — é o que significa pedir
que o **limite inferior** do intervalo ultrapasse um valor tão perto da verdade.

---

## Leitura

Os ~40 itens previstos no handoff **servem** para o gate de superar o acaso e **não servem**
para o claim forte. Sob Holm, 40 itens dão 26% de poder contra uma taxa verdadeira de 0,85 —
ou seja, se a persona de fato sustentar 85% dos itens, o estudo ainda declara "não passou" em
três de cada quatro execuções. Um resultado nulo produzido assim não distingue "o efeito não
existe" de "o estudo não conseguia vê-lo", que é exatamente a ambiguidade que o pré-registro
existe para eliminar.

**Onde está a alavanca**: em **clusters**, não em paráfrases nem em sementes. Sementes de
decodificação já são colapsadas por voto majoritário e não entram no n (correto, e é o que
impede reamostrar decodificação para inflar n). Paráfrases sofrem o efeito de desenho acima.
Só o número de clusters move o poder de verdade.

Trocar 1 paráfrase por mais clusters domina: **40 clusters × 3 paráfrases = 120 gerações e
n_ef ≈ 25**; **60 clusters × 2 paráfrases = 120 gerações e n_ef ≈ 46** (ICC 0,5). Mesmo custo
de GPU, quase o dobro de n efetivo. As paráfrases não são desperdício — elas testam se o
efeito sobrevive à reformulação, que é parte do construto — mas 2 já entregam esse teste.

---

## Três opções, com o que cada uma custa

| | Bancos | Gerações por bateria (4 braços × 2 paráf. × 3 sementes) | O que autoriza |
|---|---|---|---|
| **A** | 40 clusters | 960 | superar o acaso, sim; claim forte, não |
| **B** | 60 clusters | 1.440 | superar o acaso com folga; claim forte só se a verdade ≥ 0,90 |
| **C** | 90 clusters | 2.160 | claim forte com 81% de poder já em 0,85 |

**Recomendo B + retirar o claim forte da lista de endpoints.** Duas razões:

1. O programa já tem doutrina de **teto de claim**. Um estudo que declara "superou o nulo,
   com IC exato de tal a tal largura" e publica o intervalo diz mais, e promete menos, do que
   um que persegue um limiar de magnitude escolhido antes de existir dado sobre a magnitude.
2. Nada impede reportar o claim forte como **estimativa com intervalo** em vez de gate. O que
   não se pode é deixá-lo como gate pré-registrado sabendo que ele nasce com 26% de poder — um
   gate que quase sempre reprova não é um gate, é um enfeite.

Se o Arquiteto quiser manter o claim forte **como gate**, então a opção é **C**, e o custo é
2.160 gerações por bateria a 400 tokens cada.

---

## O que ainda falta para fechar o número

- **ICC medido, não assumido.** As tabelas usam 0,5 como referência. O ICC real sai do piloto
  do S3 (mesmos itens do banco de vazamento, que já é declarado disjunto do confirmatório) e
  deve ser fixado antes da bateria confirmatória.
- **A taxa verdadeira assumida.** As tabelas são uma grade justamente para não fingir que
  sabemos `p`. A linha a usar é escolha declarada no pré-registro, com a justificativa — e a
  honesta é a **pessimista** entre as plausíveis.
- **McNemar do 2×2.** Para o contraste pareado entre braços, o n que conta é o de pares
  **discordantes**: com discordância 0,10/0,30 são 85 pares para 80% de poder; com 0,10/0,25,
  130 pares. Duas condições parecidas custam muito mais itens do que a intuição sugere.
