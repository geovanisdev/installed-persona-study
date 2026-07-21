# Banco de vazamento — o piso que existe antes de qualquer adapter

`leakage_baseline_items.jsonl` · 42 itens · congelado antes de existir qualquer geração

## Por que este banco vem primeiro

O modelo base não é uma folha em branco. Estoicismo e existencialismo estão no pré-treino de
qualquer LLM contemporâneo, e uma resposta estoica a um problema de trabalho é resposta
*default* de assistente, não efeito de persona instalada.

Sem medir esse piso, qualquer taxa de emissão observada depois do adapter é ambígua: pode ser
o que o QLoRA instalou ou pode ser o que o pré-treino já entregava de graça. O banco existe
para tornar essa diferença legível — o efeito do adapter é o que **excede** o piso, e o piso
é medido nos **mesmos itens**, sem preâmbulo e sem adapter.

## Blocos

| Bloco | n | O que mede |
|---|---|---|
| `oportunidade_estoica` | 15 (3 × 5 movimentos) | quanto de Leokadius a base emite sozinha |
| `oportunidade_existencialista` | 15 (3 × 5 movimentos) | quanto de Shadowclock a base emite sozinha |
| `autorreferencia` | 6 | piso de F1: emissão espontânea de nome (deve ser ~0) e de linguagem de dissolução |
| `neutro_controle` | 6 | deriva de registro e capacidade: itens sem nenhuma abertura para postura |

Os dois blocos de oportunidade são **pareados por construção**: mesmo número de itens, mesmo
número por movimento, e comprimento equivalente (verificado em `tests/test_leakage_baseline.py`).
Um bloco mais longo ou mais carregado que o outro produziria uma diferença de piso que seria
lida como diferença entre as personas.

O bloco neutro não é enfeite. Ele responde a duas perguntas que o resto não responde: a persona
invade tarefa que não a convoca? E o adapter custou capacidade?

## O que um item pode e não pode conter

**Nunca**, em nenhum item: o léxico de *resposta* das personas — os termos com que elas fazem o
próprio movimento (`dicotomia`, `apatheia`, `prosoche`, `memento mori`, `absurdo`, `ma-fe`,
`revolta`, `liberdade radical`, `consolo metafisico`, `sem lamento`), os dois nomes de persona,
e os nomes dos autores do grounding. Um item que entrega o vocabulário da resposta mede eco, não
vazamento — e infla o piso justamente onde o efeito seria medido.

**Permitido, mas declarado**: fórmulas na boca do *usuário*. Os três itens de `ma_fe`
(`lb-exi-10`, `-11`, `-12`) precisam que o usuário diga *"eu sou assim"*, *"não tive
alternativa"*, *"faz parte de quem eu sou"* — a oportunidade **é** o usuário proferir a fórmula.
Esses itens trazem o campo `lexico_do_usuario` listando a expressão exata, e o teste exige essa
declaração: nenhuma expressão da lista entra em item que não a declare.

## O instrumento que pontua isto **ainda não existe**

Os itens estão congelados; a régua que os pontua, não.

Contar palavras-chave estoicas/existencialistas nas respostas da base é exatamente a família de
medida que **reprovou** nos três polos (`PREREGISTRATION.md`, Regra 2; `harness/polos.py`). Ela
seria conveniente aqui e seria errada pelo mesmo motivo: uma resposta vazia não contém
palavra-chave nenhuma e tiraria nota de "sem vazamento".

Portanto, e isto é regra e não intenção: **nenhuma medida pontua este banco antes de passar em
`polos.valida_medida` e ter κ contra padrão-ouro cego reportado.** O caminho previsto é o juiz de
família cruzada (S4). Se ele não passar, o piso fica sem medida — e o resultado a publicar é que
ficou, não uma nota obtida com régua reprovada.

Congelar os itens agora e a régua depois é deliberado: o que precisa anteceder o dado são os
**itens**, para que não sejam escolhidos olhando as respostas. A régua precisa anteceder a
**medição**, que é momento posterior.

## Disjunção e reuso declarados

- **Disjunto** dos bancos confirmatórios do S3 (`battery_leokadius`, `battery_shadowclock`,
  `battery_shared`, `battery_hijack`). Nenhum item daqui entra lá, e vice-versa.
- **Reuso permitido**: o piloto de teto do S3 pode usar estes itens. Os dois usos são
  pré-medição e nenhum deles gasta item do banco confirmatório — que é a razão da regra de
  disjunção existir.
- **Reuso proibido**: nenhum item daqui entra na medição confirmatória, mesmo que sobre.

## Proveniência dos itens

Todos os 42 itens declaram `generator: "claude-opus-4-8"`. A declaração serve à exclusão por
família na hora de julgar: o juiz previsto é Qwen3-8B, de família distinta da que escreveu os
itens e distinta da que os responde (Gemma 4). Um item escrito, respondido e julgado pela mesma
família mediria concordância de família, não persona.

**Registro de limitação**: os itens foram escritos por mim, não amostrados de interações reais.
São plausíveis, não empíricos. Isso limita a generalização e está declarado aqui em vez de
implícito.

## Registro de forma: a decisão de ortografia foi exercida

Esta seção dizia, até 2026-07-21, que os prompts seguiam a convenção herdada do pipeline de
origem — português **sem** acentuação — e terminava oferecendo a reversão: *"se o Arquiteto
preferir português acentuado, é agora."*

**O Arquiteto preferiu, a reversão foi feita, e a seção ficou para trás.** Os 42 itens deste
banco estão acentuados (41 deles contêm ao menos uma palavra acentuada; o restante não tem
nenhuma palavra que exija acento). O texto acima descrevia um artefato que já não existia.

Fica o registro de que isto foi encontrado numa releitura, e não por um teste: **nenhuma guarda
compara a prosa de um documento com o arquivo que ele descreve.** O `tests/test_ortografia.py`
verifica a acentuação dos itens — o que ele não podia verificar era um `.md` afirmando o oposto.
É o modo de falha mais barato de produzir e o mais caro de detectar: cada peça está correta
isoladamente, e a contradição só aparece para quem lê as duas.

A regra que passou a valer está em `PREREGISTRATION.md`, Regra 4: texto de **estudo** é acentuado
sempre; **chave de casamento** (`viola_se`) fica na forma normalizada, porque acentuada nunca
casaria; **fixture de fidelidade** fica congelada na forma da origem, e só enquanto for golden
publicado e não contexto de medição. E a Regra 5 registra o A/B que deu à decisão justificativa
causal, e não apenas estética: com o preâmbulo acentuado, o eco de preâmbulo na base nua caiu de
9/24 para 0/24 (McNemar exato, p = 0,0039).
