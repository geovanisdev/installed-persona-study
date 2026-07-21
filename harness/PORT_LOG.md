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
| `gemma_features.build_input_ids` + `TURN_START/END` | `model_family.py` | **Abstração de família.** Ver abaixo. Acrescenta guarda em tempo de execução dos ids de controle e um formato genérico via `chat_template`, com modo de raciocínio desligado. |
| `causal_identity.py` | `generation.py` | Âncoras do contraste saem do código e vêm do núcleo; dispositivo sai do modelo em vez de `device=0` literal; montagem do prompt vem do formato de família. Ganchos de intervenção preservados. |
| `run_id2_behavioral._load_plain`, `run_qlora._load_for_train`, `run_conviccoes_eval._load_it_conv`, `gemma_features.load_model` | `model_io.py` | **Quatro cargas quase iguais viram uma.** Acrescenta a trava de revisão (ver abaixo) e `unload` explícito. |

Verificação: `pytest` → **107 passed** (100 de comportamento + 7 de golden em CPU), mais o
golden com pesos carregados: **21/21 idênticas → FIEL**. Laudo em
[`goldens/GOLDEN_BATCH.md`](goldens/GOLDEN_BATCH.md).

## A abstração de família (a decisão da parte 2)

No original o prompt era montado injetando os ids de token de turno do Gemma direto na
sequência (105 abre, 106 fecha). Aquilo estava **certo** para o que o projeto fazia — as
strings `<start_of_turn>` não existem naquele tokenizer, então montar por id era a única
forma correta. Mas amarra o harness a uma família.

Este estudo precisa de um juiz de **outra** família: um juiz que compartilha família com o
gerador não é um segundo olhar, é o mesmo olhar duas vezes — foi essa a terceira fraqueza
do piloto. Um prompt Qwen montado com tokens de turno do Gemma não mede o Qwen; mede um
Qwen confuso. Daí `model_family.py`: `Gemma4Format` reproduz a origem byte a byte (provado
em G4/G5) e **verifica em execução** que os ids de controle são os esperados, em vez de
confiar num comentário; `TemplateFormat` honra o `chat_template` nativo e desliga o modo de
raciocínio, porque um juiz emite uma decisão e cadeia de raciocínio no meio muda o que está
sendo medido — e o custo por item.

## A trava de revisão (acrescentada, não herdada)

Nenhum runner de origem fixava a revisão da base. Isso já custou caro lá: a referência
local avançou para uma revisão nova e o modelo quase trocou por baixo de um experimento em
curso — o sintoma foi um erro de download confuso, não um aviso de que o sujeito havia
mudado. Aqui o sujeito **é** o objeto de estudo: `assert_revision` aborta se a revisão local
não for a esperada, o modo offline é o default, e a revisão efetiva volta junto com o modelo
para entrar no selo de proveniência de cada geração.

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
| `gemma_features.py` | 4 runners | **portado** como `model_family.py` (parte 2) |
| `run_id2_behavioral.py` | juiz e E5 (`_load_plain`) | carga **portada** em `model_io.py`; o runner em si, não |
| `capitulacao_screener.py` | construtor do gold | pendente |
| `e4_validators.py` | bateria E4 | pendente |
| `projector.py` + `metrics.py` (em `calib/`) | só `evaluate.py` | pendente, e ver decisão em aberto (2) |

Uma armadilha do fecho, encontrada ao rodar: `causal_identity` **só importa** se `calib/`
já estiver no `sys.path` — o caminho que o próprio módulo monta aponta para um diretório
inexistente, e funcionava apenas porque os runners inseriam o caminho certo antes de
importá-lo. Quem for reexecutar o golden precisa reproduzir essa condição.

## O que ainda não foi portado

Os **runners completos**: os dois treinadores QLoRA (`run_qlora`, `run_qlora_conviccoes`),
o juiz pairwise (`run_conviccoes_eval`), o validador juiz-vs-humano
(`run_e2_juiz_vs_humano`), as baterias `run_e5` e `run_e4b_socratico`, os construtores de
corpus e de gold, e a linha de projetor/AUC (`evaluate` + `projector` + `metrics`). Também
não foi portado o `thresholds.yaml` como template de pré-registro — ele pertence ao S3, que
é quem preenche e sela os valores.

O que **está** portado é a base sobre a qual todos eles se apoiam: núcleo, bateria, régua,
arquivamento, estatística, formato de conversa, carga/descarga de modelo e primitivas de
geração. Os runners que faltam são composição dessas peças mais a lógica de cada
experimento — e a lógica de vários deles muda no S3, quando o desenho for selado, o que é
mais um motivo para não portá-los antes.

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
