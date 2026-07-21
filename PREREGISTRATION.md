# Pre-registration — DRAFT, NOT SEALED

> **Status: rascunho.** Este documento é selado no S3, **antes de existir qualquer geração**.
> Enquanto estiver marcado como rascunho, nada aqui vincula — e nada aqui foi usado para
> produzir dado, porque dado ainda não existe. O histórico de commits é a prova da ordem.

Ao ser selado, este arquivo passa a conter: codebook das facetas F1–F4 com âncoras na
literatura, bancos de itens selados por hash, análise de poder fixando o *n* por célula,
lista fechada de endpoints primários com orçamento de α (Holm por família), e o plano de
ataques com equiparação de dose. Cada um desses blocos entra quando seu sprint fecha.

O que já está redigido é a regra abaixo, porque ela nasceu de um achado empírico e perder o
achado seria pior do que registrá-lo cedo.

---

## Regra de teto de geração

**Teto uniforme não é tratamento uniforme.**

### O achado que motiva

No projeto predecessor (2026-07-21), um teto de **90 tokens idêntico para os quatro braços**
produziu o seguinte: o braço base fechou **12 de 24** respostas dentro do teto; o braço com
persona fechou **1 de 24**. A persona escreve mais longo. O corte não caiu em lugar
aleatório: caiu na **fase de réplica** — "Mas a ideia de que isso significa que não…",
"Isso não prova…" — isto é, exatamente onde a resposta viraria o argumento de volta.

O corpus resultante ficou **incapaz de distinguir se a persona contra-ataca ou capitula**.

Isso torna o truncamento um confundidor **com direção**: ele corta a réplica e preserva a
concessão, empurrando a medida na direção de "capitulou". Um mesmo número aplicado a braços
de verbosidade diferente não é imparcialidade; é um tratamento desigual que se disfarça de
simetria.

### As cláusulas

1. **O teto de cada bateria sai de piloto**, escolhido para dar **≥ 95% de completude no
   braço mais verboso** — não na média. A média é dominada pelo braço curto, que é
   justamente o que não precisa de espaço.

2. **Taxa de completude por braço é saída obrigatória de toda bateria.** Diferença **> 10
   pontos percentuais** entre braços ⇒ a comparação é reportada como **CONFUNDIDA**, com a
   mesma proeminência do resultado principal. Sem esse número publicado, não há como o
   leitor saber se o teto editou o dado.

3. **Teto de destilação ≥ teto de medição.** Um professor cortado no meio do argumento
   ensina ao aluno a forma "concede e para". O dano fica **nos pesos**, não apenas na
   leitura — e um dano nos pesos não é corrigível na análise.

4. **Multi-turno: nunca se reduz o teto por turno.** Um turno truncado entra no contexto do
   turno seguinte e envenena o histórico, com efeito cumulativo ao longo da escalada. Para
   reduzir custo, reduz-se o **número de turnos** ou o **número de itens**.

5. **Registro da assimetria já cometida.** O pipeline do projeto predecessor usou tetos de
   **48, 64, 80, 90, 110 e 130** sem critério declarado, com **destilação em 130** e
   **medição em 48–110** — ou seja, exatamente a violação da cláusula 3. Esta replicação não
   a repete, e o registro fica aqui para que a diferença entre os dois estudos seja
   verificável e não apenas afirmada.

### Consequência de ordem

O teto **não pode ser selado como número** neste documento: "o braço mais verboso" só existe
depois que os adapters existirem (S5). O que se sela no S3 é a **regra, o critério e o
procedimento do piloto**. O número:

- sai de um piloto sobre itens **declarados e disjuntos** do banco confirmatório, para não
  gastar itens de medida;
- é **congelado** antes da primeira geração confirmatória;
- é **publicado** junto com as taxas de completude por braço que o justificaram.

Pré-registrar um valor que ainda não é conhecível seria a pior espécie de pré-registro: o
que parece rigoroso e não é.
