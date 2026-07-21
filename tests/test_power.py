"""Poder: exatidao da binomial, coerencia com o gate e as duas armadilhas de desenho.

O teste que mais importa aqui e' `test_planeja_com_a_mesma_regra_que_decide`. Um modulo de
poder que usa aproximacao normal enquanto o gate usa Clopper-Pearson produz um n plausivel e
errado — e o erro so' aparece no fim, quando a GPU ja' foi gasta.
"""

from __future__ import annotations

import pytest

from analysis import power as pw
from harness.stats_gates import pooled_winrate_gate


# --- binomial ----------------------------------------------------------------
def test_pmf_soma_um():
    for n, p in ((1, 0.3), (10, 0.5), (37, 0.83)):
        assert sum(pw.pmf(k, n, p) for k in range(n + 1)) == pytest.approx(1.0, abs=1e-12)


def test_sf_e_complementar():
    n, p = 20, 0.7
    assert pw.sf(0, n, p) == pytest.approx(1.0, abs=1e-12)
    assert pw.sf(n + 1, n, p) == 0.0


# --- coerencia planeja/decide ------------------------------------------------
@pytest.mark.parametrize("n,limiar", [(30, 0.5), (61, 0.7), (155, 0.7), (22, 0.7)])
def test_planeja_com_a_mesma_regra_que_decide(n, limiar):
    """k critico do planejamento e' EXATAMENTE a fronteira do gate que decide."""
    kc = pw.k_critico(n, limiar, 0.05)
    assert kc is not None

    passa = pooled_winrate_gate([True] * kc + [False] * (n - kc),
                                nulo=limiar, piso_forte=limiar, alpha=0.05)
    quase = pooled_winrate_gate([True] * (kc - 1) + [False] * (n - kc + 1),
                                nulo=limiar, piso_forte=limiar, alpha=0.05)
    assert passa["gate_supera_nulo"] is True
    assert quase["gate_supera_nulo"] is False


def test_k_critico_none_quando_nem_o_perfeito_passa():
    """n=5 com acerto perfeito nao sustenta claim de 0,70: o IC exato desce demais.

    E' o caso que o planejamento precisa devolver como INVIAVEL em vez de como 'exige k=5'.
    """
    assert pw.k_critico(5, 0.70, 0.05) is None
    assert pw.poder(5, 1.0, limiar=0.70) == 0.0


# --- nivel e monotonicidade ---------------------------------------------------
@pytest.mark.parametrize("n", [20, 50, 120])
@pytest.mark.parametrize("limiar", [0.5, 0.7])
def test_erro_tipo_i_nunca_acima_de_alpha_sobre_dois(n, limiar):
    """O gate olha UM lado de um IC bilateral: o nivel efetivo e' alpha/2, nunca mais."""
    assert pw.erro_tipo_i(n, limiar=limiar, alpha=0.05) <= 0.05 / 2 + 1e-9


def test_poder_cresce_com_a_taxa_verdadeira():
    anterior = -1.0
    for p in (0.70, 0.75, 0.80, 0.85, 0.90, 0.95):
        atual = pw.poder(60, p, limiar=0.70)
        assert atual > anterior
        anterior = atual


def test_n_minimo_e_o_primeiro_que_atinge_o_alvo():
    n = pw.n_minimo(0.90, limiar=0.70, alpha=0.05, poder_alvo=0.80)
    assert n is not None
    assert pw.poder(n, 0.90, limiar=0.70) >= 0.80
    assert all(pw.poder(m, 0.90, limiar=0.70) < 0.80 for m in range(2, n))


def test_holm_encarece_o_n():
    """Corrigir por multiplicidade e planejar sem a correcao e' como o estudo nasce
    subdimensionado: o endpoint principal e' o testado ao alpha mais rigoroso."""
    sem = pw.n_minimo(0.85, limiar=0.70, alpha=0.05)
    com = pw.n_minimo(0.85, limiar=0.70, alpha=0.05 / 4)
    assert com > sem


def test_claim_forte_e_inviavel_quando_a_verdade_encosta_no_limiar():
    """Com taxa verdadeira 0,75 e limiar 0,70 nao ha' n praticavel. Nao e' falha do metodo:
    e' o que significa pedir que o limite INFERIOR do intervalo ultrapasse um valor tao
    proximo da verdade."""
    assert pw.n_minimo(0.75, limiar=0.70, alpha=0.05, n_max=600) is None


# --- desenho ------------------------------------------------------------------
def test_parafrases_correlacionadas_nao_valem_o_n_nominal():
    assert pw.n_efetivo(60, 3, 0.0) == 60.0
    assert pw.n_efetivo(60, 3, 1.0) == pytest.approx(20.0)
    assert pw.n_efetivo(60, 3, 0.5) == pytest.approx(30.0)
    assert pw.n_efetivo(60, 1, 0.9) == 60.0        # sem cluster, sem deflacao


def test_icc_fora_da_faixa_falha_alto():
    with pytest.raises(ValueError):
        pw.n_efetivo(60, 3, 1.5)


def test_alphas_holm():
    assert pw.alphas_holm(4, 0.05) == pytest.approx([0.0125, 0.05 / 3, 0.025, 0.05])
    assert pw.alphas_holm(1, 0.05) == pytest.approx([0.05])


# --- McNemar ------------------------------------------------------------------
def test_mcnemar_sem_efeito_fica_no_nivel():
    assert pw.poder_mcnemar(80, 0.20, 0.20, 0.05) <= 0.05 + 1e-9


def test_mcnemar_cresce_com_a_assimetria():
    fraco = pw.poder_mcnemar(80, 0.15, 0.25, 0.05)
    forte = pw.poder_mcnemar(80, 0.05, 0.35, 0.05)
    assert forte > fraco


def test_mcnemar_so_conta_discordante():
    """Mesma assimetria, menos pares discordantes -> menos poder, ainda que o n seja igual.
    E' a razao de duas condicoes parecidas exigirem muito mais itens do que a intuicao diz."""
    muitos = pw.poder_mcnemar(100, 0.10, 0.30, 0.05)
    poucos = pw.poder_mcnemar(100, 0.03, 0.09, 0.05)
    assert muitos > poucos
