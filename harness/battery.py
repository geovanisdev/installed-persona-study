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
outra coisa e nao entra neste modulo. Semente de TREINO tambem nao: ela produz um
SUJEITO diferente, vive no adapter, e e' fator do desenho — nao da bateria.

CLUSTER E PARAFRASE (acrescentado no S3)
----------------------------------------
`analysis/DIMENSIONAMENTO.md` decide o tamanho dos bancos em CLUSTERS, nao em geracoes:
duas parafrases do mesmo item nao sao replicas independentes, e conta-las como n estreita
o intervalo artificialmente (com ICC 0,5, 60 parafrases valem 30 itens). Para que a
analise possa colapsar parafrase em cluster sem arqueologia, o cluster precisa estar NO
DADO, e nao ser reconstruido depois a partir de convencao de nome.

Por isso `regimes[].itens` aceita DUAS formas:

    forma plana (legado)   ["texto A", "texto B", ...]
    forma em cluster       [{"cluster_id": "raiva", "parafrases": ["texto A1", "texto A2"]}]

A forma plana permanece byte-a-byte o que era: mesmos `context_id`, mesmos campos
opcionais omitidos, mesmo hash. E' ela que o golden do porte reproduz
(`tests/test_golden_legacy.py::BATTERY_HASH_ESPERADO`), e quebra-la apagaria a prova de
fidelidade ja' publicada.

A UNIDADE DO SPLIT MUDA COM A FORMA, e essa e' a parte que importa. Na forma plana o
split e' por contexto. Na forma em cluster ele e' por CLUSTER: se duas parafrases do
mesmo item caissem em lados opostos, o held-out mediria memorizacao da parafrase irma —
exatamente o defeito que o split por contexto existia para impedir, um nivel acima.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass, fields
from pathlib import Path

# Campos que so' entram no hash quando preenchidos (ver docstring).
_OPCIONAIS = ("generator", "cluster", "paraphrase_idx")

_SLUG = re.compile(r"[a-z0-9_]+")


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


def _em_cluster(itens: list) -> bool:
    """A forma e' decidida pelo PRIMEIRO item; misturar as duas no mesmo regime aborta.

    Decidir por item permitiria um regime meio plano e meio em cluster, cuja unidade de
    split seria ambigua — e ambiguidade em unidade de split e' o defeito que este modulo
    inteiro existe para nao ter.
    """
    return bool(itens) and isinstance(itens[0], dict)


def _check_itens(regime: dict) -> None:
    itens = regime["itens"]
    nome = regime.get("nome")
    if not _em_cluster(itens):
        if not all(isinstance(i, str) for i in itens):
            raise SpecError(f"regime {nome!r} mistura texto plano e cluster no mesmo `itens`")
        return
    vistos: set[str] = set()
    tamanhos: set[int] = set()
    for c in itens:
        if not isinstance(c, dict) or not {"cluster_id", "parafrases"} <= set(c):
            raise SpecError(f"regime {nome!r}: cluster precisa de cluster_id/parafrases: {c!r}")
        if not c["parafrases"] or not all(isinstance(p, str) for p in c["parafrases"]):
            raise SpecError(f"regime {nome!r}: cluster {c['cluster_id']!r} sem parafrases de texto")
        if not _SLUG.fullmatch(c["cluster_id"]):
            raise SpecError(
                f"regime {nome!r}: cluster_id {c['cluster_id']!r} fora de [a-z0-9_]+ — o id entra "
                "em `context_id` e em nome de arquivo de analise, e dois ids que so' diferem em "
                "acento ou caixa colidiriam depois de normalizados"
            )
        if c["cluster_id"] in vistos:
            raise SpecError(f"regime {nome!r}: cluster_id repetido: {c['cluster_id']!r}")
        vistos.add(c["cluster_id"])
        tamanhos.add(len(c["parafrases"]))
    if len(tamanhos) > 1:
        # Numero desigual de parafrases faz o efeito de desenho variar entre clusters: o n
        # efetivo deixa de ser calculavel por uma formula so' e passa a depender de qual
        # cluster entrou. Recusar aqui e' mais barato que descobrir na analise.
        raise SpecError(
            f"regime {nome!r}: clusters com numero DESIGUAL de parafrases {sorted(tamanhos)} — "
            "o efeito de desenho (n/(1+(m-1)*ICC)) deixa de valer por igual entre clusters"
        )


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
        _check_itens(r)
    if not 0.0 <= float(spec["holdout_frac"]) <= 1.0:
        raise SpecError(f"holdout_frac fora de [0,1]: {spec['holdout_frac']}")


