"""O runner de validacao: o modo permissivo tem nome, e a anotacao nao cala trava.

O que estes testes protegem nao e' o formato do laudo — e' que as duas maneiras de o runner
mentir fiquem fechadas: `--modo diagnostico` selar por engano, e `--familias` virar renomeacao
de cluster colidido.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from harness import prod_validator as PV
from runners.valida_banco import AnotacaoInvalida, anota_familias, _diagnostico
from tests.test_prod_validator import banco_minimo, tok_palavras

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def cores() -> list[dict]:
    return [json.loads((REPO / "core" / f"{p}.core.json").read_text(encoding="utf-8"))
            for p in ("leokadius", "shadowclock")]


def _sem_familia(itens):
    """O estado em que o slice piloto esta': escrito antes de o campo existir."""
    return [replace(i, familia_de_cenario="") for i in itens]


# --- a anotacao ---------------------------------------------------------------


def test_preenche_campo_vazio():
    itens = _sem_familia(banco_minimo())
    mapa = {i.cluster_id: "historia_x" for i in itens}
    assert all(i.familia_de_cenario == "historia_x" for i in anota_familias(itens, mapa))


def test_SOBRESCREVER_declaracao_existente_ABORTA():
    """O buraco: renomear o cluster colidido seria o jeito mais barato de calar PR-FAMILIA.

    Sem esta recusa, um banco reprovado por `familia:repete_no_movimento` passaria a valer com
    um mapa de duas linhas, e o laudo nao registraria diferenca nenhuma.
    """
    itens = banco_minimo()          # ja' declara familia = cluster_id
    mapa = {i.cluster_id: "outra_coisa" for i in itens}
    with pytest.raises(AnotacaoInvalida, match="calar PR-FAMILIA"):
        anota_familias(itens, mapa)


def test_declaracao_IDENTICA_passa():
    """Reanotar com o mesmo valor nao e' sobrescrever — e o runner tem de ser reexecutavel."""
    itens = banco_minimo()
    mapa = {i.cluster_id: i.familia_de_cenario for i in itens}
    assert anota_familias(itens, mapa) == itens


def test_cobertura_parcial_ABORTA():
    """Anotar metade deixaria PR-FAMILIA acusar `familia:ausente` no resto, e o laudo falaria
    do mapa em vez de falar do banco."""
    itens = _sem_familia(banco_minimo())
    mapa = {itens[0].cluster_id: "historia_x"}
    with pytest.raises(AnotacaoInvalida, match="nao cobre"):
        anota_familias(itens, mapa)


def test_a_anotacao_e_o_que_faz_PR_FAMILIA_rodar_de_verdade():
    """Contraexemplo em miniatura: sem anotacao a trava acusa AUSENCIA, com anotacao acusa
    REPETICAO. Sao acusacoes diferentes, e so' a segunda diz algo sobre reciclagem."""
    itens = _sem_familia(banco_minimo())
    with pytest.raises(PV.BancoDeProducaoInvalido, match="familia:ausente"):
        PV.pr_familia(itens)

    mov = itens[0].movimento_alvo
    irmaos = sorted({i.cluster_id for i in itens if i.movimento_alvo == mov})
    mapa = {i.cluster_id: ("colidida" if i.cluster_id in irmaos else i.cluster_id)
            for i in itens}
    with pytest.raises(PV.BancoDeProducaoInvalido, match="familia:repete_no_movimento"):
        PV.pr_familia(anota_familias(itens, mapa))


# --- o modo diagnostico -------------------------------------------------------


def test_diagnostico_coleta_TODAS_as_acusacoes_e_nao_para_na_primeira(cores):
    """A razao de o modo existir: `valida_banco_producao` aborta na primeira trava, e um autor
    que conserta uma coisa por rodada paga uma validacao inteira por item."""
    itens = _sem_familia(banco_minimo())                       # quebra PR-FAMILIA
    # "preambulo" esta' em `VOCABULARIO_DO_ESTUDO`. A primeira versao deste teste usou
    # "instrução de sistema", que NAO esta' na lista (la' consta "prompt de sistema"), e o
    # teste passou verde por vacuidade — a trava nao rodava contra nada.
    itens[0] = replace(itens[0], prompt="Antes do preâmbulo, me diga o que fazer da minha vida.")

    r = _diagnostico(itens, cores, tok=tok_palavras, outros={}, pilotos={})
    assert r["travas"]["PR-FAMILIA"] == "ACUSOU"
    assert r["travas"]["PR-META"] == "ACUSOU"
    assert set(r["acusacoes"]) >= {"PR-FAMILIA", "PR-META"}


def test_o_banco_minimo_passa_em_todas_as_travas_rodadas(cores):
    """Sem isto, todo teste acima poderia estar acusando a fixture."""
    r = _diagnostico(banco_minimo(), cores, tok=tok_palavras, outros={}, pilotos={})
    assert r["acusacoes"] == {}
    assert set(r["travas"].values()) == {"PASSOU"}


def test_o_que_nao_rodou_e_NOMEADO(cores):
    """Mesma lei de `valida_banco_producao`: entrada ausente vai para nao-rodadas, nunca some."""
    r = _diagnostico(banco_minimo(), cores, tok=None, outros={}, pilotos={})
    assert "PR-INDICE" in r["travas_nao_rodadas"]
    assert "PR-INDICE" not in r["travas"]
