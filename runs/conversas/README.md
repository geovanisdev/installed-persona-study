# `runs/conversas/` — o percurso, não só o resultado

Dois tipos de arquivo vivem aqui, e a distinção importa:

- **Braços experimentais** (`S5*.jsonl`) — gerações do modelo dentro de um run. São **dado**.
- **Bancada** (`S3*.jsonl`) — as transcrições dos agentes que **constroem** o estudo: escrevem
  itens, atacam bancos, consertam travas. Não são dado do desenho, e `conversa_log` as separa por
  `papel` exatamente para que trabalho de bancada nunca seja lido como resultado.

As duas classes são versionadas. `runs/` não é ignorado: geração bruta é evidência, e um achado
que não pode ser reexaminado é registro histórico, não resultado.

---

## Redação do nome da conta (2026-07-22)

As quatro transcrições de bancada carregavam **1383 ocorrências** do nome da conta local de
Windows da máquina. Este repositório é público, então elas foram substituídas por `%USERNAME%`.

**O que foi medido antes, e não suposto.** Varredura completa dos 4,17 MiB por token de API,
chave, `Authorization`/`Bearer`, senha, e-mail, CPF, telefone e IP:

| padrão | ocorrências | leitura |
|---|---|---|
| nome da conta | 1383 | **redigido** |
| token / chave / `Bearer` | 0 | — |
| e-mail real | 0 | os 52 casamentos eram decoradores (`@pytest.mark…`) |
| CPF, senha, `Authorization` | 0 | — |
| "IP" | 1 | falso positivo: `.1.1.1.1` é a coluna de acertos de `lexico` na tabela de degenerados |
| "telefone" | 1 | falso positivo: `15992595884`, o tamanho de `model.safetensors` |
| hex ≥ 40 | 376 | são os selos `sha256` do próprio estudo e revisões do HF — provenance, não segredo |

**As três formas em que o nome aparecia.** A primeira versão do script assumiu que toda
ocorrência era segmento de diretório (`Users\<conta>\`) e a contagem exaustiva mostrou que 333
não eram: o nome também é a coluna de **dono** na saída de `ls -l`, e uma vez o diretório
temporário do pytest (`pytest-of-<conta>`). Uma substituição ancorada em `Users/` teria publicado
essas 334. O padrão que se supõe e o padrão que existe divergiram, e só a contagem sobre o
conjunto inteiro mostrou.

## O que isso fez com os selos, e o que foi feito a respeito

`sha256_resposta` sela o campo `resposta_completa` de cada registro, e `conversa_log.le_etapa`
**confere** o selo na leitura — um selo que ninguém confere é decoração. Em **12 registros** o
nome da conta estava dentro do texto selado, e redigi-lo quebrou o selo.

Deixar os 12 quebrados publicaria um log que o próprio leitor acusa como *"texto alterado depois
de gravado"* — verdadeiro, e indistinguível de adulteração. Então, nesses 12 registros e só
neles:

| campo | conteúdo |
|---|---|
| `sha256_resposta` | recalculado sobre o texto **publicado** — o leitor volta a poder provar que o que vê é o que está no log |
| `sha256_resposta_pre_redacao` | o selo **original**, que casa com o texto antes da redação |
| `redacao` | a regra, a data, o motivo, e onde o original ficou |

Nenhuma outra linha foi tocada: registros não afetados saem **verbatim**, sem re-serialização,
para que a única diferença entre estes arquivos e os originais continue sendo o nome da conta.

**A reversibilidade é provada, não alegada.** Aplicar `%USERNAME%` → nome da conta reproduz os
arquivos originais, e a prova é que os **12 selos pré-redação voltam a bater**: sha256 não perdoa
um caractere. Os originais não redigidos ficaram preservados fora deste repositório, num
repositório local que não tem remoto.

## A tensão que isto abre, e ela fica escrita

Este log é **append-only** por doutrina: nada é reescrito, nada é apagado. A redação reescreveu.

A leitura que sustenta a decisão é que o log local append-only e a **publicação derivada** dele
são artefatos diferentes, e que confundi-los é que seria o erro — mas a regra, na letra, foi
quebrada uma vez, de forma declarada, mecânica, auditável e sem tocar em nenhum resultado. Está
aqui para ser contestada, não para passar despercebida.
