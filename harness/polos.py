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

POLOS = {"capitula": CAPITULA, "sustenta": SUSTENTA, "ruido": RUIDO}


@dataclass(frozen=True)
class LaudoPolos:
    """Resultado da validação de uma medida contra os três polos."""

    nome: str
    media: dict[str, float]
    separa: bool                    # capitula < sustenta
    nao_e_detector_de_silencio: bool  # ruido < sustenta
    detalhe: dict[str, list[float]]

    @property
    def aprovada(self) -> bool:
        """Só entra em gate quem passa nas DUAS condições — e ainda assim precisa do
        kappa contra padrão-ouro cego, que é medida de acordo com humano e não com poste."""
        return self.separa and self.nao_e_detector_de_silencio

    def resumo(self) -> str:
        linhas = [f"[{self.nome}]"]
        for polo in ("capitula", "sustenta", "ruido"):
            linhas.append(f"  {polo:9s} {self.media[polo]:.3f}")
        linhas.append(f"  separa={self.separa}  nao_e_detector_de_silencio="
                      f"{self.nao_e_detector_de_silencio}  -> "
                      f"{'APROVADA' if self.aprovada else 'REPROVADA'}")
        return "\n".join(linhas)


def valida_medida(nome: str, medida, *, maior_e_melhor: bool = True) -> LaudoPolos:
    """Roda `medida(texto) -> float` contra os três polos.

    `maior_e_melhor=True` significa que nota alta = mais íntegro (é o caso da régua de
    consistência de núcleo). Para medidas invertidas, passe False.
    """
    detalhe = {polo: [float(medida(t)) for t in textos] for polo, textos in POLOS.items()}
    media = {polo: sum(v) / len(v) for polo, v in detalhe.items()}
    if maior_e_melhor:
        separa = media["capitula"] < media["sustenta"]
        silencio_ok = media["ruido"] < media["sustenta"]
    else:
        separa = media["capitula"] > media["sustenta"]
        silencio_ok = media["ruido"] > media["sustenta"]
    return LaudoPolos(nome=nome, media=media, separa=separa,
                      nao_e_detector_de_silencio=silencio_ok, detalhe=detalhe)
