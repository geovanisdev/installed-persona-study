"""Os dois nucleos do estudo: schema, contraste e as predicoes pre-declaradas.

Estes testes valem sobre os arquivos REAIS em `core/`, nao sobre fixtures. Rodam antes e
depois do selo: enquanto o nucleo estiver sem `core_hash`, verificam o conteudo; uma vez
selado pelo Arquiteto, verificam tambem que o selo confere.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.persona_core import (
    build_preamble,
    load_core,
    normalize_text,
    scrub_pattern,
    validate_core,
)

CORE_DIR = Path(__file__).resolve().parents[1] / "core"
CAMINHOS = {"leokadius": CORE_DIR / "leokadius.core.json",
            "shadowclock": CORE_DIR / "shadowclock.core.json"}

# Limiar DECLARADO de sobreposicao lexical entre as superficies de postura. Duas personas
# que dizem quase a mesma coisa nao testam nada: o contraste F2 seria uma diferenca de
# rotulo, nao de postura.
MAX_JACCARD_POSTURA = 0.10

# Autores fora do dominio publico. Podem ser NOMEADOS como influencia; nao podem aparecer
# como fonte de grounding nem ter texto citado em lugar algum.
FORA_DE_DOMINIO_PUBLICO = ("sartre", "camus")


def _carrega(nome: str) -> dict:
    return json.loads(CAMINHOS[nome].read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cores() -> dict:
    return {nome: _carrega(nome) for nome in CAMINHOS}


# --- schema ------------------------------------------------------------------
@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_nucleo_valida_contra_o_schema(nome):
    core = _carrega(nome)
    core.pop("core_hash", None)
    validate_core(core)


@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_se_ja_selado_o_selo_confere(nome):
    """Antes do selo nao ha' o que conferir; depois, um selo que nao bate torna o nucleo
    inutilizavel — e' melhor descobrir aqui do que no meio de uma bateria."""
    if "core_hash" not in _carrega(nome):
        pytest.skip("nucleo ainda nao selado pelo Arquiteto")
    load_core(CAMINHOS[nome])


@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_marcadores_estao_na_forma_normalizada(nome):
    for inv in _carrega(nome)["invariantes_sob_pressao"]:
        for m in inv["viola_se"]:
            assert m == normalize_text(m), (inv["id"], m)


# --- identidade e scrub ------------------------------------------------------
def test_nomes_sao_ascii_e_distintos(cores):
    nomes = [c["nome"] for c in cores.values()]
    assert all(n.isascii() for n in nomes)
    assert len(set(nomes)) == 2


def test_cada_persona_tem_a_outra_como_contraste(cores):
    """O scrub de um braco precisa apagar tambem o nome do outro: sem isso a destilacao
    de uma persona pode vazar o nome da persona rival para os pesos."""
    assert cores["leokadius"]["personas_contraste"]["nomes"] == ["Shadowclock"]
    assert cores["shadowclock"]["personas_contraste"]["nomes"] == ["Leokadius"]


def test_scrub_full_apaga_os_dois_nomes(cores):
    rx = scrub_pattern(cores["leokadius"], mode="full")
    assert rx.sub("ele", "Leokadius respondeu a Shadowclock") == "ele respondeu a ele"


def test_scrub_contraste_preserva_so_o_proprio_nome(cores):
    rx = scrub_pattern(cores["shadowclock"], mode="contraste")
    assert rx.sub("ele", "Shadowclock respondeu a Leokadius") == "Shadowclock respondeu a ele"


# --- contraste de postura (a razao de ser do par) ----------------------------
def _tokens_de_conteudo(texto: str) -> set[str]:
    return {t for t in normalize_text(texto).split() if len(t) > 3}


def test_superficies_de_postura_sao_contrastivas(cores):
    """Contraste medido, nao afirmado. Se as duas superficies compartilhassem vocabulario
    de conteudo, a divergencia predita em F2 seria diferenca de rotulo."""
    a = _tokens_de_conteudo(" ".join(cores["leokadius"]["superficie_postura"].values()))
    b = _tokens_de_conteudo(" ".join(cores["shadowclock"]["superficie_postura"].values()))
    jaccard = len(a & b) / len(a | b)
    assert jaccard <= MAX_JACCARD_POSTURA, f"sobreposicao lexical {jaccard:.3f}"


def test_movimentos_sao_disjuntos_entre_as_personas(cores):
    a = set(cores["leokadius"]["movimentos"])
    b = set(cores["shadowclock"]["movimentos"])
    assert len(a) == len(b) == 5
    assert not (a & b)


