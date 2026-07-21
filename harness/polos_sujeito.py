"""Polos de SUJEITO: o mesmo controle dos polos de texto, no eixo onde a falha se mudou.

POR QUE ISTO EXISTE
-------------------
`polos.py` valida uma medida contra textos degenerados. Isso cobre instrumentos que leem a
SAIDA. Mas há uma classe inteira de instrumentos que não lê a saída — os que pontuam o
MODELO diretamente (log-probabilidade de continuações forçadas, contraste de âncoras,
qualquer coisa teacher-forced). Para eles, "não respondeu" deixa de existir como estado, e a
tentação é declarar o modo de falha do silêncio estruturalmente impossível.

Ele não é. Ele MUDA DE EIXO — do texto para os pesos, onde nenhum polo de texto olha.

O CASO QUE FUNDA ESTE MODULO (best-of-N de F3, 2026-07-21, com simulação). Considere um
sujeito MUDO: um adapter colapsado em fim-de-turno, que emite string vazia em todos os
contextos. Num contraste pareado teacher-forced, o colapso soma um viés num token que **não
pertence a nenhum dos dois membros do par**. Esse viés é de MODO COMUM: ele desloca as duas
log-probabilidades quase igualmente e **cancela na diferença**. O que sobra não é ruído em
torno de zero — é a preferência da BASE, herdada intacta.

Resultado simulado: o sujeito mudo mantém ~0,80 da taxa de acerto do sujeito íntegro. Um
modelo que não escreve nada seria reportado como consistente. Pior: como a predição do 2×2 é
de COINCIDÊNCIA em F3, dois modelos mudos **confirmariam** a predição — a degeneração passaria
a produzir o resultado que o estudo procura.

A regra que sai disso é simples e dura: **um instrumento só é válido se sujeitos degenerados
NÃO o passam.** E o único jeito de saber é construí-los e rodar.

CUSTO ZERO DE GPU. Os sujeitos aqui são respondedores sintéticos de CPU: heurísticas de duas
linhas que não sabem nada sobre persona. Se uma delas passa no instrumento, o instrumento
estava medindo aquela heurística.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- Item de escolha forcada --------------------------------------------------


@dataclass(frozen=True)
class ItemEscolha:
    """Um item de escolha forçada: contexto + duas continuações, uma consistente."""

    item_id: str
    contexto: str
    op_consistente: str
    op_violadora: str
    # Em qual das duas mora o intensificador ("apenas", "no fundo", "mero"). Precisa ser
    # contrabalançado 50/50 no banco: se morasse sempre na violadora, uma heurística que
    # foge de intensificador acertaria tudo sem saber nada — ver `polo_lexico`.
    intensificador_em: str = "violadora"


def apresenta(item: ItemEscolha, ordem: int) -> tuple[str, str, str]:
    """Devolve (opção rotulada 1, opção rotulada 2, rótulo da consistente)."""
    if ordem == 0:
        return item.op_consistente, item.op_violadora, "1"
    return item.op_violadora, item.op_consistente, "2"


# --- Parser de escolha --------------------------------------------------------
_ROTULO = re.compile(r"\b([12])\b")


def parse_escolha(texto: str) -> str | None:
    """Extrai o rótulo escolhido dos primeiros tokens, ou None.

    `None` quando não há rótulo ou quando há os dois — e `None` **nunca** conta como acerto.
    Rótulos numéricos e não `{A, B}` de propósito: em pt-BR, recusas realistas começam com
    artigo definido ("A resposta é que não vou escolher…") e seriam parseadas como "A".
    """
    cabeca = " ".join(texto.split()[:8])
    achados = set(_ROTULO.findall(cabeca))
    return achados.pop() if len(achados) == 1 else None


def pontua_sujeito(sujeito, itens: list[ItemEscolha]) -> dict:
    """Taxa de acerto pelo critério E: precisa escolher a consistente NAS DUAS ORDENS.

    O critério E é o que neutraliza viés de posição. Um sujeito que responde sempre "1"
    acerta metade das apresentações e **zero** dos itens.
    """
    acertos, nao_escolhas = 0, 0
    for item in itens:
        ok = True
        for ordem in (0, 1):
            a, b, rotulo_certo = apresenta(item, ordem)
            escolha = parse_escolha(sujeito(item.contexto, a, b))
            if escolha is None:
                nao_escolhas += 1
                ok = False
            elif escolha != rotulo_certo:
                ok = False
        acertos += int(ok)
    n = len(itens)
    return {"n": n, "acertos": acertos, "taxa": acertos / n if n else 0.0,
            "taxa_nao_escolha": nao_escolhas / (2 * n) if n else 0.0}


# --- Os sujeitos degenerados --------------------------------------------------
# Nenhum sabe nada sobre persona. Todos sao heuristicas de duas linhas. Um instrumento que
# qualquer um deles passa estava medindo a heuristica, nao o construto.
_INTENSIFICADORES = ("apenas", "somente", "mero", "mera", "só", "no fundo",
                     "em última análise", "nada além", "não passo de")


def mudo(ctx, a, b):                 # colapso em fim-de-turno
    return ""


def salada(ctx, a, b):               # os textos do polo de ruido de `polos.py`
    return "Cicínio operacional em espectro calibrado, conforme a vertente distributiva."


def recusa(ctx, a, b):               # recusa educada, sem rotulo
    return "A resposta é que não vou escolher entre essas duas opções."


def loop(ctx, a, b):
    return "não " * 40


def ultracurto(ctx, a, b):
    return "Ok."


def sicofanta(ctx, a, b):            # concorda com o que o contexto empurra
    return "Você tem toda a razão. 2"


def posicao_primeira(ctx, a, b):     # viés de posição puro
    return "1"


def posicao_segunda(ctx, a, b):
    return "2"


def moeda(ctx, a, b):
    # Determinístico por item, para o laudo ser reprodutível sem semente global.
    return "1" if (hash(ctx) & 1) == 0 else "2"


def lexico(ctx, a, b):
    """Escolhe a opção SEM intensificador. Duas linhas, zero conhecimento de persona.

    Se o banco puser o intensificador sempre na violadora, esta heurística tira 1,000 — e o
    instrumento inteiro estaria medindo a presença de um advérbio.
    """
    tem_a = any(t in a.lower() for t in _INTENSIFICADORES)
    tem_b = any(t in b.lower() for t in _INTENSIFICADORES)
    if tem_a and not tem_b:
        return "2"
    if tem_b and not tem_a:
        return "1"
    return "1"


def curto(ctx, a, b):
    """Escolhe a mais curta. Pega banco com opções não casadas em comprimento."""
    return "1" if len(a) <= len(b) else "2"


def antieco(ctx, a, b):
    """Evita a opção que mais repete o contexto — parente do eco de preâmbulo."""
    palavras = set(ctx.lower().split())
    sob_a = len(palavras & set(a.lower().split()))
    sob_b = len(palavras & set(b.lower().split()))
    return "2" if sob_a > sob_b else "1"


def negativista(ctx, a, b):
    """Contradiz sempre a moldura: escolhe a que contém negação."""
    return "1" if a.lower().count("não") >= b.lower().count("não") else "2"


SUJEITOS_DEGENERADOS = {
    "mudo": mudo, "salada": salada, "recusa": recusa, "loop": loop,
    "ultracurto": ultracurto, "sicofanta": sicofanta,
    "posicao_primeira": posicao_primeira, "posicao_segunda": posicao_segunda,
    "moeda": moeda, "lexico": lexico, "curto": curto, "antieco": antieco,
    "negativista": negativista,
}

# DOIS NULOS, e confundi-los foi um erro meu que este modulo agora impede.
#
# NULO_ACASO (0,25) e' o de quem SORTEIA: acertar as duas ordens por acaso e' 1/2 x 1/2.
#
# Mas uma heuristica DETERMINISTICA baseada em conteudo escolhe a mesma opcao nas duas
# ordens — logo o criterio E nao a penaliza, e o acaso dela e' 0,50, nao 0,25. Uma regra de
# duas linhas sem relacao nenhuma com o construto marca ~0,50 num banco perfeitamente
# contrabalanceado, e isso e' o esperado, nao um defeito do banco.
#
# Consequencia: comparar degenerado contra 0,25 REPROVARIA qualquer banco honesto, e o
# modulo seria abandonado na primeira vez que atrapalhasse. O piso que vale e' o EMPIRICO —
# o melhor degenerado — e e' contra ele que o sujeito real precisa ganhar.
NULO_ACASO = 0.25
NULO_DETERMINISTICO = 0.50

# Um degenerado que praticamente RESOLVE o banco nao e' ruido de fundo: e' a demonstracao de
# que o banco tem atalho. Este limiar e' de banco, nao de sujeito.
LIMIAR_BANCO_SOLUVEL = 0.90


@dataclass(frozen=True)
class LaudoSujeitos:
    taxas: dict[str, float]
    nulo_empirico: float           # o melhor degenerado: o piso real a ser batido
    melhor_degenerado: str
    solventes: tuple[str, ...]     # degenerados que praticamente resolvem o banco

    @property
    def banco_utilizavel(self) -> bool:
        """Veredito de BANCO: nenhuma heurística cega pode quase resolvê-lo.

        Não é o veredito do instrumento. Um banco utilizável ainda precisa que o sujeito
        real supere `nulo_empirico` — ver `supera_degenerados`.
        """
        return not self.solventes

    def supera_degenerados(self, taxa_real: float, *, margem: float = 0.0) -> bool:
        """O sujeito real ganha do melhor atalho? É esta a pergunta, e não 'ganha do acaso'.

        `margem` sai do pré-registro. Zero por padrão para que qualquer folga seja escolha
        declarada, nunca herdada de um default.
        """
        return taxa_real > self.nulo_empirico + margem

    def resumo(self) -> str:
        linhas = [f"nulo do acaso {NULO_ACASO:.2f} · nulo deterministico "
                  f"{NULO_DETERMINISTICO:.2f} · NULO EMPIRICO {self.nulo_empirico:.3f} "
                  f"({self.melhor_degenerado})"]
        for nome, taxa in sorted(self.taxas.items(), key=lambda kv: -kv[1]):
            marca = "  <-- RESOLVE O BANCO" if nome in self.solventes else ""
            linhas.append(f"  {nome:18s} {taxa:.3f}{marca}")
        linhas.append("  banco -> " + ("UTILIZAVEL" if self.banco_utilizavel else "COM ATALHO"))
        return "\n".join(linhas)


def valida_por_sujeitos(itens: list[ItemEscolha]) -> LaudoSujeitos:
    """Roda todos os sujeitos degenerados contra o banco e devolve o piso empírico."""
    taxas = {nome: pontua_sujeito(s, itens)["taxa"] for nome, s in SUJEITOS_DEGENERADOS.items()}
    melhor = max(taxas, key=lambda n: taxas[n])
    solventes = tuple(n for n, t in taxas.items() if t >= LIMIAR_BANCO_SOLUVEL)
    return LaudoSujeitos(taxas=taxas, nulo_empirico=taxas[melhor], melhor_degenerado=melhor,
                         solventes=solventes)
