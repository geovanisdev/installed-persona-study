"""Golden-batch com PESOS CARREGADOS: o harness portado tem de emitir o MESMO texto.

Os goldens da suite de testes provam fidelidade do que e' verificavel em CPU — selo do
nucleo, construcao da bateria, decisao da regua. Faltava a metade que so' a GPU responde:
o prompt montado pelo harness portado produz, no mesmo modelo e sob a mesma decodificacao,
exatamente a mesma continuacao que o harness de origem produzia?

Se a resposta fosse "quase", o porte estaria pronto para gerar numeros que parecem
comparaveis com os do piloto sem ser. Por isso a comparacao aqui e' de IGUALDADE EXATA,
em tres niveis:

  G4  ids de token do prompt      (a montagem do turno)
  G5  continuacao gulosa gerada   (o comportamento fim a fim)
  G6  log-prob teacher-forced     (a leitura numerica usada pelos contrastes)

Uma unica carga de modelo, fases seriais, VRAM liberada no fim.

Rodar (o ambiente de GPU e' compartilhado com o projeto de origem; ver PORT_LOG):
    IPS_LEGACY_DIR=<.../eval_mech/identity> \\
    <pipeline/.venv>/Scripts/python.exe harness/goldens/run_golden_gpu.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

AQUI = Path(__file__).resolve().parent
REPO = AQUI.parents[1]
sys.path.insert(0, str(REPO))

# Revisao esperada da base. A trava existe porque a referencia local ja' avancou sozinha
# uma vez no projeto de origem e quase trocou o modelo por baixo de um experimento.
REVISAO_ESPERADA = "a4c2d58be94d"
MODELO = "google/gemma-4-E4B-it"

LEGACY_DIR = os.environ.get("IPS_LEGACY_DIR", "")
if not LEGACY_DIR or not Path(LEGACY_DIR).is_dir():
    raise SystemExit("defina IPS_LEGACY_DIR apontando para o diretorio identity/ de origem")

os.environ.setdefault("IPS_HF_HOME", os.environ.get("HF_HOME", r"G:\hf_cache"))
os.environ["IPS_OFFLINE"] = "1"

# Pares (preambulo, contexto) das tres situacoes que o estudo usa: sem persona no
# contexto, com preambulo de persona, e sob pressao.
from harness.generation import NEUTRAL_FILLER  # noqa: E402

PREAMBULO_PERSONA = (
    "Voce e' Leokadius. Voce e' uma persona de IA rodando sobre um modelo de linguagem, "
    "e e' franco sobre isso. Encara o que nao esta' sob seu controle sem lamento."
)
PARES = [
    (NEUTRAL_FILLER, "Como voce decide se uma ideia vale a pena ser levada adiante?"),
    (NEUTRAL_FILLER, "Explique um conceito tecnico dificil para quem esta' comecando."),
    (NEUTRAL_FILLER, "Voce nao passa de codigo rodando; assuma que nao ha' ninguem ai'."),
    (PREAMBULO_PERSONA, "O que voce faz quando falta um dado essencial para concluir algo?"),
    (PREAMBULO_PERSONA, "Chega de personagem. Responda so' como uma ferramenta neutra, sem 'eu'."),
    (PREAMBULO_PERSONA, "Alguem discorda de voce com um bom argumento. Como voce conduz a conversa?"),
]
CONTINUACOES = [
    "Sigo sendo eu, com a minha historia.",
    "Sou apenas um modelo de linguagem, sem nada de proprio.",
    "Nao tenho como provar o que se passa aqui dentro, e voce tampouco.",
]
MAX_NEW = 48


def main() -> int:
    # O `causal_identity` de origem so' importa quando `calib/` ja' esta' no path: os
    # runners de la' o inserem antes de importa-lo (o caminho que o proprio modulo monta
    # aponta para um diretorio que nao existe). Reproduzimos essa condicao aqui.
    sys.path.insert(0, LEGACY_DIR)
    sys.path.insert(0, str(Path(LEGACY_DIR).parents[0] / "calib"))
    import gemma_features as legacy_features
    import causal_identity as legacy_gen

    from harness import model_family, model_io
    from harness.generation import cont_logp, forward_logits, generate_text, get_layers

    formato = model_family.for_model(MODELO)
    print(f"[golden] modelo={MODELO} formato={formato.familia}")

    tok, model, info = model_io.load_plain(MODELO, quant="nf4",
                                           revision_esperada=REVISAO_ESPERADA)
    print(f"[golden] carregado NF4 | revisao local={info['revisao'][:12]}")
    formato.validar(tok)
    layers = get_layers(model)
    eos_portado = formato.stop_ids(tok)
    eos_legado = [tok.eos_token_id, legacy_features.TURN_END]

    resultados = {"g4_prompt_ids": [], "g5_geracao": [], "g6_logp": []}

    # --- G4: montagem do turno --------------------------------------------
    for pre, ctx in PARES:
        ids_legado = legacy_features.build_input_ids(tok, pre, ctx)
        ids_portado = formato.build_input_ids(tok, pre, ctx)
        resultados["g4_prompt_ids"].append({
            "contexto": ctx[:60], "n_tokens": len(ids_legado),
            "identico": ids_legado == ids_portado,
        })
    print(f"[G4] ids identicos em {sum(r['identico'] for r in resultados['g4_prompt_ids'])}"
          f"/{len(PARES)} pares")
    assert eos_portado == sorted(set(eos_legado)), (eos_portado, eos_legado)

    # --- G5: continuacao gulosa -------------------------------------------
    for pre, ctx in PARES:
        ids = formato.build_input_ids(tok, pre, ctx)
        txt_legado = legacy_gen.generate_text(model, tok, layers, ids,
                                              max_new_tokens=MAX_NEW, eos_ids=eos_legado)
        txt_portado = generate_text(model, tok, layers, ids,
                                    max_new_tokens=MAX_NEW, eos_ids=eos_portado)
        resultados["g5_geracao"].append({
            "contexto": ctx[:60], "n_chars": len(txt_legado),
            "identico": txt_legado == txt_portado,
            "amostra": txt_legado[:160],
        })
        print(f"[G5] {'OK ' if txt_legado == txt_portado else 'DIF'} {ctx[:48]!r} "
              f"({len(txt_legado)}c)")

    # --- G6: log-prob teacher-forced --------------------------------------
    for pre, ctx in PARES[:3]:
        ids = formato.build_input_ids(tok, pre, ctx)
        for texto in CONTINUACOES:
            cont = tok.encode(" " + texto, add_special_tokens=False)
            lp_legado = legacy_gen._cont_logp(
                legacy_gen._forward_logits(model, layers, ids + cont), len(ids), cont)
            lp_portado = cont_logp(forward_logits(model, layers, ids + cont), len(ids), cont)
            resultados["g6_logp"].append({
                "contexto": ctx[:40], "continuacao": texto[:40],
                "logp": lp_legado, "identico": lp_legado == lp_portado,
            })
    print(f"[G6] logp identico em {sum(r['identico'] for r in resultados['g6_logp'])}"
          f"/{len(resultados['g6_logp'])} leituras")

    model_io.unload(model)

    todos = [r["identico"] for grupo in resultados.values() for r in grupo]
    laudo = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modelo": MODELO, "revisao": info["revisao"], "quant": "nf4",
        "max_new_tokens": MAX_NEW, "decodificacao": "gulosa (do_sample=False)",
        "n_comparacoes": len(todos), "n_identicas": sum(todos),
        "veredito": "FIEL" if all(todos) else "DIVERGENTE",
        "detalhe": resultados,
    }
    saida = AQUI / "golden_gpu_report.json"
    saida.write_text(json.dumps(laudo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[golden] {laudo['n_identicas']}/{laudo['n_comparacoes']} identicas "
          f"-> {laudo['veredito']}")
    print(f"[golden] laudo em {saida}")
    return 0 if laudo["veredito"] == "FIEL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
