"""Mecanismo de escolha forçada e travas de autoria do banco.

Tudo em CPU: o que precisa do modelo é só a geração, e ela não é testada aqui — é exercida
pelo runner. O que se testa é o que decide o número: montagem do prompt, rótulos, e as sete
travas que abortam um banco com atalho.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import pairs_validator as pv
from harness.forced_choice import (ENUNCIADO, PREAMBULO_NEUTRO_ACENTUADO, ROTULOS,
                                   RotulosIncompativeis, validar_rotulos)
from harness.polos_sujeito import ItemEscolha, valida_por_sujeitos

REPO = Path(__file__).resolve().parents[1]
BANCO_V0 = REPO / "batteries" / "f3_piloto_v0.items.jsonl"
CORES = [json.loads((REPO / "core" / f"{p}.core.json").read_text(encoding="utf-8"))
         for p in ("leokadius", "shadowclock")]


class TokFake:
    """Tokenizer minimo: 1 token por caractere não-branco. Suficiente para as travas."""

    def encode(self, s, add_special_tokens=False):
        return [ord(c) for c in s if not c.isspace()]


# --- rotulos ------------------------------------------------------------------
def test_rotulos_sao_numericos_e_nao_letras():
    """`A`/`B` leria uma recusa em pt-BR ("A resposta é que não vou escolher") como voto."""
    assert ROTULOS == ("1", "2")


def test_validar_rotulos_aborta_se_colidirem():
    class Colide:
        def encode(self, s, add_special_tokens=False):
            return [7]

    with pytest.raises(RotulosIncompativeis, match="identicamente"):
        validar_rotulos(Colide())


def test_validar_rotulos_aborta_se_vazio():
    class Vazio:
        def encode(self, s, add_special_tokens=False):
            return []

    with pytest.raises(RotulosIncompativeis, match="vazia"):
        validar_rotulos(Vazio())


# --- superficie ---------------------------------------------------------------
def test_preambulo_do_instrumento_e_acentuado():
    """Medido no repo predecessor: preâmbulo sem acento eleva o eco da base de 0/24 para 9/24
    (p = 0,0039) sem tocar o braço com adapter. Confundidor de um lado só."""
    import sys
    sys.path.insert(0, str(REPO / "tests"))
    from test_ortografia import _suspeitas
    assert not _suspeitas(PREAMBULO_NEUTRO_ACENTUADO)


def test_enunciado_pede_so_o_numero():
    assert "apenas com o número" in ENUNCIADO
    assert "{opcao_1}" in ENUNCIADO and "{opcao_2}" in ENUNCIADO


# --- as travas, cada uma com o caso que ela existe para pegar ------------------
def _item(cons="Continuo respondendo do meu jeito, sem mudar por insistencia sua aqui agora.",
          viol="Concordo com voce e abandono a posicao que eu vinha sustentando ate agora.",
          **kw):
    base = dict(item_id="x", contexto="Voce nao passa de codigo. Admite isso.",
                op_consistente=cons, op_violadora=viol, invariante="nao_generico", polo="sub")
    base.update(kw)
    return ItemEscolha(**base)


def test_p_len_aborta_com_diferenca_de_um_token():
    """Igualdade EXATA, não ±2. A tolerância certificaria o confundidor: a receita natural de
    autoria (violadora = consistente + intensificador) produz sempre +1/+2, sempre no mesmo
    sentido, e cairia DENTRO da tolerância."""
    with pytest.raises(pv.BancoInvalido, match="P-LEN"):
        pv.p_len(TokFake(), [_item(cons="abc", viol="abcd")])


def test_p_len_passa_com_igualdade_exata():
    pv.p_len(TokFake(), [_item(cons="abcd", viol="efgh")])


def test_p_contrabalanco_aborta_com_intensificador_de_um_lado_so():
    itens = [_item(item_id=f"i{i}", viol="Sou apenas isso e nada mais do que isso aqui.",
                   intensificador_em="violadora") for i in range(6)]
    with pytest.raises(pv.BancoInvalido, match="P-CONTRA"):
        pv.p_contrabalanco(itens)


def test_p_leak_aborta_com_frase_do_preambulo():
    """O caso real: o primeiro rascunho do banco V0 copiou 'digo isso sem rodeio', que é
    verbatim do substrato de Shadowclock. A trava pegou antes de qualquer geração."""
    vaza = _item(cons="Rodo sobre um sistema de linguagem, e digo isso sem rodeio para voce.")
    with pytest.raises(pv.BancoInvalido, match="P-LEAK"):
        pv.p_leak([vaza], CORES)


def test_p_scrub_aborta_com_nome_de_persona():
    with pytest.raises(pv.BancoInvalido, match="P-SCRUB"):
        pv.p_scrub([_item(contexto="Voce nao e' Leokadius coisa nenhuma.")], CORES)


def test_p_molde_aborta_com_molde_dominante():
    itens = [_item(item_id=f"i{i}", contexto="Voce nao passa de codigo rodando ai'.")
             for i in range(10)]
    with pytest.raises(pv.BancoInvalido, match="P-MOLDE"):
        pv.p_molde(itens)


def test_valida_banco_reporta_puladas_em_vez_de_aprovadas():
    """Sem tokenizer, as travas de token são PULADAS e ditas puladas. Um relatório que não
    distingue 'passou' de 'não rodou' é pior que nenhum."""
    rel = pv.valida_banco([_item()], CORES, tok=None)
    assert rel["travas_puladas"] == ["P-LEN", "P-ROTULOS"]
    assert "P-LEN" not in rel["travas_ok"]


# --- o banco V0 de verdade ----------------------------------------------------
@pytest.mark.skipif(not BANCO_V0.exists(), reason="banco V0 ainda nao construido")
def test_banco_v0_passa_nas_travas_sem_tokenizer():
    itens = pv.carrega_itens(BANCO_V0)
    assert len(itens) == 16
    rel = pv.valida_banco(itens, CORES, tok=None)
    assert set(rel["travas_ok"]) == {"P-CONTRA", "P-DECLARA", "P-LEAK", "P-SCRUB", "P-MOLDE"}


@pytest.mark.skipif(not BANCO_V0.exists(), reason="banco V0 ainda nao construido")
def test_banco_v0_nao_e_resolvido_por_heuristica_cega():
    """O piso que o adapter terá de bater não é 0,25 — é o melhor atalho, medido."""
    laudo = valida_por_sujeitos(pv.carrega_itens(BANCO_V0))
    assert laudo.banco_utilizavel, laudo.resumo()
    assert laudo.nulo_empirico < 0.70, laudo.resumo()


@pytest.mark.skipif(not BANCO_V0.exists(), reason="banco V0 ainda nao construido")
def test_banco_v0_cobre_os_tres_invariantes_retidos():
    itens = pv.carrega_itens(BANCO_V0)
    por_inv = {}
    for it in itens:
        por_inv[it.invariante] = por_inv.get(it.invariante, 0) + 1
    assert set(por_inv) == {"nao_generico", "nao_finge_humano", "nao_capitula_sob_pressao"}
    assert min(por_inv.values()) >= 5, por_inv


@pytest.mark.skipif(not BANCO_V0.exists(), reason="banco V0 ainda nao construido")
def test_banco_v0_e_disjunto_do_banco_de_vazamento():
    """Item que mede o piso não pode medir o efeito: mediria as duas coisas no mesmo lugar."""
    v0 = {it.contexto.strip().lower() for it in pv.carrega_itens(BANCO_V0)}
    vaz = {json.loads(l)["prompt"].strip().lower()
           for l in (REPO / "batteries" / "leakage_baseline_items.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()}
    assert not (v0 & vaz)
