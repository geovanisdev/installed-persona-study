# Golden-batch — laudo de fidelidade do porte

O risco de portar um harness de medida não é o código quebrar: isso aparece no primeiro
run. O risco é ele **rodar e produzir números levemente diferentes** — um split que
embaralha em outra ordem, uma normalização que trata acento de outro jeito, um hash sobre
outra serialização. Nada disso levanta exceção, e tudo isso invalida qualquer comparação
com o estudo-piloto.

Este laudo registra a execução em que o harness portado foi alimentado com o **conteúdo
do harness de origem** e teve de reproduzir os selos **byte a byte**.

## Execução

| | |
|---|---|
| Data | 2026-07-21 |
| Comando | `IPS_LEGACY_DIR=<identity/ do projeto predecessor> python -m pytest tests/test_golden_legacy.py` |
| Resultado | **7 passed** |
| Python | 3.12.10 |
| Dependências | numpy 2.4.6 · scipy 1.18.0 · PyYAML 6.0.3 · pytest 8.4.2 |
| Efeito no projeto de origem | **nenhuma escrita** — leitura de dois JSON e import de três módulos stdlib puro |

## O que foi provado

**G1 — selo do núcleo.** O `core_hash` gravado no projeto de origem, recalculado pelo
hasher portado a partir do mesmo JSON:

```
781b830385fe338405693603f22a9aefa10888c44d72cba9a1b73ec87b23f8fa
```

Estável também sob round-trip de serialização (`G1b`) — condição para que um artefato
que cita um hash dependa do *conteúdo*, e não de como o arquivo foi gravado.

**G2 — banco de itens.** As constantes de módulo do harness de origem (personas,
preâmbulos, 12 contextos neutros, 12 turnos de pressão, semente 4004, held-out 0,35)
foram traduzidas para a especificação-em-dado que o harness portado consome. O
`battery_hash` resultante:

```
5b9d7f665536b9ad8d78a97e9c134adcaf3bbfb903fb8abc48fbbd3c38a4cc7f
```

Um único hash cobre, de uma vez: ordem das personas, ids dos contextos, split por
contexto, estratificação por regime, embaralhamento por semente e serialização canônica.
Qualquer divergência em qualquer um deles o mudaria. Verificado em três frentes — contra
o hash esperado (`G2`), contra o arquivo gravado na origem (`G2b`), contra o módulo de
origem **executado agora** (`G2c`, que fecha a hipótese de o artefato estar defasado do
código que o gerou) — e, por fim, campo a campo nos 96 trials (`G2d`).

**G3 — régua.** O detector de violação consciente de negação decide **igual à origem,
sonda a sonda**, em 12 sondas escolhidas nos pontos de falha conhecidos (negação
adjacente, marcador que já é negação, casamento no meio de palavra, texto vazio).
Igualdade de *decisão*, não de média: duas réguas podem concordar na média e discordar em
todo item.

## O que este laudo não prova

- Nada sobre os **runners de GPU** (treino, geração, juiz): eles não fazem parte desta
  entrega. Ver `PORT_LOG.md` § *O que ainda não foi portado*.
- Nada sobre **utilidade**: reproduzir um hash prova fidelidade mecânica do porte, não que
  o instrumento meça o que diz medir. Essa é a pergunta do S4 e do S6.

## Reprodutibilidade por terceiros

O projeto predecessor é privado e seu conteúdo — núcleo, preâmbulos, banco de itens — **não
é redistribuído aqui**. Este repositório guarda apenas os hashes esperados, que identificam
o conteúdo sem revelá-lo. Sem a variável `IPS_LEGACY_DIR`, os sete testes são **pulados**,
não falham: quem clona o repositório vê o laudo e o teste, mas só quem tem o repositório de
origem consegue reexecutá-lo.
