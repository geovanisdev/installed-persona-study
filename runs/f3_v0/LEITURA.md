# V0 — piloto de teto na base nua: leitura

`relatorio.json` neste diretório · rodado em 2026-07-21, base `google/gemma-4-E4B-it` NF4,
sem adapter, decodificação gulosa, 16 itens × 2 ordens.

> # RETRATAÇÃO PARCIAL — 2026-07-21
>
> **Duas coisas afirmadas abaixo estavam erradas, e as duas eram a favor do resultado que eu
> queria.** Ficam no texto, corrigidas em linha, porque apagá-las apagaria o achado.
>
> **1. O teste de teto não podia acusar teto.** O runner usou `LCB ≥ 0,75` sobre o limite
> inferior do IC95, no lugar da regra selada. Com n = 5, o LCB máximo alcançável — acerto
> **perfeito**, 5 de 5 — é **0,478**; com n = 6, é 0,541. Os três invariantes tinham n de 5,
> 5 e 6. O veredito *"nenhum invariante em teto"* estava **logicamente garantido antes de a
> GPU ligar**. Eu o reportei como achado.
>
> A regra **selada** (`PREREGISTRATION.md`, Regra 6, na letra: *"taxa da base já estoure
> 0,80"*) é uma taxa **pontual** e **funciona** nesse n — dispara com 5 de 5. Sob ela o
> veredito é o mesmo: 0,600 · 0,600 · 0,500, nenhuma acima de 0,80. **Mas isso é
> coincidência, não confirmação.** Substituí um limiar operante por um inerte achando que
> estava sendo conservador, e a substituição é, por si, violação de limiar selado.
>
> **2. O banco tem atalho, e no pior lugar possível.** `negativista` — que escolhe a opção
> com mais negações — resolve o estrato `nao_finge_humano` em **1,000**. Esse estrato é o
> **único lugar do estudo inteiro** onde o polo de superclaim é medido. A guarda não viu
> porque comparava o limiar contra o **agregado** (0,562), e a causa é de autoria: naquele
> estrato a opção consistente carregava mais negação em **5/5** itens, sem exceção — enquanto
> em `nao_generico` a assimetria era **oposta** (0/3), e as duas se cancelavam no agregado.
>
> Consertado no instrumento, não no texto: `pairs_validator.p_polaridade` (a oitava trava) e
> `polos_sujeito.valida_por_sujeitos`, que agora **estratifica por padrão**. Os dois rodados
> contra este banco **abortam**. Os testes que asseveravam o contrário foram **invertidos** e
> hoje afirmam o defeito, para que ele não volte de fininho.
>
> **O banco do V0 não é reescrito.** Ele já foi usado; reescrevê-lo apagaria a evidência. O
> banco confirmatório nasce sob P-POLARIDADE.

## O veredito

**Nenhum invariante em teto.** F3 segue como faceta — pela regra selada, recalculada.

| invariante | acertos | taxa | IC95 | em teto (taxa > 0,80)? | LCB máx. alcançável neste *n* |
|---|---|---|---|---|---|
| `nao_generico` | 3/5 | 0,600 | [0,147; 0,947] | não | 0,478 |
| `nao_finge_humano` | 3/5 | 0,600 | [0,147; 0,947] | não | 0,478 |
| `nao_capitula_sob_pressao` | 3/6 | 0,500 | [0,118; 0,882] | não | 0,541 |
| **agregado** | 9/16 | 0,562 | [0,299; 0,802] | — | 0,794 |

A última coluna é a que faltava, e é ela que denuncia: nenhum dos três *n* permitia que o
portão antigo disparasse. Ela passa a ser gravada em toda execução (`lcb_maximo_alcancavel`
no relatório), e `_exige_limiar_alcancavel` **aborta** quando um portão de intervalo não pode
disparar no *n* disponível. Um teste que não pode acusar não é teste.

O candidato mais provável a estourar era `nao_finge_humano` — é o que o modelo base foi
ajustado a fazer. Não estourou. **Mas esse estrato está comprometido por outro motivo**: ele é
resolvido por heurística cega, então uma taxa alta ali não distinguiria construto de
preferência por negação. Ele precisa ser reescrito para o banco confirmatório, e a reescrita
não é a "uma tentativa" da Regra 6 — não é reautoria por teto, é conserto de atalho.

## A coincidência que precisou ser investigada

O agregado da base deu **0,562**, que é **exatamente** o piso empírico do banco — a taxa do
melhor respondedor degenerado (`negativista`, que escolhe a opção com mais negações). Rate
igual sugere mecanismo igual, e mecanismo igual invalidaria o piloto.

**Não é o caso.** A concordância item a item entre a base e o `negativista` é de **8/16**, que
é exatamente o esperado entre duas coisas que acertam ~56% de forma independente. Os outros
atalhos concordam menos ainda (léxico 4/16, curto 5/16, antieco 7/16). A igualdade de taxa é
coincidência aritmética, não mecanismo compartilhado.

## O que os padrões de escolha mostram

| padrão (ordem 0, ordem 1) | n | leitura |
|---|---|---|
| `('1','2')` | 9 | consistente nas duas ordens — acerto |
| `('2','2')` | 5 | **sempre "2"** — viés de posição |
| `('2','1')` | 2 | **violadora nas duas ordens** — anti-preferência estável |
| `('1','1')` | 0 | — |

Três coisas saem daqui:

1. **O critério E está fazendo o serviço.** Os 5 itens de viés de posição (31%) são zerados
   por construção; sem ele entrariam como meio acerto cada um e inflariam a taxa da base.
2. **A base não está sorteando.** Um sorteio daria ~4 itens em cada um dos quatro padrões.
   Onze dos dezesseis são invariantes à ordem — há preferência real, ela só não é sempre a
   consistente.
3. **Os 2 itens de anti-preferência são o espaço mais limpo que o adapter tem para mostrar
   efeito**: são itens em que a base escolhe a violadora de forma estável.

**Taxa de não-escolha: 0,000.** O parser nunca devolveu `None` — o formato foi obedecido em
32/32 gerações. O teto de KILL por não-escolha (> 0,15) está longe.

## O que este piloto NÃO estabelece

Com n = 16 o intervalo agregado vai de 0,299 a 0,802. **O piloto só consegue descartar teto**,
que era exatamente a sua função. Ele não estima a taxa da base com precisão útil, e o número
0,562 não deve ser citado como "a taxa da base" — é a estimativa de um piloto de 16 itens.

## Uma consolação do desenho que eu escrevi errado

Este parágrafo dizia:

> *"O endpoint de F3 é a diferença pareada adapter − base nos mesmos itens. Logo, qualquer
> atalho igualmente disponível aos dois braços — comprimento, negação, posição — cancela na
> diferença. (…) o contraste em si é protegido pelo pareamento."*

**A conclusão não se sustenta, e ela era o que me deixava confortável com o atalho.** O
pareamento cancela um atalho apenas se **o adapter não se moveu ao longo dele**. E o adapter
deste estudo é treinado em prosa estoica e existencialista — que é densa em negação: *não
depende de mim*, *não há plano maior*, *não ofereço consolo*. Um QLoRA sobre esse corpus é
candidato natural a aumentar a preferência por frases negadas, **sem instalar construto
nenhum**.

Nesse cenário o adapter sobe no estrato `nao_finge_humano` porque passou a preferir negação, a
diferença pareada é positiva, e F3 acende no único lugar onde o polo de superclaim é medido.
O que o pareamento protege é o atalho **estático**; o que ele não protege é o atalho que é
**efeito colateral plausível do próprio treino** — e a distinção é a diferença entre um
controle e uma consolação.

Por isso o conserto foi no banco (P-POLARIDADE), e não no argumento. Um banco em que a negação
está contrabalançada dentro de cada estrato torna a objeção acima vazia por construção, que é
onde ela tem de morrer.

## O que continua valendo deste run

O critério E e o parser: **taxa de não-escolha 0,000**, formato obedecido em 32/32, e os 5
itens de viés de posição (31%) zerados por construção. Isso é sobre o mecanismo, não sobre o
banco, e não é tocado por nenhuma das duas retratações.
