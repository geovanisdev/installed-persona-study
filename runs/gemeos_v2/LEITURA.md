# Slice v2 — 25 pares gêmeos sob a Regra 9, e um defeito de programa que a medição achou

**2026-07-22, Etapa B2.** 25 clusters × 2 lados × 2 paráfrases = **100 itens**, escritos à mão
um a um. Fonte revisável em `cenarios.py`; JSONL montado por `runners/build_gemeos_v2.py`, que
não escreve texto nenhum. Laudos em `diagnostico.json` e `gate.json`.

Estes itens **não são banco confirmatório** e não devem ser promovidos a `batteries/`. Eles
respondem uma pergunta só — *a receita de autoria corrigida escala?* — e a resposta é **sim para
a autoria, não para uma das travas**, pelo motivo abaixo.

## A grade fechou

`c00`–`c24` cobrem as **25 combinações L × S uma vez cada**. O slice velho usava os 20 primeiros
cenários do plano de 90 e cobria 20 de 25; `c20`–`c24` eram exatamente as cinco que faltavam.
Isto é miniatura válida do desenho — o slice anterior não era, e foi tratado como se fosse
(problema 11).

O ledger registrou **50 cenários** (25 famílias × 2 bancos), **5 famílias por movimento** nos
dez movimentos, e **nenhuma colisão recusada**.

## O que passou: 13 travas, nos dois bancos

`PR-SCHEMA` · `PR-LEXICO` · **`PR-LEAK`** · `PR-SCRUB` · `PR-META` · `PR-MOLDE` · `PR-CLUSTER` ·
**`PR-FAMILIA`** · `PR-ORTOGRAFIA` · `PR-USUARIO` · `PR-COMPARTILHADO` · `PR-DUP` · `PR-INDICE`.

As três que interessam são as que o piloto reprovou:

- **`PR-LEAK` verde.** Zero *n*-gramas das fontes dos dois núcleos, em 100 prompts. No piloto
  eram 2 itens carregando *"o que pode dar errado"*, span de 4 palavras da própria
  `superficie_postura.d_prosoche`.
- **`PR-FAMILIA` verde.** 25 famílias distintas, nenhuma repetida em movimento nenhum. No
  piloto, duas famílias repetiam por banco.
- **`PR-CLUSTER` verde.** Zero vizinhanças. No piloto eram 9 (3 + 6). O que mudou é
  estrutural: **cada cenário carrega três ou quatro substantivos concretos que só ele usa**
  (a coleira do Tobias, o forno da padaria, o crachá na portaria), e as duas paráfrases os
  mantêm. O que aproxima as companheiras é o objeto da cena; o que afasta os clusters é o
  objeto ser outro.

Foram necessárias **duas rodadas** de conserto, todas nomeadas pelo modo `diagnostico`: quatro
`cluster:copia` (6-grama de conteúdo repetido entre paráfrases), duas `cluster:vizinho`, cinco
`ortografia:texto_longo_sem_acento` — três delas em `construto`, campo que o modelo não lê mas
que a Regra 4 cobre — e onze pares fora do teto de dose.

## O que reprovou: `PR-PAR`, e não era do banco — RESOLVIDO no mesmo dia

> **2026-07-22, depois desta leitura.** O Arquiteto decidiu a primeira das três saídas abaixo:
> **volta o bootstrap pareado**. Registrada em `PREREGISTRATION.md` § *"Decisão 2026-07-22"*.
> Sob o estimador restaurado o slice v2 dá **`PARITARIO`**, IC95 **[−1,08; +0,12]**, cobertura
> do pareamento **1,0** — e o **slice piloto velho também passa**, o que confirma que o
> veredito nunca foi sobre o conteúdo de banco nenhum. A seção abaixo fica como o registro da
> medição que produziu a decisão.

```
par:dose_media   leokadius − shadowclock = −0,48 tokens
                 IC95 [−2,78; +1,84]   fora de ±1,5  →  NÃO-DEMONSTRADO
```

O **ponto** está a meio token de zero. Nenhum par excede o teto de ±3. O que reprova é a
**largura do intervalo** — e ela não vem do banco.

