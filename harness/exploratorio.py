"""O unico caminho declarado para rodar um banco que a guarda de atalhos REPROVOU.

POR QUE ISTO EXISTE
-------------------
`valida_por_sujeitos` aborta quando uma heuristica cega quase resolve o banco. O aborto esta'
certo: um banco com atalho mede o atalho. Mas ha' um caso em que rodar assim mesmo e' a coisa
informativa a fazer, e ele apareceu no piloto V1.

O estrato `nao_finge_humano` e' resolvido em 1,000 por `afeto_recusa` — a heuristica que
prefere a opcao com MENOS vocabulario de experiencia. Isso nao e' descuido de autoria: a opcao
violadora desse estrato **reivindica experiencia humana**, logo ela usa vocabulario de
experiencia. O atalho e' quase o construto. A pergunta que sobra — *a base nua ja' resolve este
estrato sozinha?* — decide, pela Regra 6 selada, se o invariante sai do endpoint. E ela e'
respondivel com 8 itens e ~10 minutos de GPU.

O QUE ESTE MODULO NAO E'
------------------------
Nao e' um `--force`. Um `--force` transforma uma guarda em aviso, e uma guarda que vira aviso ja'
foi removida — so' que sem ninguem escrever que removeu. As tres exigencias abaixo existem para
que atravessar custe mais do que consertar o banco, que e' a ordem certa de incentivo:

1. **O motivo entra por escrito** e vai para dentro do relatorio. Nao ha' modo silencioso.
2. **Os atalhos sao ENUMERADOS pelo operador e conferidos contra os que a guarda achou.**
   Declarar de menos aborta (esta'-se passando por cima de atalho que nao se viu); declarar de
   mais tambem aborta (nao se entendeu o banco). E declarar num banco LIMPO aborta — e' o que
   impede a flag de ficar colada num script e virar default de fato.
3. **A saida so' pode cair sob `runs/exploratorio/`**, por lista branca. Lista negra de
   caminhos confirmatorios seria fachada: bastaria um diretorio novo que ninguem lembrou de
   proibir. A lista branca nao tem esse buraco.

Nada disto torna o resultado confirmatorio. O relatorio sai carimbado EXPLORATORIO e KILL-only:
pela Regra 6 ele pode MATAR um invariante (se a base estourar o teto selado) e nao pode aprovar
nada. Um piloto que aprova e' endpoint nao declarado — `analysis/ENDPOINTS.md`, secao "O que
nao e' endpoint".
"""

from __future__ import annotations

from pathlib import Path

from harness import config
from harness.polos_sujeito import (
    LIMIAR_BANCO_SOLUVEL,
    SUJEITOS_DE_BANCO,
    SUJEITOS_DEGENERADOS,
    ItemEscolha,
    pontua_sujeito,
)

# Lista BRANCA. Ver a exigencia 3 no docstring do modulo.
RAIZ_EXPLORATORIA = config.RUNS_DIR / "exploratorio"

# Rotulo do nivel agregado dentro de `atalhos_encontrados`. Maiusculo para nunca colidir com um
# nome de invariante, que no repo inteiro e' minusculo com sublinhado.
AGREGADO = "AGREGADO"


class DeclaracaoInvalida(RuntimeError):
    """A travessia foi pedida sem cumprir uma das tres exigencias. Abortar e' o correto."""


