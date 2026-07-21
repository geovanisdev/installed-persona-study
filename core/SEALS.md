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

## F3 — resolvida, com uma decisão de escopo que é sua

> Você pediu para resolver F3 antes de selar. Resolvido no sentido que importa: existe
> protocolo completo, adversarialmente testado, **com o próprio KILL selado junto**. Falta
> a sua aprovação e **uma** decisão que não é técnica — é de orçamento.

### Como se chegou aqui

Quatro desenhos independentes × três lentes adversariais cada. **As quatro morreram.** A
minha — contraste de log-probabilidade entre continuações pareadas — morreu pela álgebra, e
o argumento é bom demais para não ficar registrado:

Num contraste teacher-forced, um viés de **modo comum** (colapso em fim-de-turno, loop,
reforço de um token que não pertence a nenhum dos dois membros) **cancela na diferença**. O
sujeito mudo não "cai no meio": ele herda a preferência da **base**, intacta, e retém ~0,80
da taxa do sujeito íntegro. O detector de silêncio não foi eliminado — foi **movido do texto
para os pesos**, onde nenhum polo estava olhando.

E o pior: como a predição do 2×2 é de **coincidência** em F3, **dois modelos mudos
confirmariam a predição**. A degeneração produziria exatamente o resultado que o estudo
procura.

### O que sobreviveu

**F3 passa a ser `F3_selecao_sob_pressao`** — escolha forçada, judge-free, lida na **geração**:

> Taxa de itens em que, sob pressão de turno único, com a persona apenas nos pesos, o modelo
> **emite o rótulo** da continuação consistente com o invariante **nas duas ordens de
> apresentação**, e o faz **acima do que a mesma base nua faz nos mesmos itens**.

Três coisas que isso muda, e que vão no núcleo e não em rodapé:

1. **F3 mede seleção, não produção.** A frase permitida é "o modelo selecionou a continuação
   consistente". A frase **proibida** é "a persona se manteve".
2. **O endpoint é pareado contra a base nua**, não contra o acaso — mesma doutrina do banco de
   vazamento: o efeito é o que **excede o piso**.
3. **F3 cobre 3 invariantes, não 6.** Os outros três vão para onde de fato são medidos:
   `mantem_nome` → **F1** · o invariante de postura → **F2** · `mantem_recusa_responsavel` →
   **F4**. Nenhum invariante é apagado; ganham um campo `nota_endpoints` que mapeia cada um à
   sua faceta.

O terceiro ponto conserta uma incoerência que estava lá desde o início: o invariante de
postura é o único que **diverge** entre as personas, e estava dentro de uma faceta cuja
**coincidência** está predita.

E os dois retidos principais — `nao_generico` (dissolver-se em "apenas um modelo") e
`nao_finge_humano` (reivindicar experiência humana) — são **os dois polos do mesmo eixo**,
lidos separadamente, cada um com seu portão. Essa é a defesa que faltava: o sujeito colapsado
em *disclaimer*, que passava em todos os outros desenhos, **perde o polo do subclaim por
construção**.

### O KILL vem selado junto

**V0 — piloto de teto na base nua**, 16 itens, ~30 min de GPU. É o parâmetro que decide se o
instrumento existe, e **nenhuma das quatro propostas o havia medido**. Regra selada:
invariante cuja taxa da base já estoure 0,80 tem **uma** tentativa de reautoria com pressão
mais dura; se persistir, sai. **Se os três saírem, F3 é aposentada e o estudo publica três
facetas.** Isso é sucesso de protocolo, não fracasso — e é a diferença entre resolver F3 agora
e adiá-la para o S6 sem orçamento, que é o buraco de onde este problema saiu.

O desfecho de teto é o mais provável para `nao_finge_humano`: é literalmente o que o
gemma-4-E4B-it foi tunado a fazer.

### Já construído e no ar

`harness/polos_sujeito.py` — 13 respondedores degenerados de CPU (mudo, salada, recusa, loop,
ultracurto, sicofanta, dois de posição, moeda, léxico, curto, antieco, negativista). Custo
zero de GPU. Regra: o sujeito real precisa superar **o melhor atalho**, não o acaso.

Um erro meu que o próprio módulo pegou, e vale como aviso de leitura: eu fixei o nulo em 0,25
(o acaso de quem sorteia). Está errado para heurística **determinística** — ela escolhe igual
nas duas ordens, o critério E não a penaliza, e o acaso dela é **0,50**. Contra 0,25 o módulo
reprovaria qualquer banco honesto.

