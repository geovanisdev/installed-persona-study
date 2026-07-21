"""A classe de defeito que nenhuma outra guarda deste repositorio cobre: o documento que
descreve um artefato e o artefato divergirem.

O CASO QUE FUNDA O MODULO (2026-07-21). `batteries/LEAKAGE_BASELINE.md` terminava com uma secao
inteira declarando que os prompts do banco seguiam "portugues escrito sem acentuacao" e oferecendo
a reversao ao Arquiteto. A reversao foi exercida, os 42 itens foram reescritos acentuados, e a
secao ficou para tras. Durante algum tempo o repositorio publicou um documento afirmando o oposto
do arquivo ao lado.

Nada ficou vermelho, e nao havia como ficar: `tests/test_ortografia.py` verifica a acentuacao dos
ITENS, e `test_leakage_baseline.py` verifica o pareamento dos BLOCOS. Nenhum dos dois le prosa. E
esse e' o ponto — cada peca estava correta isoladamente, e a contradicao so' existia para quem
lesse as duas. E' o defeito mais barato de produzir e o mais caro de detectar.

Este modulo nao tenta ler prosa. Ele confere os NUMEROS e os HASHES que os documentos afirmam,
que sao a parte verificavel de uma afirmacao em portugues. O que ele deliberadamente NAO cobre
esta' declarado no fim do arquivo.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _itens(caminho: Path) -> list[dict]:
    return [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]


# --- LEAKAGE_BASELINE.md: a tabela de blocos bate com o banco? ---------------
def test_tabela_de_blocos_bate_com_o_banco():
    """A tabela do documento e' uma afirmacao sobre o arquivo. Ou ela e' verificada, ou e'
    decoracao que envelhece sem aviso."""
    doc = (REPO / "batteries" / "LEAKAGE_BASELINE.md").read_text(encoding="utf-8")
    real = Counter(i["bloco"] for i in _itens(REPO / "batteries" / "leakage_baseline_items.jsonl"))

    # linhas do tipo:  | `oportunidade_estoica` | 15 (3 x 5 movimentos) | ... |
    declarado = {m.group(1): int(m.group(2))
                 for m in re.finditer(r"^\|\s*`(\w+)`\s*\|\s*(\d+)", doc, re.MULTILINE)}

    assert declarado, "a tabela de blocos sumiu do documento — ou o formato dela mudou"
    assert declarado == dict(real), (
        f"documento diz {declarado}, banco tem {dict(real)} — um dos dois mentiu, e o banco "
        "nao mente porque e' o dado"
    )


def test_total_declarado_no_cabecalho_bate():
    doc = (REPO / "batteries" / "LEAKAGE_BASELINE.md").read_text(encoding="utf-8")
    n = len(_itens(REPO / "batteries" / "leakage_baseline_items.jsonl"))
    assert re.search(rf"\b{n} itens\b", doc), f"o documento nao declara os {n} itens que existem"


# --- SEALS.md: os hashes citados sao os hashes reais? ------------------------
def test_seals_cita_os_hashes_reais_dos_nucleos():
    """SEALS.md e' a cadeia de rastreabilidade inteira: "todo artefato do estudo cita estes dois
    hashes". Um hash errado ali nao quebra nada em execucao — so' quebra a auditoria, e so' para
    quem for conferir."""
    doc = (REPO / "core" / "SEALS.md").read_text(encoding="utf-8")
    for persona in ("leokadius", "shadowclock"):
        core = json.loads((REPO / "core" / f"{persona}.core.json").read_text(encoding="utf-8"))
        h = core["core_hash"]
        assert h in doc, f"SEALS.md nao cita o core_hash real de {persona} ({h[:16]}...)"


def test_seals_nao_cita_hash_que_nao_existe_mais():
    """A direcao inversa, que e' a que pega selo antigo esquecido: todo sha256 de 64 hex no
    documento tem de ser um hash de nucleo vivo. Um hash orfao ali e' um selo de uma versao que
    nao existe, e ninguem consegue distinguir os dois olhando."""
    doc = (REPO / "core" / "SEALS.md").read_text(encoding="utf-8")
    vivos = {json.loads((REPO / "core" / f"{p}.core.json").read_text(encoding="utf-8"))["core_hash"]
             for p in ("leokadius", "shadowclock")}
    citados = set(re.findall(r"\b[0-9a-f]{64}\b", doc))
    orfaos = citados - vivos
    assert not orfaos, f"SEALS.md cita hash que nao pertence a nucleo nenhum: {sorted(orfaos)}"


# --- o que este modulo NAO cobre --------------------------------------------
# Nao le prosa e nao tenta. Nao pega:
#   - um documento que descreve corretamente os numeros e erra o ARGUMENTO;
#   - uma secao inteira obsoleta que nao contenha numero nem hash (foi exatamente o caso do
#     LEAKAGE_BASELINE, cuja secao de ortografia nao tinha nem um nem outro — o conserto la' foi
#     editorial, e este modulo so' impede que os NUMEROS envelhecam do mesmo jeito);
#   - divergencia entre as abas PT e EN de um artefato HTML.
# Registrado aqui para que a existencia do arquivo nao seja lida como cobertura que ele nao tem.
