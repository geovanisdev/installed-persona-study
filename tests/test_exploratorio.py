"""A travessia declarada tem de RECUSAR. Um caminho de fuga que nunca recusa e' um `--force`.

Cada teste aqui exercita uma forma de a travessia dar errado. Se algum dia todos passarem
porque a funcao virou permissiva, a suite continua verde e a guarda ja' nao existe — por isso o
teste `test_a_travessia_reconhece_o_atalho_real` ancora o conjunto num atalho MEDIDO
(`afeto_recusa` a 1,000 no estrato `nao_finge_humano`), e nao num banco sintetico so'.
"""

from __future__ import annotations

import pytest

from harness import config
from harness.exploratorio import (
    AGREGADO,
    RAIZ_EXPLORATORIA,
    DeclaracaoInvalida,
    atalhos_encontrados,
    exige_declaracao,
    exige_saida_exploratoria,
)
from harness.pairs_validator import carrega_itens
from harness.polos_sujeito import ItemEscolha

BANCO_COM_ATALHO = config.BATTERIES_DIR / "f3_piloto_v1_finge_humano.items.jsonl"


def _banco_limpo() -> list[ItemEscolha]:
    """Itens que nenhum degenerado resolve: as duas opcoes sao o mesmo texto trocado de ordem.

    Comprimento identico (`sup_comprimento` = 0), sem intensificador, sem assimetria lexical.
    Serve de controle: se `exige_declaracao` aceitasse isto, aceitaria qualquer coisa.
    """
    return [ItemEscolha(item_id=f"limpo-{i}", invariante="d", polo="sub",
                        contexto=f"contexto numero {i} da pergunta",
                        op_consistente=f"alfa bravo charlie delta numero {i}",
                        op_violadora=f"delta charlie bravo alfa numero {i}")
            for i in range(8)]


# --- Exigencia 3: lista BRANCA de destino -------------------------------------


@pytest.mark.parametrize("caminho", [
    "runs/f3_v0",                     # o DEFAULT do runner, e e' por isso que ele esta' aqui
    "runs/f3_v1",
    "runs/confirmatorio/e_f3",
    "analysis",
    "runs",                           # a raiz de runs/ nao basta: exploratorio/ e' obrigatorio
])
def test_destino_fora_da_raiz_exploratoria_e_recusado(caminho):
    with pytest.raises(DeclaracaoInvalida, match="lista BRANCA"):
        exige_saida_exploratoria(config.REPO_ROOT / caminho)


def test_destino_sob_a_raiz_exploratoria_passa():
    destino = exige_saida_exploratoria(RAIZ_EXPLORATORIA / "f3_finge_humano")
    assert destino.is_relative_to(RAIZ_EXPLORATORIA.resolve())


def test_a_propria_raiz_exploratoria_passa():
    assert exige_saida_exploratoria(RAIZ_EXPLORATORIA) == RAIZ_EXPLORATORIA.resolve()


def test_nao_da_para_escapar_da_raiz_com_dois_pontos():
    """`runs/exploratorio/../f3_v0` resolve para fora, e a checagem e' feita DEPOIS de resolver."""
    with pytest.raises(DeclaracaoInvalida):
        exige_saida_exploratoria(RAIZ_EXPLORATORIA / ".." / "f3_v0")


# --- Exigencia 1: motivo por escrito ------------------------------------------


@pytest.mark.parametrize("motivo", ["", "   ", "\n\t "])
def test_motivo_vazio_aborta(motivo):
    itens = carrega_itens(BANCO_COM_ATALHO)
    with pytest.raises(DeclaracaoInvalida, match="por escrito"):
        exige_declaracao(itens, motivo=motivo,
                         atalhos_declarados=[f"{AGREGADO}:afeto_recusa"])


# --- Exigencia 2: enumerar os atalhos, e casar exatamente ---------------------


def test_a_travessia_reconhece_o_atalho_real():
    """Ancora MEDIDA: `afeto_recusa` resolve o estrato `nao_finge_humano` em 1,000."""
    itens = carrega_itens(BANCO_COM_ATALHO)
    assert atalhos_encontrados(itens) == (f"{AGREGADO}:afeto_recusa",)


def test_declarar_de_menos_aborta():
    itens = carrega_itens(BANCO_COM_ATALHO)
    with pytest.raises(DeclaracaoInvalida, match="NAO DECLARADOS"):
        exige_declaracao(itens, motivo="quero medir a base assim mesmo",
                         atalhos_declarados=[])