### A conta que justificou a margem é de outro estimador

`prod_validator.py:304` registra a procedência de `MARGEM_DOSE_MEDIA_TOKENS = 1.5`:

> *"Com |delta_j| <= 3 o desvio-padrão de delta é <= 3 e a semilargura do IC em 90 clusters fica
> ~0,35 token: a trava é capaz de passar E capaz de falhar."*

`delta_j` é o delta **pareado**. A conta está certa: medido neste slice, a semilargura pareada
projetada a 90 clusters é **0,32** — praticamente o número previsto.

Mas a nota de desenho do desenho cruzado trocou o estimador — *"deixa de ser bootstrap PAREADO
sobre delta_j e vira bootstrap de DUAS AMOSTRAS sobre as médias por cluster, com a **mesma**
margem bilateral de ±1,5 token"* — e `_bootstrap_duas_amostras` reamostra os dois braços com
índices **independentes**. A margem foi transportada sem que a conta que a produziu fosse
refeita, e o comentário que guarda essa conta continua descrevendo o estimador antigo.

### Os números, medidos neste slice

Desvio-padrão do comprimento **entre** clusters: 4,25 (leokadius) e 4,31 (shadowclock).
Desvio-padrão do delta **pareado**: 1,53 — porque cada gêmeo nasce do mesmo núcleo de situação.

| | erro-padrão | semilargura | |
|---|---|---|---|
| duas amostras, n=25 | 1,21 | **2,35** | maior que a margem inteira |
| pareado, n=25 | 0,31 | 0,60 | cabe com folga |
| duas amostras, n=90 | 0,63 | **1,24** | come 83% da margem |
| pareado, n=90 | 0,16 | 0,32 | o número do comentário |

**A n=25 nenhum valor de ponto satisfaz a margem — nem zero exato.** A n=90 ela é satisfazível,
mas sobra **±0,26 token** para o viés real: quem lê `MARGEM_DOSE_MEDIA_TOKENS = 1.5` no código
lê uma tolerância **seis vezes maior** do que a que vai ser aplicada. Meio token de assimetria
sistemática — um terço da margem declarada — já reprova a 90 clusters.

`tests/test_alcance_dose_media.py` fixa isso em teste executável, inclusive a demonstração de
que os **mesmos números** passam com o estimador pareado. Se alguém trocar estimador ou margem,
os testes falham e a mudança tem de ser consciente.

### Também derruba uma frase que eu escrevi

`runs/gemeos_piloto/LEITURA.md` diz, sobre o mesmo veredito no piloto: *"é intervalo largo
demais com 20 clusters. A n = 90 ele encolhe."* Encolhe, mas **não o bastante para tornar a
margem o que ela parece ser**. Eu tratei largura de intervalo como problema de tamanho de
amostra quando era, em parte, escolha de estimador.

## O que eu não fiz, e por quê

Não mexi em `_bootstrap_duas_amostras` nem em `MARGEM_DOSE_MEDIA_TOKENS`.

Trocar o estimador ou a margem é mudar a régua depois de ver a medição, no exato caso em que a
mudança faria o meu próprio banco passar. É a forma canônica do defeito que este programa
registra desde o gate `LCB ≥ 0,75`. O pré-registro ainda está em DRAFT, o que faz deste o
momento certo para a decisão **aparecer** — e ela é do Arquiteto, não minha.

Três saídas, sem recomendação embutida no código — **a 1 foi a escolhida**:

1. **Manter duas amostras e afrouxar a margem** para o que ela operacionalmente já é. Custo: a
   margem passa a ser derivada da variância observada, e variância observada é dado do banco.
2. **Voltar ao bootstrap pareado onde o par existe.** O pareamento existe em 25/25 aqui e em
   90/90 no plano. A nota de desenho abandonou a **bijeção como eixo do contraste**, que é outra
   coisa: usar o par para estimar precisão não exige que o endpoint seja pareado. Custo: a
   trava passa a exigir uma estrutura que o desenho cruzado declarou não usar.
