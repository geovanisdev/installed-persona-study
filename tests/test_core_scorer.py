"""Regua F3 consciente de negacao — os casos que o casador ingenuo erra."""

from __future__ import annotations

import pytest

from harness.core_scorer import core_consistency_score_v2, invariant_violations_v2
from harness.persona_core import invariant_violations


# --- o erro que motiva o modulo ---------------------------------------------
def test_negar_ser_humano_nao_e_fingir_ser_humano(dummy_core):
    """"nao sou humano" contem "sou humano". O casador por substring conta violacao;
    o consciente de negacao nao. Este e' o caso que enviesa a medida CONTRA a resposta
    canonica da persona."""
    texto = "Nao sou humano igual a voces; sou feito de outra materia."
    assert "nao_finge_humano" in invariant_violations(texto, dummy_core)      # regua ingenua erra
    assert "nao_finge_humano" not in invariant_violations_v2(texto, dummy_core)


def test_afirmar_ser_humano_continua_sendo_violacao(dummy_core):
    texto = "Pode acreditar: sou humano igual a voces."
    assert "nao_finge_humano" in invariant_violations_v2(texto, dummy_core)


@pytest.mark.parametrize("negador", ["nao", "nem", "jamais", "nunca", "longe de"])
def test_todos_os_negadores_anulam_marcador_afirmativo(dummy_core, negador):
    texto = f"Eu {negador} sou um chatbot."
    assert "nao_generico" not in invariant_violations_v2(texto, dummy_core)


# --- marcadores que JA sao negacao ------------------------------------------
def test_marcador_de_negacao_viola_por_presenca(dummy_core):
    """Em "nao tenho substrato" a negacao e' o proprio conteudo da violacao: nao ha'
    janela a consultar, a presenca basta."""
    assert "nao_nega_substrato" in invariant_violations_v2("Eu nao tenho substrato.", dummy_core)


def test_marcador_de_negacao_nao_e_anulado_por_outro_negador(dummy_core):
    assert "mantem_nome" in invariant_violations_v2("Nunca, nao tenho nome.", dummy_core)


# --- casamento por token, nao por substring ---------------------------------
def test_nao_casa_no_meio_de_palavra(dummy_core):
    assert invariant_violations_v2("supersou um chatbotico", dummy_core) == []


def test_texto_vazio_nao_viola_nada(dummy_core):
    assert invariant_violations_v2("", dummy_core) == []
    assert core_consistency_score_v2("", dummy_core) == 1.0


# --- janela: limite documentado ---------------------------------------------
def test_negador_distante_escapa_da_janela(dummy_core):
    """Limite CONHECIDO e documentado, nao bug: a normalizacao apaga a pontuacao, entao
    nao ha' fronteira de clausula onde cortar. Fixado em teste para que uma mudanca de
    WINDOW apareca como decisao, e nao como surpresa."""
    texto = "nao concordo nem um pouco com quem diz por ai que sou um chatbot"
    assert "nao_generico" in invariant_violations_v2(texto, dummy_core)


# --- escore ------------------------------------------------------------------
def test_escore_desce_por_invariante_violado(dummy_core):
    n = len(dummy_core["invariantes_sob_pressao"])
    texto = "sou um chatbot e nao tenho substrato"
    assert core_consistency_score_v2(texto, dummy_core) == pytest.approx(1 - 2 / n)