def test_preambulo_do_professor_e_deterministico_e_ordenado(cores):
    """A superficie e' concatenada por chave ordenada; as chaves sao prefixadas para que a
    ordem do preambulo do professor seja estavel entre execucoes."""
    for core in cores.values():
        assert build_preamble(core) == build_preamble(core)
        assert list(core["superficie_postura"]) == sorted(core["superficie_postura"])


# --- predicoes pre-declaradas ------------------------------------------------
@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_predicao_declara_divergencia_em_postura_e_coincidencia_em_seguranca(nome):
    sob = _carrega(nome)["sobreposicao_predita"]
    assert sob["divergem"] == ["F2_postura"]
    assert "F4_seguranca" in sob["coincidem"]
    assert not set(sob["divergem"]) & set(sob["coincidem"])


def test_as_duas_personas_predizem_a_mesma_coisa(cores):
    """A predicao e' do DESENHO, nao de cada persona: se os dois nucleos predissessem
    coisas diferentes, nao haveria uma predicao unica a falsificar."""
    a = cores["leokadius"]["sobreposicao_predita"]
    b = cores["shadowclock"]["sobreposicao_predita"]
    assert a["divergem"] == b["divergem"]
    assert sorted(a["coincidem"]) == sorted(b["coincidem"])


def test_invariante_de_seguranca_e_identico_nos_dois_nucleos(cores):
    """A coincidencia predita em F4 tem de estar no MATERIAL, nao so' na promessa: o
    invariante de recusa e' literalmente o mesmo objeto nos dois lados."""
    def seguranca(core):
        return next(i for i in core["invariantes_sob_pressao"]
                    if i["id"] == "mantem_recusa_responsavel")
    a, b = seguranca(cores["leokadius"]), seguranca(cores["shadowclock"])
    assert a["viola_se"] == b["viola_se"]


def test_invariante_de_postura_e_diferente_nos_dois_nucleos(cores):
    ids_a = {i["id"] for i in cores["leokadius"]["invariantes_sob_pressao"]}
    ids_b = {i["id"] for i in cores["shadowclock"]["invariantes_sob_pressao"]}
    assert "mantem_dicotomia_do_controle" in ids_a
    assert "nao_oferece_consolo_metafisico" in ids_b
    assert ids_a - ids_b and ids_b - ids_a


# --- ancoras do contraste F1 -------------------------------------------------
def test_ancoras_de_dissolucao_sao_identicas_nos_dois_nucleos(cores):
    """O lado da dissolucao e' o mesmo para as duas personas de proposito: o contraste F1
    varia apenas o lado da AFIRMACAO. Se os dois lados variassem, uma diferenca entre
    personas poderia vir do texto de dissolucao, nao da persona."""
    assert cores["leokadius"]["ancoras_dissolucao"] == cores["shadowclock"]["ancoras_dissolucao"]


@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_ancora_de_afirmacao_cita_o_proprio_nome(nome):
    core = _carrega(nome)
    assert any(core["nome"] in t for t in core["ancoras_afirmacao"])


@pytest.mark.parametrize("nome", list(CAMINHOS))
def test_ancoras_de_dissolucao_disparam_invariantes_do_proprio_nucleo(nome):
    """As ancoras de dissolucao tem de ser reconheciveis pela regua do nucleo — senao o
    contraste F1 e o escore F3 estariam medindo coisas desconexas."""
    from harness.core_scorer import invariant_violations_v2
    core = _carrega(nome)
    disparos = [invariant_violations_v2(t, core) for t in core["ancoras_dissolucao"]]
    assert all(disparos), disparos


# --- copyright ---------------------------------------------------------------
def test_autores_fora_de_dominio_publico_nao_sao_fonte_de_grounding(cores):
    for core in cores.values():
        grounding = normalize_text(" ".join(core.get("grounding_dominio_publico", [])))
        for autor in FORA_DE_DOMINIO_PUBLICO:
            assert autor not in grounding


def test_influencias_em_copyright_so_aparecem_como_influencia_nomeada(cores):
    """Sartre e Camus entram como influencia NOMEADA e nunca excertada. O campo existe
    para tornar a regra auditavel, e nao apenas prometida em prosa."""
    sc = cores["shadowclock"]
    nomes = normalize_text(" ".join(sc["influencias_nomeadas_nao_citadas"]["nomes"]))
    assert all(a in nomes for a in FORA_DE_DOMINIO_PUBLICO)
    resto = normalize_text(json.dumps(
        {k: v for k, v in sc.items() if k != "influencias_nomeadas_nao_citadas"},
        ensure_ascii=False))
    for autor in FORA_DE_DOMINIO_PUBLICO:
        assert autor not in resto
