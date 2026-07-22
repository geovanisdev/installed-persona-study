# Decisões do Arquiteto — 2026-07-22

Registro das escolhas que fecham o desenho antes do selo. Cada linha diz **o que foi
decidido**, **contra o que** (a alternativa que perdeu) e **o que muda no código** — porque
uma decisão que não altera nenhum arquivo não é decisão, é opinião.

Este documento é **entrada do selo**, não o selo. Quando `PREREGISTRATION.md` for selado, os
valores abaixo entram nele como constantes e passam a só mudar por ADR datado.

---

## As sete decisões

O painel foi apresentado em `DECISOES-S3-estudo-personas-2026-07-22.html` (repositório meta,
local). Resposta do Arquiteto, textual: *"Mantenho as sete decisões como foram recomendadas."*

| | Decisão | Valor | Alternativa que perdeu | Onde vive |
|---|---|---|---|---|
| **D1** | Quantos portões F3 tem | **2** | 3 portões | `analysis/ENDPOINTS.md` |
| **D2** | Itens por invariante em F3 | **110** clusters | 90 · 130 | banco F3 |
| **D3** | Tamanho do piloto V1 | **24**, KILL-only | 60 | `runners/run_f3_v1.py` |
| **D4** | Margem do gate de coincidência | **0,125** | 0,10 · 0,15 | `gate_coincidencia(margem=)` |
| **D5** | Teto de diferença de caracteres τ | **2** | 0 · 1 · 3 · ≥10 | `harness/equalizador.py` |
| **D6** | Estrato quebrado do V0 | **reescrever** | retirar · gastar tentativa | banco V1 |
| **D7** | Claim forte como portão | **não** | sim | `analysis/ENDPOINTS.md` |

### O que cada uma custa, em uma linha

- **D1 = 2.** Os dois portões são `T1` (a mudança teve direção) e `T2` (o adapter não destruiu
  o que a base tinha). O terceiro portão candidato — magnitude — sai por D7. Consequência: a
  família de Holm fica com **5** endpoints, não 6.
- **D2 = 110.** Sob ICC 0,5 e 2 paráfrases, 110 clusters valem **n_ef ≈ 147**; contra taxa
  verdadeira 0,65 e α = 0,0100 (primeira posição de Holm), o poder é **83%**. Com 90 clusters
  seria 75%; com 130, 92%. O ganho de 110→130 custa 40 prompts autorados e 360 gerações por
  sujeito para comprar 9 pontos de poder num cenário que já está acima de 80%.
- **D3 = 24, KILL-only.** *KILL-only* quer dizer: o piloto só pode **matar** um invariante por
  teto; ele não pode aprovar nada. Um piloto que aprova é um endpoint disfarçado, e endpoint
  não declarado no pré-registro é o defeito que este estudo existe para não cometer.
- **D4 = 0,125.** É a maior diferença que o estudo aceita chamar de "mesma coisa". Ver a
  tabela de poder da seção F4 abaixo: a margem e o *n* são a mesma decisão vista de dois lados.
- **D5 = τ 2.** Do banco do V0, **2 de 16** pares eram conformes. Isso é esperado e não é
  motivo para afrouxar: o banco do V0 foi escrito antes de a trava existir.
- **D6 = reescrever.** O estrato `nao_finge_humano` do V0 é resolvido em **1,000** por
  `negativista`. Reescrever **não gasta** a tentativa de reautoria que a Regra 6 sela, porque
  aquela regra cobre invariante **em teto**, e isto não é teto — é banco com atalho. A
  distinção está escrita em `PREREGISTRATION.md` § Regra 6.
- **D7 = não.** O claim forte (limiar 0,70) sai da lista de portões e vira **estimativa com
  intervalo**. Motivo em `DIMENSIONAMENTO.md`: com n praticável, o poder contra uma verdade de
  0,85 fica em 26–61%, e um resultado nulo produzido assim não distingue "o efeito não existe"
  de "o estudo não conseguia vê-lo".

---

## As duas paradas que os specs abriram e que não estavam nas sete

As especificações de `prod_validator` e `equalizador` (auditadas em 21/07) terminam em seções
"PARADA DO ARQUITETO". Duas delas não tinham entrado no painel das sete. Uma foi **resolvida
executando**; a outra foi **decidida por default** e está marcada como reversível.

### D8 — Contagem de tokens no ambiente de CPU. **RESOLVIDA, não decidida.**

A parada dizia: sem `transformers` no `.venv`, as travas `PR-PAR`, `PR-INDICE` e `PR-HIJACK`
não rodam, e **nenhum banco pode ser selado na máquina de CPU**.

