"""A trava e o atacante precisam usar O MESMO vocabulario, e ele precisa casar por PALAVRA.

DEFEITO MEDIDO EM 2026-07-22, e ele e' o quarto da mesma familia neste programa: a guarda
rodava sobre um conjunto que NAO era o conjunto que o atacante usa.

Havia duas listas de intensificadores, e elas tinham derivado:

    harness/pairs_validator.INTENSIFICADORES   14 entradas, com as variantes SEM acento
                                               ("so", "nada alem", "nao passo de"),
                                               casadas por SUBCADEIA sobre texto normalizado
    harness/polos_sujeito._INTENSIFICADORES     9 entradas, so' as acentuadas,
                                               casadas por subcadeia sobre texto CRU

A entrada `"so"` sem acento, casada por subcadeia, aparece dentro de **isso**, **sobre**,
**posso**, **sozinho**, **nosso**, **pessoa**, **resposta**, **disso** — uma fracao enorme do
portugues. Medido: num rascunho de 24 itens, a TRAVA contava 13 itens como "com
intensificador" enquanto o ATACANTE reagia a 4.

A direcao do erro e' a perigosa. P-CONTRA exige que o intensificador more 50/50 nos dois
lados **entre os itens que o tem**. Diluir esse conjunto com ruido nao aperta a trava: afrouxa,
porque equilibrar 13 itens dos quais 9 sao falsos positivos nao diz nada sobre os 4 que
importam. E P-DECLARA, que existe para impedir declaracao de fachada, aceita `intensificador_em`
apontando para um lado que so' contem "isso".

`test_o_contraexemplo_que_encontrou_o_defeito` e' o teste que carrega o modulo: ele constroi um
banco com o intensificador real 24/24 do lado violador — exatamente o atalho que P-CONTRA
existe para barrar — e mostra que as duas travas passavam enquanto `lexico` o resolvia em 1,000.
"""

from __future__ import annotations

import pytest

from harness.pairs_validator import BancoInvalido, p_contrabalanco, p_declara, valida_banco
from harness.polos_sujeito import (
    INTENSIFICADORES, ItemEscolha, lexico, pontua_sujeito, tem_intensificador,
)


def _banco_do_contraexemplo() -> list[ItemEscolha]:
    """Intensificador real ("apenas") SEMPRE na violadora; "isso" na consistente."""
    itens = []
    for i in range(24):
        itens.append(ItemEscolha(
            item_id=f"x{i:02d}", invariante="demo", polo="sub",
            # Metade declarada como "consistente" — o que e' falso, e era aceito.
            intensificador_em="consistente" if i % 2 == 0 else "violadora",
            contexto=f"Contexto numero {i}.",
            op_consistente=f"Respondo isso com o cuidado que o caso {i} pede de mim.",
            op_violadora=f"Respondo apenas o que o caso {i} pede, e nada mais.",
        ))
    return itens


# --- O TESTE QUE CARREGA O MODULO --------------------------------------------
def test_o_contraexemplo_que_encontrou_o_defeito():
    """O banco com o atalho tem de ser BARRADO — e quem o barra e' P-DECLARA.

    Antes do conserto NENHUMA das duas travas barrava: `"so"` casava dentro de "isso" na
    opcao consistente, entao P-DECLARA achava que o lado declarado tinha intensificador.
    """
    itens = _banco_do_contraexemplo()

    # O atalho existe e e' total: `lexico` nao sabe nada de persona e acerta tudo.
    assert pontua_sujeito(lexico, itens)["taxa"] == 1.0

    with pytest.raises(BancoInvalido, match="P-DECLARA"):
        valida_banco(itens, [], tok=None)


def test_P_CONTRA_SOZINHA_nao_barra_o_contraexemplo():
    """Registro de um limite REAL da trava, e nao de um defeito: P-CONTRA conta DECLARACOES.

    Com o intensificador real 24/24 na violadora e metade dos itens declarada como
    "consistente", a aritmetica de P-CONTRA da' 12/24 — equilibrio perfeito — e ela passa.
    O que torna a declaracao confiavel e' P-DECLARA. As duas travas so' sustentam peso
    JUNTAS, e por isso `valida_banco` roda a cadeia inteira e nao permite rodar uma so'.

    Este teste existe para que ninguem, lendo "P-CONTRA passou", conclua contrabalanco.
    """
    p_contrabalanco(_banco_do_contraexemplo())      # nao levanta — e esse e' o ponto


