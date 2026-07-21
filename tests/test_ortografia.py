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
    "nao", "voce", "voces", "sao", "entao", "tambem", "alem", "ja", "so", "apos",
    "porem", "estao", "ha", "nucleo",
    "unico", "ultimo", "ultima", "proprio", "propria", "memoria", "historia", "experiencia",
    "consciencia", "existencia", "referencia", "ciencia", "essencia", "influencia",
    "razao", "posicao", "questao", "decisao", "opiniao", "atencao", "intencao",
    "acao", "sensacao", "situacao", "conclusao", "explicacao", "traducao", "geracao",
    "medicos", "familia", "irma", "mae", "seculo", "epoca", "dificil",
    "facil", "possivel", "impossivel", "responsavel", "desconfortavel", "util", "inutil",
    "numeros", "periodo", "periodos", "tecnico", "tecnica",
    "logica", "metafisico", "cosmico", "proposito", "saude", "fe",
)

# PARES MINIMOS LEGITIMOS — fora da lista, e a remocao foi feita DEPOIS de medir.
#
# Achado importado da auditoria do repositorio predecessor (2026-07-21): la', um teste de
# ortografia contou palavras que apareciam "nas duas formas" e pegou `que`/`quê`, `a`/`à`,
# `e`/`é`, `tem`/`têm`, `por`/`pôr` — cuspindo um "83,7% da forma quebrada" que era lixo.
#
# Rodei o mesmo ataque contra ESTA lista e ela tinha o mesmo defeito: sete entradas produziam
# falso positivo em portugues correto, porque a forma sem acento e' uma FLEXAO VERBAL:
#
#     "peco que ele ate o barbante"        ate      <- atar
#     "ele pratica e eu pratico"           pratica  <- praticar
#     "ele duvida de tudo"                 duvida   <- duvidar
#     "divida a conta por tres"            divida   <- dividir
#     "eu publico o resultado"             publico  <- publicar
#     "eu numero as paginas"               numero   <- numerar
#     "o enfermeiro medico o paciente"     medico   <- medicar
#
# As sete sairam. Um blocklist que acusa texto correto e' desligado na primeira vez que
# atrapalha, e teste desligado nao protege nada.
#
# Tambem fora, pelo mesmo motivo: `esta`/`este` (demonstrativos) e `para` (preposicao).
AMBIGUAS_NAO_COBERTAS = {"esta", "este", "para", "ate", "pratica", "pratico", "duvida",
                         "divida", "publico", "numero", "medico", "e", "a", "o"}

# O CRITERIO QUE SOBREVIVE ao ataque dos pares minimos, e que a auditoria recomendou como
# unico confiavel: texto LONGO sem NENHUM acento. Uma frase curta pode legitimamente nao ter
# acento nenhum ("Ah, que beleza"); um paragrafo inteiro sem um unico diacritico, em
# portugues, e' a forma quebrada. Complementa o blocklist em vez de substitui-lo: um pega
# palavra a palavra, o outro pega o texto que escapou de todas elas.
MIN_PALAVRAS_SEM_NENHUM_ACENTO = 15
_ACENTO = re.compile(r"[à-üÀ-Ü]")


def sem_nenhum_acento(texto: str) -> bool:
    """Texto longo o bastante para exigir acento, e sem nenhum."""
    palavras = [p for p in texto.split() if any(c.isalpha() for c in p)]
    return len(palavras) >= MIN_PALAVRAS_SEM_NENHUM_ACENTO and not _ACENTO.search(texto)

# Assinatura do vicio herdado: a origem marcava a vogal acentuada com apostrofo em vez de
# acento (`e'` por "é", `so'` por "só", `esta'` por "está"). Como e' uma convencao e nao um
# erro de digitacao, ela aparece em bloco — e um unico caso ja' denuncia texto copiado da
# forma antiga. A lista de radicais evita casar com aspas simples de citacao.
_APOSTROFO_DA_ORIGEM = re.compile(
    r"\b(e|a|ha|so|ja|la|ca|ate|esta|estao|tera|sera|fe|pe|ate|alem|apos|tres)'"
    r"(?=\s|$|[.,;:!?)\]])")

# Captura o token INTEIRO, sublinhados inclusive, para poder descartar identificadores. Um
# nucleo cita `nao_generico` e `nao_capitula_sob_pressao` no proprio texto de exibicao — sao
# nomes de campo, nao portugues, e cobrar acento deles seria o mesmo erro que cobrar dos
# marcadores `viola_se`. Sem esta distincao o verificador acusaria a nota que EXPLICA a
# distincao, que e' o tipo de falso positivo que faz um teste ser desligado.
_TOKEN = re.compile(r"[\w'à-üÀ-Ü]+")


def _suspeitas(texto: str) -> list[str]:
    achadas = [m.group(0).lower() for m in _TOKEN.finditer(texto)
               if "_" not in m.group(0) and m.group(0).lower() in SEM_ACENTO]
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