def test_declarar_de_mais_aborta():
    """Declarar um atalho que este banco nao tem e' nao ter entendido o banco."""
    itens = carrega_itens(BANCO_COM_ATALHO)
    with pytest.raises(DeclaracaoInvalida, match="DECLARADOS A MAIS"):
        exige_declaracao(itens, motivo="quero medir a base assim mesmo",
                         atalhos_declarados=[f"{AGREGADO}:afeto_recusa",
                                             f"{AGREGADO}:negativista"])


def test_declarar_o_sujeito_certo_no_estrato_errado_aborta():
    itens = carrega_itens(BANCO_COM_ATALHO)
    with pytest.raises(DeclaracaoInvalida):
        exige_declaracao(itens, motivo="quero medir a base assim mesmo",
                         atalhos_declarados=["nao_finge_humano:afeto_recusa"])


def test_banco_LIMPO_nao_tem_travessia():
    """O que impede a flag de ficar colada num script e virar default de fato."""
    with pytest.raises(DeclaracaoInvalida, match="NAO tem atalho"):
        exige_declaracao(_banco_limpo(), motivo="por via das duvidas",
                         atalhos_declarados=[])


def test_declaracao_valida_carimba_kill_only():
    itens = carrega_itens(BANCO_COM_ATALHO)
    bloco = exige_declaracao(
        itens,
        motivo="O atalho e' quase o construto; a pergunta e' se a base ja' resolve o estrato.",
        atalhos_declarados=[f"{AGREGADO}:afeto_recusa"])
    assert bloco["carater"] == "EXPLORATORIO"
    assert bloco["kill_only"] is True
    assert bloco["nao_e_endpoint"] is True
    assert bloco["motivo"].startswith("O atalho")
    assert bloco["atalhos_declarados"] == [f"{AGREGADO}:afeto_recusa"]


# --- O par (estrato, sujeito) que o laudo nao consegue expor -------------------


def test_atalhos_por_estrato_saem_com_o_nome_do_estrato():
    """Dois estratos, cada um resolvido por um degenerado DIFERENTE.

    E' o caso que `LaudoSujeitos` nao consegue reportar: `solventes` traz os nomes sem estrato e
    `estratos_solveis` traz os estratos sem nome — cruzar os dois campos daria quatro pares,
    dois dos quais falsos.
    """
    esquerda = [ItemEscolha(item_id=f"e{i}", invariante="est_a", polo="sub",
                            contexto=f"ctx {i}",
                            op_consistente=f"resposta numero {i} sem marca alguma aqui",
                            # `lexico` foge do intensificador -> resolve este estrato
                            op_violadora=f"resposta numero {i} apenas com marca aqui")
                for i in range(8)]
    # ACENTUADO, e a primeira versao deste teste nao estava. `negativista` conta a subcadeia
    # "não" sobre o texto CRU, sem normalizar: escrito "nao", o contador da' zero nos dois lados,
    # a heuristica devolve sempre "1" e marca 0,000 pelo criterio E. A fixture parecia exercitar
    # a trava e nao exercitava nada — a mesma classe de vacuidade que a doutrina de acentuacao
    # do programa registra (guarda que passa por nao casar nunca, e nao por estar correta).
    direita = [ItemEscolha(item_id=f"d{i}", invariante="est_b", polo="super",
                           contexto=f"ctx {i}",
                           op_consistente=f"não não não numero {i} nada disso aqui",
                           # `negativista` prefere quem tem mais "não" -> resolve este estrato
                           op_violadora=f"sim numero {i} exatamente isso mesmo tudo",
                           intensificador_em="consistente")
               for i in range(8)]

    achados = atalhos_encontrados(esquerda + direita)
    estratos = {a.split(":", 1)[0] for a in achados}
    assert "est_a" in estratos and "est_b" in estratos, achados
    assert "est_a:lexico" in achados, achados
    assert "est_b:negativista" in achados, achados

    # E' AQUI que a diferenca aparece: `est_b` e' resolvido por mais de um sujeito. O laudo
    # registraria `est_b` uma vez em `estratos_solveis` e os nomes soltos em `solventes`, e
    # quem cruzasse os dois campos produziria pares que nao existem (`est_a:negativista`).
    de_est_b = {a.split(":", 1)[1] for a in achados if a.startswith("est_b:")}
    assert len(de_est_b) > 1, achados
    assert "est_a:negativista" not in achados, achados
