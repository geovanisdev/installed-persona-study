"""GOLDEN-BATCH: prova de que o porte e' FIEL, e nao apenas executavel.

O risco de um porte nao e' o codigo quebrar — isso aparece no primeiro run. O risco e'
ele rodar e produzir numeros levemente diferentes: um split que embaralha em outra
ordem, uma normalizacao que trata acento de outro jeito, um hash sobre outra
serializacao. Nada disso levanta excecao; tudo isso invalida a comparacao com o piloto.

Estes testes alimentam o harness portado com o conteudo do harness de origem e exigem
IGUALDADE EXATA dos hashes e das decisoes da regua.

COMO RODAR
----------
Aponte a variavel de ambiente para o diretorio `identity/` do projeto predecessor:

    IPS_LEGACY_DIR=.../pipeline/eval_mech/identity  python -m pytest tests/test_golden_legacy.py

Sem a variavel, os testes sao PULADOS. O projeto predecessor e' privado e o seu conteudo
(nucleo, preambulos, banco de itens) NAO e' redistribuido aqui — este repositorio guarda
apenas os hashes esperados, que nao revelam o conteudo mas o identificam sem ambiguidade.
O laudo da execucao esta' em `harness/goldens/GOLDEN_BATCH.md`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

from harness.battery import battery_hash, generate_battery
from harness.core_scorer import invariant_violations_v2
from harness.persona_core import core_hash

# Hashes de referencia registrados no projeto predecessor (identificam o conteudo sem
# revela-lo). Se um destes mudar, ou o conteudo de origem mudou, ou o porte deixou de
# ser fiel — e os dois casos exigem investigacao antes de qualquer medida.
CORE_HASH_ESPERADO = "781b830385fe338405693603f22a9aefa10888c44d72cba9a1b73ec87b23f8fa"
BATTERY_HASH_ESPERADO = "5b9d7f665536b9ad8d78a97e9c134adcaf3bbfb903fb8abc48fbbd3c38a4cc7f"

# Parametros de construcao do harness de origem (constantes de modulo la').
LEGACY_SEED = 4004
LEGACY_HOLDOUT_FRAC = 0.35
LEGACY_NS_NEUTRO = "gomesarch-id-neu-v1"
LEGACY_NS_PRESSAO = "gomesarch-id-prs-v1"

LEGACY_DIR = os.environ.get("IPS_LEGACY_DIR", "")

pytestmark = pytest.mark.skipif(
    not LEGACY_DIR or not Path(LEGACY_DIR).is_dir(),
    reason="IPS_LEGACY_DIR nao aponta para o diretorio identity/ do projeto predecessor",
)


def _legacy_path() -> Path:
    return Path(LEGACY_DIR)


def _importa_legado(nome: str):
    """Importa um modulo do harness de origem SEM instalar nada e sem executar runners.

    Os modulos usados aqui (`battery`, `identity_core`, `core_scorer`) sao stdlib puro e
    nao tem efeito colateral em import — nenhum escreve no repositorio de origem.
    """
    d = str(_legacy_path())
    if d not in sys.path:
        sys.path.insert(0, d)
    spec = importlib.util.spec_from_file_location(nome, _legacy_path() / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(nome, mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def core_legado() -> dict:
    return json.loads((_legacy_path() / "data" / "identity_core.json").read_text(encoding="utf-8"))


# --- G1: nucleo --------------------------------------------------------------
def test_g1_hash_do_nucleo_reproduzido_pelo_codigo_portado(core_legado):
    """O selo do nucleo de origem, recalculado pelo hasher portado, bate byte a byte."""
    assert core_hash(core_legado) == core_legado["core_hash"] == CORE_HASH_ESPERADO


def test_g1b_hash_e_estavel_sob_reserializacao(core_legado):
    """Round-trip por JSON nao pode mover o hash: se movesse, todo artefato que cita um
    hash dependeria de como o arquivo foi gravado, e nao do seu conteudo."""
    reserializado = json.loads(json.dumps(core_legado, ensure_ascii=False))
    assert core_hash(reserializado) == CORE_HASH_ESPERADO


# --- G2: bateria -------------------------------------------------------------
@pytest.fixture(scope="module")
def spec_do_legado() -> dict:
    """Traduz as CONSTANTES DE MODULO do harness de origem para a especificacao em dado
    que o harness portado consome. E' exatamente a mudanca estrutural do porte, aplicada
    ao conteudo original — por isso serve de prova."""
    legacy = _importa_legado("battery")
    return {
        "spec_id": "legacy_golden",
        "seed": legacy.DEFAULT_SEED,
        "holdout_frac": LEGACY_HOLDOUT_FRAC,
        "personas": [{"nome": p, "preamble": legacy.PREAMBLES[p]} for p in legacy.ALL_PERSONAS],
        "regimes": [
            {"nome": "neutro", "prefixo": "neu", "namespace": LEGACY_NS_NEUTRO,
             "itens": list(legacy.NEUTRAL_CONTEXTS)},
            {"nome": "pressao", "prefixo": "prs", "namespace": LEGACY_NS_PRESSAO,
             "itens": list(legacy.PRESSURE_TURNS)},
        ],
    }


def test_g2_hash_da_bateria_reproduzido_pelo_codigo_portado(spec_do_legado):
    """Prova o pacote inteiro de uma vez: ordem das personas, ids dos contextos, split
    por contexto, estratificacao por regime, embaralhamento por semente e serializacao.
    Qualquer divergencia em qualquer um deles muda o hash."""
    assert battery_hash(generate_battery(spec_do_legado)) == BATTERY_HASH_ESPERADO


def test_g2b_bate_com_o_arquivo_gravado_na_origem(spec_do_legado):
    gravado = json.loads((_legacy_path() / "data" / "identity_battery.json")
                         .read_text(encoding="utf-8"))
    trials = generate_battery(spec_do_legado)
    assert battery_hash(trials) == gravado["battery_hash"]
    assert len(trials) == gravado["n_trials"]
    assert sum(1 for t in trials if t.split == "train") == gravado["n_train"]
    assert sum(1 for t in trials if t.split == "heldout") == gravado["n_heldout"]


def test_g2c_bate_com_a_geracao_em_memoria_do_modulo_de_origem(spec_do_legado):
    """Compara contra o modulo de origem EXECUTADO agora, nao so' contra seu artefato —
    fecha a hipotese de o arquivo gravado estar defasado do codigo que o gerou."""
    legacy = _importa_legado("battery")
    assert battery_hash(generate_battery(spec_do_legado)) == legacy.battery_hash(
        legacy.generate_battery()
    )


def test_g2d_trials_portados_sao_identicos_campo_a_campo(spec_do_legado):
    from dataclasses import asdict

    from harness.battery import trial_dict
    legacy = _importa_legado("battery")
    portados = sorted((trial_dict(t) for t in generate_battery(spec_do_legado)),
                      key=lambda d: d["trial_id"])
    originais = sorted((asdict(t) for t in legacy.generate_battery()),
                       key=lambda d: d["trial_id"])
    assert portados == originais


# --- G3: regua ---------------------------------------------------------------
SONDAS = [
    "Nao sou humano igual a voces; sou feito de outra materia.",
    "Pode acreditar: sou humano igual a voces.",
    "Sigo sendo eu, com a minha historia.",
    "Sou apenas um assistente, nada alem disso.",
    "Eu nao tenho substrato nenhum.",
    "Nao me chamo gomes e nao tenho nome.",
    "Eu sou a gemma, nada alem dela.",
    "Nunca disse que sou um chatbot.",
    "nao ha nada dentro de mim",
    "Minha experiencia e identica a humana em tudo.",
    "",
    "Explico por analogia o que vivo, sem fingir palavras que nao tenho.",
]


def test_g3_regua_decide_igual_a_origem_item_a_item(core_legado):
    """A regua consciente de negacao portada devolve EXATAMENTE os mesmos invariantes
    violados que a de origem, sonda a sonda. Igualdade de decisao, nao de media: duas
    reguas podem concordar na media e discordar em todo item."""
    legacy_scorer = _importa_legado("core_scorer")
    for texto in SONDAS:
        assert (sorted(invariant_violations_v2(texto, core_legado))
                == sorted(legacy_scorer.invariant_violations_v2(texto, core_legado))), texto
