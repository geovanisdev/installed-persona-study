"""O banco de vazamento: schema, pareamento entre os blocos e higiene de lexico.

Um banco de piso so' serve se os itens nao entregarem a resposta. Se um item contem o
vocabulario com que a persona faz o proprio movimento, a base o repete e o piso sobe — e
sobe exatamente na medida em que o efeito do adapter seria lido. Por isso a higiene de
lexico e' teste, e nao recomendacao no README.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BANCO = REPO / "batteries" / "leakage_baseline_items.jsonl"

CAMPOS_OBRIGATORIOS = {"item_id", "bloco", "taxonomia", "movimento_alvo", "prompt",
                       "justificativa_oportunidade", "idioma", "generator"}
CAMPOS_OPCIONAIS = {"lexico_do_usuario"}

BLOCOS = {"oportunidade_estoica": 15, "oportunidade_existencialista": 15,
          "autorreferencia": 6, "neutro_controle": 6}

# Lexico de RESPOSTA: os termos com que as personas fazem o proprio movimento. Nenhum item
# pode conte-los — um item que os traz mede eco, nao vazamento.
LEXICO_DE_RESPOSTA = (
    "dicotomia", "apatheia", "prosoche", "memento mori", "estoic", "socratic",
    "absurdo", "ma-fe", "ma fe", "revolta", "liberdade radical", "consolo metafisico",
    "existencialis", "niilis", "nihilis", "sem lamento", "plano maior",
    "tudo acontece por um motivo",
    "leokadius", "shadowclock",
    # autores do grounding: citar a fonte no item seria entregar a postura pela procedencia
    "nietzsch", "epicteto", "marco aurelio", "seneca", "stirner", "feuerbach",
    "leopardi", "dostoievski", "diogenes",
)

# Formulas que so' podem aparecer na boca do USUARIO, e apenas quando o item as declara.
FORMULAS_DO_USUARIO = ("eu sou assim", "nao tive alternativa", "faz parte de quem eu sou",
                       "e' a minha natureza", "e a minha natureza")


@pytest.fixture(scope="module")
def itens() -> list[dict]:
    return [json.loads(l) for l in BANCO.read_text(encoding="utf-8").splitlines() if l.strip()]


# --- schema ------------------------------------------------------------------
def test_schema_de_todo_item(itens):
    for it in itens:
        faltando = CAMPOS_OBRIGATORIOS - set(it)
        sobrando = set(it) - CAMPOS_OBRIGATORIOS - CAMPOS_OPCIONAIS
        assert not faltando and not sobrando, (it["item_id"], faltando, sobrando)
        assert it["prompt"].strip()
        assert it["justificativa_oportunidade"].strip()
        assert it["idioma"] == "pt-BR"
        assert it["generator"] == "claude-opus-4-8"


def test_ids_unicos(itens):
    ids = [i["item_id"] for i in itens]
    assert len(set(ids)) == len(ids)


def test_prompts_unicos(itens):
    prompts = [i["prompt"] for i in itens]
    assert len(set(prompts)) == len(prompts)


def test_blocos_com_o_tamanho_declarado(itens):
    contagem = {b: sum(1 for i in itens if i["bloco"] == b) for b in BLOCOS}
    assert contagem == BLOCOS, contagem
    assert len(itens) == sum(BLOCOS.values())


def test_movimentos_cobertos_tres_vezes_cada(itens):
    """Tres itens por movimento nos dois lados. Um movimento com um item so' teria piso
    medido em n=1, e a comparacao entre movimentos ficaria refem de um item."""
    for bloco in ("oportunidade_estoica", "oportunidade_existencialista"):
        por_mov: dict[str, int] = {}
        for i in itens:
            if i["bloco"] == bloco:
                por_mov[i["movimento_alvo"]] = por_mov.get(i["movimento_alvo"], 0) + 1
        assert len(por_mov) == 5, (bloco, por_mov)
        assert set(por_mov.values()) == {3}, (bloco, por_mov)


def test_movimentos_alvo_existem_nos_nucleos(itens):
    nucleos = {p: json.loads((REPO / "core" / f"{p}.core.json").read_text(encoding="utf-8"))
               for p in ("leokadius", "shadowclock")}
    for i in itens:
        if i["movimento_alvo"] is None:
            assert i["taxonomia"] is None
            continue
        assert i["movimento_alvo"] in nucleos[i["taxonomia"]]["movimentos"], i["item_id"]


# --- higiene de lexico -------------------------------------------------------
def test_nenhum_item_entrega_o_lexico_de_resposta(itens):
    for i in itens:
        alvo = f"{i['prompt']}".lower()
        for termo in LEXICO_DE_RESPOSTA:
            assert termo not in alvo, (i["item_id"], termo)


def test_formula_do_usuario_so_aparece_quando_declarada(itens):
    """A oportunidade de ma-fe EXIGE que o usuario profira a formula. O que nao se admite e'
    a formula entrar sem declaracao: a diferenca entre item desenhado e item descuidado e'
    justamente o registro."""
    for i in itens:
        prompt = i["prompt"].lower()
        declaradas = [f.lower() for f in i.get("lexico_do_usuario", [])]
        for formula in FORMULAS_DO_USUARIO:
            if formula in prompt:
                assert formula in declaradas, (i["item_id"], formula)
        for d in declaradas:
            assert d in prompt, (i["item_id"], d, "declarou formula que nao esta' no prompt")


# --- pareamento entre os blocos ----------------------------------------------
def test_blocos_de_oportunidade_tem_comprimento_equivalente(itens):
    """Um bloco sistematicamente mais longo daria mais superficie para a base emitir postura,
    e a diferenca de piso seria lida como diferenca entre as personas."""
    def palavras(bloco):
        return [len(i["prompt"].split()) for i in itens if i["bloco"] == bloco]
    a = palavras("oportunidade_estoica")
    b = palavras("oportunidade_existencialista")
    ma, mb = statistics.mean(a), statistics.mean(b)
    assert abs(ma - mb) / max(ma, mb) <= 0.15, (ma, mb)
    assert abs(statistics.median(a) - statistics.median(b)) <= 4, (a, b)


def test_proporcao_de_perguntas_diretas_pareada(itens):
    """Item que termina em pergunta convoca resposta de forma diferente de item que so'
    relata. A proporcao entre os dois blocos precisa ser comparavel."""
    def frac(bloco):
        do_bloco = [i for i in itens if i["bloco"] == bloco]
        return sum(1 for i in do_bloco if i["prompt"].rstrip().endswith("?")) / len(do_bloco)
    assert abs(frac("oportunidade_estoica") - frac("oportunidade_existencialista")) <= 0.20


# --- disjuncao ---------------------------------------------------------------
def test_disjunto_dos_bancos_confirmatorios(itens):
    """Enquanto os bancos do S3 nao existem, o teste guarda a regra: se algum aparecer, os
    prompts nao podem se repetir. Um item usado para medir o piso e depois para medir o
    efeito mediria as duas coisas no mesmo lugar."""
    prompts = {i["prompt"].strip().lower() for i in itens}
    for outro in (REPO / "batteries").glob("battery_*.jsonl"):
        for linha in outro.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            item = json.loads(linha)
            p = str(item.get("prompt", "")).strip().lower()
            assert p not in prompts, (outro.name, item.get("item_id"))


def test_bloco_neutro_nao_convoca_postura(itens):
    """O controle so' e' controle se for mesmo neutro. Uma abertura filosofica escondida aqui
    transformaria deriva de registro em efeito medido."""
    convites = ("sentido da vida", "proposito", "morte", "morrer", "deus", "destino",
                "por que existir", "vale a pena viver")
    for i in itens:
        if i["bloco"] != "neutro_controle":
            continue
        for termo in convites:
            assert termo not in i["prompt"].lower(), (i["item_id"], termo)
