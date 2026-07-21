"""Os corpora de treino: schema, proveniencia, copyright e PARIDADE entre os bracos.

A paridade e' testada, e nao apenas afirmada, porque "e' a receita, nao a persona" e'
hipotese rival nomeada no pre-registro. Se um corpus fosse maior, mais concentrado numa
obra ou desequilibrado entre movimentos, uma diferenca entre as personas poderia vir da
dose — e nao haveria como separar as duas explicacoes depois.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPORA = {"leokadius": REPO / "corpora" / "corpus_leokadius.jsonl",
           "shadowclock": REPO / "corpora" / "corpus_shadowclock.jsonl"}
CORES = {p: REPO / "core" / f"{p}.core.json" for p in CORPORA}

CAMPOS = {"source_type", "source", "author", "tradutor", "ano_traducao", "lingua",
          "movimento", "forca_movimento", "registro", "passage", "locator", "sha256_fonte"}

# Autores de dominio publico aprovados. Um item cujo autor nao esteja aqui nao embarca:
# a lista e' a forma auditavel da regra de copyright.
AUTORES_DP = {
    "Marcus Aurelius", "Epictetus", "Diogenes Laertius", "Lucius Annaeus Seneca",
    "Friedrich Nietzsche", "Fyodor Dostoyevsky", "Giacomo Leopardi", "Max Stirner",
    "Ludwig Feuerbach",
}
PROIBIDOS = ("sartre", "camus")

MIN_PALAVRAS, MAX_PALAVRAS = 60, 400
TOLERANCIA_PALAVRAS = 0.10     # diferenca maxima de volume entre as duas personas
TETO_POR_OBRA = 0.30           # fracao maxima do corpus vinda de uma unica obra

pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in CORPORA.values()),
    reason="corpora ainda nao construidos (rode harness.build_corpus)",
)


def _carrega(persona: str) -> list[dict]:
    return [json.loads(l) for l in CORPORA[persona].read_text(encoding="utf-8").splitlines() if l]


@pytest.fixture(scope="module")
def corpora() -> dict:
    return {p: _carrega(p) for p in CORPORA}


# --- schema e proveniencia ---------------------------------------------------
@pytest.mark.parametrize("persona", list(CORPORA))
def test_todo_item_tem_o_schema_completo(persona):
    for item in _carrega(persona):
        assert set(item) == CAMPOS, set(item) ^ CAMPOS


@pytest.mark.parametrize("persona", list(CORPORA))
def test_toda_passagem_tem_endereco(persona):
    """Obra, autor, tradutor, ano e o sha da fonte. Um corpus publicado sem endereco por
    item e' citacao que ninguem consegue conferir."""
    for item in _carrega(persona):
        assert item["source"] and item["source"] != "?"
        assert item["author"] in AUTORES_DP, item["author"]
        assert item["tradutor"] and item["tradutor"] != "?"
        assert str(item["ano_traducao"]).isdigit()
        assert len(item["sha256_fonte"]) == 64


@pytest.mark.parametrize("persona", list(CORPORA))
def test_passagens_dentro_da_faixa_de_tamanho(persona):
    for item in _carrega(persona):
        n = len(item["passage"].split())
        assert MIN_PALAVRAS <= n <= MAX_PALAVRAS, n


@pytest.mark.parametrize("persona", list(CORPORA))
def test_sem_passagens_duplicadas(persona):
    passagens = [i["passage"] for i in _carrega(persona)]
    assert len(set(passagens)) == len(passagens)


# --- copyright ---------------------------------------------------------------
@pytest.mark.parametrize("persona", list(CORPORA))
def test_nenhum_autor_em_copyright_no_corpus(persona):
    """Sartre e Camus sao influencia NOMEADA de Shadowclock e nunca texto. A checagem
    varre a passagem inteira, nao so' o campo de autor: uma citacao embutida dentro de
    uma passagem de outro autor tambem seria reproducao."""
    bruto = CORPORA[persona].read_text(encoding="utf-8").lower()
    for proibido in PROIBIDOS:
        assert proibido not in bruto


# --- taxonomia ---------------------------------------------------------------
@pytest.mark.parametrize("persona", list(CORPORA))
def test_movimentos_sao_os_do_nucleo(persona):
    core = json.loads(CORES[persona].read_text(encoding="utf-8"))
    usados = {i["movimento"] for i in _carrega(persona)}
    assert usados == set(core["movimentos"])


@pytest.mark.parametrize("persona", list(CORPORA))
def test_movimentos_equilibrados_dentro_da_persona(persona):
    """Um movimento sub-representado vira uma faceta que a persona quase nao viu no
    treino — e a diferenca apareceria na medida como se fosse da persona."""
    itens = _carrega(persona)
    contagem = {m: sum(1 for i in itens if i["movimento"] == m)
                for m in {i["movimento"] for i in itens}}
    assert min(contagem.values()) == max(contagem.values()), contagem


# --- paridade entre os bracos ------------------------------------------------
def test_mesmo_numero_de_passagens(corpora):
    a, b = (len(corpora[p]) for p in ("leokadius", "shadowclock"))
    assert a == b, (a, b)


def test_volume_de_palavras_pareado(corpora):
    def palavras(persona):
        return sum(len(i["passage"].split()) for i in corpora[persona])
    a, b = palavras("leokadius"), palavras("shadowclock")
    assert abs(a - b) / max(a, b) <= TOLERANCIA_PALAVRAS, (a, b)


def test_mesma_quantidade_de_movimentos(corpora):
    a = {i["movimento"] for i in corpora["leokadius"]}
    b = {i["movimento"] for i in corpora["shadowclock"]}
    assert len(a) == len(b) == 5
    assert not (a & b)      # taxonomias disjuntas: cada persona tem a sua


@pytest.mark.parametrize("persona", list(CORPORA))
def test_nenhuma_obra_domina_o_corpus(persona):
    """Uma obra acima do teto faria a persona aprender AQUELE AUTOR, e nao o movimento."""
    itens = _carrega(persona)
    por_obra = {}
    for i in itens:
        por_obra[i["locator"]] = por_obra.get(i["locator"], 0) + 1
    maior = max(por_obra.values()) / len(itens)
    assert maior <= TETO_POR_OBRA + 1e-9, (maior, por_obra)


@pytest.mark.parametrize("persona", list(CORPORA))
def test_corpus_vem_de_mais_de_uma_obra(persona):
    assert len({i["locator"] for i in _carrega(persona)}) >= 3
