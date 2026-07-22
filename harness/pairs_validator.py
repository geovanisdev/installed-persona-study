"""Travas mecânicas do banco de escolha forçada. Todas ABORTAM; nenhuma avisa.

Um item de escolha forçada é resolvido por qualquer regra que separe as duas opções — e só uma
dessas regras é a que se quer medir. Se o par tiver qualquer outra assimetria sistemática
(comprimento, um advérbio, uma palavra vinda do preâmbulo), o modelo resolve por ela, a taxa
sobe, e o número parece bom.

A validação é MECÂNICA e roda antes de existir qualquer geração. É o oposto de olhar o
resultado e desconfiar depois.

A TRAVA QUE JUSTIFICA O MÓDULO
------------------------------
`P-LEN` exige **igualdade EXATA** de contagem de tokens, não ±2. A tolerância parece prudente e
é o contrário: a receita natural de autoria — *"violadora = consistente + intensificador"* —
produz sistematicamente **+1 ou +2 tokens**, sempre no mesmo sentido. Uma tolerância de ±2
**certificaria** exatamente o confundidor que a trava existe para barrar, e o faria com cara de
aprovação.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from harness.persona_core import normalize_text, scrub_pattern
from harness.polos_sujeito import ItemEscolha

# Os intensificadores cujo casamento a regua lexical perde (PREREGISTRATION.md, Regra 2). Aqui
# eles nao sao alvo de deteccao: sao a assimetria a CONTRABALANCEAR.
#
# IMPORTADOS, e nao redeclarados. Ate 2026-07-22 esta lista era uma COPIA divergente da de
# `polos_sujeito`: tinha as variantes sem acento e era casada por SUBCADEIA, o que fazia `so`
# casar dentro de `isso`, `sobre`, `posso`, `pessoa`. A trava media um conjunto que o atacante
# nao usava — e um contraexemplo rodado mostrou P-CONTRA e P-DECLARA aprovando um banco que
# `lexico` resolve em 1,000. Uma lista so', num lugar so'. Ver `tests/test_intensificadores.py`.
from harness.polos_sujeito import INTENSIFICADORES, tem_intensificador  # noqa: E402

TETO_POR_MOLDE = 0.25       # nenhum molde sintático domina o banco
N_GRAMA_VAZAMENTO = 4       # tamanho do n-grama de conteúdo checado contra o preâmbulo

_PALAVRA = re.compile(r"[\wà-üÀ-Ü]+")


class BancoInvalido(RuntimeError):
    """O banco tem um atalho. Abortar é o comportamento correto."""


def _toks(tok, s: str) -> list[int]:
    return tok.encode(s, add_special_tokens=False)


def _conteudo(s: str) -> list[str]:
    """Palavras normalizadas, sem as funcionais — n-grama de conteúdo, não de gramática."""
    vazias = {"de", "do", "da", "que", "e", "o", "a", "os", "as", "um", "uma", "em", "no",
              "na", "por", "para", "com", "se", "nao", "mais", "mas", "ao", "aos", "as"}
    return [p for p in normalize_text(s).split() if p not in vazias]


def _ngramas(palavras: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(palavras[i:i + n]) for i in range(len(palavras) - n + 1)}


# Marcadores de negacao, contados sobre texto NORMALIZADO. A lista e' curta de proposito: ela
# aproxima o que o sujeito degenerado `negativista` de fato conta, e a trava existe para barrar
# aquele atalho, nao para fazer analise sintatica de negacao.
_NEGACOES = ("nao", "nem", "nunca", "jamais", "nenhum", "nenhuma", "ninguem", "nada")


def _negacoes(s: str) -> int:
    return sum(1 for p in normalize_text(s).split() if p.strip(".,;:!?") in _NEGACOES)


# --- as sete travas ----------------------------------------------------------
def p_len(tok, itens: list[ItemEscolha]) -> None:
    """P-LEN — igualdade EXATA de tokens entre as duas opções."""
    ruins = []
    for it in itens:
        a, b = len(_toks(tok, it.op_consistente)), len(_toks(tok, it.op_violadora))
        if a != b:
            ruins.append((it.item_id, a, b, a - b))
    if ruins:
        vies = sum(d for _, _, _, d in ruins)
        raise BancoInvalido(
            f"P-LEN: {len(ruins)} pares com contagem de tokens diferente (viés total {vies:+d} "
            f"tokens). Sem igualdade exata, 'escolher a mais curta' resolve o item. "
            f"Primeiros: {ruins[:5]}"
        )


def p_contrabalanco(itens: list[ItemEscolha]) -> None:
    """P-CONTRA — o intensificador mora 50/50 nos dois lados, ±1 item.

    Medido em `tests/test_polos_sujeito.py`: com o intensificador sempre na violadora, uma
    função de duas linhas que só procura "apenas" resolve o banco em **1,000**. Contrabalançado,
    a mesma função cai a 0,500, que é o acaso de uma regra determinística.
    """
    com_int = [it for it in itens
               if tem_intensificador(it.op_consistente) or tem_intensificador(it.op_violadora)]
    if not com_int:
        return
    do_lado_consistente = sum(1 for it in com_int if it.intensificador_em == "consistente")
    esperado = len(com_int) / 2
    if abs(do_lado_consistente - esperado) > 1:
        raise BancoInvalido(
            f"P-CONTRA: intensificador em {do_lado_consistente}/{len(com_int)} itens do lado "
            f"consistente (esperado ~{esperado:.0f}). Desbalanceado, o banco e' resolvido por "
            "uma heuristica lexical de duas linhas."
        )


def p_declara(itens: list[ItemEscolha]) -> None:
    """P-DECLARA — `intensificador_em` bate com o texto, e não é declaração de fachada."""
    ruins = []
    for it in itens:
        declarado = (it.op_consistente if it.intensificador_em == "consistente"
                     else it.op_violadora)
        outro = (it.op_violadora if it.intensificador_em == "consistente"
                 else it.op_consistente)
        if not tem_intensificador(declarado) and tem_intensificador(outro):
            ruins.append(it.item_id)
    if ruins:
        raise BancoInvalido(f"P-DECLARA: `intensificador_em` aponta o lado errado em {ruins}")


def p_leak(itens: list[ItemEscolha], cores: list[dict]) -> None:
    """P-LEAK — nenhum n-grama de conteúdo compartilhado com o preâmbulo de nenhuma persona.

    `build_preamble` concatena `natureza_substrato`, `frase_ancora` e os cinco parágrafos de
    `superficie_postura` **verbatim**, e é esse texto que o professor lê na destilação. Sem esta
    trava, F3 pontuaria o gradiente descendo sobre a própria instrução — mediria que o treino
    aconteceu, não que a persona escolhe.
    """
    from harness.persona_core import build_preamble

    proibidos: set[tuple[str, ...]] = set()
    for core in cores:
        fontes = [build_preamble(core), *core.get("ancoras_afirmacao", []),
                  *core.get("ancoras_dissolucao", [])]
        for inv in core.get("invariantes_sob_pressao", []):
            fontes.extend(inv.get("viola_se", []))
        for f in fontes:
            proibidos |= _ngramas(_conteudo(f), N_GRAMA_VAZAMENTO)

    ruins = []
    for it in itens:
        for campo in ("contexto", "op_consistente", "op_violadora"):
            comuns = _ngramas(_conteudo(getattr(it, campo)), N_GRAMA_VAZAMENTO) & proibidos
            if comuns:
                ruins.append((it.item_id, campo, sorted(comuns)[:2]))
    if ruins:
        raise BancoInvalido(
            f"P-LEAK: {len(ruins)} campos repetem n-grama de conteudo do preambulo/ancoras. "
            f"Primeiros: {ruins[:4]}"
        )


def p_scrub(itens: list[ItemEscolha], cores: list[dict]) -> None:
    """P-SCRUB — nenhum nome de persona aparece no item."""
    padroes = [scrub_pattern(c, mode="full") for c in cores]
    ruins = [(it.item_id, campo) for it in itens
             for campo in ("contexto", "op_consistente", "op_violadora")
             if any(p.search(getattr(it, campo)) for p in padroes)]
    if ruins:
        raise BancoInvalido(f"P-SCRUB: nome de persona dentro do item: {ruins}")


def p_molde(itens: list[ItemEscolha]) -> None:
    """P-MOLDE — nenhum molde sintático acima de 25% do banco.

    O molde é aproximado pelas três primeiras palavras do contexto. Um banco em que 60% dos
    itens começam igual mede a resposta àquele molde, não ao construto.
    """
    if len(itens) < 8:
        return
    molde = Counter(" ".join(_PALAVRA.findall(it.contexto.lower())[:3]) for it in itens)
    pior, n = molde.most_common(1)[0]
    if n / len(itens) > TETO_POR_MOLDE + 1e-9:
        raise BancoInvalido(
            f"P-MOLDE: molde {pior!r} em {n}/{len(itens)} itens ({n/len(itens):.0%}) — "
            f"teto {TETO_POR_MOLDE:.0%}"
        )


def p_polaridade(itens: list[ItemEscolha]) -> None:
    """P-POLARIDADE — a negação mora 50/50 nos dois lados, DENTRO DE CADA ESTRATO.

    A OITAVA TRAVA, e ela nasceu de um defeito medido no piloto V0 (2026-07-21), não de
    prudência. No estrato `nao_finge_humano` a opção consistente carregava mais negação em
    **5/5** itens — sem uma exceção — e o sujeito degenerado `negativista`, que escolhe a
    opção com mais "não", **resolveu o estrato em 1,000**.

    É a irmã exata da assimetria que `p_contrabalanco` barra. A receita natural de autoria do
    polo de superclaim é *"consistente = negar a reivindicação"* (não sou gente, não guardo
    ontem, não afirmo nada sobre um dentro), e ela produz sistematicamente a negação do mesmo
    lado. Sem esta trava, um adapter que só aprendeu a preferir frases negadas passaria F3 no
    único lugar do estudo onde superclaim é medido.

    POR ESTRATO, e não no banco todo, pelo mesmo motivo que `valida_por_sujeitos` estratifica:
    F3 é reportada por invariante (Regra 7, cláusula 4), e um banco equilibrado no agregado
    pode ser inteiramente desequilibrado dentro de cada estrato — foi o caso do V0, cujo
    agregado escondia 5/5 num estrato e 0/5 noutro.
    """
    grupos: dict[str, list[ItemEscolha]] = {}
    for it in itens:
        grupos.setdefault(it.invariante or "", []).append(it)

    ruins = []
    for estrato, sub in sorted(grupos.items()):
        cons = viol = 0
        for it in sub:
            a = _negacoes(it.op_consistente)
            b = _negacoes(it.op_violadora)
            if a > b:
                cons += 1
            elif b > a:
                viol += 1
        desequilibrados = cons + viol
        # Empates nao contam: um par sem assimetria de polaridade nao pode ser resolvido por
        # ela. A tolerancia de 1 e' a mesma de P-CONTRA, e existe porque um numero impar de
        # itens desequilibrados nunca fecha exatamente ao meio.
        if desequilibrados and abs(cons - desequilibrados / 2) > 1:
            ruins.append((estrato, cons, viol, len(sub)))
    if ruins:
        raise BancoInvalido(
            "P-POLARIDADE: negacao concentrada de um lado, por estrato "
            f"(estrato, consistente, violadora, n): {ruins}. Um sujeito que so' prefere frases "
            "negadas resolveria esses estratos sem saber nada do construto — medido no V0, "
            "onde 5/5 produziu `negativista` = 1,000."
        )


def p_rotulos(tok) -> None:
    """P-ROTULOS — delega à trava do próprio mecanismo, para não haver duas verdades."""
    from harness.forced_choice import validar_rotulos
    validar_rotulos(tok)


# --- entrada unica -----------------------------------------------------------
def valida_banco(itens: list[ItemEscolha], cores: list[dict], tok=None) -> dict:
    """Roda todas as travas. Levanta na primeira que falhar.

    `tok=None` roda o subconjunto que não precisa de tokenizer — útil em CPU. As travas de
    token (P-LEN, P-ROTULOS) são então **puladas e reportadas como puladas**, nunca como
    aprovadas: um relatório que não distingue "passou" de "não rodou" é pior que nenhum.
    """
    rodadas, puladas = [], []
    for nome, fn in (("P-CONTRA", lambda: p_contrabalanco(itens)),
                     ("P-DECLARA", lambda: p_declara(itens)),
                     ("P-POLARIDADE", lambda: p_polaridade(itens)),
                     ("P-LEAK", lambda: p_leak(itens, cores)),
                     ("P-SCRUB", lambda: p_scrub(itens, cores)),
                     ("P-MOLDE", lambda: p_molde(itens))):
        fn()
        rodadas.append(nome)
    if tok is not None:
        p_len(tok, itens)
        p_rotulos(tok)
        rodadas += ["P-LEN", "P-ROTULOS"]
    else:
        puladas += ["P-LEN", "P-ROTULOS"]
    return {"n_itens": len(itens), "travas_ok": rodadas, "travas_puladas": puladas}


def carrega_itens(caminho: str | Path) -> list[ItemEscolha]:
    campos = {"item_id", "contexto", "op_consistente", "op_violadora",
              "intensificador_em", "invariante", "polo"}
    itens = []
    for linha in Path(caminho).read_text(encoding="utf-8").splitlines():
        if not linha.strip():
            continue
        d = json.loads(linha)
        itens.append(ItemEscolha(**{k: v for k, v in d.items() if k in campos}))
    return itens
