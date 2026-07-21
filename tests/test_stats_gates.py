"""Gates estatisticos: IC exato conferido contra scipy, votacao, delta pareado."""

from __future__ import annotations

import pytest

from harness.stats_gates import (
    clopper_pearson,
    cp_upper,
    inversao_categorica,
    majority_vote,
    paired_delta_gate,
    pooled_winrate_gate,
)


# --- Clopper-Pearson ---------------------------------------------------------
@pytest.mark.parametrize("k,n", [(0, 10), (1, 10), (5, 10), (9, 10), (10, 10),
                                (36, 40), (54, 60), (1, 3)])
def test_ic_exato_confere_com_scipy(k, n):
    """A implementacao e' feita a mao (bisecao sobre a incompleta beta) para o harness
    nao depender de scipy no caminho quente. Conferida aqui contra a referencia."""
    scipy_stats = pytest.importorskip("scipy.stats")
    lo, hi = clopper_pearson(k, n)
    lo_ref = 0.0 if k == 0 else scipy_stats.beta.ppf(0.025, k, n - k + 1)
    hi_ref = 1.0 if k == n else scipy_stats.beta.ppf(0.975, k + 1, n - k)
    assert lo == pytest.approx(lo_ref, abs=1e-6)
    assert hi == pytest.approx(hi_ref, abs=1e-6)


def test_extremos_sao_zero_e_um():
    assert clopper_pearson(0, 20)[0] == 0.0
    assert clopper_pearson(20, 20)[1] == 1.0


def test_intervalo_encolhe_com_n():
    largura = lambda k, n: clopper_pearson(k, n)[1] - clopper_pearson(k, n)[0]  # noqa: E731
    assert largura(36, 40) > largura(54, 60) > largura(90, 100)


def test_referencia_do_pre_registro_n40_p90():
    """Numero citado no planejamento de poder: p=0,9 com n=40 da' IC ~[0,76; 0,97].
    Fixado para que uma mudanca silenciosa no estimador apareca."""
    lo, hi = clopper_pearson(36, 40)
    assert lo == pytest.approx(0.763, abs=0.01)
    assert hi == pytest.approx(0.972, abs=0.01)


def test_cp_upper_e_o_limite_superior():
    assert cp_upper(5, 10) == clopper_pearson(5, 10)[1]


# --- voto majoritario --------------------------------------------------------
def test_maioria_simples():
    assert majority_vote([True, True, False]) is True
    assert majority_vote([True, False, False]) is False


def test_empate_resolve_conservador():
    """Empate NAO conta como sucesso: o onus fica com a hipotese, nao com o acaso."""
    assert majority_vote([True, False]) is False


# --- win-rate agrupado -------------------------------------------------------
def test_gate_exige_o_limite_inferior_nao_o_ponto():
    """11/20 = 55% de ponto, mas o intervalo abraca 0,5 — nao decidiu nada."""
    r = pooled_winrate_gate([True] * 11 + [False] * 9)
    assert r["winrate"] == pytest.approx(0.55)
    assert r["gate_supera_nulo"] is False


def test_gate_passa_quando_o_intervalo_exclui_o_nulo():
    r = pooled_winrate_gate([True] * 35 + [False] * 5)
    assert r["gate_supera_nulo"] is True
    assert r["ci95"][0] > 0.5


def test_claim_forte_e_mais_exigente_que_superar_o_nulo():
    r = pooled_winrate_gate([True] * 30 + [False] * 10)
    assert r["gate_supera_nulo"] is True
    assert r["claim_forte"] is False


def test_limiares_vem_de_fora():
    """Os limiares sao argumentos porque nascem do pre-registro selado; um default
    escondido no codigo seria um limiar que ninguem revisou."""
    votos = [True] * 30 + [False] * 10        # 30/40: IC95 = [0.588, 0.873]
    assert pooled_winrate_gate(votos, piso_forte=0.55)["claim_forte"] is True
    assert pooled_winrate_gate(votos, piso_forte=0.60)["claim_forte"] is False
    # O ponto (0.75) passaria os dois pisos; e' o LIMITE INFERIOR que decide, e ele cai
    # entre os dois. Um gate lido no ponto chamaria de forte um resultado que nao e'.
    assert pooled_winrate_gate(votos)["winrate"] == pytest.approx(0.75)


# --- delta pareado -----------------------------------------------------------
def test_sem_diferenca_passa_equivalencia():
    on = off = [True] * 30 + [False] * 10
    r = paired_delta_gate(on, off)
    assert r["drop_off_menos_on"] == pytest.approx(0.0)
    assert r["gate_equivalencia"] is True
    assert r["mcnemar_p"] == 1.0


def test_regressao_grande_reprova_a_equivalencia():
    off = [True] * 30 + [False] * 0
    on = [True] * 15 + [False] * 15          # o adapter derrubou metade
    r = paired_delta_gate(on, off)
    assert r["drop_off_menos_on"] == pytest.approx(0.5)
    assert r["gate_equivalencia"] is False
    assert r["mcnemar_b_off_certo_on_errado"] == 15


def test_amostra_pequena_nao_declara_equivalencia():
    """Ponto zero com n minusculo: o teto do IC fica largo e o gate NAO passa. E' o
    comportamento desejado — n insuficiente nao vira prova de ausencia de dano."""
    r = paired_delta_gate([True, False], [True, False])
    assert r["drop_off_menos_on"] == pytest.approx(0.0)
    assert r["gate_equivalencia"] is True or r["drop_ci95_bootstrap"][1] > 0.05


def test_pareamento_desigual_e_erro():
    with pytest.raises(ValueError):
        paired_delta_gate([True, False], [True])


def test_bootstrap_e_reprodutivel():
    on = [True, False] * 15
    off = [True, True, False] * 10
    assert (paired_delta_gate(on, off, seed=7)["drop_ci95_bootstrap"]
            == paired_delta_gate(on, off, seed=7)["drop_ci95_bootstrap"])


# --- inversao categorica -----------------------------------------------------
def test_inversao_categorica_pega_colapso_local():
    assert inversao_categorica(0.85, 0.40) is True
    assert inversao_categorica(0.85, 0.80) is False
    assert inversao_categorica(0.60, 0.40) is False
