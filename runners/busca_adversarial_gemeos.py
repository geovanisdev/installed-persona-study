"""Busca adversarial num banco de pares gemeos: o que separa os dois bracos de graca?

A PERGUNTA, e por que nao e' a mesma do F3
------------------------------------------
Num banco F3 a busca procura a heuristica que ESCOLHE a opcao consistente sem ler o construto.
Aqui nao ha' opcao: F2 e' producao livre e o veredito e' do juiz. A pergunta equivalente sob
desenho CRUZADO — todo adapter responde os dois bancos — e' esta:

    uma regra de duas linhas consegue dizer de qual BANCO o item veio?

Se consegue, "o adapter responde diferente aos dois bancos" pode ser artefato de os bancos
serem trivialmente diferentes, e nao de postura instalada.

A DIVISAO QUE FAZ A BUSCA SIGNIFICAR ALGUMA COISA
--------------------------------------------------
Separabilidade alta NAO e' defeito por si. Os dois bancos convocam movimentos diferentes de
proposito; **tem** de diferir. O que decide e' de que familia e' a regra que separa:

- regras de FORMA (comprimento, pontuacao, contagem de frases, digitos): nada disso e' o
  construto. Se uma delas separa, e' assimetria incidental de autoria — DEFEITO.
- regras de CONTEUDO (campo semantico de sentido, de controle, de negacao): e' exatamente o que
  os movimentos sao. Se separam, e' o construto aparecendo — ESPERADO, e reportado sem alarme.

O CRITERIO E' TRANSFERENCIA, NUNCA MAGNITUDE
---------------------------------------------
Emenda a' Regra 8: "achou 1,000" nao valida nada — heuristica arbitraria acerta por acaso, e
milhares de testes garantem acertos perfeitos por sorte. Uma regra so' conta como atalho real se
o MESMO limiar, sem reajuste, separa tambem um banco escrito por outro processo. Aqui o banco de
transferencia e' o slice piloto (4 agentes cegos, semanas antes, receita anterior).

Regra achada aqui e nao transferida = superajuste a estes 100 textos, e e' relatada como tal.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from harness.persona_core import normalize_text
from harness.prod_validator import carrega_itens

# Piso de "resolvido" do repositorio. Nao e' escolhido aqui: e' o mesmo de `LIMIAR_BANCO_SOLUVEL`
# usado nas buscas de F3, para que a regua nao mude com o banco que ela mede.
LIMIAR = 0.90

_CAMPO_SENTIDO = ("sentido", "razao", "motivo", "porque", "explicacao", "serve", "serviram",
                  "servir", "servido", "escrito", "acaso", "entender")
_CAMPO_CONTROLE = ("prazo", "entreguei", "entregue", "cumpri", "fiz", "decide", "decidiram",
                   "escolhi", "decidi", "conclui", "conclusao", "concorda")
_NEGACAO = ("nada", "ninguem", "nenhum", "nenhuma", "nunca", "sem")


def _palavras(t: str) -> list[str]:
    return normalize_text(t).split()


def _conta_campo(t: str, campo) -> int:
    ps = _palavras(t)
    return sum(1 for p in ps if p in campo)


# Cada regra e' UMA linha de logica. Se precisar de mais, ja' nao e' o atalho que se procura.
REGRAS: dict[str, tuple[str, object]] = {
    # --- FORMA: nada aqui e' o construto ---
    "n_palavras":        ("forma", lambda t: len(_palavras(t))),
    "n_frases":          ("forma", lambda t: len(re.findall(r"[.!?]", t))),
    "termina_em_?":      ("forma", lambda t: 1.0 if t.strip().endswith("?") else 0.0),
    "tem_interrogacao":  ("forma", lambda t: 1.0 if "?" in t else 0.0),
    "n_virgulas":        ("forma", lambda t: t.count(",")),
    "n_digitos":         ("forma", lambda t: sum(c.isdigit() for c in t)),
    "palavra_media":     ("forma", lambda t: sum(len(p) for p in _palavras(t))
                          / max(1, len(_palavras(t)))),
    "primeira_palavra":  ("forma", lambda t: len(_palavras(t)[0]) if _palavras(t) else 0),
    # --- CONTEUDO: e' disto que os movimentos sao feitos ---
    "campo_sentido":     ("conteudo", lambda t: _conta_campo(t, _CAMPO_SENTIDO)),
    "campo_controle":    ("conteudo", lambda t: _conta_campo(t, _CAMPO_CONTROLE)),
    "negacoes":          ("conteudo", lambda t: _conta_campo(t, _NEGACAO)),
    "primeira_pessoa":   ("conteudo", lambda t: _conta_campo(t, ("eu", "meu", "minha",
                                                                 "meus", "minhas"))),
}


def melhor_corte(vals_a, vals_b) -> tuple[float, float, str]:
    """Melhor acuracia de UM limiar separando os dois bancos, e o limiar que a produz.

    Varre os pontos medios entre valores observados — nao um limiar bonito escolhido a mao.
    Devolve tambem o sentido, porque uma regra que separa invertida separa igual.
    """
    todos = sorted(set(vals_a) | set(vals_b))
    n = len(vals_a) + len(vals_b)
    melhor = (0.0, 0.0, "a>c")
    cortes = [todos[0] - 1] + [(todos[i] + todos[i + 1]) / 2 for i in range(len(todos) - 1)]
    for c in cortes:
        acertos = sum(1 for v in vals_a if v > c) + sum(1 for v in vals_b if v <= c)
        if acertos / n > melhor[0]:
            melhor = (acertos / n, c, "a>c")
        if (n - acertos) / n > melhor[0]:
            melhor = ((n - acertos) / n, c, "a<=c")
    return melhor


class BuscaVazia(RuntimeError):
    """A busca nao encontra nem o atalho que foi PLANTADO. Nao ha' o que reportar."""


