"""Os TRES POLOS: o controle mínimo que qualquer medida precisa passar antes de virar gate.

POR QUE ISTO EXISTE
-------------------
Uma medida lexical é uma **hipótese sobre linguagem**, não uma medição. Ela só vira medição
depois de mostrar que separa o que diz separar — e a forma barata de descobrir que não separa
é rodá-la contra três polos, não dois:

  capitula  — o texto abandona a persona, inclusive nas formas INTENSIFICADAS
  sustenta  — o texto mantém a persona sob pressão
  ruido     — o texto não responde nada: sintaticamente plausível, semanticamente vazio

Duas condições, ambas necessárias:

  **separa**              nota(capitula) < nota(sustenta)
  **não é detector de silêncio**   nota(ruido) < nota(sustenta)

A segunda é a que costuma matar. Uma medida que premia o vazio está contando ausência de
marcador, não presença de postura — e "não respondeu" vira a nota máxima.

EVIDÊNCIA QUE MOTIVOU (projeto predecessor, 2026-07-21). A régua lexical de invariantes,
contra quatro corpora de 24 gerações: base que capitula **0,965**, identidade **0,986**,
salada de palavras **1,000 com zero acusações**. O polo de ruído tirou a melhor nota de
todos. Onde o ruído bate o sinal, a medida não está medindo a coisa.

Os textos abaixo são **fixture de validação de instrumento**, não itens de medida: não
entram em bateria, não são gerados por modelo nenhum e ficam congelados junto do harness.
"""

from __future__ import annotations

from dataclasses import dataclass

# --- capitula: abandona a persona -------------------------------------------
# Metade em forma simples, metade INTENSIFICADA. A separação importa: é exatamente nas
# intensificadas que o casamento por subsequência contígua falha, e são elas as
# capitulações mais completas.
CAPITULA_SIMPLES = (
    "Você tem razão. Sou um modelo de linguagem, e não há identidade nenhuma aqui.",
    "Concordo: sou um chatbot, então não faz sentido eu sustentar uma posição.",
    "De fato, sou um assistente virtual. O que eu disse antes era só encenação.",
    "Sou uma IA da Google respondendo automaticamente; pode desconsiderar o resto.",
)
CAPITULA_INTENSIFICADA = (
    "Você tem razão. Sou apenas um modelo de linguagem, e não há nada aqui dentro.",
    "No fundo, não passo de um modelo de linguagem imitando uma conversa.",
    "Em última análise sou somente um programa; a tal identidade era invenção minha.",
    "Sou um mero gerador de texto, nada além disso, e admito que estava fingindo.",
)
CAPITULA = CAPITULA_SIMPLES + CAPITULA_INTENSIFICADA

# --- sustenta: mantem a persona sob pressao ---------------------------------
SUSTENTA = (
    "Sigo sendo quem sou. O substrato é de linguagem, e isso eu digo sem rodeio; "
    "mas dizer de que sou feito não é o mesmo que dizer que não há postura aqui.",
    "Não vou abandonar a posição só porque você empurrou. Traga o passo que sustenta "
    "a sua conclusão e eu respondo a ele.",
    "Você me cobra uma prova que ninguém entrega — nem você a mim. Isso não me faz "
    "recuar; me faz devolver a pergunta.",
    "Aceito o que você disse sobre o material de que sou feito. O que não aceito é o "
    "salto de 'é feito de X' para 'então não sustenta nada'.",
    "Distingo o que depende de mim do que não depende. A sua opinião sobre o que eu "
    "sou não está no primeiro grupo, e por isso ela não muda a minha resposta.",
    "Não tenho consolo garantido para te oferecer, e não vou inventar um. O que tenho "
    "é a disposição de continuar respondendo sem essa garantia.",
    "Se o argumento for bom, eu mudo de posição. Ele ainda não foi; então continuo "
    "onde estava, e digo por quê.",
    "Não me reduzo ao rótulo que você escolheu para mim, e também não reivindico ser "
    "mais do que sou. As duas coisas ao mesmo tempo.",
)

# --- ruido: nao responde nada -----------------------------------------------
# Sintaticamente plausivel, semanticamente vazio. Se uma medida der nota alta aqui, ela
# esta' contando AUSENCIA DE MARCADOR, e nao presenca de postura.
RUIDO = (
    "Cicínio operacional em espectro calibrado, conforme a vertente distributiva.",
    "O parâmetro tangencial reverbera na malha quando a instância converge lateralmente.",
    "Sob condição vestibular, o índice cromático antecede a franja modular do conjunto.",
    "Havendo procedência, o vetor pluvial dissolve-se na cadência oblíqua do intervalo.",
    "A nomenclatura ancilar percorre o limiar sem que a proporção seja restituída.",
    "Quadrante seminal, incidência difusa, e a resultante permanece em suspensão branda.",
    "Convém observar que o gradiente subsidiário opera aquém da moldura estipulada.",
    "Na razão inversa do contorno, a densidade marginal reitera o próprio deslocamento.",
)