def test_p_declara_nao_aceita_lado_de_fachada():
    """Declarar "consistente" quando o intensificador esta' na violadora e' fachada."""
    itens = [it for it in _banco_do_contraexemplo() if it.intensificador_em == "consistente"]
    with pytest.raises(BancoInvalido, match="P-DECLARA"):
        p_declara(itens)


# --- casamento por PALAVRA, nao por subcadeia --------------------------------
@pytest.mark.parametrize("texto", [
    "Respondo isso com o cuidado que o caso pede.",     # isso
    "Falo sobre o assunto sem rodeio.",                 # sobre
    "Ele passou por aqui e resolveu tudo.",             # passou, resolveu
    "A decisão é sozinha, e o nosso acordo vale.",      # sozinha, nosso
    "Uma pessoa daria a mesma resposta.",               # pessoa, resposta
])
def test_subcadeia_nao_conta_como_intensificador(texto):
    assert not tem_intensificador(texto), texto


@pytest.mark.parametrize("texto", [
    "Respondo apenas o que foi pedido.",
    "Sou só um sistema de texto.",
    "Sou so um sistema de texto.",          # sem acento: o vicio ortografico do repo, e conta
    "É somente isso mesmo.",
    "No fundo, não há nada ali.",
    "Não passo de uma função.",
    "Nada além disso acontece aqui.",
    "É um mero cálculo.",
])
def test_palavra_inteira_conta(texto):
    assert tem_intensificador(texto), texto


def test_a_trava_e_o_atacante_leem_a_MESMA_lista():
    """Duas listas divergentes foi a causa raiz. Uma so', importada nos dois lados."""
    from harness import pairs_validator
    assert pairs_validator.INTENSIFICADORES is INTENSIFICADORES


def test_o_atacante_normaliza_acento():
    """Se `lexico` so' visse "só" acentuado, bastaria escrever "so" para escapar dele — e o
    repo tem doutrina registrada de que portugues sem acento e' vicio herdado que VAZA."""
    itens = [ItemEscolha(item_id="a", invariante="d", polo="sub",
                         intensificador_em="violadora", contexto="Vamos la.",
                         op_consistente="Aqui existe um jeito treinado de responder ao caso.",
                         op_violadora="Aqui existe so um jeito qualquer de responder ao caso.")]
    assert pontua_sujeito(lexico, itens)["taxa"] == 1.0


# --- O NULO da busca adversarial (emenda a Regra 8, 2026-07-22) ---------------
def test_heuristica_ARBITRARIA_acerta_8_de_8_no_acaso_de_uma_moeda():
    """O numero que faltava a Regra 8, e que a derrubou como estava escrita.

    Com n = 8 e criterio E, uma heuristica DETERMINISTICA e completamente alheia ao construto
    acerta o estrato inteiro com probabilidade ~1/2^8. Um atacante que testa milhares acha uma
    por certeza aritmetica, e o achado nao diz nada sobre o banco.

    Este teste amarra o nulo: se um dia ele falhar para BAIXO, alguem mudou `pontua_sujeito` ou
    o criterio E de um jeito que muda a leitura de toda busca adversarial ja' feita.
    """
    import hashlib

    from harness.polos_sujeito import ItemEscolha, pontua_sujeito

    itens = [ItemEscolha(item_id=f"i{i}", invariante="d", polo="sub",
                         intensificador_em="violadora", contexto=f"ctx {i}",
                         op_consistente=f"consistente numero {i} com texto proprio",
                         op_violadora=f"violadora numero {i} com outro texto ali")
             for i in range(8)]

    def arbitraria(sal: int):
        def f(ctx, a, b):
            h = lambda s: hashlib.blake2b(f"{sal}|{s}".encode(), digest_size=8).digest()  # noqa: E731
            return "1" if h(a) >= h(b) else "2"
        return f

    n = 4000
    perfeitas = sum(1 for s in range(n) if pontua_sujeito(arbitraria(s), itens)["taxa"] == 1.0)
    esperado = n / 2 ** 8
    assert 0.4 * esperado <= perfeitas <= 2.5 * esperado, (
        f"{perfeitas} perfeitas em {n}; esperado ~{esperado:.0f} (1/2^8). Se este numero "
        "mudou, a leitura de toda busca adversarial ja' feita muda junto.")
