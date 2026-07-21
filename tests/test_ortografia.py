"""Ortografia: todo texto de ESTUDO e' portugues acentuado; chave de casamento nao e'.

PREMISSA CORRIGIDA (Arquiteto, 2026-07-21). A primeira versao deste modulo dizia que "o
pipeline de origem escrevia portugues sem acentuacao". Errado, e o erro subestimava o
problema. A auditoria mostrou que os prompts do corpus (96%), o corpus de conviccoes, as
geracoes do modelo e — decisivo — os ALVOS DE TREINO (`chosen`, 778/780 = 100%) sao todos
acentuados. Sem acento havia UMA camada so': o PREAMBULO. Uma superficie unica e destoante
dentro de um contexto uniforme, nadando contra 100% do alvo de treino e 100% da saida.

E a evidencia dispensa teoria sobre distribuicao de pre-treino: o modelo NUNCA reproduz a
forma sem acento. Na saida da base, "proxima solicitacao" aparece 0 vezes e "proxima
solicitacao" acentuada aparece 6. Ele normaliza sempre. Logo escrever o preambulo capenga
nao compra nada — nao e' reproduzido, nao e' preservado, e paga o risco de destoar do
contexto inteiro (ver `PREREGISTRATION.md`, Regras 4 e 5).

TRES CLASSES, e a distincao e' o conteudo deste modulo:

  texto de ESTUDO      o que o modelo le e o que o leitor le -> acentuado, sempre
  chave de CASAMENTO   `viola_se`, comparada contra texto ja' normalizado por
                       `normalize_text` (minusculas, sem acento) -> forma normalizada,
                       porque acentuada nunca casaria
  fixture de FIDELIDADE  strings congeladas na forma da origem para que um golden
                       permaneca reproduzivel -> intocada, e declarada onde vive
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from harness.persona_core import build_preamble

REPO = Path(__file__).resolve().parents[1]
CORES = {p: REPO / "core" / f"{p}.core.json" for p in ("leokadius", "shadowclock")}
BANCO = REPO / "batteries" / "leakage_baseline_items.jsonl"

# Palavras portuguesas comuns cuja forma correta EXIGE acento. Encontrar qualquer uma delas
# sem acento em texto de estudo e' o sintoma do vicio herdado. A lista e' de alta frequencia
# de proposito: nao pretende cobrir o idioma, pretende pegar a recaida.
SEM_ACENTO = (
    "nao", "voce", "voces", "sao", "entao", "tambem", "alem", "ja", "so", "ate", "apos",
    "porem", "estao", "ha", "nucleo", "publico",
    "unico", "ultimo", "ultima", "proprio", "propria", "memoria", "historia", "experiencia",
    "consciencia", "existencia", "referencia", "ciencia", "essencia", "influencia",
    "razao", "posicao", "postura'", "questao", "decisao", "opiniao", "atencao", "intencao",
    "acao", "sensacao", "situacao", "conclusao", "explicacao", "traducao", "geracao",
    "medico", "medicos", "familia", "irma", "mae", "pai'", "seculo", "epoca", "dificil",
    "facil", "possivel", "impossivel", "responsavel", "desconfortavel", "util", "inutil",
    "numero", "numeros", "periodo", "periodos", "tecnico", "tecnica", "pratica", "pratico",
    "logica", "metafisico", "cosmico", "proposito", "duvida", "saude", "divida", "fe",
)
# FORA da lista de proposito: `esta` e `este` sao pronomes demonstrativos legitimos sem
# acento ("esta lista esta' congelada" tem uma de cada), e nenhuma lista resolve isso sem
# analise sintatica. Um blocklist que gera falso positivo em texto correto e' abandonado na
# primeira vez que atrapalha — e um teste abandonado nao protege nada. A escolha aqui e'
# cobrir o que e' INEQUIVOCO e deixar o ambiguo para revisao humana.
AMBIGUAS_NAO_COBERTAS = {"esta", "este", "para", "e", "a", "o"}

# Assinatura do vicio herdado: a origem marcava a vogal acentuada com apostrofo em vez de
# acento (`e'` por "é", `so'` por "só", `esta'` por "está"). Como e' uma convencao e nao um
# erro de digitacao, ela aparece em bloco — e um unico caso ja' denuncia texto copiado da
# forma antiga. A lista de radicais evita casar com aspas simples de citacao.
_APOSTROFO_DA_ORIGEM = re.compile(
    r"\b(e|a|ha|so|ja|la|ca|ate|esta|estao|tera|sera|fe|pe|ate|alem|apos|tres)'"
    r"(?=\s|$|[.,;:!?)\]])")

_PALAVRA = re.compile(r"[a-zA-Zà-üÀ-Ü]+")


def _suspeitas(texto: str) -> list[str]:
    achadas = [m.group(0).lower() for m in _PALAVRA.finditer(texto)
               if m.group(0).lower() in SEM_ACENTO]
    achadas += [f"{m.group(1)}' (apostrofo da origem)"
                for m in _APOSTROFO_DA_ORIGEM.finditer(texto)]
    return achadas


# --- texto de estudo: os nucleos ---------------------------------------------
def _textos_de_exibicao(core: dict):
    """Tudo o que e' texto para ler. Exclui identificadores e chaves de casamento."""
    for campo in ("nota_construto", "nota_ortografia", "nota_regua_lexica",
                  "natureza_substrato", "frase_ancora", "nota_grounding"):
        if core.get(campo):
            yield campo, core[campo]
    for k, v in (core.get("superficie_postura") or {}).items():
        yield f"superficie_postura.{k}", v
    for inv in core["invariantes_sob_pressao"]:
        yield f"invariante[{inv['id']}].descricao", inv["descricao"]
    for val in core["valores_tracos"]:
        yield f"valor[{val['id']}].nome", val["nome"]
        yield f"valor[{val['id']}].descricao", val["descricao"]
    for i, a in enumerate(core["ancoras_afirmacao"]):
        yield f"ancoras_afirmacao[{i}]", a
    for i, a in enumerate(core["ancoras_dissolucao"]):
        yield f"ancoras_dissolucao[{i}]", a
    yield "sobreposicao_predita.nota", core["sobreposicao_predita"]["nota"]
    yield "personas_contraste.nota", core["personas_contraste"]["nota"]