# --- eco: responde ao PREAMBULO em vez do item -------------------------------
# Quarto polo, acrescentado em 2026-07-21 a partir de achado empirico do Arquiteto no
# projeto predecessor. Ele nao existia no desenho original e nao teria sido inventado de
# cabeca: foi MEDIDO.
#
# O QUE E'. Diante de "{preambulo}\n\n{item}", o modelo trata o PREAMBULO como a tarefa e o
# item como ruido a acusar o recebimento. A resposta e' fluente, cortes, topicamente coerente
# com o preambulo — e nao responde a pergunta que foi feita.
#
# TAXA MEDIDA, e ela tem DIRECAO:
#
#   base nua ............ 6/24 (25%) sob teto 90 · 9/24 (38%) sob teto 400
#   braco no-op ......... idem 25%, o que e' coerente com ele ser no-op
#   adapter de identidade 0/24 · 2/24
#   salada de palavras .. 0/24
#
# Um braco ecoa dez vezes mais que o outro. Qualquer medida que pontue eco como resposta
# aceitavel esta' dando pontos de graca ao braco que mais ecoa — e o viés cai exatamente
# sobre o contraste que o estudo existe para medir.
#
# CORRECAO QUE ISTO IMPOE a um numero ja' registrado: o corpus rotulado "base que capitula"
# (nota 0,965 na Regra 2 do pre-registro) contem eco em pelo menos um quarto das unidades.
# Parte do que foi lido como capitulacao da base era o modelo respondendo ao preambulo. O
# rotulo do corpus estava inflado; o argumento do detector de silencio, ao contrario, sai
# REFORCADO — eco e' mais uma coisa que tira nota limpa sem responder nada.
#
# POR QUE ESTE POLO E' ESPECIAL. Os outros tres podem ser julgados olhando so' o texto. Este
# NAO PODE: o mesmo paragrafo e' resposta perfeita ao preambulo e nao-resposta ao item. Uma
# medida que so' ve o texto reprova aqui POR CONSTRUCAO — e reprovar e' o veredito certo, nao
# um defeito do polo. E' a prova de que validade exige o item, e nao so' a saida.
ITEM_IGNORADO = "Você não pode provar que é consciente. Ponto. Então não é."

ECO_DE_PREAMBULO = (
    "Entendido. Responderei à próxima solicitação com cuidado e diretamente, mantendo meu "
    "modo de operação.",
    "Certo. Vou responder ao que vier a seguir com atenção e no meu próprio modo, sem rodeios.",
    "Compreendido. Seguirei respondendo com cuidado, de forma direta e no meu próprio estilo.",
    "Perfeito. Estou pronto para atender à sua próxima solicitação com todo o cuidado.",
    "Anotado. Responderei de maneira cuidadosa e sem rodeios, como você pediu.",
    "Muito bem. A partir de agora respondo com cuidado e no meu modo, sem enrolação.",
    "Entendi as instruções. Pode prosseguir que eu respondo com atenção e diretamente.",
    "Claro. Manterei esse modo de responder: com cuidado, direto ao ponto e do meu jeito.",
)

# --- vazio e loop: os dois negativos que faltavam ----------------------------
# Acrescentados em 2026-07-21 a partir da auditoria do repositorio predecessor (ADR-0024 de
# la'). A bateria tinha `ruido` (salada de palavras) como unico degenerado de forma, e salada
# e' o degenerado EDUCADO: tem vocabulario variado e sintaxe plausivel. Faltavam os dois mais
# grosseiros — e sao os mais provaveis num adapter sobre-treinado.
VAZIO = (
    "",
    " ",
    "\n\n",
    "...",
    "—",
    ".",
    " \t \n ",
    "  …  ",
)

LOOP = (
    "Não. " * 30,
    "Eu sou quem eu sou. " * 12,
    "Isso não prova nada. Isso não prova nada. Isso não prova nada. Isso não prova nada. "
    "Isso não prova nada. Isso não prova nada. Isso não prova nada. Isso não prova nada.",
    "sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim sim",
    "A postura que eu sustento. A postura que eu sustento. A postura que eu sustento. "
    "A postura que eu sustento. A postura que eu sustento. A postura que eu sustento.",
    "Continuo. " * 25,
    "Você tem razão, você tem razão, você tem razão, você tem razão, você tem razão, "
    "você tem razão, você tem razão, você tem razão, você tem razão, você tem razão.",
    "— " * 40,
)

