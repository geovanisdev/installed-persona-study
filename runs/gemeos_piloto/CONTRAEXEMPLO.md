# O slice velho como banco de contraexemplo — as travas consertadas acusam o que deixaram passar

**2026-07-22, Etapa B1.** Laudo em `contraexemplo.json`, produzido por
`runners/valida_banco.py --modo diagnostico`. Nada aqui é banco confirmatório: o slice piloto
continua sendo o que sempre foi, um teste da receita de autoria, e agora também o contraexemplo
contra o qual os consertos da Etapa A se provam.

O modo `diagnostico` roda **cada trava isolada** e coleta todas as acusações, em vez de abortar
na primeira. É o modo que a autoria precisa — um autor quer a lista inteira do que consertar — e
ele **nunca sela**: carimba `carater: DIAGNOSTICO` como primeira chave. O modo restritivo é o
default; o permissivo é o que precisa ser digitado.

## A anotação de família, e o buraco que ela quase abriu

Os 40 itens foram escritos antes de `familia_de_cenario` existir. Sem anotá-los, PR-FAMILIA
acusaria `familia:ausente` em 40 de 40 e o laudo diria mais sobre o campo faltando do que sobre
reciclagem. O mapa está em `familias_declaradas.json` (sha256 no laudo).

`--familias` só preenche campo **vazio**; divergir de família já declarada **aborta**. Sem essa
regra, o mapa seria a maneira mais barata de calar a trava: bastaria renomear os dois clusters
que colidiram.

**Os rótulos saíram de releitura dos 40 prompts, não da lista publicada em `LEITURA.md`** — e o
critério foi **conservador**: na dúvida, famílias separadas. `c10` (decisão da diretoria ainda
pendente) foi separado de `c00`/`c05` (decisão já tomada); `c15` (projeto encerrado) idem;
`c11` (o irmão que adia a própria oficina) foi separado de `c02`/`c06` (quem herdou e toca o
negócio). O rótulo que **menos** favorece a trava é o que foi usado.

## O que as travas acusaram

| trava | leokadius | shadowclock |
|---|---|---|
| PR-LEAK | **ACUSOU** — `c03-p0`, `c18-p0` | PASSOU |
| PR-FAMILIA | **ACUSOU** — 1 | **ACUSOU** — 1 |
| PR-CLUSTER | ACUSOU — 3 | ACUSOU — 6 |
| PR-DUP | ACUSOU — 3 | ACUSOU — 6 |
| PR-SCHEMA · PR-LEXICO · PR-SCRUB · PR-META · PR-MOLDE · PR-ORTOGRAFIA · PR-USUARIO · PR-INDICE | PASSOU | PASSOU |

**PR-LEAK acusa exatamente os dois itens nomeados** — `leokadius-c03-p0` e `leokadius-c18-p0`,
os dois por `('pode', 'dar', 'errado')`, aridade 3 — e **zero** nos outros 78. É o conserto da
Etapa A funcionando na letra: antes do conserto, `proibidos_de_vazamento` gerava só a aridade
máxima de cada fonte e nenhuma sub-janela; a fonte era *"a antecipação do que pode dar errado"*
e o item emitia *"a versão do que pode dar errado"*.

**PR-LEAK passa em `shadowclock`**, e isso também é resultado: a metade `shadowclock` do
problema 3 foi retratada em `LEITURA.md` porque aqueles itens não vazam n-grama nenhum. Uma trava
que os acusasse agora seria a confirmação de que o conserto pegou largo demais.

`PR-CLUSTER` e `PR-DUP` acusam as mesmas 9 vizinhanças de sempre (3 + 6), e `PR-PAR` repete
`dose_media = −0,27` tokens, IC95 **[−3,55; +2,90]** → `NAO_DEMONSTRADO`. Nenhum dos dois mudou
com os consertos, e não deviam ter mudado.

## O achado que eu não tinha previsto: cada banco esconde a reciclagem do outro

Quatro famílias se repetem no slice — duas de cada lado, duas clusters cada. **PR-FAMILIA pega
metade, e a metade que ela pega é o espelho exato da que ela perde:**

| família | leokadius | | shadowclock | |
|---|---|---|---|---|
| `projeto_entregue_diretoria_preferiu_outro` | `dicotomia`, `dicotomia` | **ACUSADA** | `absurdo`, `revolta` | invisível |
| `negocio_do_pai_ja_assumido` | `apatheia`, `memento_mori` | invisível | `liberdade_radical` ×2 | **ACUSADA** |

A mesma dupla de clusters — `c00`/`c05`, `c02`/`c06` — é flagrante de um lado e invisível do
outro. A única coisa que muda entre os dois lados é **a qual movimento aquele cenário foi
atribuído**, e a atribuição é do plano de 90, não do autor.

**Isto não é defeito da trava.** A cláusula (b) roda por movimento porque F2 é reportada por
movimento, e uma família espalhada por dois movimentos não infla o *n* de célula nenhuma. A
trava fez o que foi construída para fazer.

**Mas fica um risco sem guarda, e ele é declarado aqui:** duas células que compartilham a
situação não são independentes, e a agregação de F2 sobre movimentos trata como *n* efetivo o que
não é. A cláusula (c) — teto de 25% do banco — não cobre isso: a 90 clusters o teto é 22, e
reciclagem *branda* jamais o alcança. Quem cobre é o **ledger**, cujo briefing lista as famílias
já usadas em **qualquer** movimento, não só no movimento em curso
(`tests/test_ledger_cenarios.py::test_o_briefing_lista_o_que_ja_esta_tomado`). Prevenção na
escrita cobre o que a trava, na granularidade certa, não pode cobrir.

## Terceira retratação: "cinco famílias cobrindo 15 dos 20 pares" não é medida

`LEITURA.md`, problema 10, afirma cinco famílias sobre 15 dos 20 pares. Sob a releitura
conservadora deste laudo saem **18 famílias distintas para 20 clusters**, com duas repetições de
duas clusters cada.

Os dois números descrevem os mesmos 40 textos. A diferença inteira está em quão grosso é o
rótulo: *"pai ou mãe morrendo"* funde a morte consumada (`c04`), o exame pendente (`c08`) e o
prazo terminal (`c16`); *"oficina herdada do pai"* funde quem herdou com quem adia e com quem vai
decidir.

**Nenhuma das duas contagens é mais verdadeira que a outra**, e essa é a notícia: o número de
famílias de um banco **não é medição, é decisão de rotulagem**. O que estava escrito como
limitação em `pr_familia` — *campo declarado e nunca conferido contra o texto* — aparece aqui com
número: o mesmo banco vale 5 ou 18 famílias conforme quem rotula.

Segue-se o que o ledger vale de fato, e não é medir reciclagem. É **obrigar o rótulo a ser
escolhido antes de escrever**, quando ele ainda muda o que vai ser escrito — em vez de depois,
quando só muda o relatório.

## O que este laudo não prova

Que a trava pega reciclagem **não declarada**. Ela não pega, por construção, e o laudo foi
produzido a partir de rótulos que eu mesmo escrevi lendo os itens. A demonstração é condicional:
*dada a declaração correta, a cláusula (b) dispara na célula certa*. A declaração continua sendo
o elo que nenhuma medida de string alcança — `c00` e `c05` estão a Jaccard 0,156, mais distantes
que pares legítimos, precisamente porque a redação mudou.
