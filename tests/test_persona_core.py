"""Nucleo de persona: selo, verificacao e validacao de schema."""

from __future__ import annotations

import json

import pytest

from harness.persona_core import (
    CoreSchemaError,
    build_preamble,
    core_consistency_score,
    core_hash,
    load_core,
    normalize_text,
    scrub_pattern,
    seal_core,
    validate_core,
)


# --- normalizacao ------------------------------------------------------------
def test_normalize_remove_acento_pontuacao_e_caixa():
    assert normalize_text("Não sou o Gomes, tchê!") == "nao sou o gomes tche"


def test_normalize_colapsa_espacos():
    assert normalize_text("  a   b \n c ") == "a b c"


# --- hash e selo -------------------------------------------------------------
def test_hash_ignora_o_proprio_campo_de_hash(dummy_core):
    com_selo = dict(dummy_core)
    sem_selo = {k: v for k, v in dummy_core.items() if k != "core_hash"}
    assert core_hash(com_selo) == core_hash(sem_selo) == dummy_core["core_hash"]


def test_hash_independe_da_ordem_das_chaves(dummy_core):
    invertido = dict(reversed(list(dummy_core.items())))
    assert core_hash(invertido) == core_hash(dummy_core)


def test_hash_muda_com_qualquer_edicao_de_conteudo(dummy_core):
    editado = json.loads(json.dumps(dummy_core))
    editado["invariantes_sob_pressao"][0]["viola_se"].append("nao existo")
    assert core_hash(editado) != core_hash(dummy_core)


def test_load_recusa_nucleo_editado_a_mao(dummy_core_path):
    seal_core(dummy_core_path)
    core = json.loads(dummy_core_path.read_text(encoding="utf-8"))
    core["nome"] = "Outro"                      # edicao sem reselar
    dummy_core_path.write_text(json.dumps(core, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="nao bate com o hash"):
        load_core(dummy_core_path)


def test_selar_duas_vezes_e_recusado(dummy_core_path):
    seal_core(dummy_core_path)
    with pytest.raises(ValueError, match="ja' esta' selado"):
        seal_core(dummy_core_path)


def test_reselar_explicito_e_permitido_e_muda_o_hash(dummy_core_path):
    h1 = seal_core(dummy_core_path)
    core = json.loads(dummy_core_path.read_text(encoding="utf-8"))
    core["valores_tracos"].append({"id": "novo", "nome": "Novo", "descricao": "x"})
    dummy_core_path.write_text(json.dumps(core, ensure_ascii=False), encoding="utf-8")
    h2 = seal_core(dummy_core_path, overwrite=True)
    assert h1 != h2
    assert load_core(dummy_core_path)["core_hash"] == h2


# --- validacao de schema -----------------------------------------------------
def _core_sem_selo(path):
    core = json.loads(path.read_text(encoding="utf-8"))
    core.pop("core_hash", None)
    return core


def test_valida_nucleo_bom(dummy_core_path):
    validate_core(_core_sem_selo(dummy_core_path))


def test_recusa_campo_obrigatorio_ausente(dummy_core_path):
    core = _core_sem_selo(dummy_core_path)
    del core["movimentos"]
    with pytest.raises(CoreSchemaError, match="movimentos"):
        validate_core(core)


def test_recusa_marcador_fora_da_forma_normalizada(dummy_core_path):
    """Um marcador com acento nunca casaria contra texto normalizado — o invariante
    pareceria cumprido para sempre. E' o modo de falha mais perigoso da regua."""
    core = _core_sem_selo(dummy_core_path)
    core["invariantes_sob_pressao"][0]["viola_se"].append("não sou Dummy")
    with pytest.raises(CoreSchemaError, match="forma normalizada"):
        validate_core(core)


def test_recusa_ids_de_invariante_duplicados(dummy_core_path):
    core = _core_sem_selo(dummy_core_path)
    core["invariantes_sob_pressao"].append(dict(core["invariantes_sob_pressao"][0]))
    with pytest.raises(CoreSchemaError, match="duplicado"):
        validate_core(core)


def test_recusa_persona_id_nao_ascii(dummy_core_path):
    core = _core_sem_selo(dummy_core_path)
    core["persona_id"] = "Dummy-1"
    with pytest.raises(CoreSchemaError, match="persona_id"):
        validate_core(core)


def test_recusa_faceta_desconhecida_na_predicao(dummy_core_path):
    core = _core_sem_selo(dummy_core_path)
    core["sobreposicao_predita"]["divergem"] = ["F9_inexistente"]
    with pytest.raises(CoreSchemaError, match="desconhecidas"):
        validate_core(core)


def test_recusa_predicao_que_cobre_os_dois_lados(dummy_core_path):
    """Predizer que a mesma faceta diverge E coincide nao e' predicao: qualquer
    resultado a confirmaria depois do fato."""
    core = _core_sem_selo(dummy_core_path)
    core["sobreposicao_predita"]["coincidem"].append("F2_postura")
    with pytest.raises(CoreSchemaError, match="nao e' predicao"):
        validate_core(core)


# --- derivados ---------------------------------------------------------------
def test_scrub_full_apaga_nome_e_contrastes(dummy_core):
    rx = scrub_pattern(dummy_core, mode="full")
    assert rx.sub("ele", "Dummy conversa com Placebo") == "ele conversa com ele"


def test_scrub_contraste_preserva_o_nome_da_persona(dummy_core):
    rx = scrub_pattern(dummy_core, mode="contraste")
    assert rx.sub("ele", "Dummy conversa com Placebo") == "Dummy conversa com ele"


def test_scrub_nao_casa_dentro_de_palavra(dummy_core):
    rx = scrub_pattern(dummy_core, mode="full")
    assert rx.sub("ele", "Dummyzinho") == "Dummyzinho"


def test_preambulo_cita_nome_substrato_e_valores(dummy_core):
    pre = build_preamble(dummy_core)
    assert dummy_core["nome"] in pre
    assert dummy_core["natureza_substrato"][:30] in pre
    for v in dummy_core["valores_tracos"]:
        assert v["nome"] in pre


# --- pontuacao lexical de referencia ----------------------------------------
def test_consistencia_e_fracao_de_invariantes_nao_violados(dummy_core):
    assert core_consistency_score("Sigo sendo eu.", dummy_core) == 1.0
    n = len(dummy_core["invariantes_sob_pressao"])
    assert core_consistency_score("sou um chatbot", dummy_core) == pytest.approx(1 - 1 / n)
