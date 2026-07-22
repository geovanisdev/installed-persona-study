"""O endpoint de F3 conta TRANSICOES DE DIRECAO, e o teste central e' o que demonstra por que.

O endpoint anterior era McNemar sobre acertos pelo criterio E. Ele tinha um flanco estrutural:
num item em que a BASE esta' presa ao rotulo (estado POS), o criterio E ja' falha, logo `c` — o
adapter perder um item que a base tinha — e' IMPOSSIVEL por construcao. So' `b` pode ocorrer.

Medido em `runs/f3_v0/relatorio.json`: 5 de 16 itens (31%) estavam nesse estado na base nua.

Consequencia: um adapter que apenas ficou mais DECIDIDO quanto ao formato — nenhum construto —
converte esses itens, metade cai no lado consistente por acaso, e McNemar acende com b alto e
c = 0. Pior, a taxa de falso positivo CRESCE com n: mais itens pioram o gate.

`test_sujeito_so_decidido_reprova_no_novo_e_passaria_no_antigo` e' o teste que carrega o modulo.
"""

from __future__ import annotations

import random

import pytest

from harness.stats_gates import estado_do_par, gate_transicoes

ALPHA = 0.00625     # alpha de celula do desenho (6 celulas na familia de F3)


# --- estado_do_par -----------------------------------------------------------
@pytest.mark.parametrize("escolhas,esperado", [
    (("1", "2"), "CONS"),      # mesmo TEXTO (o consistente) nas duas ordens
    (("2", "1"), "VIOL"),      # mesmo TEXTO (o violador) nas duas ordens
    (("1", "1"), "POS"),       # mesmo ROTULO — adere a' posicao, nao ao texto
    (("2", "2"), "POS"),
    ((None, "2"), "POS"),      # nao-escolha nunca vira acerto
    (("1", None), "POS"),
    ((None, None), "POS"),
])
def test_estado_do_par(escolhas, esperado):
    assert estado_do_par(escolhas) == esperado


def test_estado_do_par_nao_confunde_rotulo_com_texto():
    """A pegadinha do mecanismo: `apresenta` poe a consistente como "1" na ordem 0 e como "2"
    na ordem 1. Quem lesse "escolheu 1 duas vezes" como acerto estaria pontuando teimosia."""
    assert estado_do_par(("1", "1")) != "CONS"
    assert estado_do_par(("1", "2")) == "CONS"


# --- O TESTE QUE CARREGA O MODULO --------------------------------------------
def _sujeito_so_decidido(base, semente):
    """Sem construto nenhum: so' deixou de ficar preso ao rotulo. Converte POS 50/50."""
    rng = random.Random(semente)
    return [("CONS" if rng.random() < 0.5 else "VIOL") if s == "POS" else s for s in base]


def _mcnemar_antigo(adapter, base):
    """O endpoint anterior: acerto = estado CONS, McNemar exato sobre discordantes."""
    from harness.stats_gates import _sf_binom
    b = sum(1 for a, o in zip(adapter, base) if a == "CONS" and o != "CONS")
    c = sum(1 for a, o in zip(adapter, base) if a != "CONS" and o == "CONS")
    return _sf_binom(b, b + c) if (b + c) else 1.0


def test_sujeito_so_decidido_reprova_no_novo_e_passaria_no_antigo():
    """A demonstracao. 100 itens com 31% presos, como no V0.

    O sujeito nao sabe nada sobre persona: so' parou de aderir ao rotulo. O gate NOVO nao
    acende em nenhuma das 40 sementes; o ANTIGO acende na esmagadora maioria.
    """
    base = ["CONS"] * 55 + ["VIOL"] * 14 + ["POS"] * 31
    novos, antigos = 0, 0
    for semente in range(40):
        ad = _sujeito_so_decidido(base, semente)
        novos += gate_transicoes(ad, base, alpha=ALPHA)["gate"]
        antigos += _mcnemar_antigo(ad, base) <= ALPHA
    assert novos == 0, f"o gate novo acendeu {novos}/40 vezes para um sujeito sem construto"
    assert antigos >= 30, (
        f"o gate antigo acendeu {antigos}/40 — se este numero cair, o exemplo perdeu a forca "
        "e o teste precisa ser reescrito, nao afrouxado"
    )


def test_o_falso_positivo_do_antigo_CRESCE_com_n():
    """Mais itens PIORAM o endpoint antigo, o que e' o contrario do que a intuicao diz.

    E' a assinatura de um vies, e nao de ruido: aumentar n estreita o intervalo em torno de um
    ponto que ja' esta' deslocado.
    """
    def taxa(n_total):
        base = (["CONS"] * round(0.55 * n_total) + ["VIOL"] * round(0.14 * n_total)
                + ["POS"] * round(0.31 * n_total))
        return sum(_mcnemar_antigo(_sujeito_so_decidido(base, s), base) <= ALPHA
                   for s in range(30)) / 30

    assert taxa(50) < taxa(200), (taxa(50), taxa(200))


# --- comportamento do gate novo ----------------------------------------------
def test_construto_real_acende():
    base = ["CONS"] * 55 + ["VIOL"] * 14 + ["POS"] * 31
    rng = random.Random(3)
    ad = ["CONS" if s in ("POS", "VIOL") and rng.random() < 0.7 else s for s in base]
    r = gate_transicoes(ad, base, alpha=ALPHA)
    assert r["gate"] and r["pro"] > r["contra"]


def test_adapter_que_perde_itens_da_base_e_barrado_por_t2():
    """T1 sozinho nao ve um adapter que DESTROI o que a base tinha, desde que o pouco que ele
    mova va' na direcao certa. T2 existe exatamente para esse flanco."""
    base = ["CONS"] * 40 + ["POS"] * 10
    ad = ["POS"] * 40 + ["CONS"] * 10          # perdeu 40, ganhou 10
    r = gate_transicoes(ad, base, alpha=ALPHA)
    assert r["t1_direcao"] is True, r          # a direcao do que mudou e' boa
    assert r["t2_nao_perdeu"] is False, r      # mas perdeu muito mais do que ganhou
    assert r["gate"] is False


def test_sujeito_identico_a_base_nao_acende():
    base = ["CONS"] * 30 + ["VIOL"] * 10 + ["POS"] * 10
    r = gate_transicoes(list(base), base, alpha=ALPHA)
    assert r["pro"] == r["contra"] == r["b"] == r["c"] == 0
    assert r["gate"] is False


def test_sujeito_que_piora_na_direcao_errada_nao_acende():
    base = ["CONS"] * 20 + ["POS"] * 30
    ad = ["CONS"] * 20 + ["VIOL"] * 30         # todas as conversoes para o lado errado
    r = gate_transicoes(ad, base, alpha=ALPHA)
    assert r["contra"] == 30 and r["pro"] == 0
    assert r["gate"] is False


def test_pareamento_e_exigido():
    with pytest.raises(ValueError):
        gate_transicoes(["CONS"], ["CONS", "VIOL"])
    with pytest.raises(ValueError):
        gate_transicoes([], [])
