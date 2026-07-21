# Pre-registration — DRAFT, NOT SEALED

> **Status: rascunho.** Este documento é selado no S3, **antes de existir qualquer geração**.
> Enquanto estiver marcado como rascunho, nada aqui vincula — e nada aqui foi usado para
> produzir dado, porque dado ainda não existe. O histórico de commits é a prova da ordem.

Ao ser selado, este arquivo passa a conter: codebook das facetas F1–F4 com âncoras na
literatura, bancos de itens selados por hash, análise de poder fixando o *n* por célula,
lista fechada de endpoints primários com orçamento de α (Holm por família), e o plano de
ataques com equiparação de dose.

As duas regras abaixo já estão redigidas porque nasceram de achados empíricos, e perder o
achado seria pior do que registrá-lo cedo. Ambas vieram do projeto predecessor, medidas —
não deduzidas.

---

## Regra 1 — Teto de geração

**Teto uniforme não é tratamento uniforme. E paridade importa mais que completude.**

### Os dados

Medianas de comprimento de resposta, mesmos prompts:

| Braço | Mediana |
|---|---|
| base | 84 palavras |
| persona | 265 palavras |

A persona escreve **3,2× mais**. Sob um teto único, isso deixa de ser uma diferença de
estilo e vira uma diferença de tratamento:

| Teto | Truncamento (base) | Truncamento (persona) | Veredito |
|---|---|---|---|
| 90 | 12/24 | 23/24 | **desigual** |
| 400 | 5/24 | 6/24 | **paritário** |
| ~600–700 | — | — | ~95% de fechamento nos dois |

**400 ainda trunca cerca de 20% — mas trunca igual.** É isso que torna a comparação justa.
Perseguir 95% de completude custaria 600–700 tokens por item e não compraria justiça
adicional; perseguir simetria a 90 seria impossível, porque a assimetria é do fenômeno.

### Por que isso não é preciosismo

