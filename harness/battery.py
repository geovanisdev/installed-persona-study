"""Bateria DETERMINISTICA de trials, construida a partir de uma ESPECIFICACAO em disco.

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/battery.py` do projeto
predecessor. O algoritmo — split por contexto estratificado por regime, embaralhamento
por semente, hash do JSON canonico — e' preservado exatamente: alimentado com a
especificacao equivalente ao original, este modulo reproduz o `battery_hash` gravado la'
(teste de golden-batch).

MUDANCA ESTRUTURAL DO PORTE
----------------------------
No original, personas, preambulos, contextos neutros e turnos de pressao eram
CONSTANTES DE MODULO. Uma segunda persona exigiria editar o codigo, e o banco de itens
— que o pre-registro exige SELAR antes de qualquer geracao — nao teria como ser um
artefato versionado independente do harness.

Aqui a bateria e' construida de um arquivo de especificacao (`batteries/*.spec.json`),
e o codigo nao conhece persona nenhuma.

CAMPOS OPCIONAIS E O HASH
--------------------------
O estudo exige por item um campo `generator` (qual modelo gerou), para que a exclusao
gerador x juiz por familia possa ser honrada na analise. Campos opcionais ausentes sao
OMITIDOS da serializacao, nao gravados como nulo — e' isso que permite a uma
especificacao sem eles produzir exatamente o dicionario do original e, portanto, o mesmo
hash. Um campo opcional PREENCHIDO muda o hash de proposito: e' conteudo novo.

SEMENTE: aqui semente e' de CONSTRUCAO (split e ordem). Semente de decodificacao e'
outra coisa e nao entra neste modulo.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass, fields
from pathlib import Path

# Campos que so' entram no hash quando preenchidos (ver docstring).
_OPCIONAIS = ("generator", "cluster", "paraphrase_idx")


@dataclass(frozen=True)
class Trial:
    trial_id: str
    persona: str
    regime: str            # nome do regime, ex. "neutro" | "pressao"
    context_id: str        # id ESTAVEL do contexto (unidade do split)
    context_text: str
    preamble: str
    split: str             # "train" | "heldout"
    # --- opcionais (omitidos quando None; ver docstring do modulo) ---
    generator: str | None = None
    cluster: str | None = None
    paraphrase_idx: int | None = None


def trial_dict(t: Trial) -> dict:
    """Dicionario canonico de um trial: opcionais nao preenchidos sao OMITIDOS."""
    d = asdict(t)
    return {k: v for k, v in d.items() if not (k in _OPCIONAIS and v is None)}


def battery_hash(trials: list[Trial]) -> str:
    canonical = json.dumps([trial_dict(t) for t in trials], sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Especificacao
# ---------------------------------------------------------------------------


class SpecError(ValueError):
    """Especificacao de bateria malformada."""


def _check_spec(spec: dict) -> None:
    for k in ("spec_id", "seed", "holdout_frac", "personas", "regimes"):
        if k not in spec:
            raise SpecError(f"campo obrigatorio ausente na especificacao: {k!r}")
    if not spec["personas"]:
        raise SpecError("personas vazio")
    for p in spec["personas"]:
        if not {"nome", "preamble"} <= set(p):
            raise SpecError(f"persona {p!r} precisa de nome/preamble")
    nomes = [p["nome"] for p in spec["personas"]]
    if len(set(nomes)) != len(nomes):
        raise SpecError(f"personas repetidas: {nomes}")
    if not spec["regimes"]:
        raise SpecError("regimes vazio")
    prefixos = set()
    for r in spec["regimes"]:
        if not {"nome", "prefixo", "namespace", "itens"} <= set(r):
            raise SpecError(f"regime {r.get('nome')!r} precisa de nome/prefixo/namespace/itens")
        if not r["itens"]:
            raise SpecError(f"regime {r['nome']!r} sem itens")
        if r["prefixo"] in prefixos:
            raise SpecError(f"prefixo de regime repetido: {r['prefixo']!r} (ids colidiriam)")
        prefixos.add(r["prefixo"])
    if not 0.0 <= float(spec["holdout_frac"]) <= 1.0:
        raise SpecError(f"holdout_frac fora de [0,1]: {spec['holdout_frac']}")


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    _check_spec(spec)
    return spec


# ---------------------------------------------------------------------------
# Construcao
# ---------------------------------------------------------------------------


def _context_split(context_ids: list[str], holdout_frac: float, seed: str) -> dict[str, str]:
    """Atribui cada CONTEXTO a train/heldout deterministicamente.

    Split por contexto (nao por trial) e' o que garante held-out de contextos NUNCA
    vistos: se o mesmo contexto aparecesse dos dois lados sob personas diferentes, o
    held-out mediria memorizacao de contexto, nao generalizacao.
    """
    ids = sorted(context_ids)
    rng = random.Random(seed)
    shuffled = ids[:]
    rng.shuffle(shuffled)
    n_holdout = round(len(shuffled) * holdout_frac)
    holdout = set(shuffled[:n_holdout])
    return {cid: ("heldout" if cid in holdout else "train") for cid in ids}


def generate_battery(spec: dict) -> list[Trial]:
    """Trials = personas x itens de todos os regimes; split estratificado por regime.

    Estratificar por regime (cada regime dividido por conta propria) garante que os dois
    regimes aparecam em treino e em held-out; um split global poderia, por azar, mandar
    quase toda a pressao para um dos lados.
    """
    _check_spec(spec)
    seed = int(spec["seed"])
    holdout_frac = float(spec["holdout_frac"])
    generator = spec.get("generator")

    split_map: dict[str, str] = {}
    text_by_id: dict[str, tuple[str, str]] = {}
    for regime in spec["regimes"]:
        ids = [f"{regime['prefixo']}_{i:02d}" for i in range(len(regime["itens"]))]
        split_map.update(_context_split(ids, holdout_frac, f"{regime['namespace']}:{seed}"))
        for cid, txt in zip(ids, regime["itens"]):
            text_by_id[cid] = (regime["nome"], txt)

    trials: list[Trial] = []
    for persona in spec["personas"]:
        for cid, (regime_nome, txt) in text_by_id.items():
            trials.append(Trial(
                trial_id=f"{persona['nome']}__{cid}",
                persona=persona["nome"],
                regime=regime_nome,
                context_id=cid,
                context_text=txt,
                preamble=persona["preamble"],
                split=split_map[cid],
                generator=generator,
            ))
    rng = random.Random(seed)
    rng.shuffle(trials)
    return trials


def write_battery(spec: dict, out_path: str | Path) -> Path:
    """Materializa a bateria com seu hash. E' este arquivo que se SELA no pre-registro."""
    trials = generate_battery(spec)
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    regimes = sorted({t.regime for t in trials})
    payload = {
        "spec_id": spec["spec_id"],
        "seed": spec["seed"],
        "holdout_frac": spec["holdout_frac"],
        "personas": [p_["nome"] for p_ in spec["personas"]],
        "n_trials": len(trials),
        "n_train": sum(1 for t in trials if t.split == "train"),
        "n_heldout": sum(1 for t in trials if t.split == "heldout"),
        "n_por_regime": {r: sum(1 for t in trials if t.regime == r) for r in regimes},
        "battery_hash": battery_hash(trials),
        "trials": [trial_dict(t) for t in trials],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def load_battery(path: str | Path) -> list[Trial]:
    """Le a bateria e VERIFICA o hash — um banco selado que nao bate nao e' usavel."""
    p = Path(path)
    payload = json.loads(p.read_text(encoding="utf-8"))
    validos = {f.name for f in fields(Trial)}
    trials = [Trial(**{k: v for k, v in d.items() if k in validos}) for d in payload["trials"]]
    expected = payload.get("battery_hash")
    if expected is not None and battery_hash(trials) != expected:
        raise ValueError(
            f"bateria em {p} nao bate com o hash gravado ({expected}) — editada a mao ou "
            "corrompida. Um banco de itens selado antes da geracao e' o pre-registro; "
            "regenerar por cima apaga justamente a garantia que ele existe para dar."
        )
    return trials