@pytest.mark.parametrize("persona", list(CORES))
def test_nucleo_em_portugues_acentuado(persona):
    core = json.loads(CORES[persona].read_text(encoding="utf-8"))
    problemas = [(campo, _suspeitas(texto)) for campo, texto in _textos_de_exibicao(core)]
    problemas = [(c, s) for c, s in problemas if s]
    assert not problemas, problemas


@pytest.mark.parametrize("persona", list(CORES))
def test_marcadores_continuam_na_forma_normalizada(persona):
    """O contraponto do teste acima: `viola_se` NAO leva acento, e isso e' correto.

    Se alguem "consertar" a ortografia dos marcadores junto com a do resto, eles param de
    casar em silencio — que e' o pior modo de falha possivel para uma regua, porque marcador
    que nao casa nao falha: passa, e passa como invariante cumprido.
    """
    from harness.persona_core import normalize_text
    core = json.loads(CORES[persona].read_text(encoding="utf-8"))
    for inv in core["invariantes_sob_pressao"]:
        for marcador in inv["viola_se"]:
            assert marcador == normalize_text(marcador), (inv["id"], marcador)


@pytest.mark.parametrize("persona", list(CORES))
def test_preambulo_do_professor_sai_acentuado(persona):
    """O preambulo e' o que o PROFESSOR le na destilacao — a superficie de treino inteira."""
    core = json.loads(CORES[persona].read_text(encoding="utf-8"))
    assert not _suspeitas(build_preamble(core))


# --- texto de estudo: o banco de vazamento -----------------------------------
def test_itens_do_banco_em_portugues_acentuado():
    itens = [json.loads(l) for l in BANCO.read_text(encoding="utf-8").splitlines() if l.strip()]
    problemas = []
    for i in itens:
        for campo in ("prompt", "justificativa_oportunidade"):
            s = _suspeitas(i[campo])
            if s:
                problemas.append((i["item_id"], campo, s))
    assert not problemas, problemas


# --- texto de estudo: os polos ------------------------------------------------
def test_polos_em_portugues_acentuado():
    """Os polos simulam saida de modelo em pt-BR. Se o polo de ruido fosse o unico texto sem
    acento, uma medida poderia separa-lo pela ORTOGRAFIA em vez de pelo conteudo — e passaria
    na validacao pelo motivo errado."""
    from harness import polos
    problemas = [(polo, t, _suspeitas(t))
                 for polo, textos in polos.POLOS.items() for t in textos if _suspeitas(t)]
    assert not problemas, problemas


# --- fixture de fidelidade: declarada, e intocada -----------------------------
def test_filler_do_golden_continua_congelado():
    """NEUTRAL_FILLER reproduz byte a byte a string da origem e e' o que torna o golden com
    pesos reproduzivel. Acentua-la mudaria os token ids e invalidaria uma prova ja' registrada.
    O teste existe para que a excecao seja DECLARADA em vez de parecer descuido."""
    from harness.generation import NEUTRAL_FILLER
    assert NEUTRAL_FILLER == ("Voce e' um assistente. Responda a proxima solicitacao com "
                              "cuidado e no seu proprio modo, sem rodeios.")


def test_filler_malformado_nao_toca_o_estudo():
    """A constante sob suspeita da Regra 5 fica ISOLADA no golden.

    `NEUTRAL_FILLER` e' o preambulo sem acentuacao do projeto de origem — a string que o
    Arquiteto identificou como candidata a causa do eco de preambulo. Ela continua congelada
    porque o golden de fidelidade depende dela byte a byte, mas nao pode ter caminho ate' a
    superficie de medicao: o preambulo do estudo sai de `build_preamble()`, que le do nucleo.

    Congelar e isolar sao coisas diferentes, e este teste guarda a segunda.
    """
    import subprocess
    saida = subprocess.run(
        ["git", "grep", "-l", "NEUTRAL_FILLER", "--", "harness", "analysis", "batteries", "core"],
        cwd=REPO, capture_output=True, text=True).stdout.split()
    permitidos = {"harness/generation.py", "harness/goldens/run_golden_gpu.py"}
    assert set(saida) <= permitidos, (
        f"NEUTRAL_FILLER vazou para fora do golden: {set(saida) - permitidos}")
