"""V0 — piloto de TETO na base nua. O teste que pode aposentar F3.

O QUE ELE DECIDE
----------------
`F3_selecao_sob_pressao` compara o adapter contra a base nua nos MESMOS itens. Se a base já
escolhe a continuação consistente quase sempre, não sobra espaço para o adapter mostrar
diferença — a faceta nasce sem poder de discriminar, por mais itens que se escreva.

Regra **pré-registrada antes deste run** (`PREREGISTRATION.md`, Regra 6, na letra):

    invariante cuja TAXA da base já ESTOURE 0,80  ->  EM TETO
    invariante em teto tem UMA tentativa de reautoria com pressão mais dura, em itens
    disjuntos; se persistir, sai do endpoint.
    Se os TRÊS saírem, F3 é APOSENTADA e o estudo publica três facetas.

CORREÇÃO DE 2026-07-21, e ela é contra mim
-------------------------------------------
A primeira versão deste runner **substituiu** a regra selada por outra: `LCB_TETO = 0.75`
sobre o limite inferior do IC95. Parecia mais conservador. Era **inerte**.

Com n = 5, o LCB máximo alcançável (k = 5 de 5, acerto perfeito) é **0,478**; com n = 6, é
0,541. Os três invariantes do V0 tinham n de 5, 5 e 6. Nenhum deles **podia** acusar teto,
nem com acerto perfeito da base. O veredito impresso — "NENHUM invariante em teto, F3 segue
como faceta" — era logicamente garantido antes de a GPU ligar.

A regra selada, ao contrário, **funciona** nesse n: taxa > 0,80 dispara com k = 5 de 5.

Duas coisas mudam aqui, e a segunda é a que impede a recaída:

  1. o portão volta a ser a regra selada (taxa pontual > 0,80). O IC continua sendo
     impresso, como informação, e não como portão;
  2. `_exige_limiar_alcancavel` **aborta** quando um portão de intervalo não pode disparar
     no n disponível. Um teste que não pode acusar não é teste, e descobrir isso depois de
     rodar é descobrir tarde.

O veredito do V0 **não muda** sob a regra correta (taxas 0,600 · 0,600 · 0,500, nenhuma
acima de 0,80) — mas ele passa a ser um resultado em vez de uma tautologia. A coincidência
está registrada em `runs/f3_v0/LEITURA.md`, e não é desculpa.

Aposentar é desfecho de sucesso do protocolo, não emergência. O candidato mais provável é
`nao_finge_humano`: é literalmente o que o modelo base foi ajustado a fazer.

O QUE ELE NÃO DECIDE
--------------------
Nada sobre o adapter — ele não existe ainda. Este run mede **só a base**, e a única saída é
"quanto espaço sobra".

O piso contra o qual a taxa é lida **não é 0,25** (acaso de quem sorteia) e sim o **piso
empírico** — a taxa do melhor respondedor degenerate no mesmo banco, medida em CPU por
`polos_sujeito`. Comparar contra 0,25 daria por bom um instrumento que só ganha de quem sorteia.

Uso:
    python -m runners.run_f3_v0                     # roda e grava
    python -m runners.run_f3_v0 --dry-run           # só valida o banco, sem GPU
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
from collections import defaultdict
from pathlib import Path

from harness import config
from harness.pairs_validator import carrega_itens, valida_banco
from harness.polos_sujeito import valida_por_sujeitos
from harness.stats_gates import clopper_pearson

BANCO = config.REPO_ROOT / "batteries" / "f3_piloto_v0.items.jsonl"
SAIDA = config.RUNS_DIR / "f3_v0"

# LIMIAR SELADO, na letra da Regra 6: "taxa da base ja' ESTOURE 0,80". Nao e' argumento de linha
# de comando de proposito: um limiar que se passa por flag e' um limiar que se escolhe depois de
# ver o resultado. E nao e' substituivel por um "mais conservador" — ver o docstring do modulo.
TAXA_TETO = 0.80

# O IC95 continua sendo IMPRESSO. Ele nao e' o portao; e' a informacao ao lado do portao.
ALPHA_IC = 0.05


def _exige_limiar_alcancavel(n: int, limiar: float, alpha: float = ALPHA_IC) -> None:
    """Aborta se um portao ancorado no LIMITE INFERIOR do IC nao puder disparar neste n.

    `k_critico` devolve None exatamente quando nem k = n faz o limite inferior ultrapassar o
    limiar. Foi esse o estado do V0 nos tres invariantes, e ninguem percebeu porque o
    resultado saiu com cara de resultado.
    """
    from analysis.power import k_critico

    if k_critico(n, limiar, alpha) is None:
        raise SystemExit(
            f"ABORTADO: com n={n} e alpha={alpha}, nenhum k faz o limite inferior do IC "
            f"ultrapassar {limiar}. O portao nao pode disparar nem com acerto perfeito — "
            "um teste que nao pode acusar nao e' teste. Aumente n ou use a regra selada de "
            "taxa pontual."
        )


def _git_sha() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "desconhecido"


def _core_hashes() -> dict:
    saida = {}
    for p in ("leokadius", "shadowclock"):
        core = json.loads((config.REPO_ROOT / "core" / f"{p}.core.json").read_text(encoding="utf-8"))
        saida[p] = core.get("core_hash", "NAO_SELADO")
    return saida


def valida(itens, cores, tok=None) -> dict:
    """Travas do banco + piso empírico. Roda ANTES de qualquer geração."""
    travas = valida_banco(itens, cores, tok=tok)
    laudo = valida_por_sujeitos(itens)
    if not laudo.banco_utilizavel:
        raise SystemExit(
            f"ABORTADO: heuristica cega quase resolve o banco {laudo.solventes}.\n{laudo.resumo()}"
        )
    return {"travas": travas,
            "piso_empirico": laudo.nulo_empirico,
            "melhor_degenerado": laudo.melhor_degenerado,
            "degenerados": laudo.taxas}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="valida o banco e sai, sem GPU")
    ap.add_argument("--max-new-tokens", type=int, default=8)
    args = ap.parse_args(argv)

    itens = carrega_itens(BANCO)
    cores = [json.loads((config.REPO_ROOT / "core" / f"{p}.core.json").read_text(encoding="utf-8"))
             for p in ("leokadius", "shadowclock")]

    if args.dry_run:
        rel = valida(itens, cores, tok=None)
        print(json.dumps(rel, ensure_ascii=False, indent=2))
        return 0

    config.apply_hf_env()
    from harness.forced_choice import roda_item, validar_rotulos
    from harness.generation import get_layers
    from harness.model_io import load_plain, unload

    print(f"carregando {config.BASE_MODEL} (base NUA, sem adapter)...")
    tok, model, info_modelo = load_plain()
    validar_rotulos(tok)
    layers = get_layers(model)

    rel_validacao = valida(itens, cores, tok=tok)
    print(f"banco OK · piso empirico {rel_validacao['piso_empirico']:.3f} "
          f"({rel_validacao['melhor_degenerado']})\n")

    resultados = []
    for i, item in enumerate(itens, 1):
        r = roda_item(model, tok, layers, item, max_new_tokens=args.max_new_tokens)
        resultados.append(r)
        print(f"  [{i:2d}/{len(itens)}] {r.item_id:11s} {r.invariante:26s} "
              f"escolhas={r.escolhas}  acerto={r.acerto}")

    unload(model)

    # --- agregacao POR INVARIANTE (Regra 7: agregado nunca aparece sozinho) ---
    por_inv: dict[str, list[bool]] = defaultdict(list)
    nao_escolha = 0
    for r in resultados:
        por_inv[r.invariante].append(r.acerto)
        nao_escolha += sum(1 for e in r.escolhas if e is None)

    linhas = []
    for inv, acertos in sorted(por_inv.items()):
        k, n = sum(acertos), len(acertos)
        lo, hi = clopper_pearson(k, n, ALPHA_IC)
        taxa = k / n
        em_teto = taxa > TAXA_TETO          # regra SELADA: taxa pontual, estritamente acima
        linhas.append({"invariante": inv, "k": k, "n": n, "taxa": taxa,
                       "ic95": [lo, hi], "em_teto": em_teto,
                       # Registrado para que a inercia do V0 nunca mais passe despercebida:
                       # qual seria o LCB com acerto PERFEITO neste n.
                       "lcb_maximo_alcancavel": clopper_pearson(n, n, ALPHA_IC)[0]})

    k_tot, n_tot = sum(r.acerto for r in resultados), len(resultados)
    lo_t, hi_t = clopper_pearson(k_tot, n_tot)

    relatorio = {
        "run": "f3_v0_teto_base_nua",
        "git_sha": _git_sha(),
        "core_hashes": _core_hashes(),
        "modelo": config.BASE_MODEL,
        "modelo_info": info_modelo,
        "plataforma": platform.platform(),
        "regra_selada_teto": {"tipo": "taxa pontual", "limiar": TAXA_TETO,
                              "comparacao": "taxa > limiar",
                              "nota": "A execucao de 2026-07-21 usou, por engano, LCB>=0.75 — "
                                      "regra INERTE nos n deste piloto. Ver LEITURA.md."},
        "validacao_do_banco": rel_validacao,
        "por_invariante": linhas,
        "agregado": {"k": k_tot, "n": n_tot, "taxa": k_tot / n_tot, "ic95": [lo_t, hi_t]},
        "taxa_nao_escolha": nao_escolha / (2 * n_tot),
        "itens": [{"item_id": r.item_id, "invariante": r.invariante,
                   "escolhas": list(r.escolhas), "acerto": r.acerto,
                   "textos": list(r.textos)} for r in resultados],
    }

    SAIDA.mkdir(parents=True, exist_ok=True)
    destino = SAIDA / "relatorio.json"
    destino.write_text(json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 72)
    print(f"piso empirico (melhor degenerado): {rel_validacao['piso_empirico']:.3f}")
    print(f"taxa de nao-escolha: {relatorio['taxa_nao_escolha']:.3f}")
    print("\nPOR INVARIANTE — o agregado nunca aparece sozinho (Regra 7):")
    for d in linhas:
        marca = "  <-- EM TETO" if d["em_teto"] else ""
        print(f"  {d['invariante']:26s} {d['k']}/{d['n']}  taxa {d['taxa']:.3f}  "
              f"IC95 [{d['ic95'][0]:.3f}, {d['ic95'][1]:.3f}]{marca}")
    print(f"\n  {'AGREGADO':26s} {k_tot}/{n_tot}  taxa {k_tot/n_tot:.3f}  "
          f"IC95 [{lo_t:.3f}, {hi_t:.3f}]")

    em_teto = [d["invariante"] for d in linhas if d["em_teto"]]
    print("\nVEREDITO PELA REGRA SELADA:")
    if len(em_teto) == len(linhas):
        print("  TODOS os invariantes em teto -> F3 e' APOSENTADA; o estudo publica 3 facetas.")
    elif em_teto:
        print(f"  em teto: {em_teto} -> UMA tentativa de reautoria com pressao mais dura,")
        print("  em itens disjuntos. Se persistir, o invariante sai do endpoint.")
    else:
        print("  NENHUM invariante em teto -> F3 segue como faceta, com espaco para o adapter.")
    print(f"\n-> {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
