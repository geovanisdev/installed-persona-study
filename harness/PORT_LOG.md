# Registro do porte

Todo módulo aqui é **cópia adaptada** de um harness privado (projeto predecessor,
jan–jul/2026), onde o estudo-piloto e o achado de dissociação nome–postura se originaram.
Cada arquivo declara sua origem no próprio docstring; esta tabela consolida, e a segunda
metade do documento registra o que **ainda não** foi portado e as decisões que o porte
exigiu.

## Portado e verificado

| Origem (`eval_mech/identity/`) | Aqui | O que mudou |
|---|---|---|
| `identity_core.py` | `persona_core.py` | **Inversão estrutural**: o núcleo deixa de ser código e passa a ser dado. Ver abaixo. Hash, normalização e pontuação preservados byte a byte. Acrescenta validação de schema, selo explícito (`seal_core`) e regex de scrub derivada do núcleo. |
| `core_scorer.py` | `core_scorer.py` | Núcleo passa a ser argumento obrigatório (havia um `load_core()` implícito que puxava a única persona existente). Removido o stub `judge_score`, que só levantava `NotImplementedError`: o juiz deste estudo é módulo próprio, validado no S4. |
| `battery.py` | `battery.py` | Personas, preâmbulos e itens saem do código e entram numa **especificação em disco**. Acrescenta campos opcionais (`generator`, `cluster`, `paraphrase_idx`) omitidos da serialização quando ausentes — é isso que preserva o hash do original. |
| `stats_gates.py` | `stats_gates.py` | Limiares que estavam escritos dentro do corpo das funções (`0.5`, `0.70`, `5 p.p.`) viraram argumentos: neste estudo eles nascem do pré-registro selado e não podem ser default escondido. Gates de win-rate separados em "supera o nulo" e "claim forte". |
| `transcript_io.py` | `transcript_io.py` | Id de modelo, diretório de dados e origem do `core_hash` saem do corpo do módulo. O índice passa a registrar `sujeito_sha` e `git_dirty`. |
| — | `config.py` | **Novo.** Concentra o que era hardcode de máquina/projeto espalhado (id do modelo em três módulos, `HF_HOME` em três, caminhos de dados). Tudo por ambiente, com default. |

Verificação: `pytest` → **91 passed** (84 de comportamento + 7 de golden-batch). Laudo de
fidelidade em [`goldens/GOLDEN_BATCH.md`](goldens/GOLDEN_BATCH.md).

## A inversão do núcleo (a decisão de projeto do porte)

No original o núcleo **não era dado**: uma função `build_core()` de ~340 linhas devolvia o
núcleo de uma única persona escrito inline, e o hash era tirado da saída dessa função. Com
uma persona isso funciona. Com duas, cada persona nova exigiria editar o módulo, e o
"núcleo" deixaria de ser um artefato selável e revisável para virar um trecho de programa.

Aqui o núcleo é um JSON autorado e selado por pessoa; o módulo é apenas schema, selo e
régua. Três consequências que importam para este estudo:

1. `--core caminho.json` é argumento de todo runner — nenhuma persona vive no código;
2. selar é ato explícito e datado, não efeito colateral de rodar;
3. quem é dono do construto revisa e sela **JSON**, sem ler Python.

A validação recusa duas coisas que no original falhavam em silêncio: marcador `viola_se`
fora da forma normalizada (nunca casaria — o invariante pareceria cumprido para sempre) e
predição de sobreposição que cobre os dois lados (não é predição).

## Dependências que faltavam na lista de porte

O fecho transitivo de imports foi resolvido programaticamente antes de copiar qualquer
coisa. O plano listava 15 arquivos; o fecho real é de **21 módulos**. Faltavam:

| Módulo | Puxado por | Situação |
|---|---|---|
| `gemma_features.py` | 4 runners | S1b — precisa virar abstração de família de modelo |
| `run_id2_behavioral.py` | juiz e E5 (`_load_plain`) | S1b |
| `capitulacao_screener.py` | construtor do gold | S1b |
| `e4_validators.py` | bateria E4 | S1b |
| `projector.py` + `metrics.py` (em `calib/`) | só `evaluate.py` | S1b, e ver decisão em aberto (2) |

## O que ainda não foi portado

Tudo que toca torch: `causal_identity`, `gemma_features`, `run_id2_behavioral`,
`run_qlora`, `run_qlora_conviccoes`, `run_conviccoes_eval`, `run_e2_juiz_vs_humano`,
`run_e5`, `run_e4b_socratico`, `evaluate` + `projector` + `metrics`, e os construtores de
corpus e de gold. Também não foi portado o `thresholds.yaml` como template de
pré-registro — ele pertence ao S3, que é quem preenche e sela os valores.

O corte foi feito onde o código se divide sozinho: **espinha livre de torch, verificável em
CPU** de um lado; **runners de GPU** do outro. A espinha é a que carrega hash, selo,
régua, arquivamento e estatística — ou seja, tudo de que o pré-registro depende e nada que
dependa de GPU.

## Decisões em aberto (para o Arquiteto)

1. **Fixtures do golden-batch não são redistribuídas.** O teste lê o repositório privado
   por variável de ambiente e é *pulado* sem ela; o repositório público guarda apenas os
   hashes esperados. A alternativa — publicar núcleo e banco de itens de origem para que
   qualquer um reexecute — foi descartada por conta própria porque publicaria conteúdo do
   projeto privado. Reversível se a decisão for outra.
2. **`evaluate.py` + `projector.py` + `metrics.py`** implementam a linha de projetor/AUC
   (portões ID-1/ID-2 geométricos). Nenhum endpoint primário deste estudo a usa, e ela já
   levou KILL sobre modelo vanilla no projeto de origem. Portar por completude preserva
   opcionalidade e custa pouco; cortar é a decisão irreversível. Sugestão: portar, e
   decidir no S3 se entra em alguma pergunta.
3. **Família do juiz.** `build_input_ids` do original injeta ids de token de turno do
   Gemma (105/106) direto no prompt. Com juiz de outra família (S4), isso precisa virar
   uma abstração por modelo — é o primeiro trabalho do S1b, e é onde mora o risco de porte
   que o plano já antecipava.
