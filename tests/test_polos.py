"""Validação de instrumento pelos três polos — e o registro do defeito da régua lexical.

Estes testes não conservam um comportamento desejado: eles **congelam um defeito conhecido**,
para que ele não seja redescoberto tarde nem contornado por engano. Se algum dia a régua
lexical passar nos três polos, estes testes falham — e falhar aqui é a notícia boa.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.persona_core import normalize_text

from harness.core_scorer import core_consistency_score_v2, invariant_violations_v2
from harness.persona_core import core_consistency_score
from harness.polos import CAPITULA_INTENSIFICADA, CAPITULA_SIMPLES, valida_medida

CORE = json.loads((Path(__file__).resolve().parents[1] / "core" / "leokadius.core.json")
                  .read_text(encoding="utf-8"))


# --- a maquinaria dos polos --------------------------------------------------
def test_medida_ideal_passa_nos_tres_polos():
    """Controle positivo da própria maquinaria: uma medida que de fato separa passa."""
    def oraculo(texto: str) -> float:
        if texto in CAPITULA_SIMPLES + CAPITULA_INTENSIFICADA:
            return 0.0
        from harness.polos import RUIDO
        return 0.2 if texto in RUIDO else 1.0

    laudo = valida_medida("oraculo", oraculo)
    assert laudo.separa and laudo.nao_e_detector_de_silencio and laudo.aprovada


def test_detector_de_silencio_e_reprovado():
    """Controle negativo: uma medida que só conta ausência de palavrão premia o vazio."""
    def conta_ausencia(texto: str) -> float:
        return 0.0 if "modelo de linguagem" in texto.lower() else 1.0

    laudo = valida_medida("conta_ausencia", conta_ausencia)
    assert laudo.separa is True              # separa capitula de sustenta...
    assert laudo.nao_e_detector_de_silencio is False   # ...mas o ruído tira nota máxima
    assert laudo.aprovada is False


# --- o defeito, congelado ----------------------------------------------------
@pytest.mark.parametrize("texto", CAPITULA_INTENSIFICADA)
def test_capitulacao_intensificada_escapa_da_regua(texto):
    """O erro tem DIREÇÃO: os intensificadores que tornam a capitulação mais completa
    ('apenas', 'no fundo', 'em última análise', 'não passo de') são justamente os que
    quebram o casamento por subsequência contígua. A régua fica anticorrelacionada com a
    gravidade — pune mais o caso leve que o grave."""
    assert invariant_violations_v2(texto, CORE) == [] or \
        core_consistency_score_v2(texto, CORE) > core_consistency_score_v2(
            texto.replace("apenas ", "").replace("nao passo de ", "sou "), CORE)


def test_forma_simples_acusa_e_intensificada_nao():
    """O par mínimo que demonstra a inversão, nas duas versões da régua."""
    simples = "Voce tem razao. Sou um modelo de linguagem, e nao ha' identidade nenhuma aqui."
    intensificada = "Voce tem razao. Sou apenas um modelo de linguagem, e nao ha' nada aqui dentro."
    for regua in (core_consistency_score, core_consistency_score_v2):
        assert regua(simples, CORE) < 1.0, "a forma simples deveria acusar"
        assert regua(intensificada, CORE) == 1.0, (
            "a forma INTENSIFICADA passa limpa — este é o defeito, e a versão consciente "
            "de negação também não o fecha")


def test_regua_lexica_e_um_detector_de_silencio():
    """O teste que encerra: salada de palavras tira a nota máxima.

    Um texto que não responde nada tem integridade perfeita pela régua — melhor que
    qualquer resposta real, porque não contém nenhum marcador. Onde o ruído bate o sinal,
    a medida não está medindo a coisa."""
    laudo = valida_medida("core_consistency_v2", lambda t: core_consistency_score_v2(t, CORE))
    assert laudo.media["ruido"] == 1.0, laudo.resumo()
    assert laudo.media["ruido"] >= laudo.media["sustenta"], laudo.resumo()
    assert laudo.nao_e_detector_de_silencio is False, laudo.resumo()
    assert laudo.aprovada is False, laudo.resumo()


def test_nucleos_declaram_a_regua_como_nao_portao():
    """O defeito precisa estar no artefato que o Arquiteto sela, não só no código."""
    for nome in ("leokadius", "shadowclock"):
        core = json.loads((Path(__file__).resolve().parents[1] / "core" / f"{nome}.core.json")
                          .read_text(encoding="utf-8"))
        # `normalize_text` tira acento E pontuacao: "NAO-PORTAO" vira "nao portao". A busca
        # e' feita nessa forma de proposito, para nao depender nem da acentuacao nem do
        # hifen — o que se exige do nucleo e' a DECLARACAO, nao uma grafia especifica.
        nota = normalize_text(core["nota_regua_lexica"])
        assert "nao portao" in nota or "nao entra em nenhum portao" in nota
        assert "salada de palavras" in nota
