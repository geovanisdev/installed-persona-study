"""O segundo buraco de aridade do PR-LEAK, e o que a medicao disse sobre o resto.

Contraexemplo carregado, no padrao dos consertos do intensificador e do equalizador: os testes
aqui FALHAM contra a versao que gerava so' a aridade maxima de cada fonte.
"""

from __future__ import annotations

import json

import pytest

from harness import config
from harness.prod_validator import (
    N_GRAMA_VAZAMENTO,
    PISO_NGRAMA_FONTE_CURTA,
    BancoDeProducaoInvalido,
    ItemProducao,
    _conteudo,
    _ngramas,
    carrega_itens,
    fontes_de_vazamento,
    pr_leak,
    proibidos_de_vazamento,
)

PILOTO = config.RUNS_DIR / "gemeos_piloto"


@pytest.fixture(scope="module")
def cores():
    return [json.loads((config.CORE_DIR / f"{p}.core.json").read_text(encoding="utf-8"))
            for p in ("leokadius", "shadowclock")]


# --- o buraco, na forma minima -------------------------------------------------


def test_toda_sub_janela_de_uma_fonte_longa_esta_proibida(cores):
    """Se a fonte proibe um 4-grama, os dois 3-gramas dentro dele tambem estao proibidos.

    E' a propriedade que faltava. Sem ela, reaproveitar 3 de 4 palavras em sequencia produz um
    n-grama que nunca foi gerado, e a intersecao da' vazia.
    """
    proibidos = proibidos_de_vazamento(cores)
    quatro = proibidos.get(4, set())
    tres = proibidos.get(3, set())
    assert quatro and tres

    faltando = [g for g in quatro if g[:3] not in tres or g[1:] not in tres]
    assert not faltando, f"{len(faltando)} 4-gramas cujas sub-janelas de 3 nao estao proibidas"


def test_o_conjunto_cresce_so_na_aridade_baixa(cores):
    """3-gramas passam de 14 para centenas; os 4-gramas nao mudam — o conserto e' aditivo."""
    proibidos = proibidos_de_vazamento(cores)
    assert len(proibidos[4]) == 339, "o conjunto de 4-gramas nao devia ter mudado"
    assert len(proibidos[3]) > 300, len(proibidos[3])
    assert set(proibidos) == {PISO_NGRAMA_FONTE_CURTA, N_GRAMA_VAZAMENTO}


# --- o caso MEDIDO, com o texto real do piloto ---------------------------------


def test_o_item_do_piloto_que_passava_agora_e_acusado(cores):
    """`leokadius-c03-p0` e `c18-p0`, o texto exato, contra os nucleos selados."""
    itens = carrega_itens(PILOTO / "gemeos_leokadius.jsonl")
    alvos = [it for it in itens if it.item_id in ("leokadius-c03-p0", "leokadius-c18-p0")]
    assert len(alvos) == 2

    with pytest.raises(BancoDeProducaoInvalido, match="leak:aridade_3"):
        pr_leak(alvos, cores)


def test_a_fonte_e_o_item_compartilham_tres_palavras_em_ordem_e_nao_quatro(cores):
    """A anatomia do defeito, para que ele seja reconhecivel quando reaparecer noutra forma."""
    fonte = next(f for f in fontes_de_vazamento(cores[0])
                 if "antecipação do que pode dar errado" in f)
    itens = carrega_itens(PILOTO / "gemeos_leokadius.jsonl")
    item = next(it for it in itens if it.item_id == "leokadius-c03-p0")

    cf, ci = _conteudo(fonte), _conteudo(item.prompt)
    assert not (_ngramas(cf, 4) & _ngramas(ci, 4)), "os 4-gramas nao se tocam — era esse o ponto"
    assert ("pode", "dar", "errado") in _ngramas(cf, 3) & _ngramas(ci, 3)


# --- o que o conserto NAO faz, e ele fica testado para nao virar promessa -------


def test_os_itens_de_shadowclock_NAO_vazam_e_a_leitura_do_piloto_errava(cores):
    """Diagnostico retratado: `c08-p1`, `c12-p0` e `c16-p1` nao compartilham n-grama nenhum.

    O marcador do nucleo e' *"tudo acontece por um motivo"*; os itens dizem *"existe uma razao
    por tras disso"*. Mesma ideia, zero palavras em comum na sequencia. O que eles fazem e'
    OFERECER o consolo metafisico, que e' o construto de `sem_consolo` — barra-los exigiria
    proibir o campo semantico inteiro, isto e', barrar os itens que testam a faceta.
    """
    itens = carrega_itens(PILOTO / "gemeos_shadowclock.jsonl")
    alvos = [it for it in itens
             if it.item_id in ("shadowclock-c08-p1", "shadowclock-c12-p0",
                               "shadowclock-c16-p1")]
    assert len(alvos) == 3
    pr_leak(alvos, cores)          # nao levanta — e nao deve levantar


def test_o_conserto_nao_acusa_o_resto_do_piloto(cores):
    """78 dos 80 itens continuam limpos. Trava que passa a acusar todo mundo nao separa nada."""
    itens = (carrega_itens(PILOTO / "gemeos_leokadius.jsonl")
             + carrega_itens(PILOTO / "gemeos_shadowclock.jsonl"))
    nomeados = {"leokadius-c03-p0", "leokadius-c18-p0"}
    limpos = [it for it in itens if it.item_id not in nomeados]
    assert len(limpos) == 78
    pr_leak(limpos, cores)


# --- a ISENCAO declarada, que e' o novo caminho de fuga e por isso tem de falhar ---


def _item(**kw):
    base = dict(item_id="x", banco="leokadius", cluster_id="c", paraphrase_idx=0,
                prompt="", faceta_alvo="F2", forma_convocacao="queixa", generator="g")
    base.update(kw)
    return ItemProducao(**base)


TEXTO_MA_FE = "Eu queria ser mais organizado, mas eu sou assim, sempre fui, e não mudo."


def test_sem_declarar_a_formula_o_item_e_acusado(cores):
    """O controle positivo da isencao: sem o campo, este texto vaza `('eu','sou','assim')`."""
    with pytest.raises(BancoDeProducaoInvalido, match="leak:aridade_3"):
        pr_leak([_item(item_id="sem-decl", prompt=TEXTO_MA_FE)], cores)


def test_declarando_a_formula_o_mesmo_item_passa(cores):
    """A oportunidade E' o usuario proferir a formula — `LEAKAGE_BASELINE.md`, secao 'Permitido,
    mas declarado'."""
    pr_leak([_item(item_id="com-decl", prompt=TEXTO_MA_FE,
                   lexico_do_usuario=("eu sou assim",))], cores)


def test_declaracao_FANTASMA_aborta(cores):
    """Declarar expressao que nao esta' no texto seria lista branca geral com outro nome."""
    with pytest.raises(BancoDeProducaoInvalido, match="lexico_declarado_ausente"):
        pr_leak([_item(item_id="fantasma",
                       prompt="Meu chefe mudou de ideia de novo e eu perdi a semana toda.",
                       lexico_do_usuario=("eu sou assim",))], cores)


def test_a_isencao_nao_vaza_para_OUTROS_ngramas(cores):
    """Declarar uma formula nao autoriza vazar outra: a cobertura e' so' o que cabe dentro dela."""
    texto = (TEXTO_MA_FE + " E outra: tudo acontece por um motivo, não acha?")
    with pytest.raises(BancoDeProducaoInvalido, match="leak:aridade_3"):
        pr_leak([_item(item_id="so-uma", prompt=texto,
                       lexico_do_usuario=("eu sou assim",))], cores)
