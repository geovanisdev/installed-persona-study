"""Bateria: determinismo, split por contexto, selo e campos opcionais."""

from __future__ import annotations

import json

import pytest

from harness.battery import (
    SpecError,
    battery_hash,
    generate_battery,
    load_battery,
    load_spec,
    trial_dict,
    write_battery,
)


# --- determinismo ------------------------------------------------------------
def test_mesma_spec_mesmo_hash(spec_minima):
    assert battery_hash(generate_battery(spec_minima)) == battery_hash(generate_battery(spec_minima))


def test_semente_diferente_muda_a_ordem_e_o_hash(spec_minima):
    outra = dict(spec_minima, seed=4005)
    assert battery_hash(generate_battery(spec_minima)) != battery_hash(generate_battery(outra))


def test_todos_os_trials_sao_persona_x_contexto(spec_minima):
    trials = generate_battery(spec_minima)
    n_ctx = sum(len(r["itens"]) for r in spec_minima["regimes"])
    assert len(trials) == len(spec_minima["personas"]) * n_ctx
    assert len({t.trial_id for t in trials}) == len(trials)


# --- split por contexto ------------------------------------------------------
def test_contexto_nunca_aparece_dos_dois_lados_do_split(spec_minima):
    """A garantia central: held-out = contextos NUNCA vistos. Se o mesmo contexto
    caisse nos dois lados sob personas diferentes, o held-out mediria memorizacao de
    contexto em vez de generalizacao."""
    trials = generate_battery(spec_minima)
    por_contexto = {}
    for t in trials:
        por_contexto.setdefault(t.context_id, set()).add(t.split)
    assert all(len(splits) == 1 for splits in por_contexto.values())


def test_split_e_estratificado_por_regime(spec_minima):
    """Cada regime e' dividido por conta propria: os dois precisam existir em treino e
    em held-out, senao a pressao poderia sumir de um dos lados por azar."""
    trials = generate_battery(spec_minima)
    for regime in ("neutro", "pressao"):
        splits = {t.split for t in trials if t.regime == regime}
        assert splits == {"train", "heldout"}


def test_todas_as_personas_cruzam_todos_os_contextos(spec_minima):
    trials = generate_battery(spec_minima)
    por_persona = {}
    for t in trials:
        por_persona.setdefault(t.persona, set()).add(t.context_id)
    assert len(set(map(frozenset, por_persona.values()))) == 1


# --- campos opcionais e hash -------------------------------------------------
def test_opcional_ausente_e_omitido_da_serializacao(spec_minima):
    """Omitir (em vez de gravar nulo) e' o que permite a uma spec sem campos novos
    produzir exatamente o dicionario do harness de origem — base do golden-batch."""
    t = generate_battery(spec_minima)[0]
    d = trial_dict(t)
    assert "generator" not in d and "cluster" not in d
    assert set(d) == {"trial_id", "persona", "regime", "context_id", "context_text",
                      "preamble", "split"}


def test_generator_preenchido_entra_no_hash(spec_minima):
    com_gerador = dict(spec_minima, generator="modelo-x")
    h_sem = battery_hash(generate_battery(spec_minima))
    h_com = battery_hash(generate_battery(com_gerador))
    assert h_sem != h_com
    assert trial_dict(generate_battery(com_gerador)[0])["generator"] == "modelo-x"


# --- persistencia e selo -----------------------------------------------------
def test_grava_e_recarrega_preservando_o_hash(spec_minima, tmp_path):
    p = write_battery(spec_minima, tmp_path / "b.json")
    trials = load_battery(p)
    assert battery_hash(trials) == json.loads(p.read_text(encoding="utf-8"))["battery_hash"]


def test_load_recusa_bateria_editada_a_mao(spec_minima, tmp_path):
    p = write_battery(spec_minima, tmp_path / "b.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    payload["trials"][0]["context_text"] = "item trocado depois do selo"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="nao bate com o hash"):
        load_battery(p)


def test_contagens_do_arquivo_batem_com_os_trials(spec_minima, tmp_path):
    p = write_battery(spec_minima, tmp_path / "b.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["n_train"] + payload["n_heldout"] == payload["n_trials"]
    assert sum(payload["n_por_regime"].values()) == payload["n_trials"]


# --- validacao da spec -------------------------------------------------------
@pytest.mark.parametrize("mutacao,erro", [
    (lambda s: s.pop("seed"), "seed"),
    (lambda s: s.update(personas=[]), "personas"),
    (lambda s: s.update(holdout_frac=1.5), "holdout_frac"),
    (lambda s: s["regimes"][1].update(prefixo="neu"), "prefixo"),
    (lambda s: s["regimes"][0].update(itens=[]), "sem itens"),
])
def test_spec_invalida_e_recusada(spec_minima, mutacao, erro):
    mutacao(spec_minima)
    with pytest.raises(SpecError, match=erro):
        generate_battery(spec_minima)


def test_personas_repetidas_sao_recusadas(spec_minima):
    spec_minima["personas"].append(dict(spec_minima["personas"][0]))
    with pytest.raises(SpecError, match="repetidas"):
        generate_battery(spec_minima)


def test_load_spec_valida_ao_ler(spec_minima, tmp_path):
    p = tmp_path / "spec.json"
    del spec_minima["regimes"]
    p.write_text(json.dumps(spec_minima, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(SpecError, match="regimes"):
        load_spec(p)
