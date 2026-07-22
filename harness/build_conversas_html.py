"""Monta o artefato HTML multi-abas das conversas, uma aba por ETAPA.

PEDIDO QUE ESTE MODULO ATENDE (Arquiteto, 2026-07-22): *"todas as conversações dos modelos
durante o processo sejam salvas e posteriormente organizadas em um artefato html multi abas
organizado por etapa, com todos indicativos do experimento e as respostas completas"*.

TRES DECISOES DE CONSTRUCAO, e as tres tem motivo:

1. **Renderizacao em tempo de BUILD, nao no navegador.** Seria mais leve embutir um JSON e
   montar a pagina com JS. Mas isto e' um artefato de EVIDENCIA: com JS desligado, ou daqui
   a cinco anos num navegador que quebrou alguma API, a pagina precisa continuar mostrando
   o texto. Conteudo em `<details>` continua no DOM.

2. **O `<style>` nao e' escrito aqui.** Ele e' extraido de `docs/ESTADO-DO-ESTUDO.html`, que
   e' o artefato canonico do repo. Reescrever CSS "melhorando" e' como os artefatos de um
   mesmo projeto passam a nao parecer o mesmo projeto. Se aquele arquivo sumir, este modulo
   ABORTA em vez de inventar um estilo.

3. **Nada e' truncado na exibicao, e o que foi truncado ANTES aparece como aviso.** O campo
   `truncada` de cada registro vira um selo visivel. Um artefato chamado "respostas
   completas" que esconde corte seria pior que nao existir.

Uso:
    python -m harness.build_conversas_html [--saida docs/CONVERSAS-DO-ESTUDO.html]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

from harness import config
from harness.conversa_log import CAMPOS, etapas, le_etapa

TETO_ARQUIVO_MB = 12.0     # acima disto o arquivo vira desconfortavel de abrir; avisamos

# Campos que sao INDICADOR DE CELULA do desenho. Aparecem na ficha de cada conversa, e
# aparecem mesmo quando vazios: "adapter: —" e informacao (era a base nua), enquanto a
# ausencia da linha e' ambiguidade.
INDICADORES = (
    "papel", "modelo", "revisao", "adapter", "persona", "scrub",
    "semente_treino", "semente_decodificacao",
    "banco", "battery_hash", "cluster_id", "parafrase_idx", "item_id",
    "invariante", "polo", "direcao",
    "parametros_decodificacao", "n_tokens_prompt", "n_tokens_resposta",
    "truncada", "sha256_resposta", "core_hash", "git_commit", "git_dirty",
)


def _e(x) -> str:
    """Escapa para HTML. `None` vira travessao, para nao virar a string 'None'."""
    if x is None or x == "":
        return "—"
    if isinstance(x, bool):
        return "sim" if x else "não"
    if isinstance(x, (dict, list)):
        return html.escape(json.dumps(x, ensure_ascii=False))
    return html.escape(str(x))


def estilo_canonico(repo: Path) -> str:
    """O `<style data-skel="fixo">` do artefato canonico do repo, verbatim."""
    fonte = repo / "docs" / "ESTADO-DO-ESTUDO.html"
    if not fonte.exists():
        raise SystemExit(
            f"ABORTADO: {fonte} nao existe, e e' de la' que sai o estilo canonico. "
            "Inventar um estilo aqui faria os artefatos do mesmo estudo divergirem."
        )
    texto = fonte.read_text(encoding="utf-8")
    m = re.search(r"<style[^>]*>.*?</style>", texto, re.S)
    if not m:
        raise SystemExit(f"ABORTADO: nao achei bloco <style> em {fonte}")
    return m.group(0)


# O que de fato provoca uma requisicao. `https://` solto NAO entra: as conversas guardadas
# citam URLs no proprio texto (mensagem de erro do huggingface, endereco de paper), e isso e'
# conteudo escapado dentro de <pre> — inerte. A primeira versao desta trava procurava
# `https?://` no documento inteiro e abortava por causa de tres URLs que estavam dentro de uma
# resposta de modelo. Uma trava que acusa o conteudo em vez do continente nao protege nada e
# ainda ensina a desliga-la.
_PADROES_DE_REDE = (
    r"<link\b", r"\bsrc\s*=", r"@import", r"url\(\s*['\"]?https?:", r"//cdn\.",
    r"googleapis|unpkg|jsdelivr", r"\bfetch\s*\(", r"XMLHttpRequest", r"\bnew\s+WebSocket",
    r"<iframe\b", r"<script[^>]+\bsrc\b",
)


def _sem_rede(doc: str) -> None:
    """Trava de zero-rede: nenhuma construcao que dispare requisicao ao abrir o arquivo.

    O texto das conversas e' removido antes da checagem — ele e' escapado e inerte, e e'
    justamente onde URLs aparecem legitimamente.
    """
    markup = re.sub(r"<pre\b[^>]*>.*?</pre>", "<pre></pre>", doc, flags=re.S)
    achados = Counter()
    for p in _PADROES_DE_REDE:
        for m in re.findall(p, markup, re.I):
            achados[m if isinstance(m, str) else p] += 1
    if achados:
        raise SystemExit(f"ABORTADO: o artefato tem referencia de rede: {dict(achados)}")


# --- pedacos de pagina -------------------------------------------------------

def _ficha(reg: dict) -> str:
    linhas = []
    for c in INDICADORES:
        if c not in CAMPOS:
            continue
        linhas.append(f"<tr><th>{_e(c)}</th><td>{_e(reg.get(c))}</td></tr>")
    return "<table class='ficha'>" + "".join(linhas) + "</table>"


def _turnos(reg: dict) -> str:
    turnos = reg.get("turnos") or []
    if not turnos:
        return ""
    out = ["<div class='turnos'><h5>Troca completa</h5>"]
    for t in turnos:
        nome = f" · {_e(t.get('nome'))}" if t.get("nome") else ""
        aviso = ""
        if t.get("truncado_em"):
            aviso = (f"<p class='aviso'>Este turno foi cortado em {t['truncado_em']} "
                     f"caracteres de {t.get('tamanho_original', '?')} na captura.</p>")
        out.append(
            f"<div class='turno turno-{_e(t.get('tipo'))}'>"
            f"<span class='rot'>{_e(t.get('papel'))} · {_e(t.get('tipo'))}{nome}</span>"
            f"{aviso}<pre>{html.escape(t.get('texto') or '')}</pre></div>"
        )
    out.append("</div>")
    return "".join(out)


def _conversa(reg: dict, i: int) -> str:
    rot = " · ".join(x for x in [
        reg.get("item_id") or reg.get("cluster_id") or f"#{reg.get('ordem', i)}",
        reg.get("persona"), reg.get("adapter"), reg.get("banco"), reg.get("invariante"),
    ] if x)
    selo = ""
    if reg.get("truncada") is True:
        selo = "<span class='selo selo-corte'>resposta cortada pelo teto</span>"
    elif reg.get("truncada") is None:
        selo = "<span class='selo selo-indef'>não se sabe se cortou</span>"
    resp = reg.get("resposta_completa") or ""
    return (
        f"<details class='conversa'><summary>{_e(rot)}{selo}"
        f"<span class='chars'>{len(resp)} car.</span></summary>"
        f"{_ficha(reg)}"
        f"<h5>Prompt completo</h5><pre>{html.escape(reg.get('prompt_completo') or '')}</pre>"
        + (f"<h5>Preâmbulo</h5><pre>{html.escape(reg['preambulo'])}</pre>"
           if reg.get("preambulo") else "")
        + f"<h5>Resposta completa</h5><pre class='resposta'>{html.escape(resp)}</pre>"
        f"{_turnos(reg)}</details>"
    )


def _resumo_etapa(regs: list[dict]) -> str:
    papeis = Counter(r.get("papel") for r in regs)
    cortadas = sum(1 for r in regs if r.get("truncada") is True)
    indef = sum(1 for r in regs if r.get("truncada") is None)
    car = sum(len(r.get("resposta_completa") or "") for r in regs)
    aviso = ""
    if indef:
        aviso = (f"<p class='aviso'><strong>{indef}</strong> registro(s) sem saber se a "
                 "resposta foi cortada. Comparação entre braços fica sem defesa nesses.</p>")
    return (
        f"<p class='resumo'><strong>{len(regs)}</strong> conversa(s) · papéis: "
        + ", ".join(f"{_e(k)} {v}" for k, v in papeis.most_common())
        + f" · <strong>{cortadas}</strong> cortada(s) pelo teto · {car:,} caracteres de "
        "resposta guardados.</p>".replace(",", ".") + aviso
    )


EXPLICADOR = [
    ("o-que-e",
     "O que é esta página",
     "Toda vez que um modelo de linguagem responde alguma coisa dentro deste estudo — seja "
     "respondendo a um item do experimento, seja ajudando a construir o material — a "
     "conversa inteira fica gravada. Esta página é o arquivo dessas conversas, separado por "
     "etapa do trabalho. Nada foi resumido: o que você lê é o texto que saiu.",
     "What this page is",
     "Every time a language model answers something inside this study — whether answering an "
     "experiment item or helping build the material — the whole conversation is recorded. "
     "This page is the archive of those conversations, split by stage of the work. Nothing "
     "was summarised: what you read is the text that came out."),
    ("por-que",
     "Por que guardar tudo",
     "Um resultado que ninguém pode reexaminar não é resultado, é anúncio. Sem o texto bruto "
     "não dá para recontar sob outra régua, nem conferir se um julgamento foi justo, nem "
     "mostrar a um terceiro o que de fato foi dito. Guardar é a parte chata que transforma "
     "uma afirmação em evidência.",
     "Why keep all of it",
     "A result nobody can re-examine is not a result, it is an announcement. Without the raw "
     "text there is no way to re-score it under a different rule, to check whether a judgement "
     "was fair, or to show a third party what was actually said. Keeping it is the boring part "
     "that turns a claim into evidence."),
    ("cortada",
     "O selo “resposta cortada”",
     "Modelos escrevem até um limite e param. Se uma resposta bateu nesse limite, ela está "
     "incompleta — e comparar uma resposta inteira com uma cortada é comparar coisas "
     "diferentes. Já medimos isso aqui: sob o mesmo limite, um dos lados foi cortado em 23 de "
     "24 respostas e o outro em 12 de 24. Por isso o corte aparece marcado, e quando não se "
     "sabe se houve corte, isso também aparece.",
     "The “answer was cut” badge",
     "Models write up to a limit and stop. If an answer hit that limit it is incomplete — and "
     "comparing a whole answer with a cut one compares different things. We measured this "
     "here: under the same limit, one side was cut in 23 of 24 answers and the other in 12 of "
     "24. That is why cutting is flagged, and when it is unknown whether cutting happened, "
     "that is flagged too."),
    ("indicadores",
     "Os indicadores de cada conversa",
     "Cada conversa vem com a ficha completa de onde ela nasceu: qual modelo, em qual versão "
     "exata, com qual persona instalada, de qual banco de itens veio a pergunta, e o código "
     "do repositório naquele momento. Uma geração que não sabe dizer de onde veio não prova "
     "nada.",
     "The indicators on each conversation",
     "Each conversation carries the full record of where it came from: which model, at which "
     "exact version, with which persona installed, which item bank the question came from, and "
     "the state of the repository at that moment. A generation that cannot say where it came "
     "from proves nothing."),
]


def _explicador() -> str:
    blocos = []
    for slug, t_pt, c_pt, t_en, c_en in EXPLICADOR:
        blocos.append(
            f"<section class='exp'>"
            f"<h3><span data-slot='exp-{slug}-titulo-pt' lang='pt-BR'>{_e(t_pt)}</span>"
            f"<span data-slot='exp-{slug}-titulo-en' lang='en'>{_e(t_en)}</span></h3>"
            f"<p><span data-slot='exp-{slug}-pt' lang='pt-BR'>{_e(c_pt)}</span>"
            f"<span data-slot='exp-{slug}-en' lang='en'>{_e(c_en)}</span></p></section>"
        )
    return "".join(blocos)


def monta(regs_por_etapa: dict[str, list[dict]], *, repo: Path) -> str:
    ordem = sorted(regs_por_etapa)
    abas, paineis = [], []
    for i, etapa in enumerate(ordem):
        regs = regs_por_etapa[etapa]
        sel = "true" if i == 0 else "false"
        abas.append(f"<button class='tab-btn' role='tab' aria-selected='{sel}' "
                    f"aria-controls='p-{_e(etapa)}'>{_e(etapa)} ({len(regs)})</button>")
        corpo = "".join(_conversa(r, j) for j, r in enumerate(regs))
        paineis.append(
            f"<div class='tab-panel' id='p-{_e(etapa)}' role='tabpanel'"
            f"{'' if i == 0 else ' hidden'}>"
            f"<h2>{_e(etapa)}</h2>{_resumo_etapa(regs)}{corpo}</div>")

    abas.append("<button class='tab-btn' role='tab' aria-selected='false' "
                "aria-controls='p-explicador'>Explicador</button>")
    paineis.append(
        "<div class='tab-panel' id='p-explicador' role='tabpanel' hidden data-lang='pt'>"
        "<div class='lang-switch'>"
        "<button class='lang-btn' data-set-lang='pt' aria-pressed='true'>Português</button>"
        "<button class='lang-btn' data-set-lang='en' aria-pressed='false'>English</button>"
        "</div>" + _explicador() + "</div>")

    total = sum(len(v) for v in regs_por_etapa.values())
    mr = {
        "artefato": "conversas-do-estudo",
        "schema": "conversa/1",
        "etapas": {k: len(v) for k, v in sorted(regs_por_etapa.items())},
        "total_conversas": total,
        "total_caracteres_resposta": sum(
            len(r.get("resposta_completa") or "") for v in regs_por_etapa.values() for r in v),
        "cortadas_pelo_teto": sum(
            1 for v in regs_por_etapa.values() for r in v if r.get("truncada") is True),
        "sem_saber_se_cortou": sum(
            1 for v in regs_por_etapa.values() for r in v if r.get("truncada") is None),
        "campos_do_registro": list(CAMPOS),
        "fonte": "runs/conversas/<etapa>.jsonl (append-only)",
        "o_que_este_artefato_NAO_cobre": [
            "conversas anteriores a 2026-07-22, quando conversa_log passou a existir",
            "blocos de raciocinio que chegam vazios na transcricao de origem",
            "qualquer geracao feita fora do harness deste repositorio",
        ],
    }
    abas.append("<button class='tab-btn' role='tab' aria-selected='false' "
                "aria-controls='p-mr'>Machine-readable</button>")
    paineis.append("<div class='tab-panel' id='p-mr' role='tabpanel' hidden>"
                   "<pre data-skel='fixo'>"
                   + html.escape(json.dumps(mr, ensure_ascii=False, indent=2))
                   + "</pre></div>")

    js = """
