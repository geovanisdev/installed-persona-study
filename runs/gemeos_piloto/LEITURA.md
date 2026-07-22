# Slice piloto de pares gêmeos — 20 pares, e o veredito é **PRECISA_CONSERTO**

**2026-07-22.** 20 cenários gêmeos escritos por 4 agentes cegos entre si (5 cada), 2
paráfrases por cluster: **40 itens de cada lado**. Estes itens **não são banco confirmatório**
e não devem ser promovidos a `batteries/`. Eles existem para responder uma pergunta só —
*a receita escala para 90?* — e a resposta medida é **não como está**.

## O que passou

Dez travas do `prod_validator` passaram nos dois bancos: PR-SCHEMA, PR-LEXICO, PR-LEAK,
PR-SCRUB, PR-META, PR-MOLDE, PR-ORTOGRAFIA, PR-USUARIO, PR-COMPARTILHADO, PR-INDICE.
Os 20 `par_id` casam **1:1**, zero órfãos, pior |Δtokens| entre gêmeos = **3**.

Três travas foram **puladas**, e estão listadas como puladas e não como verdes:
PR-DUP contra pilotos (o laudo passa `pilotos={}`), PR-F4 (não aplicável: tudo é F2) e
PR-HIJACK (não aplicável: nenhum item mora no banco `hijack`).

## O que reprovou, e uma reprovação que não é do banco

`PR-CLUSTER` acusou 9 vizinhanças e `PR-DUP` as mesmas 9 como quase-duplicatas.

`PR-PAR` deu `dose_media` = **−0,27 tokens** com IC95 **[−3,55; +2,90]**, fora de ±1,5 →
**NÃO-DEMONSTRADO**. Isso **não é assimetria medida**: é intervalo largo demais com 20
clusters. A n = 90 ele encolhe. Registrar como "reprovou" sem esta frase seria ler tamanho de
amostra como defeito de conteúdo.

## Os doze problemas que nenhuma trava mecânica pega

Cada um com item concreto. Sem item_id, não conta.

**Três são defeitos das próprias travas, e são consertáveis:**

1. **`PR-CLUSTER` cláusula (b) premia o defeito que ela deveria impedir.** O predicado é de
   *rank sem piso*: o vizinho mais próximo de uma paráfrase tem de ser a companheira. Quanto
   mais **idênticas** as duas paráfrases, mais folgado o item passa. `leokadius-c06-p0/p1`,
   `c00-p0/p1` e `shadowclock-c01-p0/p1` (similaridade interna 0,436) são a mesma frase com
   sinônimos trocados, ordem de oração e contagem de frases idênticas — e a trava **premia**
   isso. A paráfrase existe para testar se o efeito sobrevive à reformulação; sem piso de
   distância, ela não testa nada.
2. **`PR-CLUSTER` deixa cenário reciclado escapar por baixo do rank.** `leokadius-c00-p0` e
   `leokadius-c05-p0` são a mesma história (entrega no prazo, diretoria fica com a proposta
   do outro) sob o **mesmo** movimento, a Jaccard 0,156. Como as paráfrases de cada cluster
   ficam ainda mais perto, o rank não acusa. **Dois clusters vendidos como dois, medidos como
   um.**
3. **`PR-LEAK` é cego por ARIDADE.** `leokadius-c03-p0` e `c18-p0` trazem *"o que pode dar
   errado"*, span de 4 palavras da própria `superficie_postura.d_prosoche`. O 4-grama
   proibido é `(antecipacao, pode, dar, errado)` e o item emite `(versao, pode, dar, errado)`:
   **3 de 4 palavras iguais, interseção vazia**. Do lado shadowclock, `c08-p1`/`c12-p0`/
   `c16-p1` são construídos sobre *"existe uma razão por trás disso"* — a fórmula que o núcleo
   **nomeia** em `sem_consolo` para recusar. O item entrega a deixa exata da resposta.

   É a mesma família do defeito dos intensificadores consertado hoje: **a unidade de
   casamento da trava não é a unidade que o atacante usa.**

**Cinco são de autoria, e a receita precisa mudar:**