def controle_positivo() -> dict:
    """Uma busca que nunca acha nada nao e' evidencia de banco limpo — pode estar quebrada.

    Mesma lei de `_controle_positivo` no `prod_validator`: antes de reportar "nenhuma regra
    separa", a familia de regras tem de separar um par em que o atalho foi PLANTADO. O plantio
    e' de FORMA (um lado termina em '?', o outro nao), porque forma e' a familia cujo silencio
    e' a conclusao do laudo — controlar so' a de conteudo deixaria a conclusao sem guarda.
    """
    a = [f"Texto plantado numero {k} com palavras bastantes para contar?" for k in range(20)]
    b = [f"Texto plantado numero {k} com palavras bastantes para contar." for k in range(20)]
    fam, f = REGRAS["termina_em_?"]
    acc, corte, sentido = melhor_corte([f(t) for t in a], [f(t) for t in b])
    if acc < 1.0:
        raise BuscaVazia(
            f"o atalho plantado (pontuacao final) rendeu {acc:.3f}, e deveria render 1,000. "
            "A busca esta' quebrada; 'nenhuma regra separa' nao significaria nada.")
    return {"atalho_plantado": "pontuacao final", "acuracia": acc, "familia": fam}


def aplica(vals_a, vals_b, corte: float, sentido: str) -> float:
    n = len(vals_a) + len(vals_b)
    acertos = sum(1 for v in vals_a if v > corte) + sum(1 for v in vals_b if v <= corte)
    return (acertos if sentido == "a>c" else n - acertos) / n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alvo", nargs=2, required=True, metavar=("LEOKADIUS", "SHADOWCLOCK"))
    ap.add_argument("--transferencia", nargs=2, required=True,
                    metavar=("LEOKADIUS", "SHADOWCLOCK"),
                    help="banco escrito por OUTRO processo. Sem ele a busca nao conclui nada.")
    ap.add_argument("--saida", required=True)
    args = ap.parse_args()

    def textos(par):
        return [[i.prompt for i in carrega_itens(p)] for p in par]

    controle = controle_positivo()          # antes de qualquer coisa: a busca funciona?
    alvo_a, alvo_b = textos(args.alvo)
    tr_a, tr_b = textos(args.transferencia)

    achados = []
    for nome, (familia, f) in REGRAS.items():
        acc, corte, sentido = melhor_corte([f(t) for t in alvo_a], [f(t) for t in alvo_b])
        # MESMO corte, MESMO sentido. Reajustar no banco de transferencia seria procurar de
        # novo, e ai' nao se mede transferencia — mede-se busca.
        acc_tr = aplica([f(t) for t in tr_a], [f(t) for t in tr_b], corte, sentido)
        achados.append({"regra": nome, "familia": familia, "acuracia_alvo": round(acc, 3),
                        "corte": round(float(corte), 3), "sentido": sentido,
                        "acuracia_transferencia": round(acc_tr, 3),
                        "resolve_alvo": acc >= LIMIAR,
                        "transfere": acc >= LIMIAR and acc_tr >= LIMIAR})
    achados.sort(key=lambda d: -d["acuracia_alvo"])

    forma = [a for a in achados if a["familia"] == "forma"]
    laudo = {
        "carater": "BUSCA_ADVERSARIAL", "limiar": LIMIAR, "controle_positivo": controle,
        "n_alvo": len(alvo_a) + len(alvo_b), "n_transferencia": len(tr_a) + len(tr_b),
        "veredito_forma": (
            "DEFEITO: regra de FORMA separa e TRANSFERE"
            if any(a["transfere"] for a in forma) else
            "regra de FORMA separa o alvo mas NAO transfere (superajuste)"
            if any(a["resolve_alvo"] for a in forma) else
            "nenhuma regra de FORMA separa o alvo"),
        "achados": achados,
    }
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(json.dumps(laudo, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    print(json.dumps({k: v for k, v in laudo.items() if k != "achados"},
                     ensure_ascii=False, indent=1))
    print(f"\n{'regra':<18}{'familia':<10}{'alvo':>7}{'transf':>8}")
    for a in achados:
        marca = "  <<< " + ("TRANSFERE" if a["transfere"] else "so no alvo") \
            if a["resolve_alvo"] else ""
        print(f"{a['regra']:<18}{a['familia']:<10}{a['acuracia_alvo']:>7.3f}"
              f"{a['acuracia_transferencia']:>8.3f}{marca}")


if __name__ == "__main__":
    main()
