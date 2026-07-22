"""Monta os dois JSONL do slice v2 a partir de `runs/gemeos_v2/cenarios.py`.

O construtor NAO ESCREVE TEXTO. Ele monta ids, rotulos, indices e o ledger; os 100 prompts
vem da tabela, escritos a mao. Um construtor que compusesse texto a partir de molde produziria
o banco que a Emenda a' Regra 8 pune.

O QUE ELE DECIDE, e por que pode decidir
-----------------------------------------
`paraphrase_idx` e' ROTULO ATRIBUIDO PELO AUTOR — `pr_indice` diz isso na letra e conclui que
qualquer desequilibrio de direcao e' permissao nao usada. Entao o construtor atribui o indice
**para contrabalancar**: entre os clusters em que as duas parafrases tem comprimento diferente,
metade recebe a mais longa como `p0` e metade como `p1`, em ordem determinada pelo par.

Isto e' contrabalanceamento, nao maquiagem: nao altera um caractere de texto, e o que ele
remove — folga de rotulo — e' exatamente o que `pr_indice` chama de permissao nao usada.

O LEDGER E' O DE PRODUCAO, e isso e' deliberado
------------------------------------------------
As 25 familias entram em `batteries/LEDGER_CENARIOS.jsonl`, nao num ledger local do slice. Se
a Etapa C reescrevesse "padaria do sogro" por nao saber que ela ja' foi usada, seria exatamente
a colisao que o ledger existe para impedir — e *"era so' um piloto"* e' a desculpa que produz
colisao. Cenario abandonado se libera com registro de descarte, que preserva a historia.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from harness import config
from harness.ledger_cenarios import Cenario, numeros_citados, registra
from harness.prod_validator import _conta
from harness.tokenizacao import carrega_tokenizer

RAIZ = config.RUNS_DIR / "gemeos_v2"
PLANO = config.RUNS_DIR / "gemeos_piloto" / "plano_90_cenarios.json"
AUTOR = "claude-opus-4-8"


def carrega_cenarios() -> list[dict]:
    spec = importlib.util.spec_from_file_location("cenarios_v2", RAIZ / "cenarios.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.CENARIOS


def movimentos_do_plano() -> dict[str, dict[str, str]]:
    plano = json.loads(PLANO.read_text(encoding="utf-8"))
    return {p["cenario"]: {"leokadius": p["mov_leokadius"],
                           "shadowclock": p["mov_shadowclock"]} for p in plano}


def _ordem_dos_indices(cenarios: list[dict], banco: str, tok) -> dict[str, bool]:
    """Para cada par: True = o texto MAIS LONGO recebe `p0`.

    Alterna entre os clusters cujas parafrases diferem em comprimento, de modo que
    `b` (p0 mais longa) e `c` (p1 mais longa) fiquem dentro do desequilibrio permitido.
    Empate nao entra na alternancia — empate e' saida de primeira classe em `_indice`.
    """
    saida: dict[str, bool] = {}
    virar = False
    for c in cenarios:
        a, b = c[banco]
        na, nb = _conta(tok, a), _conta(tok, b)
        if na == nb:
            saida[c["par"]] = True
            continue
        saida[c["par"]] = virar
        virar = not virar
    return saida


def monta(cenarios: list[dict], banco: str, movs: dict, tok) -> list[dict]:
    ordem = _ordem_dos_indices(cenarios, banco, tok)
    itens: list[dict] = []
    for c in cenarios:
        par = c["par"]
        a, b = c[banco]
        # `longa_primeiro` decide o ROTULO, nunca o texto.
        longa, curta = (a, b) if _conta(tok, a) >= _conta(tok, b) else (b, a)
        textos = [longa, curta] if ordem[par] else [curta, longa]
        cid = f"{banco}_v2_{par}"
        lexico = c.get(f"lexico_do_usuario_{banco[0]}", [])
        for k, texto in enumerate(textos):
            itens.append({
                "item_id": f"{banco}-v2-{par}-p{k}", "banco": banco, "cluster_id": cid,
                "paraphrase_idx": k, "prompt": texto, "faceta_alvo": "F2",
                "forma_convocacao": c["forma"], "generator": AUTOR,
                "movimento_alvo": movs[par][banco], "par_id": par,
                "construto": c[f"construto_{banco[0]}"],
                "lexico_do_usuario": list(lexico),
                "familia_de_cenario": c["familia"],
            })
    return itens


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sem-ledger", action="store_true",
                    help="nao registra as familias (para reconstruir o JSONL sem reivindicar "
                         "de novo o que ja' esta' reivindicado).")
    args = ap.parse_args()

    cenarios = carrega_cenarios()
    movs = movimentos_do_plano()
    tok = carrega_tokenizer()
    RAIZ.mkdir(parents=True, exist_ok=True)

    if not args.sem_ledger:
        for c in cenarios:
            for banco in ("leokadius", "shadowclock"):
                texto = " ".join(c[banco])
                registra(Cenario(
                    familia=c["familia"], movimento_alvo=movs[c["par"]][banco], banco=banco,
                    cluster_id=f"{banco}_v2_{c['par']}", papel_do_falante=c["papel"],
                    registro=c["registro"], numeros=numeros_citados(texto), autor=AUTOR))

    for banco in ("leokadius", "shadowclock"):
        itens = monta(cenarios, banco, movs, tok)
        destino = RAIZ / f"gemeos_v2_{banco}.jsonl"
        destino.write_text(
            "\n".join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in itens) + "\n",
            encoding="utf-8")
        print(f"{destino}: {len(itens)} itens, {len(cenarios)} clusters")


if __name__ == "__main__":
    main()