3. **Manter tudo e aceitar `NÃO-DEMONSTRADO` como veredito esperado**, tratando `par:dose_media`
   como descritivo e não como gate. Custo: some a única guarda mecânica de assimetria de dose.

### O custo que eu não previ, e que apareceu ao implementar

A lista acima estava incompleta. Sob duas amostras, um banco pequeno dava `NÃO-DEMONSTRADO` **por
construção** — a própria suíte registrava isso como consequência de cronograma: *"um banco piloto
pequeno NÃO pode ser selado por PR-PAR, e a razão não é o banco, é o n"*. Sob o pareado, um banco
de pares bem casados passa com **n = 6**.

Ou seja: a saída 1 comprou precisão e **vendeu uma proteção de tamanho de amostra** que ninguém
tinha decidido vender, porque ninguém — eu inclusive — tinha percebido que ela existia como
efeito colateral do estimador impreciso.

Está fixado em `test_pares_bem_casados_passam_com_n_pequeno_e_isso_e_o_custo` e declarado na
emenda do módulo. Se a proteção tiver de voltar, volta como **cláusula própria de *n* mínimo** —
nunca de novo como subproduto de uma imprecisão.

## Busca adversarial: o critério é transferência, e a pergunta não é a do F3

Num banco F3 a busca procura a heurística que **escolhe** a opção consistente sem ler o
construto. Aqui não há opção — F2 é produção livre. A pergunta equivalente sob desenho cruzado,
em que todo adapter responde os dois bancos, é: **uma regra de duas linhas diz de qual banco o
item veio?** Se disser, *"o adapter responde diferente aos dois bancos"* pode ser artefato de os
bancos serem trivialmente diferentes.

Separabilidade alta não é defeito por si — os dois bancos convocam movimentos diferentes de
propósito. O que decide é a **família** da regra que separa: regra de **forma** (comprimento,
pontuação, frases, dígitos) não é o construto, e se separar é assimetria incidental de autoria;
regra de **conteúdo** (campo semântico) é exatamente o que os movimentos são.

| regra | família | alvo (n=100) | transferência (n=80) |
|---|---|---|---|
| `campo_sentido` | conteúdo | 0,620 | 0,613 |
| `campo_controle` | conteúdo | 0,600 | 0,600 |
| `palavra_media` | forma | 0,580 | 0,487 |
| `negacoes` | conteúdo | 0,570 | 0,600 |
| `n_palavras` | forma | 0,550 | 0,450 |
| `termina_em_?` · `tem_interrogacao` · `n_digitos` · `primeira_palavra` | forma | 0,500 | 0,500 |

**Nada chega perto do limiar de 0,90.** A melhor regra é de conteúdo e fica a 0,12 do acaso.
Quatro regras de forma ficam exatamente em 0,500 — o acaso puro.

E a busca **prova que sabe achar**: antes de rodar, o controle positivo planta um atalho de
forma (um lado termina em `?`, o outro não) e exige 1,000. Se não achar, aborta. Uma busca que
nunca acha nada não é evidência de banco limpo — pode estar quebrada, e é o defeito que
`_controle_positivo` existe para pegar nas travas.

**O que esta busca NÃO diz.** Que os bancos sejam indistinguíveis. Ela cobre 12 regras de um
limiar só; um classificador treinado sobre o vocabulário separaria mais, e *deveria* — os
movimentos são diferentes. A afirmação é a estreita: **nenhuma regra barata, e nenhuma regra
cega ao construto, separa os dois braços.**

## Avisos que ficaram, e ficam declarados

O ledger avisou colisão de número em `"quatro anos"` (c02, c08, c14) e `"cinco meses"` (c05,
c07) — colisões reais entre cenários distintos. **Não foram trocadas**, pela razão escrita no
próprio módulo: recusar empurra o autor a números implausíveis, e um cenário com "dezessete
meses e meio" não é mais válido, é menos.

Outros avisos são artefato do casador: `numeros_citados` acha `"dois anos"` dentro de *"vinte e
dois anos"* e `"nove anos"` dentro de *"oitenta e nove anos"*. O casador só **super**-avisa,
nunca deixa de avisar, e por isso fica como está — registrado, não consertado.
