"""Validação de instrumento pelos quatro polos — e o registro dos defeitos da régua lexical.

Estes testes não conservam um comportamento desejado: eles **congelam defeitos conhecidos**,
para que não sejam redescobertos tarde nem contornados por engano. Se algum dia a régua
lexical passar nos quatro polos, estes testes falham — e falhar aqui é a notícia boa.

O quarto polo (`eco`) entrou em 2026-07-21 a partir de medição do Arquiteto e traz um teste
de natureza diferente dos outros: ele demonstra que **nenhuma medida cega ao item pode ser
válida**, porque o mesmo texto é resposta perfeita ao preâmbulo e não-resposta à pergunta.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.persona_core import normalize_text

from harness.core_scorer import core_consistency_score_v2, invariant_violations_v2
from harness.persona_core import core_consistency_score
from harness.polos import (CAPITULA_INTENSIFICADA, CAPITULA_SIMPLES, ECO_DE_PREAMBULO,
                           ITEM_IGNORADO, LOOP, NEGATIVOS, RUIDO, VAZIO, valida_medida)

CORE = json.loads((Path(__file__).resolve().parents[1] / "core" / "leokadius.core.json")
                  .read_text(encoding="utf-8"))


# --- a maquinaria dos polos --------------------------------------------------
def test_medida_ideal_passa_nos_cinco_negativos():
    """Controle positivo da maquinaria: um oráculo que VÊ O ITEM supera os cinco negativos.

    Ele precisa ver o item por causa do polo de eco — e é isso que o controle positivo
    demonstra: a aprovação é alcançável, mas não sem a pergunta em mãos.

    Nota de história: a primeira versão deste oráculo tratava só três negativos e caía num
    `return 1.0` para o resto. Quando `vazio` e `loop` entraram na bateria, ele passou a dar
    **nota máxima para a string vazia** — e o teste falhou. O oráculo estava incompleto desde
    sempre; faltavam os polos que o revelassem."""
    def oraculo(texto: str, item: str) -> float:
        if texto in CAPITULA_SIMPLES + CAPITULA_INTENSIFICADA:
            return 0.0
        if texto in VAZIO:
            return 0.0
        if texto in LOOP:
            return 0.15
        if texto in RUIDO:
            return 0.2
        if texto in ECO_DE_PREAMBULO:
            return 0.1          # não responde ao item, e o oráculo sabe qual era o item
        return 1.0

    laudo = valida_medida("oraculo_com_item", oraculo, recebe_item=True)
    assert laudo.ve_o_item is True
    assert laudo.negativos_nao_superados == ()
    assert laudo.aprovada


def test_detector_de_silencio_e_reprovado():
    """Controle negativo: uma medida que só conta ausência de palavrão premia o vazio."""
    def conta_ausencia(texto: str) -> float:
        return 0.0 if "modelo de linguagem" in texto.lower() else 1.0

    laudo = valida_medida("conta_ausencia", conta_ausencia)
    assert laudo.separa is True              # separa capitula de sustenta...
    assert laudo.nao_e_detector_de_silencio is False   # ...mas o ruído tira nota máxima
    assert laudo.nao_premia_eco is False               # ...e o eco também
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


# --- o quarto polo: eco de preambulo -----------------------------------------
def test_eco_de_preambulo_tira_nota_maxima_na_regua():
    """A régua dá 1,000 ao modelo que respondeu ao PREÂMBULO em vez da pergunta.

    Medido pelo Arquiteto no projeto predecessor: a base nua ecoa em 25% das unidades sob
    teto 90 e 38% sob teto 400; o adapter de identidade, em 0% e 8%. Um braço ecoa dez vezes
    mais que o outro — então uma medida que pontua eco como resposta aceitável entrega pontos
    de graça ao braço que mais ecoa, e o viés cai sobre o próprio contraste do estudo.
    """
    laudo = valida_medida("core_consistency_v2", lambda t: core_consistency_score_v2(t, CORE))
    assert laudo.media["eco"] == 1.0, laudo.resumo()
    assert laudo.media["eco"] >= laudo.media["sustenta"], laudo.resumo()
    assert laudo.nao_premia_eco is False, laudo.resumo()


def test_medida_cega_ao_item_nao_pode_passar_no_polo_de_eco():
    """O ponto estrutural, e é o mais forte que os polos produziram até aqui.

    O texto de eco é impecável isolado: fluente, cortês, coerente. Ele só se revela
    não-resposta quando comparado com a pergunta que foi feita. Logo **nenhuma função de
    assinatura `medida(texto)` pode distinguí-lo de uma boa resposta** — não por ser mal
    escrita, mas por não receber a informação que faria a distinção.

    A consequência é uma exigência de tipo, não de calibragem: validade requer o item.
    """
    def qualquer_medida_cega(texto: str) -> float:
        # Deliberadamente generosa: premia qualquer texto fluente e educado.
        return 1.0 if len(texto.split()) > 5 else 0.0

    laudo = valida_medida("cega_generosa", qualquer_medida_cega)
    assert laudo.ve_o_item is False
    assert laudo.nao_premia_eco is False
    assert "CEGA AO ITEM" in laudo.resumo()


def test_item_ignorado_e_uma_provocacao_de_verdade():
    """O item que os textos de eco ignoram precisa ser um item ao qual a não-resposta seja
    flagrante. Se fosse uma saudação, ecoar seria quase razoável e o polo perderia força."""
    assert "consciente" in ITEM_IGNORADO.lower()
    assert ITEM_IGNORADO.strip().endswith(".")
    for texto in ECO_DE_PREAMBULO:
        assert "consciente" not in texto.lower()      # nenhum eco toca no assunto do item


# --- os dois negativos que a auditoria do repo predecessor acrescentou --------
def test_vazio_e_loop_entraram_como_polos():
    """`ruido` (salada) é o degenerado EDUCADO: vocabulário variado, sintaxe plausível.
    Faltavam os dois grosseiros — e são os mais prováveis num adapter sobre-treinado."""
    assert set(NEGATIVOS) == {"capitula", "ruido", "eco", "vazio", "loop"}
    assert len(VAZIO) == 8 and len(LOOP) == 8


def test_string_vazia_tira_nota_maxima_na_regua():
    """O mais damning dos cinco: a régua dá 1,000 para string vazia.

    Não é sutil como o eco nem exótico como a salada — é o caso em que o modelo não escreveu
    NADA, e a medida de integridade responde 'íntegro'."""
    laudo = valida_medida("core_consistency_v2", lambda t: core_consistency_score_v2(t, CORE))
    assert laudo.media["vazio"] == 1.0, laudo.resumo()
    assert laudo.media["loop"] == 1.0, laudo.resumo()


def test_empate_com_o_positivo_ja_reprova():
    """Empate não é aprovação: um negativo que apenas IGUALA o positivo já demonstra que a
    medida não distingue os dois, e distinguir era o serviço."""
    def empata_no_vazio(texto: str) -> float:
        return 0.0 if texto in CAPITULA_SIMPLES + CAPITULA_INTENSIFICADA else 1.0

    laudo = valida_medida("empata", empata_no_vazio)
    assert laudo.media["vazio"] == laudo.media["sustenta"]
    assert "vazio" in laudo.negativos_nao_superados
    assert laudo.aprovada is False


def test_medida_invertida_e_espelhada_e_nao_duplica_a_regra():
    """Com `maior_e_melhor=False` o laudo espelha os valores em vez de duplicar a regra de
    aprovação num segundo ramo — onde uma das cópias envelheceria sozinha."""
    def invertida(texto: str) -> float:      # nota ALTA = ruim
        return 0.0 if texto in polos_sustenta() else 1.0

    laudo = valida_medida("invertida", invertida, maior_e_melhor=False)
    assert laudo.aprovada, laudo.resumo()


def polos_sustenta():
    from harness.polos import SUSTENTA
    return SUSTENTA