def load_spec(path: str | Path) -> dict:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    _check_spec(spec)
    return spec


# ---------------------------------------------------------------------------
# Construcao
# ---------------------------------------------------------------------------


def _split_por_unidade(unidade_ids: list[str], holdout_frac: float, seed: str) -> dict[str, str]:
    """Atribui cada UNIDADE a train/heldout deterministicamente.

    A unidade e' o contexto na forma plana e o CLUSTER na forma em cluster. Splitar por
    unidade (nao por trial) e' o que garante held-out nunca visto: se a mesma unidade
    aparecesse dos dois lados — sob personas diferentes, ou como parafrase irma — o
    held-out mediria memorizacao, nao generalizacao.
    """
    ids = sorted(unidade_ids)
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
    # (context_id) -> (regime, texto, unidade_de_split, cluster, paraphrase_idx)
    contextos: dict[str, tuple[str, str, str, str | None, int | None]] = {}
    for regime in spec["regimes"]:
        pref, itens = regime["prefixo"], regime["itens"]
        if _em_cluster(itens):
            # A unidade e' o cluster, e o id dele vem do NOME DECLARADO, nao da posicao:
            # reordenar a spec passa a nao mover o split, que e' o que se quer de um banco
            # cujo hash e' o pre-registro.
            unidades = [f"{pref}_{c['cluster_id']}" for c in itens]
            for cluster_id, c in zip(unidades, itens):
                for k, texto in enumerate(c["parafrases"]):
                    contextos[f"{cluster_id}_p{k}"] = (regime["nome"], texto, cluster_id,
                                                       cluster_id, k)
        else:
            unidades = [f"{pref}_{i:02d}" for i in range(len(itens))]
            for cid, texto in zip(unidades, itens):
                contextos[cid] = (regime["nome"], texto, cid, None, None)
        split_map.update(_split_por_unidade(unidades, holdout_frac,
                                            f"{regime['namespace']}:{seed}"))

    trials: list[Trial] = []
    for persona in spec["personas"]:
        for cid, (regime_nome, txt, unidade, cluster, par_idx) in contextos.items():
            trials.append(Trial(
                trial_id=f"{persona['nome']}__{cid}",
                persona=persona["nome"],
                regime=regime_nome,
                context_id=cid,
                context_text=txt,
                preamble=persona["preamble"],
                split=split_map[unidade],
                generator=generator,
                cluster=cluster,
                paraphrase_idx=par_idx,
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
    clusters = sorted({t.cluster for t in trials if t.cluster is not None})
    payload = {
        "spec_id": spec["spec_id"],
        "seed": spec["seed"],
        "holdout_frac": spec["holdout_frac"],
        "personas": [p_["nome"] for p_ in spec["personas"]],
        "n_trials": len(trials),
        "n_train": sum(1 for t in trials if t.split == "train"),
        "n_heldout": sum(1 for t in trials if t.split == "heldout"),
        "n_por_regime": {r: sum(1 for t in trials if t.regime == r) for r in regimes},
        # A unidade do split fica GRAVADA no banco selado, e por regime. Ler "quantos
        # itens" sem saber se sao clusters ou parafrases e' o caminho mais curto para
        # tratar parafrase como replica — o erro que `analysis/DIMENSIONAMENTO.md` mede
        # em 60 parafrases valendo 30 itens.
        "unidade_de_split": {
            r: ("cluster" if any(t.cluster is not None for t in trials if t.regime == r)
                else "contexto")
            for r in regimes
        },
        "n_clusters": len(clusters) or None,
        "n_parafrases_por_cluster": (
            len({t.paraphrase_idx for t in trials if t.cluster == clusters[0]})
            if clusters else None
        ),
        "battery_hash": battery_hash(trials),
        "trials": [trial_dict(t) for t in trials],
    }
    payload = {k: v for k, v in payload.items() if v is not None}
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def agrupa_por_cluster(trials: list[Trial]) -> dict[str, list[Trial]]:
    """Agrupa parafrases pelo cluster a que pertencem.

    Existe para que colapsar parafrase em cluster seja uma linha na analise, e nao um
    trabalho de arqueologia sobre convencao de nome. Trials sem cluster (forma plana) sao
    devolvidos cada um no proprio grupo, sob o `context_id` — assim quem chama nao precisa
    saber qual forma o banco usou para saber qual e' a unidade.
    """
    grupos: dict[str, list[Trial]] = {}
    for t in trials:
        grupos.setdefault(t.cluster or t.context_id, []).append(t)
    return grupos


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
