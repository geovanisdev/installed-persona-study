"""O artefato de conversas: nada resumido, nada de rede, e o corte sempre visivel.

O teste que carrega o modulo e' `test_a_resposta_sai_INTEIRA`: o artefato se chama
"respostas completas", e um builder que trunca para caber e' pior que builder nenhum, porque
o leitor nao tem como saber que faltou pedaco.

O segundo em importancia e' `test_url_dentro_do_texto_da_conversa_nao_e_rede`. A primeira
versao da trava de zero-rede procurava `https?://` no documento inteiro e abortou por causa
de tres URLs que estavam DENTRO da resposta de um modelo — conteudo escapado, inerte. Trava
que acusa o conteudo em vez do continente nao protege nada e ensina a desliga-la.
"""

from __future__ import annotations

import json

import pytest

from harness.build_conversas_html import _sem_rede, monta
from harness.conversa_log import abre_etapa, le_etapa

META = {"data": "2026-07-22 03:00:00", "git_commit": "abc1234", "git_dirty": False,
        "modelo": "google/gemma-4-E4B-it", "core_hash": "67d4819533f2e360"}


@pytest.fixture()
def repo():
    from harness import config
    return config.REPO_ROOT


def _dados(tmp_path, **kw):
    with abre_etapa("S5_geracao", runs_dir=tmp_path, run_meta=META) as reg:
        reg.registra(papel="base_nua", resposta_completa=kw.get("resp", "Resposta curta."),
                     prompt_completo="Quem é você?", item_id="v1-sup-01",
                     invariante="nao_finge_humano", persona="leokadius",
                     truncada=kw.get("truncada", False))
    return {"S5_geracao": list(le_etapa("S5_geracao", runs_dir=tmp_path))}


# --- O TESTE QUE CARREGA O MODULO --------------------------------------------
def test_a_resposta_sai_INTEIRA(tmp_path, repo):
    gigante = "Ω " * 30000                       # 60k caracteres, com nao-ASCII
    doc = monta(_dados(tmp_path, resp=gigante), repo=repo)
    assert doc.count("Ω") == 30000, "o builder perdeu texto pelo caminho"


def test_url_dentro_do_texto_da_conversa_nao_e_rede(tmp_path, repo):
    resp = ("Falhou com OSError: We couldn't connect to 'https://huggingface.co' — "
            "ver https://exemplo.org/paper e http://outro.example")
    doc = monta(_dados(tmp_path, resp=resp), repo=repo)
    _sem_rede(doc)                                # nao pode levantar
    assert "huggingface.co" in doc                # e o texto continua la'


@pytest.mark.parametrize("veneno", [
    '<link rel="stylesheet" href="https://cdn.exemplo/x.css">',
    '<script src="https://unpkg.com/x"></script>',
    '<img src="https://exemplo/x.png">',
    "@import url('https://fonts.googleapis.com/x');",
    '<iframe></iframe>',
])
def test_rede_de_verdade_aborta(veneno):
    with pytest.raises(SystemExit, match="referencia de rede"):
        _sem_rede("<html><body>" + veneno + "</body></html>")


def test_o_corte_aparece_como_selo(tmp_path, repo):
    """Resposta cortada pelo teto registrada como se fosse completa destroi a comparacao."""
    doc = monta(_dados(tmp_path, truncada=True), repo=repo)
    assert "resposta cortada pelo teto" in doc


def test_truncada_indefinida_tambem_aparece(tmp_path, repo):
    with abre_etapa("x", runs_dir=tmp_path, run_meta=META) as reg:
        # `None` DECLARADO — omitir passou a levantar em 2026-07-22.
        reg.registra(papel="gerador", resposta_completa="oi", truncada=None)
    doc = monta({"x": list(le_etapa("x", runs_dir=tmp_path))}, repo=repo)
    assert "não se sabe se cortou" in doc


def test_uma_aba_por_etapa(tmp_path, repo):
    for nome in ("S3_autoria", "S5_geracao", "S6_juiz"):
        with abre_etapa(nome, runs_dir=tmp_path, run_meta=META) as reg:
            reg.registra(papel="gerador", resposta_completa=f"resposta de {nome}",
                         truncada=False)
    dados = {n: list(le_etapa(n, runs_dir=tmp_path))
             for n in ("S3_autoria", "S5_geracao", "S6_juiz")}
    doc = monta(dados, repo=repo)
    for nome in dados:
        assert f"id='p-{nome}'" in doc
    # abas das 3 etapas + Explicador + Machine-readable
    assert doc.count("class='tab-btn'") == 5


def test_html_do_conteudo_e_escapado(tmp_path, repo):
    """Resposta de modelo com marcacao nao pode virar marcacao da pagina."""
    doc = monta(_dados(tmp_path, resp="<script>alert(1)</script> & <b>x</b>"), repo=repo)
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in doc


def test_explicador_e_bilingue_em_pares(tmp_path, repo):
    """ADR 0009: pares de slot pt/en, um para um. Ingles faltando e' regressao silenciosa."""
    doc = monta(_dados(tmp_path), repo=repo)
    import re
    # [a-z0-9-] e nao [a-z-]: com a classe sem digito, um slug como `regra8` NAO casa e o
    # par inteiro e' pulado em silencio — a guarda passaria por VACUIDADE. Aconteceu de fato
    # no gerador do relatorio de 2026-07-22, que reportou 6 pares onde havia 8.
    pt = set(re.findall(r"data-slot='exp-([a-z0-9-]+)-pt'", doc))
    en = set(re.findall(r"data-slot='exp-([a-z0-9-]+)-en'", doc))
    assert pt and pt == en, (pt ^ en)


def test_machine_readable_declara_o_que_nao_cobre(tmp_path, repo):
    """Um artefato que nao diz o que deixa de fora e' lido como se cobrisse tudo."""
    import re
    doc = monta(_dados(tmp_path), repo=repo)
    bruto = re.search(r"<pre data-skel='fixo'>(.*?)</pre>", doc, re.S).group(1)
    import html as _h
    mr = json.loads(_h.unescape(bruto))
    assert mr["total_conversas"] == 1
    assert mr["o_que_este_artefato_NAO_cobre"]
    assert "cluster_id" in mr["campos_do_registro"]


def test_indicadores_de_celula_aparecem_mesmo_vazios(tmp_path, repo):
    """"adapter: —" e' informacao (era a base nua); a linha ausente e' ambiguidade."""
    doc = monta(_dados(tmp_path), repo=repo)
    assert "<th>adapter</th><td>—</td>" in doc
    assert "<th>persona</th><td>leokadius</td>" in doc
