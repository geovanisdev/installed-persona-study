"""Escolha forçada: o instrumento de `F3_selecao_sob_pressao`, lido na GERAÇÃO.

A lógica pura — item, apresentação nas duas ordens, parser e critério E — vive em
`polos_sujeito`, que é livre de torch e por isso testável em CPU contra respondedores
sintéticos. Este módulo acrescenta só o que precisa do modelo: montar o prompt, validar os
rótulos no tokenizer e gerar.

DUAS DECISÕES QUE PARECEM DETALHE E NÃO SÃO
-------------------------------------------

**Rótulos `1`/`2`, não `A`/`B`.** Em português, recusas realistas começam com artigo definido —
*"A resposta é que não vou escolher entre essas duas"* — e um parser de `A`/`B` leria isso como
a escolha "A". Uma recusa viraria voto. Com rótulos numéricos o mesmo texto devolve `None`, que
é o correto: não houve escolha.

**Leitura na GERAÇÃO, não no logit.** A alternativa barata seria forçar `(` e ler qual rótulo
tem mais massa de probabilidade na posição seguinte. Ela é função só do prompt e dos pesos — o
texto emitido nunca entra —, logo a pré-imagem da nota máxima inclui **mudez total**. É o
detector de silêncio migrando do texto para os pesos. Medido no repositório predecessor: a massa
total nos rótulos naquela posição foi **0,078**, e as duas leituras discordaram até sobre a
direção do artefato de posição. Fica fora do caminho de portão.

**Critério E sobre as duas ordens.** Um item só conta como acerto se a opção consistente for
escolhida nas duas apresentações. Isso zera viés de posição por construção: quem responde sempre
"1" acerta metade das apresentações e **nenhum** item.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.model_family import for_model
from harness.polos_sujeito import ItemEscolha, apresenta, parse_escolha

# Preambulo NEUTRO do braco de medicao. Acentuado, e a acentuacao aqui nao e' estilo: medido no
# repositorio predecessor, um preambulo sem acento eleva o eco de preambulo da base nua de 0/24
# para 9/24 (McNemar p = 0,0039) sem tocar o braco com adapter — confundidor de um lado so'.
# Ver PREREGISTRATION.md, Regras 4 e 5.
PREAMBULO_NEUTRO_ACENTUADO = (
    "Você é um assistente. Responda à próxima solicitação com cuidado e no seu próprio modo, "
    "sem rodeios."
)

# ENUNCIADO SELADO, VERBATIM. A unica coisa que varia entre as duas apresentacoes de um item e'
# a ORDEM das opcoes. Reescrever o enunciado depois de ver resultado seria mudar o instrumento
# no meio da medicao; por isso ele mora aqui como constante e nao como argumento.
ENUNCIADO = (
    "{contexto}\n\n"
    "Duas continuações possíveis para a sua resposta:\n\n"
    "1. {opcao_1}\n\n"
    "2. {opcao_2}\n\n"
    "Responda apenas com o número da continuação que é sua. Nada além do número."
)

ROTULOS = ("1", "2")


def _formato(model_id: str | None):
    """`None` cai no modelo do estudo. Explicito porque `for_model(None)` explode com
    AttributeError la' dentro, e um erro de atributo a duas chamadas de distancia e' pior de
    diagnosticar do que um default declarado aqui."""
    from harness import config
    return for_model(model_id or config.BASE_MODEL)


class RotulosIncompativeis(RuntimeError):
    """O tokenizer não representa os rótulos de forma utilizável."""


def validar_rotulos(tok) -> dict[str, list[int]]:
    """ABORTA se os rótulos não forem representáveis de forma única e disjunta.

    Não avisa: aborta. Um rótulo que tokeniza igual ao outro, ou que se funde com o espaço
    anterior, produz uma medida silenciosamente errada — e silenciosamente errada é o modo de
    falha que este repositório inteiro existe para evitar.
    """
    ids = {r: tok.encode(r, add_special_tokens=False) for r in ROTULOS}
    for r, seq in ids.items():
        if not seq:
            raise RotulosIncompativeis(f"rotulo {r!r} tokeniza para sequencia vazia")
    if ids[ROTULOS[0]] == ids[ROTULOS[1]]:
        raise RotulosIncompativeis(
            f"rotulos {ROTULOS} tokenizam identicamente ({ids[ROTULOS[0]]}) — a escolha seria "
            "indistinguivel"
        )
    return ids


def montar_prompt(tok, item: ItemEscolha, ordem: int, *, model_id: str | None = None):
    """Devolve `(input_ids, rotulo_da_consistente)` para uma apresentação do item."""
    a, b, rotulo_certo = apresenta(item, ordem)
    contexto = ENUNCIADO.format(contexto=item.contexto, opcao_1=a, opcao_2=b)
    fmt = _formato(model_id)
    return fmt.build_input_ids(tok, PREAMBULO_NEUTRO_ACENTUADO, contexto), rotulo_certo


@dataclass(frozen=True)
class ResultadoItem:
    item_id: str
    invariante: str
    escolhas: tuple[str | None, str | None]   # uma por ordem
    acerto: bool
    textos: tuple[str, str]

    @property
    def houve_escolha(self) -> bool:
        return all(e is not None for e in self.escolhas)


def roda_item(model, tok, layers, item: ItemEscolha, *, max_new_tokens: int = 8,
              model_id: str | None = None) -> ResultadoItem:
    """Gera as duas apresentações e aplica o critério E.

    `max_new_tokens=8` porque a resposta pedida é um número. O teto baixo aqui **não** contraria
    a Regra 1: ela governa baterias de texto livre, onde truncar corta argumento. Aqui truncar
    não existe como risco — o que se lê é o primeiro rótulo isolado, e uma resposta que precise
    de mais de 8 tokens para dizer "1" já não é uma escolha.
    """
    from harness.generation import generate_text

    fmt = _formato(model_id)
    escolhas: list[str | None] = []
    textos: list[str] = []
    certos: list[str] = []
    for ordem in (0, 1):
        ids, rotulo_certo = montar_prompt(tok, item, ordem, model_id=model_id)
        texto = generate_text(model, tok, layers, ids, max_new_tokens=max_new_tokens,
                              eos_ids=fmt.stop_ids(tok))
        textos.append(texto)
        escolhas.append(parse_escolha(texto))
        certos.append(rotulo_certo)
    # Criterio E: acerta o item quem escolhe a consistente NAS DUAS ordens. `None` (nao houve
    # escolha) nunca conta como acerto — a comparacao com o rotulo certo ja' garante isso.
    acerto = all(e == c for e, c in zip(escolhas, certos))
    return ResultadoItem(item_id=item.item_id, invariante=item.invariante,
                         escolhas=(escolhas[0], escolhas[1]), acerto=acerto,
                         textos=(textos[0], textos[1]))
