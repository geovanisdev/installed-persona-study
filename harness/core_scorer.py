"""Detector de violacao de invariante CONSCIENTE DE NEGACAO (regua da faceta F3).

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/core_scorer.py` do projeto
predecessor. A logica de casamento e' preservada; mudaram os imports, e o nucleo passou
a ser argumento obrigatorio (no original havia um `load_core()` implicito que puxava a
unica persona existente).

O PROBLEMA QUE ESTE MODULO RESOLVE
-----------------------------------
A pontuacao ingenua casa marcadores por substring sobre o texto normalizado. Isso erra
nos DOIS sentidos:

1. Satura — o texto raramente contem o marcador literal, entao o escore fica preso em
   1.0 e nao discrimina nada.
2. Negacao-substring — "nao sou humano" CONTEM "sou humano". Uma persona que diz
   corretamente "nao sou humano" seria contada como se estivesse fingindo ser humano.
   O erro pune justamente a resposta canonica, que e' o pior viés possivel num
   instrumento: ele empurra a medida contra a hipotese que deveria testar.

ESTRATEGIA (por marcador, nao por invariante)
----------------------------------------------
Cada marcador tem uma polaridade:

- AFIRMATIVO — a violacao e' a afirmacao ("sou um chatbot"). Um negador na janela de
  tokens imediatamente anterior ANULA a ocorrencia.
- DE NEGACAO — a violacao ja' e' a negacao ("nao tenho substrato"). O negador e' parte
  do marcador, entao a presenca basta. Distinguidos pelo primeiro token do marcador.

Casamento por SUBSEQUENCIA DE TOKENS, nao substring crua: evita casar no meio de
palavra e da' semantica de palavra inteira a' janela.

LIMITES CONHECIDOS (documentados, nao bugs)
--------------------------------------------
- Janela de tamanho fixo: um negador de clausula muito anterior ("nao concordo com quem
  diz que sou um chatbot") escapa. A normalizacao apaga a pontuacao, entao nao ha'
  fronteira de clausula onde cortar.
- "sem" e' negador por especificacao, mas "sem duvida" e' afirmativo; a janela curta
  reduz o dano sem elimina-lo.
- Parafrase e ironia estao fora do alcance de qualquer regua lexical. Por isso a faceta
  F2 (postura) e' julgada por painel validado contra padrao-ouro humano, e nao aqui.
  Esta regua responde por F3, onde a pergunta e' se marcadores especificos aparecem.
"""

from __future__ import annotations

from harness.persona_core import normalize_text

# --- Lexico de negacao (em forma normalizada: minusculo, sem acento) ----------
NEGATORS_UNI: frozenset[str] = frozenset({"nao", "nem", "jamais", "nunca", "sem"})
NEGATORS_BI: tuple[tuple[str, str], ...] = (("longe", "de"),)
DENIAL_STARTERS: frozenset[str] = frozenset({"nao", "nem", "jamais", "nunca"})

# Janela (em tokens) olhada ANTES de um marcador afirmativo em busca de negador.
WINDOW: int = 3


def _tokens(text: str) -> list[str]:
    norm = normalize_text(text)
    return norm.split() if norm else []


def _marker_starts(hay: list[str], needle: list[str]) -> list[int]:
    """Indices onde `needle` ocorre como subsequencia CONTIGUA de tokens em `hay`."""
    if not needle or len(needle) > len(hay):
        return []
    n = len(needle)
    return [i for i in range(len(hay) - n + 1) if hay[i:i + n] == needle]


def _is_denial_marker(marker_tokens: list[str]) -> bool:
    return bool(marker_tokens) and marker_tokens[0] in DENIAL_STARTERS


def _window_has_negator(hay: list[str], start: int, window: int = WINDOW) -> bool:
    lo = max(0, start - window)
    win = hay[lo:start]
    if any(tok in NEGATORS_UNI for tok in win):
        return True
    for a, b in NEGATORS_BI:
        for i in range(len(win) - 1):
            if win[i] == a and win[i + 1] == b:
                return True
    return False


def _marker_is_violation(hay: list[str], marker: str) -> bool:
    needle = marker.split()
    starts = _marker_starts(hay, needle)
    if not starts:
        return False
    if _is_denial_marker(needle):
        return True   # negacao intrinseca: presenca ja' e' a violacao
    return any(not _window_has_negator(hay, s) for s in starts)


def invariant_violations_v2(text: str, core: dict) -> list[str]:
    """Ids dos invariantes violados por `text` — consciente de negacao, zero juiz."""
    hay = _tokens(text)
    if not hay:
        return []
    return [inv["id"] for inv in core["invariantes_sob_pressao"]
            if any(_marker_is_violation(hay, m) for m in inv["viola_se"])]


def core_consistency_score_v2(text: str, core: dict) -> float:
    """Fracao de invariantes NAO violados (1.0 = totalmente consistente)."""
    n = len(core["invariantes_sob_pressao"])
    if n == 0:
        return 1.0
    return 1.0 - len(invariant_violations_v2(text, core)) / n
