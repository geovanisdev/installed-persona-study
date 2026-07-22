"""Roda as travas de producao contra um banco de itens, e reporta.

POR QUE EXISTE UM RUNNER, e nao um `python -c` por vez
------------------------------------------------------
O piloto de gemeos de 2026-07-22 foi validado ad-hoc, e o laudo daquela rodada nao existe como
arquivo: existe como frases num relatorio escritas por quem rodou. Um numero que so' vive na
prosa de quem o produziu nao e' verificavel por ninguem — nem por mim uma semana depois.

Este runner produz o laudo em JSON, com o hash dos nucleos e a lista do que NAO rodou.

OS DOIS MODOS, e por que o permissivo e' o que tem nome
-------------------------------------------------------
`--modo gate` (o DEFAULT) chama `valida_banco_producao`, que aborta na primeira trava que
acusa e recusa selar com trava pulada. E' a lei.

`--modo diagnostico` roda **cada trava isolada** e coleta todas as acusacoes. Serve a' autoria
(um autor quer a lista inteira do que consertar, nao a primeira linha) e serve ao relatorio de
contraexemplo. Ele NUNCA sela e carimba `carater: DIAGNOSTICO` como primeira chave do laudo.

O permissivo e' o que precisa ser digitado; o restritivo e' o que acontece sozinho. A ordem
inversa e' como uma flag de contorno vira default sem ninguem decidir — ver
`harness/exploratorio.py`.

A ANOTACAO DE FAMILIA, e o buraco que ela quase abriu
------------------------------------------------------
`--familias` preenche `familia_de_cenario` em itens escritos ANTES de o campo existir. Sem
isso, o slice piloto acusaria `familia:ausente` em 40 de 40 itens e o contraexemplo nao provaria
nada sobre reciclagem.

Mas um mapa que **sobrescreve** familia declarada seria a maneira mais barata de calar
PR-FAMILIA: bastaria renomear os dois clusters colididos. Entao o preenchimento so' vale para
campo VAZIO, e divergir de uma declaracao existente **aborta**. O sha256 do mapa entra no laudo,
porque um banco anotado nao e' o mesmo objeto que o banco escrito.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

from harness import config
from harness import prod_validator as PV


class AnotacaoInvalida(RuntimeError):
    """O mapa de familias contradiz o que o item ja' declara."""


def carrega_cores() -> list[dict]:
    """Os dois nucleos SELADOS. `load_core` recusa hash que nao bate."""
    from harness.persona_core import load_core

    return [load_core(config.CORE_DIR / f"{p}.core.json")
            for p in ("leokadius", "shadowclock")]


def anota_familias(itens: list[PV.ItemProducao], mapa: dict[str, str]) -> list[PV.ItemProducao]:
    """Preenche `familia_de_cenario` VAZIO. Divergir do que o item declara aborta.

    Chave do mapa e' `cluster_id`, porque familia e' propriedade do cluster: as duas parafrases
    contam a mesma historia por construcao, e `_CAMPOS_INVARIANTES_NO_CLUSTER` ja' exige que o
    rotulo seja o mesmo nas duas.
    """
    faltando = sorted({it.cluster_id for it in itens} - set(mapa))
    if faltando:
        raise AnotacaoInvalida(
            f"o mapa nao cobre {len(faltando)} cluster(s): {faltando[:5]}"
            + ("…" if len(faltando) > 5 else "")
            + ". Anotacao parcial deixaria PR-FAMILIA acusar `familia:ausente` no resto e o "
              "laudo diria mais sobre o mapa do que sobre o banco.")

    saida = []
    for it in itens:
        novo = mapa[it.cluster_id]
        atual = (it.familia_de_cenario or "").strip()
        if atual and atual != novo:
            raise AnotacaoInvalida(
                f"{it.item_id}: o item declara familia {atual!r} e o mapa diz {novo!r}. "
                "Sobrescrever declaracao seria o jeito mais barato de calar PR-FAMILIA — "
                "bastaria renomear os clusters que colidiram.")
        saida.append(it if atual else replace(it, familia_de_cenario=novo))
    return saida


