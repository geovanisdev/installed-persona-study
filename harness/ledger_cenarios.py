"""Ledger append-only de cenarios: o que os agentes de autoria leem ANTES de escrever.

POR QUE ELE EXISTE, e o numero que o justifica
-----------------------------------------------
No slice piloto de 2026-07-22, quatro agentes escreveram cinco cenarios cada, cegos entre si.
Saiu isto: **cinco familias cobrindo 15 dos 20 pares** ("diretoria mata o projeto" em c00, c05,
c10 e c15; "oficina herdada do pai" em c02, c06, c11 e c19; "pai ou mae morrendo" em c04, c08 e
c16). Ate' os numeros colidiram — *"oito meses"* em c07 e c15, *"tres da manha"* em c08 e c13,
os dois confirmados na releitura.

Com 4 agentes ja' saiu assim. A 90 clusters a colisao e' estrutural, e quem paga sao PR-FAMILIA,
PR-CLUSTER e PR-DUP: travas que abortam DEPOIS de o item existir, quando o custo ja' foi pago.

A DIVISAO DE TRABALHO COM `PR-FAMILIA`
--------------------------------------
As duas fazem a MESMA pergunta em momentos diferentes, e isso e' deliberado:

- o ledger recusa na ESCRITA — o agente descobre a colisao antes de gastar autoria;
- `PR-FAMILIA` recusa na VALIDACAO — pega o que nao passou pelo ledger.

Nenhuma das duas dispensa a outra. Um ledger sem trava confia em quem escreve; uma trava sem
ledger transforma toda colisao em retrabalho. E a limitacao das duas e' a mesma e esta' escrita
em `pr_familia`: a familia e' **declarada** e nunca conferida contra o texto. Dois agentes que
contem a mesma historia sob slugs diferentes atravessam as duas.

APPEND-ONLY, na letra
---------------------
Nada e' reescrito e nada e' apagado. Um cenario abandonado depois de escrito continua no ledger
com `descartado: true` acrescentado por um registro NOVO — porque saber que uma familia foi
tentada e rejeitada e' informacao para o proximo agente, e apagar a linha destruiria justamente
isso. `carrega` reconstroi o estado lendo tudo em ordem.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from harness import config
from harness.persona_core import normalize_text

CAMINHO_PADRAO = config.BATTERIES_DIR / "LEDGER_CENARIOS.jsonl"

# Numeros que aparecem no texto de um cenario: "oito meses", "tres da manha", "50 anos".
# Por extenso E em algarismo, porque a colisao medida foi por extenso e um casador so' de
# digitos nao teria visto nenhuma das duas.
_POR_EXTENSO = ("um", "uma", "dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito",
                "nove", "dez", "onze", "doze", "quinze", "vinte", "trinta", "quarenta",
                "cinquenta", "sessenta", "setenta", "oitenta", "noventa", "cem", "mil")
_UNIDADES = ("minuto", "minutos", "hora", "horas", "dia", "dias", "semana", "semanas",
             "mes", "meses", "ano", "anos", "vez", "vezes", "manha", "tarde", "noite")
_NUMERO = re.compile(
    r"(?<![\w])(?:" + "|".join(_POR_EXTENSO) + r"|\d{1,4})"
    r"(?:\s+(?:da|de|do|em)?\s*)?(?:" + "|".join(_UNIDADES) + r")(?![\w])")


class ColisaoDeCenario(RuntimeError):
    """A familia ja' foi usada neste movimento. E' a mesma regra da clausula (b) de PR-FAMILIA."""


def numeros_citados(texto: str) -> tuple[str, ...]:
    """Expressoes numericas do texto, normalizadas. Base do aviso de colisao de numero."""
    return tuple(sorted({" ".join(m.split()) for m in _NUMERO.findall(normalize_text(texto))}))


@dataclass(frozen=True)
class Cenario:
    familia: str
    movimento_alvo: str
    banco: str
    cluster_id: str
    papel_do_falante: str        # "vitima", "cumplice", "espectador"… — o problema 9 do piloto
    registro: str               # "coloquial", "formal", "telegrafico"
    numeros: tuple[str, ...] = ()
    autor: str = ""
    descartado: bool = False

    def chave(self) -> tuple[str, str]:
        return (normalize_text(self.familia), normalize_text(self.movimento_alvo))


@dataclass
class Estado:
    """O que um agente precisa saber antes de escrever. Reconstruido lendo o ledger inteiro."""

    cenarios: list[Cenario] = field(default_factory=list)

    @property
    def vivos(self) -> list[Cenario]:
        """Reconstruido por REPLAY em ordem, e nao por diferenca de conjuntos.

        A primeira versao fazia `{vivos} - {descartados}` sobre o arquivo inteiro, e o defeito
        so' aparece na sequencia reivindica -> descarta -> **reivindica de novo**: o terceiro
        registro, valido, era anulado pelo descarte que veio ANTES dele. Diferenca de conjuntos
        nao tem tempo; um log append-only e' exatamente uma estrutura em que o tempo importa.
        """
        ativos: dict[tuple[str, str], Cenario] = {}
        for c in self.cenarios:
            if c.descartado:
                ativos.pop(c.chave(), None)
            else:
                ativos[c.chave()] = c
        return list(ativos.values())

    def familias_por_movimento(self) -> dict[str, set[str]]:
        saida: dict[str, set[str]] = {}
        for c in self.vivos:
            saida.setdefault(c.movimento_alvo, set()).add(c.familia)
        return saida

    def numeros_usados(self) -> dict[str, list[str]]:
        saida: dict[str, list[str]] = {}
        for c in self.vivos:
            for n in c.numeros:
                saida.setdefault(n, []).append(c.cluster_id)
        return saida

    def briefing(self, movimento: str) -> str:
        """O texto que vai no prompt do agente de autoria. Curto de proposito: um briefing que
        ninguem le' nao evita colisao nenhuma."""
        fams = sorted(self.familias_por_movimento().get(movimento, ()))
        repetidos = {n: c for n, c in self.numeros_usados().items() if len(c) > 1}
        linhas = [f"JA' USADAS no movimento {movimento!r} ({len(fams)}): "
                  + (", ".join(fams) if fams else "nenhuma — este e' o primeiro")]
        todas = sorted({c.familia for c in self.vivos})
        if todas:
            linhas.append(f"JA' USADAS em qualquer movimento ({len(todas)}): "
                          + ", ".join(todas))
        usados = sorted(self.numeros_usados())
        if usados:
            linhas.append("NUMEROS ja' citados (evite repetir): " + ", ".join(usados))
        if repetidos:
            linhas.append("JA' COLIDIRAM mais de uma vez: " + ", ".join(sorted(repetidos)))
        papeis = sorted({c.papel_do_falante for c in self.vivos if c.papel_do_falante})
        if papeis:
            linhas.append("PAPEIS de falante ja' usados: " + ", ".join(papeis))
        return "\n".join(linhas)


