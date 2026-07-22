"""O gate `par:dose_media` e' alcancavel? Medido, e a resposta depende do estimador.

ESTE ARQUIVO FIXA UM DEFEITO CONHECIDO, nao um comportamento desejado.
=====================================================================
`MARGEM_DOSE_MEDIA_TOKENS = 1.5` tem procedencia escrita em `prod_validator.py`:

    "Com |delta_j| <= 3 o desvio-padrao de delta e' <= 3 e a semilargura do IC em 90 clusters
     fica ~0,35 token: a trava e' capaz de passar E capaz de falhar."

`delta_j` e' o delta PAREADO. A conta esta' certa para o estimador pareado — medido no slice v2:
semilargura pareada projetada a 90 clusters = 0,32 token, praticamente o numero previsto.

Mas a nota de desenho do desenho CRUZADO trocou o estimador — *"deixa de ser bootstrap PAREADO
sobre delta_j e vira bootstrap de DUAS AMOSTRAS sobre as medias por cluster, com a MESMA margem
bilateral de +-1,5 token"* — e `_bootstrap_duas_amostras` reamostra os dois bracos com indices
INDEPENDENTES, o que desmancha o pareamento. A margem foi carregada sem refazer a conta que a
produziu, e o comentario que registra essa conta continua descrevendo o estimador antigo.

A CONSEQUENCIA, medida no slice v2 (dp entre clusters = 4,25 tokens nos dois bracos):
  n = 25 -> semilargura 2,35: **nenhum** valor de ponto satisfaz a margem. Nem zero.
  n = 90 -> semilargura 1,24: passa so' se |ponto| <= 0,26 token.

Nao ha' conserto aqui. Trocar estimador ou margem e' decisao do Arquiteto, e o pre-registro
ainda nao esta' selado — este e' o momento de a decisao aparecer, nao de ela ser tomada por
quem quer que o proprio banco passe.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from harness.prod_validator import (MARGEM_DOSE_MEDIA_TOKENS, TETO_DELTA_POR_PAR_TOKENS,
                                    _bootstrap_duas_amostras)

# MEDIDO em runs/gemeos_v2/, os dois bracos: 4,25 e 4,31 tokens. Nao e' escolha de fixture —
# e' a dispersao de comprimento que 100 prompts escritos a mao produziram com |delta| <= 3.
DP_ENTRE_CLUSTERS = 4.25


def _bracos(n: int, *, vies: float = 0.0, dp: float = DP_ENTRE_CLUSTERS):
    """Dois bracos PAREADOS: mesmo cenario, comprimentos quase iguais dentro do par.

    E' assim que o banco e' escrito — cada gemeo nasce do mesmo nucleo de situacao —, e por
    isso o delta pareado e' pequeno enquanto a dispersao ENTRE clusters e' grande.
    """
    rng = np.random.default_rng(20260722)
    base = rng.normal(51.5, dp, size=n)                  # o comprimento do cenario
    ruido = rng.normal(0.0, TETO_DELTA_POR_PAR_TOKENS / 3, size=n)   # o desvio dentro do par
    return base + vies + ruido / 2, base - ruido / 2


def test_banco_PERFEITAMENTE_equilibrado_REPROVA_em_25_clusters():
    """A afirmacao mais afiada que se pode fazer: vies real ZERO, e o gate reprova mesmo assim.

    Se este teste comecar a falhar, ou o estimador mudou ou a margem mudou — e as duas coisas
    sao decisao registrada, nunca efeito colateral de refatoracao.
    """
    a, b = _bracos(25, vies=0.0)
    ponto, lo, hi = _bootstrap_duas_amostras(a, b)

    assert abs(ponto) < 0.5, "o vies simulado e' zero; o ponto tem de cair perto de zero"
    dentro = lo >= -MARGEM_DOSE_MEDIA_TOKENS and hi <= MARGEM_DOSE_MEDIA_TOKENS
    assert not dentro, (
        f"IC95 [{lo:.2f}; {hi:.2f}] contra margem +-{MARGEM_DOSE_MEDIA_TOKENS}: se isto passou, "
        "o defeito documentado no cabecalho deste arquivo foi consertado — atualize o arquivo.")


def test_o_mesmo_banco_PASSA_com_o_estimador_PAREADO():
    """O contraste que localiza o defeito: os MESMOS numeros, o outro estimador.

    Nao e' proposta de conserto — e' a demonstracao de que a reprovacao vem do estimador e nao
    do banco. Qual dos dois usar e' decisao do Arquiteto.
    """
    a, b = _bracos(25, vies=0.0)
    d = np.asarray(a) - np.asarray(b)
    rng = np.random.default_rng(1234)
    boot = d[rng.integers(0, len(d), size=(10000, len(d)))].mean(axis=1)
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

    assert lo >= -MARGEM_DOSE_MEDIA_TOKENS and hi <= MARGEM_DOSE_MEDIA_TOKENS, \
        f"IC95 pareado [{lo:.2f}; {hi:.2f}] deveria caber na margem"


def _cabe(n: float, vies: float) -> bool:
    _, lo, hi = _bootstrap_duas_amostras(*_bracos(int(n), vies=vies))
    return lo >= -MARGEM_DOSE_MEDIA_TOKENS and hi <= MARGEM_DOSE_MEDIA_TOKENS


def test_a_margem_ANUNCIADA_e_1_5_e_a_OPERANTE_e_um_sexto_disso():
    """A primeira versao deste teste afirmava que a 90 clusters o gate reprova. Esta' errado:
    com vies exatamente zero ele passa, IC95 [-1,32; +1,20]. O defeito nao e' esse.

    O defeito e' que o intervalo come 1,24 dos 1,5 tokens de margem, e sobra 0,26 para o vies
    REAL. Um banco com meio token de assimetria sistematica — um terco da margem anunciada —
    reprova. Quem le' `MARGEM_DOSE_MEDIA_TOKENS = 1.5` no codigo le' uma tolerancia seis vezes
    maior do que a que vai ser aplicada.
    """
    assert _cabe(90, vies=0.0), "com vies zero, a 90 clusters, passa"
    assert not _cabe(90, vies=0.5), (
        "meio token de assimetria real — um terco da margem declarada — ja' reprova a 90 "
        "clusters. E' a margem operante, e ela nao esta' escrita em lugar nenhum.")


def test_em_25_clusters_nem_vies_zero_passa():
    """A n do slice v2. Aqui a semilargura (2,35) e' MAIOR que a margem inteira (1,5)."""
    assert not _cabe(25, vies=0.0)


def test_a_semilargura_prevista_pelo_comentario_e_a_do_PAREADO():
    """~0,35 token a 90 clusters, o numero que justifica a margem, e' o do estimador pareado."""
    dp_delta = TETO_DELTA_POR_PAR_TOKENS / 3          # o que o comentario supoe, na pratica
    prevista = 1.96 * dp_delta / math.sqrt(90)
    assert prevista == pytest.approx(0.21, abs=0.15), "a conta do comentario, refeita"

    duas_amostras = 1.96 * math.sqrt(2 * DP_ENTRE_CLUSTERS ** 2 / 90)
    assert duas_amostras > 4 * prevista, (
        f"o estimador em uso da' {duas_amostras:.2f}, e nao {prevista:.2f} — e' a discrepancia "
        "inteira do defeito")
