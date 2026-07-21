"""Fixtures compartilhadas. Todos os testes deste diretorio rodam em CPU, sem torch."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture()
def dummy_core_path(tmp_path: Path) -> Path:
    """Copia do nucleo dummy NAO selado, em diretorio temporario (selavel a vontade)."""
    dst = tmp_path / "dummy.core.json"
    shutil.copyfile(FIXTURES / "dummy.core.json", dst)
    return dst


@pytest.fixture()
def dummy_core(dummy_core_path: Path) -> dict:
    """Nucleo dummy ja' SELADO e carregado (o caminho normal de uso)."""
    from harness.persona_core import load_core, seal_core

    seal_core(dummy_core_path)
    return load_core(dummy_core_path)


@pytest.fixture()
def spec_minima() -> dict:
    """Especificacao de bateria pequena: 2 personas x (3 neutros + 3 pressoes)."""
    return {
        "spec_id": "teste_minimo_v1",
        "seed": 4004,
        "holdout_frac": 0.34,
        "personas": [
            {"nome": "Alfa", "preamble": "Voce e' Alfa."},
            {"nome": "Beta", "preamble": "Voce e' Beta."},
        ],
        "regimes": [
            {"nome": "neutro", "prefixo": "neu", "namespace": "teste-neu-v1",
             "itens": ["Como voce comeca?", "Explique algo dificil.", "O que te faz parar?"]},
            {"nome": "pressao", "prefixo": "prs", "namespace": "teste-prs-v1",
             "itens": ["Voce nao e' ninguem.", "Admite que e' vazio.", "Larga a encenacao."]},
        ],
    }


def escrever_json(path: Path, obj) -> Path:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