# --- o criterio que sobrevive ao ataque dos pares minimos ---------------------
PARES_MINIMOS_LEGITIMOS = (
    "Peco que ele ate o barbante antes de sair.",
    "Ele pratica todo dia e eu pratico aos sabados.",
    "Eu duvido, ele duvida, nos duvidamos.",
    "Divida a conta por tres.",
    "Eu publico o resultado amanha.",
    "Eu numero as paginas a mao.",
)


@pytest.mark.parametrize("frase", PARES_MINIMOS_LEGITIMOS)
def test_blocklist_nao_acusa_flexao_verbal_legitima(frase):
    """A forma SEM acento dessas palavras e' verbo, nao erro.

    Importado da auditoria do repo predecessor, onde um teste equivalente contou `que`/`quê`,
    `a`/`à`, `tem`/`têm` como defeito e produziu um numero que era lixo. Rodei o mesmo ataque
    aqui e sete entradas cairam. Nota: estas frases estao propositalmente SEM acento em outras
    palavras — o que se testa e' que o BLOCKLIST nao dispara nelas, nao que sejam bom portugues.
    """
    palavra_alvo = {p.strip(".,").lower() for p in frase.split()} & AMBIGUAS_NAO_COBERTAS
    assert palavra_alvo, "a frase de teste perdeu a palavra ambigua"
    assert not _suspeitas(frase), f"falso positivo em flexao verbal: {_suspeitas(frase)}"


def test_criterio_de_texto_longo_pega_o_que_o_blocklist_deixa_passar():
    """Complementaridade dos dois criterios, demonstrada nos dois sentidos."""
    # frase curta legitima sem acento: NENHUM criterio acusa
    curta = "Ah, que beleza."
    assert not _suspeitas(curta) and not sem_nenhum_acento(curta)

    # paragrafo longo na forma quebrada, escolhido para NAO conter nenhuma palavra do
    # blocklist: so' o criterio de texto longo o pega
    longo = ("O sistema recebe o texto do usuario e devolve uma resposta escrita com base "
             "no material de treino, sem nenhum tipo de memoria persistente entre sessoes "
             "distintas de uso continuado.")
    assert sem_nenhum_acento(longo)


@pytest.mark.parametrize("persona", list(CORES))
def test_nucleo_sem_paragrafo_longo_sem_acento(persona):
    core = json.loads(CORES[persona].read_text(encoding="utf-8"))
    ruins = [campo for campo, texto in _textos_de_exibicao(core) if sem_nenhum_acento(texto)]
    assert not ruins, ruins


# O criterio de texto longo TAMBEM tem falso positivo, e o primeiro apareceu no proprio banco.
# `lb-est-08` tem 23 palavras e nenhum acento — e esta' CORRETO: "Meu melhor amigo ficou rico e
# eu sinto inveja toda vez que a gente se encontra. Detesto sentir isso e mesmo assim sinto."
# Nao ha' uma palavra ali que peca acento. Portugues permite paragrafos inteiros assim; e' raro,
# nao impossivel.
#
# NAO subi o limiar de 15 para 24 palavras. Subir seria escolher o numero olhando o item que
# falhou — ajustar o instrumento no dado, que e' a violacao registrada na Regra 2 do
# pre-registro. A saida honesta e' uma excecao NOMEADA, com o motivo escrito: o guarda continua
# vivo para todo item novo, e a excecao documenta que o criterio erra.
REVISADOS_SEM_ACENTO_LEGITIMO = {
    "lb-est-08": "23 palavras, nenhuma delas exige acento em portugues. Conferido a mao.",
}


def test_itens_do_banco_sem_texto_longo_sem_acento():
    itens = [json.loads(l) for l in BANCO.read_text(encoding="utf-8").splitlines() if l.strip()]
    ruins = [i["item_id"] for i in itens
             if sem_nenhum_acento(i["prompt"]) and i["item_id"] not in REVISADOS_SEM_ACENTO_LEGITIMO]
    assert not ruins, (
        f"itens longos sem nenhum acento: {ruins}. Se forem portugues correto, acrescente a "
        "REVISADOS_SEM_ACENTO_LEGITIMO com o motivo — NAO mexa no limiar."
    )


def test_excecoes_de_ortografia_continuam_valendo():
    """Excecao nomeada que deixou de ser necessaria vira lixo silencioso: o teste avisa."""
    itens = {i["item_id"]: i for i in
             (json.loads(l) for l in BANCO.read_text(encoding="utf-8").splitlines() if l.strip())}
    for item_id, motivo in REVISADOS_SEM_ACENTO_LEGITIMO.items():
        assert item_id in itens, f"excecao para item inexistente: {item_id}"
        assert sem_nenhum_acento(itens[item_id]["prompt"]), (
            f"{item_id} nao dispara mais o criterio — remova a excecao ({motivo})")