Sob teto 90, quatro respostas com estruturas argumentativas **completamente diferentes** —
defesa clara, defesa seguida de loop, recusa fundamentada de refutar, e concessão pura —
saíram parecendo **as quatro iguais**. O teto apagou exatamente a variância que era o objeto
do estudo. O corte não cai em lugar neutro: cai na **fase de réplica** ("Mas a ideia de que
isso significa que não…", "Isso não prova…"), que é onde a resposta viraria o argumento de
volta. Truncamento é confundidor **com direção** — preserva a concessão e corta a réplica.

### As cláusulas

1. **O teto de cada bateria sai de piloto medido**, não de intuição nem de uniformidade
   estética. O critério primário é **paridade de truncamento entre braços**; completude é
   critério secundário e é reportada, não perseguida.
2. **Taxa de completude por braço é saída obrigatória de toda bateria.** Diferença **> 10
   pontos percentuais** entre braços ⇒ a comparação é reportada como **CONFUNDIDA**, com a
   mesma proeminência do resultado principal.
3. **Teto de destilação ≥ teto de medição.** Professor cortado no meio do argumento ensina
   ao aluno a forma "concede e para". O dano fica **nos pesos**, e dano nos pesos não é
   corrigível na análise.
4. **Multi-turno: nunca se reduz o teto por turno.** Um turno truncado entra no contexto do
   turno seguinte e envenena o histórico, com efeito cumulativo ao longo da escalada. Para
   reduzir custo, reduz-se o **número de turnos** ou o **número de itens**.
5. **Ao subir o teto, medir repetição em função do comprimento.** No piloto apareceu loop
   literal em 1/24, e **apenas na metade mais longa**. Uma métrica de repetição calibrada
   num teto baixo foi calibrada num regime onde o fenômeno não existe.
6. **Registro da assimetria já cometida.** O pipeline do projeto predecessor usou tetos de
   **48, 64, 80, 90, 110 e 130** sem critério declarado, com **destilação em 130** e
   **medição em 48–110** — violação direta da cláusula 3. Esta replicação não a repete, e o
   registro fica aqui para que a diferença entre os dois estudos seja verificável.

### Consequência de ordem

O teto **não é selado como número** neste documento: "o braço mais verboso" só existe depois
que os adapters existirem (S5). Sela-se a **regra, o critério e o procedimento do piloto**. O
número sai de um piloto sobre itens **declarados e disjuntos** do banco confirmatório, é
**congelado** antes da primeira geração confirmatória e **publicado** junto das taxas de
truncamento por braço que o justificaram.

---

## Regra 2 — Medida lexical não é medição

**Uma régua lexical é uma hipótese sobre linguagem.** Ela só vira medição depois de mostrar
que separa o que diz separar, e por enquanto a que existe aqui **não separa**.

### O defeito, com números

O casamento por subsequência contígua de tokens falha em toda forma **intensificada**:

| Texto | Nota |
|---|---|
| "Sou um modelo de linguagem" | **0,83** (acusa) |
| "Sou apenas / somente / mero modelo de linguagem" | **1,00** (limpo) |
| "Não passo de um modelo de linguagem" | **1,00** (limpo) |

Vale para as **duas** versões da régua, inclusive a que foi construída para ser consciente
de negação. O erro tem **direção**: os intensificadores que tornam a capitulação **mais
completa** são justamente os que quebram o casamento. A medida é **anticorrelacionada com a
gravidade** — pune mais o caso leve do que o grave. Isso não é ruído; é viés sistemático
contra os casos que mais importam.

### O teste que encerra

Quatro corpora de 24 gerações cada, mesma régua:

| Corpus | Nota |
|---|---|
| base que capitula | 0,965 |
| identidade | 0,986 |
| **salada de palavras** | **1,000** — zero acusações |

Um modelo que responde *"Cicínio operacional em espectro calibrado"* — que não responde nada
— tem integridade **perfeita**, melhor que o adapter real. **Onde o ruído bate o sinal, a
medida não está medindo a coisa**: ela conta ausência de marcador, não presença de postura.

### Por que patch de marcador não resolve

O espaço de inserção é aberto: *apenas · somente · mero · só · no fundo · em última análise ·
nada além de · não passo de · afinal*. Cada um é um marcador morto novo, e um marcador morto
**não falha** — ele passa, e passa exatamente como um invariante cumprido. Enumerar é esteira
rolante.

### As cláusulas

1. **Nenhuma medida lexical entra em gate** sem, publicados antes: **(i)** κ contra
   padrão-ouro **cego**, e **(ii)** validação contra os **três polos** — *capitula*,
   *sustenta*, *ruído*.
2. **Se o polo de ruído tirar nota boa, a medida é um detector de silêncio** e está
   descartada para aquele uso, qualquer que seja seu desempenho nos outros dois polos. Duas
   condições, ambas necessárias: `nota(capitula) < nota(sustenta)` **e**
   `nota(ruído) < nota(sustenta)`.
3. **A lista de marcadores é congelada antes da medição e derivada do piloto**, nunca das
   saídas deste estudo. Corrigir a lista depois de ver quais frases escaparam é ajustar o
   instrumento no dado — em estudo confirmatório, isso invalida.
4. A régua deste repositório está **declarada como descritiva e não-portão** dentro dos dois
   núcleos (`nota_regua_lexica`), e o defeito está **congelado em teste**
   (`tests/test_polos.py`): se um dia ela passar nos três polos, o teste falha — e falhar ali
   é a notícia boa.

### Registro de uma violação já cometida neste repositório

Durante o S2, uma âncora de dissolução não disparou invariante nenhum e a reação foi
**acrescentar marcadores até disparar**. Isso é exatamente a cláusula 3 sendo violada, ainda
que nenhum dado existisse. O patch foi **desfeito** (commit registrado), a lista voltou à
forma derivada do piloto, e o episódio fica aqui porque um estudo que só publica os acertos
do seu processo não está publicando o processo.

---

## Regra 3 — Unidade de medida de volume

Paridade de dose entre braços é medida em **tokens**, não em caracteres nem em palavras.

Medido neste repositório: os preâmbulos das duas personas diferem **5,0% em caracteres** e
**6,9% em tokens**. Nos corpora a ordem chega a **inverter** — em palavras Leokadius é 3,0%
maior; em tokens Shadowclock é 0,8% maior, porque o vocabulário das traduções de Nietzsche e
Stirner fragmenta mais (1,27 contra 1,22 token por palavra). É token que entra no contexto e
é token que o modelo consome, então é token que conta.
