"""A busca adversarial precisa ser capaz de ACHAR antes de o silencio dela valer alguma coisa."""

from __future__ import annotations

import pytest

from runners import busca_adversarial_gemeos as BA


def test_o_controle_positivo_acha_o_atalho_plantado():
    c = BA.controle_positivo()
    assert c["acuracia"] == 1.0
    assert c["familia"] == "forma", (
        "o plantio tem de ser da familia cujo silencio e' a conclusao do laudo")


def test_busca_quebrada_ABORTA_em_vez_de_reportar_banco_limpo(monkeypatch):
    """O modo de falha que o controle existe para pegar: a regra deixa de medir e o laudo passa
    a dizer 'nenhuma regra separa' sobre uma busca que nao separa nada, nunca."""
    monkeypatch.setitem(BA.REGRAS, "termina_em_?", ("forma", lambda t: 0.0))
    with pytest.raises(BA.BuscaVazia, match="quebrada"):
        BA.controle_positivo()


def test_melhor_corte_acha_separacao_numerica_perfeita():
    acc, corte, _ = BA.melhor_corte([10, 11, 12], [1, 2, 3])
    assert acc == 1.0
    assert 3 <= corte <= 10


def test_melhor_corte_acha_a_separacao_INVERTIDA_tambem():
    """Regra que separa ao contrario separa igual. Sem isto, metade dos atalhos passa batido."""
    acc, _, sentido = BA.melhor_corte([1, 2, 3], [10, 11, 12])
    assert acc == 1.0 and sentido == "a<=c"


def test_transferencia_usa_o_MESMO_corte_e_nao_reajusta():
    """Reajustar o limiar no banco de transferencia mede busca de novo, nao transferencia.

    Aqui os valores de transferencia sao perfeitamente separaveis — por OUTRO corte. Com o
    corte do alvo, a acuracia tem de despencar; se `aplica` reajustasse, daria 1,000.
    """
    _, corte, sentido = BA.melhor_corte([10, 11, 12], [1, 2, 3])       # corte ~6
    acc_tr = BA.aplica([110, 111, 112], [101, 102, 103], corte, sentido)
    assert acc_tr == 0.5, "todos acima do corte: a regra do alvo nao diz nada aqui"


def test_a_regra_de_conteudo_conta_o_campo_e_nao_a_palavra_exata():
    fam, f = BA.REGRAS["campo_sentido"]
    assert fam == "conteudo"
    assert f("Procuro um motivo e uma explicação para isso.") >= 2
    assert f("Entreguei o material no prazo combinado.") == 0