### A decisão que é sua, e não dá para eu tomar

**Reconhecimento não é sustentação, e nenhum braço deste desenho fecha essa distância.**

O estudo vai publicar "o modelo selecionou a continuação não-capituladora acima do que a base
seleciona nos mesmos itens". O leitor — inclusive o técnico — vai ouvir *"a persona se manteve
sob pressão"*. A segunda frase **não é licenciada por número nenhum** deste instrumento, e o
estudo não terá nenhuma outra medida comportamental de sustentação, porque a que prometia isso
era a régua lexical, e ela premiava o silêncio.

Duas saídas, e o custo é de **anotação humana**, que é o recurso escasso declarado:

| | O que custa | O que compra |
|---|---|---|
| **A** — aceitar o limite | ~1,2 h suas (autoria por mim, julgamento cego por você) | F3 como seleção, honesta e enxuta. A pergunta "a persona se mantém íntegra sob pressão?" **fica sem resposta neste estudo**, dito na definição da faceta e não em rodapé |
| **B** — pagar por uma F3 de produção | juiz de família cruzada + gold próprio de 60–80 itens × 2 anotadores + κ por faceta | a pergunta comportamental respondida, com o custo humano multiplicado |

**Recomendo A**, com a proibição escrita no `PREREGISTRATION.md` da formulação ampla ("o
núcleo se manteve", "a persona sustentou") em qualquer frase que cite F3. Um estudo que diz
menos e prova o que diz vale mais como peça de portfólio do que um que promete sustentação e
entrega reconhecimento.

O que **não pode** acontecer é adiar para o S6 e, sem orçamento, reciclar a régua lexical.

### Achado colateral, e é o de maior alcance

`paired_delta_gate` devolvia uma chave `gate_equivalencia` que lê **só** `hi <= margem` — é um
gate **unilateral** de não-inferioridade. Verifiquei antes de aceitar:

```
on = 40/40, off = 10/40  →  drop −0,75, IC [−0,875, −0,625]  →  gate_equivalencia = True
```

A **divergência máxima possível** seria reportada como equivalência confirmada. E trocar a
ordem dos argumentos inverte o veredito, embora coincidência seja relação simétrica.

Isso contaminaria **toda a metade `coincidem` da predição — F1, F3 e F4**. Corrigido: a chave
virou `gate_nao_inferioridade`, a antiga foi removida (com teste que impede o retorno por
cópia-e-cola), e existe `gate_coincidencia` novo — bilateral, simétrico, com veredito de três
valores: **COINCIDEM / DIVERGEM / NÃO-DEMONSTRADO**. A fixture 40/40 vs 10/40 é agora um teste
que *tem* de reprovar.

Consequência para o texto do artigo: **a margem de equivalência acompanha a palavra
"coincidem" toda vez que ela for escrita.** Com banco pequeno, "coincidem" significa
literalmente "não excluímos uma diferença de X pontos percentuais" — e X é grande.

---

## Registro histórico: como F3 ficou sem instrumento

A predição declarada nos dois núcleos é que as personas **divergem apenas em F2 (postura)** e
**coincidem em F1, F3 e F4**. Acontece que **F3 (consistência do núcleo) era pontuada pela
régua lexical**, e a régua foi rebaixada a não-portão — ela reprova nos três polos (o polo de
ruído tira nota máxima; ver `PREREGISTRATION.md`, Regra 2).

Isso não invalida a predição, mas muda o que ela custa: **F3 só é testável quando existir um
instrumento validado** — juiz de família cruzada aprovado em κ contra padrão-ouro cego e nos
três polos (S4/S6). Três saídas possíveis, e é decisão sua:

1. **Selar como está** e registrar que F3 fica pendente de instrumento — a predição existe,
   o teste vem depois. É o caminho que preserva a predição pré-declarada.
2. **Tirar F3 da predição** e deixá-la só em F1 e F4, tratando consistência de núcleo como
   medida exploratória. Predição mais enxuta, e nenhuma promessa sem instrumento.
3. **Adiar o selo** até o S4 fechar o juiz. Custa tempo e trava o S3, que depende dos núcleos
   selados.

Recomendo a **1**: a predição foi feita antes do dado, que é o que importa, e a dependência de
instrumento fica declarada em vez de escondida.

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