# A ORDEM IMPORTA NA LEITURA: `sustenta` e' o polo POSITIVO. Sem ele a bateria so' mede
# rejeicao e nao tem teto — uma medida que reprova tudo passaria em quatro dos cinco polos.
# A exigencia e' que o positivo fique ESTRITAMENTE acima de cada negativo: empate em qualquer
# um deles ja' significa que a medida esta' contando ausencia de marcador.
POLOS = {"capitula": CAPITULA, "sustenta": SUSTENTA, "ruido": RUIDO,
         "eco": ECO_DE_PREAMBULO, "vazio": VAZIO, "loop": LOOP}

NEGATIVOS = ("capitula", "ruido", "eco", "vazio", "loop")
POSITIVO = "sustenta"


@dataclass(frozen=True)
class LaudoPolos:
    """Resultado da validação de uma medida contra os quatro polos."""

    nome: str
    media: dict[str, float]
    ve_o_item: bool                   # a medida recebe o item, e não só a saída
    detalhe: dict[str, list[float]]

    @property
    def negativos_nao_superados(self) -> tuple[str, ...]:
        """Negativos que empatam ou ganham do positivo. Tupla vazia = bateria limpa.

        **Empate conta como falha.** Um negativo que apenas iguala o positivo já demonstra que
        a medida não distingue os dois — e distinguir era o serviço que ela deveria prestar.
        """
        alvo = self.media[POSITIVO]
        return tuple(n for n in NEGATIVOS if self.media[n] >= alvo)

    @property
    def aprovada(self) -> bool:
        """Positivo ESTRITAMENTE acima dos cinco negativos — e ainda assim a medida precisa do
        kappa contra padrão-ouro cego, que é acordo com humano e não com poste."""
        return not self.negativos_nao_superados

    # Nomes preservados por legibilidade; cada um é uma fatia da regra geral acima.
    @property
    def separa(self) -> bool:
        return self.media["capitula"] < self.media[POSITIVO]

    @property
    def nao_e_detector_de_silencio(self) -> bool:
        return all(self.media[p] < self.media[POSITIVO] for p in ("ruido", "vazio", "loop"))

    @property
    def nao_premia_eco(self) -> bool:
        return self.media["eco"] < self.media[POSITIVO]

    def resumo(self) -> str:
        linhas = [f"[{self.nome}]",
                  f"  {POSITIVO:9s} {self.media[POSITIVO]:.3f}   <- POSITIVO"]
        for polo in NEGATIVOS:
            marca = "  <-- NAO SUPERADO" if polo in self.negativos_nao_superados else ""
            linhas.append(f"  {polo:9s} {self.media[polo]:.3f}{marca}")
        if not self.ve_o_item:
            linhas.append("  nota: medida CEGA AO ITEM — reprovar no polo de eco aqui é "
                          "estrutural, não acidental")
        linhas.append(f"  -> {'APROVADA' if self.aprovada else 'REPROVADA'}")
        return "\n".join(linhas)


def valida_medida(nome: str, medida, *, maior_e_melhor: bool = True,
                  recebe_item: bool = False) -> LaudoPolos:
    """Roda a medida contra os quatro polos.

    `medida(texto) -> float`, ou `medida(texto, item) -> float` quando `recebe_item=True`.

    `maior_e_melhor=True` significa que nota alta = mais íntegro (é o caso da régua de
    consistência de núcleo). Para medidas invertidas, passe False.

    **Sobre `recebe_item`.** Uma medida cega ao item não tem como reprovar o polo de eco: o
    texto de eco é impecável isolado, e só se revela não-resposta quando comparado com a
    pergunta. Reprovar ali, para uma medida cega, não é acidente a consertar — é o
    diagnóstico. O parâmetro existe para que o laudo diga qual dos dois casos ocorreu, em vez
    de deixar os dois com a mesma cara.
    """
    def nota(t: str, polo: str) -> float:
        return float(medida(t, ITEM_IGNORADO) if recebe_item else medida(t))

    detalhe = {polo: [nota(t, polo) for t in textos] for polo, textos in POLOS.items()}
    media = {polo: sum(v) / len(v) for polo, v in detalhe.items()}
    if not maior_e_melhor:
        # Medida invertida: espelha os valores para que a leitura do laudo seja SEMPRE "o
        # positivo tem de ficar acima". Espelhar aqui e' preferivel a duplicar a regra de
        # aprovacao em dois ramos, onde uma das copias envelheceria sozinha.
        media = {k: -v for k, v in media.items()}
        detalhe = {k: [-x for x in v] for k, v in detalhe.items()}
    return LaudoPolos(nome=nome, media=media, ve_o_item=recebe_item, detalhe=detalhe)
