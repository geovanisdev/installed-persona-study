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

> **Atualizado em 2026-07-21, depois da decisão do desenho cruzado.** A família passou a ter
> **5** endpoints primários (`E-F2-DISC` entrou), e o primeiro colocado passa a ser testado a
> **α/5 = 0,0100**. As grades abaixo, que foram calculadas a 0,0125, ficam como estão porque
> são a leitura histórica; a grade que vale para o desenho é a da seção final.

**4. Um erro de aritmética meu, encontrado por auditoria em 2026-07-21.** `n_efetivo` recebe
**observações**, não clusters — a própria docstring dela diz *"60 paráfrases (20 clusters × 3)"*.
A seção de decisão deste documento passava `90` (clusters) quando devia passar `180`
(90 × 2 paráfrases), **e** usava ICC 0,25 quando o texto ao lado declara 0,5. Dois erros somados,
e ambos na mesma direção: subestimavam o próprio *n*. Corrigido abaixo. O efeito é que a manchete
de poder deste documento estava **conservadora**, não inflada — o que é o lado bom de errar, mas
não é motivo para deixar errado.

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

---

## Decisão, com GPU disponível (2026-07-21)

O Arquiteto informou que a GPU fica livre assim que a trilha de identidade rodar o último
teste, e pediu "o que for melhor para o projeto". Isso **muda qual é a restrição** e, com ela,
qual é a compra certa.

### Com GPU livre, o gargalo é autoria de item — não geração

(90 + 90 + 60 + 60) × 2 = **600 prompts escritos à mão**, cada um sujeito às regras de higiene de
léxico e de pareamento. Passado certo ponto, mais itens não compram poder: compram itens medianos,
e um banco cheio de item morno mede pior que um banco menor e afiado.

*(Este número dizia **720** até 2026-07-21. Era `90 × 2 × 4` — a multiplicação tratou os quatro
bancos como se todos tivessem 90 clusters. O erro é inócuo em consequência e não em espécie: 120
prompts de folga inexistente são 120 prompts que alguém poderia ter gastado em outra coisa
achando que estavam orçados.)*

Por isso a escolha não é "o maior que a GPU aguenta":

| Banco | Clusters | Justificativa |
|---|---|---|
| `battery_leokadius`, `battery_shadowclock` | **90** | é onde vivem os endpoints primários; 81% de poder a p=0,85 sob Holm |
| `battery_shared` | **60** | capacidade e neutro: estimativa com intervalo, não gate de magnitude |
| `battery_hijack` | **60** | multi-turno custa turnos, e a cláusula 4 da Regra 1 proíbe cortar o teto para compensar |

Com 2 paráfrases por cluster, o *n* efetivo é:

| Banco | clusters | observações | n_ef (ICC 0,5) | n_ef (ICC 0,25) |
|---|---|---|---|---|
| persona | 90 | 180 | **120** | 144 |
| shared / hijack | 60 | 120 | **80** | 96 |

`n_efetivo(180, 2, 0.5) = 120`. **O primeiro argumento é o número de observações**, não o de
clusters — é o erro corrigido acima, e ele custava 40% do *n* no papel. A consequência para a
manchete: `poder(120; p=0,85; limiar=0,70; α=0,0125) = **0,917**`, contra os 0,814 que este
documento anunciava calculando sobre 90 crus. Sob a família de 5 endpoints (α = 0,0100) o mesmo
gate dá **0,917 também** — o *k* crítico não se move (97 nos dois), porque a binomial é discreta e
o aperto de α não chega a comprar mais um acerto. Só na família de 6 (α = 0,00833) ele sobe para
98 e o poder cai a 0,874.