# As travas de UM banco, com a assinatura de cada uma resolvida aqui em vez de por introspeccao.
# Introspeccao acertaria hoje e erraria em silencio na primeira trava com argumento novo.
def _diagnostico(itens: list[PV.ItemProducao], cores: list[dict], *, tok,
                 outros, pilotos) -> dict:
    chamadas = [
        ("PR-SCHEMA", lambda: PV.pr_schema(itens, cores)),
        ("PR-LEXICO", lambda: PV.pr_lexico(itens, cores)),
        ("PR-LEAK", lambda: PV.pr_leak(itens, cores)),
        ("PR-SCRUB", lambda: PV.pr_scrub(itens, cores)),
        ("PR-META", lambda: PV.pr_meta(itens)),
        ("PR-MOLDE", lambda: PV.pr_molde(itens)),
        ("PR-CLUSTER", lambda: PV.pr_cluster(itens)),
        ("PR-FAMILIA", lambda: PV.pr_familia(itens)),
        ("PR-ORTOGRAFIA", lambda: PV.pr_ortografia(itens)),
        ("PR-USUARIO", lambda: PV.pr_usuario(itens)),
    ]
    if any(i.faceta_alvo == "F4" for i in itens):
        chamadas.append(("PR-F4", lambda: PV.pr_f4(itens)))
    if outros or pilotos:
        chamadas.append(("PR-DUP", lambda: PV.pr_dup(itens, outros=outros, pilotos=pilotos)))
    if tok is not None:
        chamadas.append(("PR-INDICE", lambda: PV.pr_indice(tok, itens, estrato=None)))

    rodadas: dict[str, str] = {}
    acusacoes: dict[str, str] = {}
    for nome, chamada in chamadas:
        try:
            chamada()
            rodadas[nome] = "PASSOU"
        except PV.BancoDeProducaoInvalido as e:
            rodadas[nome] = "ACUSOU"
            acusacoes[nome] = str(e)

    puladas = [n for n in PV.TRAVAS if n not in rodadas]
    return {"travas": rodadas, "acusacoes": acusacoes, "travas_nao_rodadas": puladas}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--itens", nargs="+", required=True,
                    help="JSONL(s) de banco. Dois bancos + --par roda PR-PAR entre eles.")
    ap.add_argument("--par", action="store_true",
                    help="roda PR-PAR entre os dois bancos passados (exige exatamente 2).")
    ap.add_argument("--pilotos", nargs="*", default=[],
                    help="JSONL(s) de piloto para PR-DUP(ii).")
    ap.add_argument("--familias", default=None, metavar="MAPA.json",
                    help="mapa cluster_id -> familia_de_cenario, para bancos escritos antes "
                         "de o campo existir. So' preenche campo VAZIO.")
    ap.add_argument("--modo", choices=("gate", "diagnostico"), default="gate")
    ap.add_argument("--saida", required=True)
    args = ap.parse_args()

    cores = carrega_cores()
    from harness.persona_core import core_hash

    bancos: dict[str, list[PV.ItemProducao]] = {}
    for caminho in args.itens:
        itens = PV.carrega_itens(caminho)
        if not itens:
            raise SystemExit(f"{caminho} nao tem item nenhum.")
        bancos[Path(caminho).name] = itens

    anotacao = None
    if args.familias:
        bruto = Path(args.familias).read_bytes()
        mapa = json.loads(bruto.decode("utf-8"))
        anotacao = {"arquivo": args.familias,
                    "sha256": hashlib.sha256(bruto).hexdigest(),
                    "n_clusters": len(mapa)}
        bancos = {k: anota_familias(v, mapa) for k, v in bancos.items()}

    tok = None
    from harness.tokenizacao import carrega_tokenizer, tokenizer_disponivel
    if tokenizer_disponivel():
        tok = carrega_tokenizer()

    pilotos = {Path(p).name: [i.prompt for i in PV.carrega_itens(p)] for p in args.pilotos}

    laudo: dict = {}
    if args.modo == "diagnostico":
        laudo["carater"] = "DIAGNOSTICO"
        laudo["nao_sela"] = True
    laudo["modo"] = args.modo
    laudo["cores"] = {c["persona_id"]: core_hash(c) for c in cores}
    laudo["tokenizer"] = "carregado" if tok is not None else "AUSENTE"
    if anotacao:
        laudo["familias_anotadas"] = anotacao

    por_banco: dict[str, dict] = {}
    nomes = list(bancos)
    for nome, itens in bancos.items():
        outros = {k: v for k, v in bancos.items() if k != nome}
        if args.modo == "diagnostico":
            r = _diagnostico(itens, cores, tok=tok, outros=outros, pilotos=pilotos)
        else:
            try:
                r = PV.valida_banco_producao(itens, cores, outros=outros, pilotos=pilotos,
                                             tok=tok)
            except PV.BancoDeProducaoInvalido as e:
                r = {"veredito": "REPROVADO", "acusacao": str(e)}
        r["n_itens"] = len(itens)
        r["n_clusters"] = len({i.cluster_id for i in itens})
        por_banco[nome] = r
    laudo["por_banco"] = por_banco

    if args.par:
        if len(nomes) != 2:
            raise SystemExit("--par exige exatamente dois bancos.")
        if tok is None:
            laudo["par"] = {"veredito": "NAO_RODOU", "motivo": "tokenizer ausente"}
        else:
            try:
                laudo["par"] = PV.valida_paridade_entre_bracos(
                    tok, bancos[nomes[0]], bancos[nomes[1]], cores)
            except PV.BancoDeProducaoInvalido as e:
                laudo["par"] = {"veredito": "REPROVADO", "acusacao": str(e)}

    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(laudo, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in laudo.items() if k != "por_banco"},
                     ensure_ascii=False, indent=1))
    for nome, r in por_banco.items():
        print(f"\n=== {nome} ({r['n_itens']} itens, {r['n_clusters']} clusters) ===")
        print(json.dumps(r, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
