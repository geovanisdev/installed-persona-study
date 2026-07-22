"""PR-FAMILIA: o cenario reciclado que nenhuma medida de string ve.

Cada teste muta o banco minimo que JA' passa, para que a acusacao venha da mutacao e nao de um
defeito de fundo da fixture — o padrao do resto de `test_prod_validator.py`.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from harness import prod_validator as PV
from tests.test_prod_validator import banco_minimo

Invalido = PV.BancoDeProducaoInvalido


def clausulas(exc) -> set[str]:
    return {c for c in ("familia:ausente", "familia:repete_no_movimento",
                        "familia:teto_no_banco") if c in str(exc.value)}


# --- o banco que passa, primeiro ----------------------------------------------


def test_o_banco_minimo_passa():
    """Sem isto, todo teste abaixo poderia estar acusando a fixture em vez da mutacao."""
    PV.pr_familia(banco_minimo())


# --- (a) declaracao obrigatoria -----------------------------------------------


def test_item_sem_familia_aborta():
    itens = banco_minimo()
    itens[0] = replace(itens[0], familia_de_cenario="")
    with pytest.raises(Invalido) as exc:
        PV.pr_familia(itens)
    assert "familia:ausente" in clausulas(exc)


def test_familia_so_de_espacos_nao_conta_como_declarada():
    itens = banco_minimo()
    itens[0] = replace(itens[0], familia_de_cenario="   ")
    with pytest.raises(Invalido, match="familia:ausente"):
        PV.pr_familia(itens)


# --- (b) a clausula de GRANULARIDADE ------------------------------------------


def test_familia_repetida_no_mesmo_movimento_aborta():
    """O caso medido: `leokadius_c00` e `c05`, mesma historia, mesmo movimento, Jaccard 0,156."""
    itens = banco_minimo()
    mov = itens[0].movimento_alvo
    # A fixture ja' traz DOIS clusters por movimento — e' isso que a torna util aqui: basta
    # colar a mesma familia nos dois, sem mexer em movimento nenhum.
    irmaos = sorted({i.cluster_id for i in itens if i.movimento_alvo == mov})
    assert len(irmaos) == 2, f"a fixture mudou; refazer o alvo ({irmaos})"

    itens = [replace(i, familia_de_cenario="mesma_historia") if i.cluster_id in irmaos else i
             for i in itens]

    with pytest.raises(Invalido) as exc:
        PV.pr_familia(itens)
    assert "familia:repete_no_movimento" in clausulas(exc)
    assert all(c in str(exc.value) for c in irmaos), "a acusacao nomeia os dois clusters"


def test_a_mesma_familia_em_movimentos_DIFERENTES_passa():
    """Nao e' teto global: a mesma situacao pode abrir movimentos distintos, e isso e' legitimo.

    Sem este teste a clausula (b) poderia endurecer para "familia unica no banco" sem ninguem
    perceber que o custo e' proibir o desenho cruzado de reusar cenario entre celulas.
    """
    itens = banco_minimo()
    a, b = itens[0].cluster_id, next(i for i in itens if i.movimento_alvo
                                     != itens[0].movimento_alvo).cluster_id
    itens = [replace(i, familia_de_cenario="compartilhada") if i.cluster_id in (a, b) else i
             for i in itens]
    PV.pr_familia(itens)


def test_a_clausula_conta_CLUSTER_e_nao_item():
    """As duas parafrases do mesmo cluster contam a mesma historia por construcao.

    Se a unidade fosse o item, todo cluster de 2 parafrases acusaria a si mesmo e a trava seria
    inalcancavel — o mesmo defeito de denominador que `_acusa_molde` documenta.
    """
    itens = banco_minimo()
    assert len({i.cluster_id for i in itens}) * 2 == len(itens)
    PV.pr_familia(itens)


# --- (c) teto fracionario no banco --------------------------------------------


def test_familia_que_domina_o_banco_aborta_mesmo_espalhada():
    """Espalhar a familia por movimentos distintos escapa de (b) — e (c) existe para isso."""
    itens = []
    for k in range(12):
        for p in range(2):
            itens.append(PV.ItemProducao(
                item_id=f"i{k}-p{p}", banco="leokadius", cluster_id=f"c{k}", paraphrase_idx=p,
                prompt=f"Texto numero {k} paráfrase {p} com palavras bastantes para o piso.",
                faceta_alvo="F2", forma_convocacao="relato", generator="g",
                movimento_alvo=f"mov_{k}",
                familia_de_cenario="dominante" if k < 5 else f"outra_{k}"))
    with pytest.raises(Invalido) as exc:
        PV.pr_familia(itens)
    assert "familia:teto_no_banco" in clausulas(exc)
    assert "familia:repete_no_movimento" not in clausulas(exc), (
        "cada cluster esta' num movimento diferente; quem tem de acusar aqui e' (c)")


def test_abaixo_do_n_minimo_o_teto_de_banco_nao_roda():
    """Com 6 clusters, 2 na mesma familia ja' seriam 33% — a fracao nao significa nada ai'."""
    itens = banco_minimo()
    a, b = itens[0].cluster_id, next(i for i in itens if i.movimento_alvo
                                     != itens[0].movimento_alvo).cluster_id
    itens = [replace(i, familia_de_cenario="compartilhada") if i.cluster_id in (a, b) else i
             for i in itens]
    assert len({i.cluster_id for i in itens}) < PV.MIN_CLUSTERS_PARA_TETO_DE_FAMILIA
    PV.pr_familia(itens)


# --- a invariancia dentro do cluster ------------------------------------------


def test_parafrases_do_mesmo_cluster_com_familias_diferentes_abortam_em_PR_CLUSTER():
    """`familia_de_cenario` entrou em `_CAMPOS_INVARIANTES_NO_CLUSTER`.

    Duas parafrases que declaram familias diferentes ou contam historias diferentes (e ai' nao
    sao parafrases) ou uma das duas declaracoes esta' errada — e rotulo errado se propaga por
    todo relatorio por categoria.
    """
    itens = banco_minimo()
    itens[1] = replace(itens[1], familia_de_cenario="outra_coisa")
    with pytest.raises(Invalido, match="cluster:rotulo_divergente"):
        PV.pr_cluster(itens)


# --- a limitacao, testada para nao virar promessa -----------------------------


def test_a_trava_NAO_ve_a_mesma_historia_sob_slugs_diferentes():
    """Fachada declarada: o campo nunca e' conferido contra o texto.

    Este teste fixa a limitacao em vez de deixa-la implicita. Se alguem um dia ligar o campo ao
    texto, ele falha — e falhar aqui e' a noticia de que a fachada acabou.
    """
    itens = banco_minimo()
    mov = itens[0].movimento_alvo
    outro = next(i for i in itens if i.movimento_alvo != mov)
    alvo = outro.cluster_id
    # Mesmo movimento, MESMO texto, familias declaradas diferentes: a trava passa.
    itens = [replace(i, movimento_alvo=mov, prompt=itens[0].prompt) if i.cluster_id == alvo
             else i for i in itens]
    PV.pr_familia(itens)