Isto é registro de uma correção contra a auditoria que me corrigiu: o laudo do desenho afirmou
0,900 para α = 0,0100. O número é **0,917**, e a diferença tem causa — em *n* = 90 a mesma
mudança de α **custa** de verdade (0,814 → 0,730, porque ali o *k* crítico anda de 74 para 75).
Aceitar 0,900 sem recalcular seria importar um número plausível de uma fonte confiável, que é
exatamente como um número errado sobrevive a uma revisão.

**O ICC é medido, não assumido.** As duas colunas existem porque o valor real sai do piloto do S3
e é fixado antes da bateria confirmatória. Publicar a grade nos dois valores plausíveis é o que
impede escolher o ICC depois de ver de qual lado do gate o resultado caiu.

### O que a GPU livre compra de verdade: **réplica de semente de treino**

Aqui está a fraqueza real deste desenho, e ela não se conserta com mais itens: **cada célula do
2×2 tem UM adapter**. n = 1 no nível do sujeito. Se o efeito só existir naquela corrida de
QLoRA, o estudo inteiro terá medido uma corrida — com intervalos exatos, poder calculado e
todo o aparato apontando para um sujeito só.

Nenhuma quantidade de itens corrige isso: itens estimam a variância **dentro** do adapter; o
que falta é a variância **entre** adapters. É o mesmo erro de tratar paráfrase como réplica,
um nível acima.

**Recomendação: treinar cada célula do 2×2 em ≥2 sementes independentes** — 8 corridas de QLoRA
em vez de 4 — e declarar `semente_de_treino` como fator do desenho, com o efeito lido como
consistente **entre** sementes. Isso é barato em GPU (o corpus tem 200 passagens por persona) e
é exatamente o tipo de coisa que só GPU abundante permite.

Distinção que a Regra do handoff já faz e que continua valendo: **semente de decodificação não
é réplica** (é colapsada por voto majoritário e não entra no *n*). **Semente de treino é** — ela
produz um sujeito diferente, e sujeito é a unidade sobre a qual a conclusão é feita.

Se as duas sementes divergirem, isso não é ruído a ser mediado: é o resultado, e é publicável.

### Custo total estimado — sob o desenho CRUZADO decidido em 2026-07-21

O desenho é **cruzado**: os 8 adapters **e a base nua** respondem os **quatro** bancos, e a
divergência predita de F2 vira uma interação persona × banco. Isso não acrescenta um item ao que
já ia ser escrito; acrescenta uma restrição de pareamento (ver `batteries/README.md`).

**9 sujeitos × 300 clusters × 2 paráfrases × 3 sementes de decodificação = 16 200 gerações** de
turno único, a 400 tokens cada, mais o sequestro multi-turno. É o regime que a GPU livre torna
irrelevante — e é por isso que a restrição real deste sprint é autoria de item, não geração.

### O que continua sendo decisão do Arquiteto

Manter ou não o **claim forte como gate**, e agora a pergunta é só de doutrina, porque a
aritmética parou de forçar qualquer lado:

| família de Holm | α do 1º colocado | poder do claim forte em n_ef = 120, p = 0,85 |
|---|---|---|
| 5 endpoints (claim forte **fora** do portão) | 0,0100 | 0,917 |
| 6 endpoints (claim forte **como** portão) | 0,00833 | 0,874 |

As duas são defensáveis. A favor de mantê-lo: o poder existe, dos dois jeitos. Contra: a doutrina
de teto de claim do programa, e o fato de que o limiar 0,70 foi escolhido **antes de existir
qualquer dado sobre a magnitude** — que é a definição de limiar escolhido no escuro.

**Recomendação: deixá-lo fora do portão**, reportado como estimativa com intervalo ao lado. Não é
recuo: com o intervalo publicado, o leitor que quiser aplicar o limiar 0,70 pode fazê-lo por conta
própria, e o estudo não terá gastado α para carimbar um número que ele não escolheu com
informação.

**Se o Arquiteto não decidir, é este o default que vai ao selo.** Está escrito aqui para que o
silêncio tenha consequência declarada em vez de virar decisão minha por omissão.