def carrega(caminho: str | Path = CAMINHO_PADRAO) -> Estado:
    """Le o ledger inteiro em ordem. Arquivo ausente devolve estado vazio — nao e' erro."""
    p = Path(caminho)
    if not p.exists():
        return Estado()
    cenarios = []
    for linha in p.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d = json.loads(linha)
            d["numeros"] = tuple(d.get("numeros", ()) or ())
            cenarios.append(Cenario(**d))
    return Estado(cenarios)


def registra(cenario: Cenario, *, caminho: str | Path = CAMINHO_PADRAO,
             estado: Estado | None = None) -> Estado:
    """Acrescenta ao ledger. RECUSA colisao de (familia, movimento) — nao avisa: recusa.

    Avisar seria o modo de falha do piloto: os quatro agentes teriam visto o aviso depois de
    escrever, e escrever e' o custo que se quer evitar. A recusa e' a mesma regra da clausula
    (b) de `PR-FAMILIA`, aplicada um passo antes.

    Registro de DESCARTE nao colide consigo mesmo: e' o unico jeito de liberar uma familia sem
    apagar historia.
    """
    est = estado if estado is not None else carrega(caminho)
    if not cenario.descartado:
        ocupadas = {c.chave(): c for c in est.vivos}
        anterior = ocupadas.get(cenario.chave())
        if anterior is not None:
            raise ColisaoDeCenario(
                f"a familia {cenario.familia!r} ja' esta' usada no movimento "
                f"{cenario.movimento_alvo!r} pelo cluster {anterior.cluster_id!r}"
                + (f" (autor {anterior.autor})" if anterior.autor else "")
                + ".\nEscolha outra familia, ou registre o descarte da anterior. "
                "Duas historias iguais na mesma celula fazem a celula reportar n maior do que "
                "mediu — e e' a celula que decide o endpoint de F2."
            )
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8", newline="\n") as f:
        d = {"familia": cenario.familia, "movimento_alvo": cenario.movimento_alvo,
             "banco": cenario.banco, "cluster_id": cenario.cluster_id,
             "papel_do_falante": cenario.papel_do_falante, "registro": cenario.registro,
             "numeros": list(cenario.numeros), "autor": cenario.autor,
             "descartado": cenario.descartado}
        f.write(json.dumps(d, ensure_ascii=False) + "\n")
    est.cenarios.append(cenario)
    return est


def avisa_colisao_de_numero(estado: Estado, texto: str) -> tuple[str, ...]:
    """Numeros do texto que o ledger ja' viu. AVISO, nao recusa — e a distincao e' deliberada.

    Familia repetida na mesma celula corrompe o n reportado; numero repetido nao. *"Tres da
    manha"* em dois cenarios distintos e' coincidencia estilistica, nao dado duplicado. Recusar
    aqui empurraria os autores a escreverem numeros cada vez mais estranhos so' para passar na
    trava, e um cenario com "dezessete meses e meio" nao e' mais valido — e' menos plausivel.
    """
    ja = set(estado.numeros_usados())
    return tuple(n for n in numeros_citados(texto) if n in ja)


def registra_lote(cenarios: Iterable[Cenario], *,
                  caminho: str | Path = CAMINHO_PADRAO) -> Estado:
    """Registra em sequencia, parando na primeira colisao. O que ja' entrou FICA.

    Nao ha' transacao. Desfazer parte de um append-only exigiria reescrever o arquivo, que e'
    exatamente o que ele nao faz — e os registros anteriores sao verdadeiros: aqueles cenarios
    foram mesmo reivindicados.
    """
    est = carrega(caminho)
    for c in cenarios:
        est = registra(c, caminho=caminho, estado=est)
    return est