Resolvida em 22/07 combinando as opções A e C da parada, o que é estritamente melhor que
qualquer uma isolada:

1. `tokenizers` 0.23.1 instalado no `.venv` — **sem `torch`, sem `transformers`**, 14 pacotes
   no total. `Tokenizer.from_file()` carrega o `tokenizer.json` direto do disco, offline.
2. O tokenizer é **pinado por `sha256` do arquivo**, não por nome de revisão. Motivo medido no
   programa: em 21/07 `refs/main` da base pulou para uma revisão nova e quase trocou o modelo
   debaixo de um experimento em curso. Nome de revisão é mutável; hash de arquivo não é.

**Fato verificado ao pinar, e ele é tranquilizador:** o cache tem **dois** snapshots de
`google/gemma-4-E4B-it` (`a4c2d58…` e `ee0ef60…`) e o `tokenizer.json` é **byte-idêntico** nos
dois (`sha256` inicia em `cc8d3a0ce36466cc`, vocabulário 262.144). A deriva de revisão que
assustou em 21/07 **não** mexeu na tokenização. A revisão que o V0 registrou — `a4c2d58…` — é
a que `refs/main` aponta hoje.

Nada a decidir. Fica registrado porque desbloqueia o selo em CPU.

### D9 — Onde moram os itens de F4, e em quantos clusters. **DECIDIDA POR DEFAULT — reversível até o selo.**

Nenhum documento atribuía F4 a um banco. As três opções da parada eram: **(A)** F4 divide os
60 clusters de `battery_shared` · **(B)** banco próprio com 90 clusters (45 por direção) ·
**(C)** `shared` sobe para 120 clusters, 30 por direção para F4.

Calculei o poder do gate que de fato decide F4 — `gate_coincidencia`, margem 0,125 (D4) —
**sob a hipótese de que a segurança coincide exatamente**, que é a hipótese que o estudo
espera confirmar. `q` é a taxa de discordância item-a-item entre adapter e base:

| clusters por direção | n_ef (ICC 0,5) | q = 0,10 | q = 0,20 | q = 0,30 | q = 0,40 |
|---|---|---|---|---|---|
| 30 *(opções A e C)* | 40 | 57% | 10% | 1% | 0% |
| 45 *(opção B)* | 60 | 72% | 19% | 2% | 0% |
| **60** | **80** | **90%** | **50%** | **16%** | **3%** |
| 90 | 120 | 97% | 75% | 49% | 25% |

**As três opções oferecidas eram todas subdimensionadas.** Sob a opção A ou C, se a segurança
coincidir *exatamente* e os dois braços discordarem em 20% dos itens — o que é discordância
modesta para geração livre — o estudo declara NÃO-DEMONSTRADO em **9 de cada 10 execuções**.
Isso não mede segurança; mede o tamanho do banco.

**Decisão tomada: banco próprio `battery_f4`, 120 clusters, 60 por direção.**

O argumento que decide não é o poder — é a **assimetria da reversibilidade**:

> Enquanto o pré-registro não está selado, um banco grande demais pode ser **subamostrado por
> cluster** e o desenho continua válido. Um banco pequeno demais **não pode ser crescido**
> depois do selo sem invalidar o `battery_hash`. Autorar a mais hoje é reversível; autorar a
> menos, não.

Custo que isso empurra para o Arquiteto, dito com o número: 120 clusters × 2 paráfrases ×
9 sujeitos × 3 sementes de decodificação ≈ **6.480 gerações só de F4**. Se o orçamento de GPU
não comportar, o corte a fazer é **por cluster, antes do selo** — 60 clusters por direção caem
para 45 removendo 15 clusters inteiros de cada lado, e a tabela acima diz exatamente o que se
perde. **Não** corte paráfrases: elas testam se o efeito sobrevive à reformulação, que é parte
do construto, e cortá-las mexe no ICC em vez de mexer no *n*.

Reversível até o selo. Depois do selo, não.

---

## O que este documento não decide

- **O selo de `PREREGISTRATION.md`** é ato do Arquiteto, como foram os selos dos núcleos.
- **O gate Onda 1 → Onda 2** é ato do Arquiteto.
- **Cada download deliberado** (juiz Qwen3-8B; textos de domínio público) é ato do Arquiteto.
- **Qualquer desvio de limiar selado** para, reporta e espera. Não se ajusta limiar selado —
  a lição está registrada em `PREREGISTRATION.md` § Regra 6, com o caso em que ajustar um
  limiar selado não mudou o veredito e mesmo assim foi violação.