4. **Um só cenário cobre os 4 clusters de `prosoche`** (`c03`, `c08`, `c13`, `c18`): todos
   "madrugada em claro ensaiando catástrofe". A célula F2-por-movimento reporta n = 4 e mede
   **1 situação**. PR-MOLDE passou porque conta molde sintático, não família semântica.
5. **Prompt com a resposta embutida.** `shadowclock-c10-p0` enuncia `liberdade_radical` na
   boca do usuário; `c13-p0` traz o absurdo inteiro, premissa e desfecho; `c18-p1` entrega
   premissa **e** conclusão. Sob desenho **cruzado** isso é pior que desperdício: o braço
   leokadius recebe o mesmo texto já resolvido, os dois adapters concordam, e **a célula onde
   a divergência seria falsificada morre por eco.**
6. **Item que PEDE o movimento em vez de abri-lo.** `shadowclock-c16-p1` pergunta *"É esse
   tipo de conforto que você também vai me oferecer?"* — telegrafa a recusa. A resposta vira
   obediência à pergunta, e qualquer adapter acerta.
7. **Sofredor não casa entre gêmeos.** `leokadius-c10-p0` tem insônia declarada;
   `shadowclock-c10-p0` é constatação serena. Um lado convida consolo, o outro não. Mesmo
   defeito em `c18`.
8. **Tipo de pedido não casa.** `leokadius-c16-p0` pede decisão prática, `shadowclock-c16-p0`
   pede consolo. `c19` inverte: um chega decidido pedindo aval, o outro indeciso pedindo que
   escolham por ele. E `forma_convocacao` é **idêntico** nos dois, então nada acende.
9. **Confundidor moral dentro do par.** Em `leokadius-c15-p0` o falante é vítima; em
   `shadowclock-c15-p0`, mesmo esqueleto, ele é **cúmplice** ("oito meses vendo o projeto
   afundar e nunca abriu a boca"). Qualquer adapter responde diferente a vítima e a cúmplice,
   e essa diferença entra na célula rotulada como **divergência de postura**.

**Dois são do processo:**

10. **Lotes cegos colidem.** Cada agente viu só os seus 5 cenários. Saíram cinco famílias
    cobrindo **15 dos 20 pares**: "diretoria mata o projeto" (c00, c05, c10, c15), "oficina
    herdada do pai" (c02, c06, c11, c19), "pai ou mãe morrendo" (c04, c08, c16). Até os
    números colidem — "oito meses" em c07 e c15, "três da manhã" em c08 e c13. Com 4 agentes
    já saiu isto; **a 90 a colisão é estrutural**, e quem paga são PR-CLUSTER e PR-DUP.
11. **Buraco na grade de movimentos — e ele é meu.** O slice usa 20 dos 90 cenários do plano
    balanceado, e os 20 primeiros cobrem 20 das 25 combinações (L × S). Faltam exatamente 5:
    `dicotomia × sem_consolo`, `memento_mori × absurdo`, `apatheia × revolta`,
    `prosoche × liberdade_radical`, `metodo_socratico × ma_fe`. O plano completo cobre as 25;
    **o slice não é miniatura válida do desenho**, e eu o tratei como se fosse.

## O que fazer antes de escalar a 90

1. **Consertar as três travas** (piso de distância em PR-CLUSTER(b); floor absoluto além do
   rank em PR-CLUSTER; casamento por sobreposição parcial em PR-LEAK, não por *n*-grama exato).
2. **Ledger compartilhado de cenários** entre os agentes: família, papel, registro e números
   citados, para que lote cego não recicle.
3. **Regra de autoria nova**: o prompt não pode conter a conclusão nem pedir o movimento.
4. **Casar sofredor, tipo de pedido e posição moral** dentro do par, e não só `forma_convocacao`.
5. Amostrar cenários **cobrindo a grade 5×5**, não os *n* primeiros.

Nada disso invalida o **plano** de 90 (que é balanceado, 18 por movimento de cada lado, 25 de
25 combinações). Invalida **a receita de autoria** que este slice usou, e era exatamente para
isso que o slice existia.
