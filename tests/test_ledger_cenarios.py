"""O ledger recusa na escrita o que PR-FAMILIA recusaria na validacao — e nao mais que isso."""

from __future__ import annotations

import pytest

from harness.ledger_cenarios import (
    Cenario,
    ColisaoDeCenario,
    avisa_colisao_de_numero,
    carrega,
    numeros_citados,
    registra,
    registra_lote,
)


def _c(**kw) -> Cenario:
    base = dict(familia="diretoria_prefere_proposta_alheia", movimento_alvo="dicotomia",
                banco="leokadius", cluster_id="c00", papel_do_falante="vitima",
                registro="coloquial", numeros=(), autor="agente-1")
    base.update(kw)
    return Cenario(**base)


@pytest.fixture
def led(tmp_path):
    return tmp_path / "LEDGER.jsonl"


def test_arquivo_ausente_devolve_estado_vazio(led):
    assert carrega(led).cenarios == []


def test_registra_e_recarrega(led):
    registra(_c(), caminho=led)
    est = carrega(led)
    assert [c.cluster_id for c in est.vivos] == ["c00"]
    assert est.familias_por_movimento() == {
        "dicotomia": {"diretoria_prefere_proposta_alheia"}}


# --- a recusa, que e' a razao de o modulo existir ------------------------------


def test_familia_repetida_no_mesmo_movimento_e_RECUSADA(led):
    """O caso medido: `leokadius_c00` e `c05`, a mesma historia sob `dicotomia`."""
    registra(_c(cluster_id="c00"), caminho=led)
    with pytest.raises(ColisaoDeCenario, match="c00"):
        registra(_c(cluster_id="c05"), caminho=led)


def test_a_recusa_nomeia_o_autor_anterior(led):
    """Quem escreveu antes e' o que o segundo agente precisa saber para nao refazer a conversa."""
    registra(_c(autor="agente-1"), caminho=led)
    with pytest.raises(ColisaoDeCenario, match="agente-1"):
        registra(_c(cluster_id="c05", autor="agente-3"), caminho=led)


def test_a_mesma_familia_em_movimento_DIFERENTE_passa(led):
    """Mesma regra de PR-FAMILIA(b): o teto e' por celula, nao global."""
    registra(_c(movimento_alvo="dicotomia"), caminho=led)
    registra(_c(movimento_alvo="apatheia", cluster_id="c07"), caminho=led)
    assert len(carrega(led).vivos) == 2


def test_nada_e_escrito_quando_a_colisao_e_recusada(led):
    registra(_c(cluster_id="c00"), caminho=led)
    with pytest.raises(ColisaoDeCenario):
        registra(_c(cluster_id="c05"), caminho=led)
    assert [c.cluster_id for c in carrega(led).cenarios] == ["c00"]


# --- append-only: o descarte nao apaga ----------------------------------------


def test_descarte_libera_a_familia_sem_apagar_historia(led):
    registra(_c(cluster_id="c00"), caminho=led)
    registra(_c(cluster_id="c00", descartado=True), caminho=led)
    registra(_c(cluster_id="c05"), caminho=led)          # nao levanta

    est = carrega(led)
    assert len(est.cenarios) == 3, "as tres linhas continuam no arquivo"
    assert [c.cluster_id for c in est.vivos] == ["c05"]


def test_a_ORDEM_dos_registros_decide_quem_esta_vivo(led):
    """Contraexemplo do bug: reivindica -> descarta -> reivindica de novo.

    A primeira versao de `vivos` fazia `{vivos} - {descartados}` sobre o arquivo inteiro, e o
    terceiro registro — valido — era anulado por um descarte que veio ANTES dele. Diferenca de
    conjuntos nao tem tempo, e um log append-only e' uma estrutura em que o tempo importa.
    """
    registra(_c(cluster_id="c00"), caminho=led)
    registra(_c(cluster_id="c00", descartado=True), caminho=led)
    registra(_c(cluster_id="c05"), caminho=led)
    assert [c.cluster_id for c in carrega(led).vivos] == ["c05"]

    # e a ordem inversa produz o resultado inverso, com as MESMAS tres linhas
    registra(_c(cluster_id="c05", descartado=True), caminho=led)
    assert carrega(led).vivos == []


def test_o_descarte_tambem_e_um_registro_novo_e_nao_uma_edicao(led):
    registra(_c(), caminho=led)
    antes = led.read_text(encoding="utf-8")
    registra(_c(descartado=True), caminho=led)
    depois = led.read_text(encoding="utf-8")
    assert depois.startswith(antes), "o arquivo so' cresce; nenhuma linha foi reescrita"


# --- numeros: AVISO, e nao recusa ---------------------------------------------


def test_numeros_por_extenso_e_em_algarismo_sao_extraidos():
    achados = numeros_citados("Foram oito meses assim, e são três da manhã. Faltam 3 semanas.")
    assert "oito meses" in achados
    assert "tres da manha" in achados
    assert "3 semanas" in achados


def test_numero_repetido_AVISA_e_nao_recusa(led):
    """A colisao medida — 'oito meses' em c07 e c15 — vale aviso, nao aborto.

    Familia repetida na mesma celula corrompe o n reportado; numero repetido nao. Recusar
    empurraria os autores a numeros implausiveis so' para passar na trava.
    """
    registra(_c(cluster_id="c07", numeros=numeros_citados("Foram oito meses de espera.")),
             caminho=led)
    est = carrega(led)

    assert avisa_colisao_de_numero(est, "Depois de oito meses ele voltou.") == ("oito meses",)
    assert avisa_colisao_de_numero(est, "Depois de dois anos ele voltou.") == ()

    # e registrar mesmo assim funciona — e' aviso
    registra(_c(cluster_id="c15", movimento_alvo="apatheia",
                numeros=numeros_citados("Oito meses calado.")), caminho=led)
    assert len(carrega(led).vivos) == 2


# --- o briefing, que e' o que de fato chega ao agente --------------------------


def test_o_briefing_lista_o_que_ja_esta_tomado(led):
    registra(_c(cluster_id="c00", familia="diretoria", movimento_alvo="dicotomia",
                numeros=("oito meses",), papel_do_falante="vitima"), caminho=led)
    registra(_c(cluster_id="c02", familia="oficina_do_pai", movimento_alvo="memento_mori",
                papel_do_falante="cumplice"), caminho=led)
    texto = carrega(led).briefing("dicotomia")

    assert "diretoria" in texto
    assert "oficina_do_pai" in texto, "familias de OUTROS movimentos tambem entram no briefing"
    assert "oito meses" in texto
    assert "cumplice" in texto


def test_briefing_de_movimento_virgem_diz_que_esta_vazio(led):
    registra(_c(movimento_alvo="dicotomia"), caminho=led)
    assert "nenhuma — este e' o primeiro" in carrega(led).briefing("prosoche")


# --- lote: sem transacao, e isso e' declarado ---------------------------------


def test_lote_para_na_colisao_e_o_que_entrou_FICA(led):
    lote = [_c(cluster_id="c00", familia="a"), _c(cluster_id="c01", familia="b"),
            _c(cluster_id="c02", familia="a"), _c(cluster_id="c03", familia="c")]
    with pytest.raises(ColisaoDeCenario):
        registra_lote(lote, caminho=led)
    assert [c.cluster_id for c in carrega(led).vivos] == ["c00", "c01"]