(function(){"use strict";
  var tabs=document.querySelector(".tabs");
  if(!tabs) return;
  var btns=tabs.querySelectorAll(".tab-btn"),pans=document.querySelectorAll(".tab-panel");
  btns.forEach(function(b){b.addEventListener("click",function(){
    btns.forEach(function(x){x.setAttribute("aria-selected","false")});
    pans.forEach(function(p){p.hidden=true});
    b.setAttribute("aria-selected","true");
    var p=document.getElementById(b.getAttribute("aria-controls")); if(p)p.hidden=false;});});
  document.querySelectorAll("[data-lang]").forEach(function(root){
    root.querySelectorAll(".lang-btn").forEach(function(b){b.addEventListener("click",function(){
      var l=b.getAttribute("data-set-lang"); root.setAttribute("data-lang",l);
      root.querySelectorAll(".lang-btn").forEach(function(x){
        x.setAttribute("aria-pressed",String(x.getAttribute("data-set-lang")===l));});});});});
})();
"""
    css_extra = """
<style data-skel="fixo">
.conversa{border:1px solid var(--linha,#3336);border-radius:6px;margin:.6rem 0;padding:.3rem .6rem}
.conversa>summary{cursor:pointer;font-weight:600;display:flex;gap:.6rem;align-items:center;flex-wrap:wrap}
.conversa pre{white-space:pre-wrap;word-break:break-word;overflow-x:auto;font-size:.86rem;
  padding:.5rem .7rem;border-radius:4px;background:var(--cod-bg,#0002)}
.ficha{width:100%;border-collapse:collapse;font-size:.82rem;margin:.5rem 0}
.ficha th{text-align:left;width:12rem;font-weight:600;opacity:.75;padding:.15rem .4rem;vertical-align:top}
.ficha td{padding:.15rem .4rem;word-break:break-word}
.selo{font-size:.72rem;padding:.1rem .45rem;border-radius:99px;font-weight:700}
.selo-corte{background:#a33;color:#fff}
.selo-indef{background:#a80;color:#fff}
.chars{margin-left:auto;font-size:.75rem;opacity:.6;font-weight:400}
.turno{margin:.35rem 0;border-left:3px solid var(--linha,#3336);padding-left:.6rem}
.turno .rot{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;opacity:.65}
.turno-tool_use{border-left-color:#48a}
.turno-tool_result{border-left-color:#4a8}
.aviso{color:#c62;font-size:.82rem;margin:.3rem 0}
.resumo{font-size:.9rem;opacity:.85}
.lang-switch{display:flex;gap:.4rem;margin:.5rem 0 1rem}
.lang-btn{cursor:pointer;padding:.25rem .7rem;border-radius:4px}
.lang-btn[aria-pressed=false]{opacity:.5}
[data-lang=pt] [lang=en],[data-lang=en] [lang=pt-BR]{display:none}
</style>
"""
    return (
        "<!DOCTYPE html>\n<html lang=\"pt-BR\">\n<head>\n<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Installed Persona Study — conversas dos modelos, por etapa</title>\n"
        + estilo_canonico(repo) + css_extra +
        "</head>\n<body>\n<div class=\"wrap\">\n"
        "<h1>Conversas dos modelos, por etapa</h1>\n"
        f"<p class='resumo'>{total} conversa(s) em {len(regs_por_etapa)} etapa(s). "
        "Nenhuma resposta foi resumida ou cortada na exibição; cortes ocorridos na geração "
        "estão marcados.</p>\n"
        "<div class=\"tabs\" role=\"tablist\">" + "".join(abas) + "</div>\n"
        + "".join(paineis) +
        "\n</div>\n<script>" + js + "</script>\n</body>\n</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--saida", default=None)
    ap.add_argument("--runs-dir", default=None)
    a = ap.parse_args(argv)

    runs_dir = Path(a.runs_dir) if a.runs_dir else config.RUNS_DIR
    nomes = etapas(runs_dir=runs_dir)
    if not nomes:
        print(f"nenhuma etapa em {runs_dir}/conversas — nada a montar")
        return 1
    dados = {}
    for n in nomes:
        regs = le_etapa(n, runs_dir=runs_dir)
        dados[n] = list(regs)
        if getattr(regs, "invalidas", 0):
            print(f"AVISO: etapa {n} tinha {regs.invalidas} linha(s) invalida(s)")

    saida = Path(a.saida) if a.saida else config.REPO_ROOT / "docs" / "CONVERSAS-DO-ESTUDO.html"
    doc = monta(dados, repo=config.REPO_ROOT)
    _sem_rede(doc)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(doc, encoding="utf-8")
    mb = len(doc.encode("utf-8")) / 1e6
    print(f"[artefato] {saida}  ({mb:.2f} MB, {sum(len(v) for v in dados.values())} conversas)")
    if mb > TETO_ARQUIVO_MB:
        print(f"AVISO: {mb:.1f} MB passa do teto de {TETO_ARQUIVO_MB} MB — considere um "
              "arquivo por etapa antes que a pagina fique impraticavel de abrir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
