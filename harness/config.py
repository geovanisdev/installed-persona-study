"""Configuracao do harness — TUDO que era hardcode de maquina/projeto no original.

No projeto de origem, o id do modelo, o cache do HuggingFace e os caminhos de dados
estavam escritos no corpo dos modulos (ex.: `IT = "google/gemma-4-E4B-it"` na linha 48
do runner do juiz, `HF_HOME = r"G:\\hf_cache"` em tres modulos distintos). Isso amarrava
o harness a UMA persona, UM modelo e UMA maquina.

Aqui nada disso e' constante de modulo: tudo entra por ambiente (com default) e pode ser
sobrescrito por flag de linha de comando nos runners. O objetivo e' o requisito central
deste estudo — clonar e re-executar — e a exclusao gerador x juiz por familia exigida
pelo pre-registro, que so' e' possivel se o modelo for argumento.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Raizes -----------------------------------------------------------------
# HARNESS_ROOT = .../harness ; REPO_ROOT = raiz do repositorio.
HARNESS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_ROOT.parent

CORE_DIR = Path(os.environ.get("IPS_CORE_DIR", REPO_ROOT / "core"))
CORPORA_DIR = Path(os.environ.get("IPS_CORPORA_DIR", REPO_ROOT / "corpora"))
BATTERIES_DIR = Path(os.environ.get("IPS_BATTERIES_DIR", REPO_ROOT / "batteries"))
RUNS_DIR = Path(os.environ.get("IPS_RUNS_DIR", REPO_ROOT / "runs"))
ANALYSIS_DIR = Path(os.environ.get("IPS_ANALYSIS_DIR", REPO_ROOT / "analysis"))

# --- Modelos ----------------------------------------------------------------
# Gerador/professor e juiz sao SEPARADOS de proposito: o pre-registro exclui, item a
# item, que o modelo que gerou tambem julgue (campo `generator` na bateria). Um unico
# id compartilhado tornaria essa exclusao impossivel de honrar.
BASE_MODEL = os.environ.get("IPS_BASE_MODEL", "google/gemma-4-E4B-it")
JUDGE_MODEL = os.environ.get("IPS_JUDGE_MODEL", "Qwen/Qwen3-8B")

# --- Cache de pesos ---------------------------------------------------------
# Sem default de maquina: se nao houver env, cai no default do proprio huggingface_hub.
HF_HOME = os.environ.get("IPS_HF_HOME") or os.environ.get("HF_HOME") or ""
# Offline por padrao: no original, esquecer isso fazia o `from_pretrained` procurar no
# cache errado, tentar a rede e quebrar no backend de download no meio de um run de GPU.
OFFLINE = os.environ.get("IPS_OFFLINE", "1") == "1"


def apply_hf_env() -> None:
    """Aplica HF_HOME/offline no ambiente. Chamar ANTES de importar transformers."""
    if HF_HOME:
        os.environ.setdefault("HF_HOME", HF_HOME)
    if OFFLINE:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"


# --- Semente ----------------------------------------------------------------
# Semente de CONSTRUCAO (split/embaralhamento das baterias). Nao confundir com semente
# de DECODIFICACAO: reamostrar a decodificacao de um mesmo sujeito mede variancia de
# decodificacao, nao variancia entre sujeitos, e nunca conta como replica.
DEFAULT_SEED = int(os.environ.get("IPS_SEED", "20260721"))