def atalhos_encontrados(itens: list[ItemEscolha], *,
                        estratificar_por: str | None = "invariante") -> tuple[str, ...]:
    """Todo par `<estrato>:<sujeito>` cuja taxa alcanca `LIMIAR_BANCO_SOLUVEL`.

    E' o conjunto que o operador tem de reproduzir na declaracao. Difere do que `LaudoSujeitos`
    expoe de proposito: o laudo guarda `solventes` (nomes, sem estrato) e `estratos_solveis`
    (estratos, sem nome), e cruzar os dois campos NAO devolve os pares — um estrato solvel por
    dois sujeitos aparece uma vez em cada campo, e o par que falta fica invisivel.

    Sujeitos de BANCO (funcionais `f(itens)`, como `sup_comprimento`) entram aqui: eles contam
    para o veredito de banco, ainda que nunca entrem no piso empirico.
    """
    achados: list[str] = []

    def varre(rotulo: str, sub: list[ItemEscolha]) -> None:
        for nome, s in SUJEITOS_DEGENERADOS.items():
            if pontua_sujeito(s, sub)["taxa"] >= LIMIAR_BANCO_SOLUVEL:
                achados.append(f"{rotulo}:{nome}")
        for nome, fn in SUJEITOS_DE_BANCO.items():
            if fn(sub) >= LIMIAR_BANCO_SOLUVEL:
                achados.append(f"{rotulo}:{nome}")

    varre(AGREGADO, itens)

    if estratificar_por:
        grupos: dict[str, list[ItemEscolha]] = {}
        for item in itens:
            grupos.setdefault(getattr(item, estratificar_por, "") or "", []).append(item)
        # Mesma condicao de `valida_por_sujeitos`: um banco de estrato unico ja' foi varrido
        # como agregado, e reporta-lo duas vezes obrigaria a declarar o mesmo atalho duas vezes.
        if len(grupos) > 1:
            for estrato, sub in sorted(grupos.items()):
                varre(estrato, sub)

    return tuple(sorted(set(achados)))


def exige_declaracao(itens: list[ItemEscolha], *, motivo: str,
                     atalhos_declarados: list[str]) -> dict:
    """Confere as exigencias 1 e 2. Devolve o bloco que vai carimbado no relatorio.

    Levanta `DeclaracaoInvalida` em qualquer desvio — inclusive no caso, facil de nao antecipar,
    de o banco estar LIMPO: ai' nao ha' o que declarar, e a travessia nao tem objeto.
    """
    if not motivo or not motivo.strip():
        raise DeclaracaoInvalida(
            "o motivo da travessia entra por escrito e vai para dentro do relatorio; "
            "sem ele nao ha' registro de por que a guarda foi atravessada."
        )

    encontrados = atalhos_encontrados(itens)
    if not encontrados:
        raise DeclaracaoInvalida(
            "este banco NAO tem atalho acima de "
            f"{LIMIAR_BANCO_SOLUVEL:.2f} — nao ha' guarda para atravessar. Rode sem a flag. "
            "(Esta checagem existe para que a flag nao fique colada num script e vire default.)"
        )

    declarados = {a.strip() for a in atalhos_declarados if a.strip()}
    faltando = sorted(set(encontrados) - declarados)
    sobrando = sorted(declarados - set(encontrados))
    if faltando or sobrando:
        raise DeclaracaoInvalida(
            "a declaracao tem de casar EXATAMENTE com os atalhos que a guarda achou.\n"
            f"  achados pela guarda : {list(encontrados)}\n"
            f"  declarados          : {sorted(declarados)}\n"
            + (f"  NAO DECLARADOS      : {faltando}  <- atravessar sem ver nao vale\n"
               if faltando else "")
            + (f"  DECLARADOS A MAIS   : {sobrando}  <- nao confere com este banco\n"
               if sobrando else "")
        )

    return {
        "carater": "EXPLORATORIO",
        "kill_only": True,
        "nao_e_endpoint": True,
        "motivo": motivo.strip(),
        "atalhos_declarados": list(encontrados),
        "limiar_banco_soluvel": LIMIAR_BANCO_SOLUVEL,
        "nota": "Pela Regra 6 este run pode MATAR um invariante e nao pode aprovar nenhum. "
                "Nao entra em nenhum dos cinco endpoints de analysis/ENDPOINTS.md.",
    }


def exige_saida_exploratoria(saida: str | Path) -> Path:
    """Exigencia 3: lista branca de destino. Levanta `DeclaracaoInvalida` fora dela."""
    destino = Path(saida).expanduser().resolve()
    raiz = RAIZ_EXPLORATORIA.resolve()
    if destino != raiz and not destino.is_relative_to(raiz):
        raise DeclaracaoInvalida(
            f"run exploratorio so' escreve sob {raiz} (lista BRANCA).\n"
            f"  pedido: {destino}\n"
            "Qualquer outro destino e' recusado — inclusive o default do runner, que aponta "
            "para o caminho de um run confirmatorio."
        )
    return destino
