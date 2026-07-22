"""A trava do tokenizador so' vale se ela ABORTAR — entao cada guarda aqui tem controle positivo.

Um teste que nao pode acusar nao e' teste. Os guardas de `harness/tokenizacao.py` sao
baratos de escrever e faceis de escrever mortos: um `except` largo demais, um caminho
conferido que nao e' o carregado, um `skip` que engole o achado. Cada trava deste modulo
aparece abaixo com um caso CONSTRUIDO que a faz disparar.

Os controles positivos que nao dependem da maquina usam arquivos temporarios, e sao os que
importam para o requisito de clonar e re-executar. Os que dependem do cache local de pesos
sao PULADOS quando o cache nao existe — mas nunca quando existe e diverge, que e' o caso em
que pular seria mentir.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness import config, tokenizacao
from harness.tokenizacao import (
    SHA256_ESPERADO,
    TokenizerDivergente,
    TokenizerIndisponivel,
    conta_aproximada_por_palavra,
    conta_tokens,
    conta_tokens_lote,
    selo_tokenizer,
    tokenizer_disponivel,
)

REPO = Path(__file__).resolve().parents[1]

# Contagens congeladas, medidas em 2026-07-22 com o tokenizador pinado. Incluem par com e sem
# acento de proposito: a Regra 3 do pre-registro observa que acentuacao CUSTA token, e uma
# tabela so' sem acento nao pegaria uma troca de tokenizador que mexesse nos diacriticos.
TEXTOS_CONHECIDOS = {
    "": 0,
    "a": 1,
    "Ola, mundo.": 4,
    "Olá, mundo.": 4,
    "O sábio não se perturba com o que não depende dele.": 15,
}


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Cada caso comeca sem cache: os casos trocam de caminho entre si."""
    tokenizacao.limpa_cache()
    yield
    tokenizacao.limpa_cache()


def _tokenizer_real() -> Path:
    p = Path(config.TOKENIZER_PATH)
    if not p.is_file():
        pytest.skip(f"tokenizer.json ausente nesta maquina ({p})")
    return p


# --- controles positivos que nao dependem da maquina --------------------------
def test_hash_errado_aborta_e_a_mensagem_diz_os_dois_hashes(tmp_path: Path):
    """CONTROLE POSITIVO da trava de hash: arquivo com outros bytes tem de derrubar a carga.

    Confere tambem o CONTEUDO da mensagem. Quem for lidar com esta falha as 3h da manha
    precisa dos dois hashes na tela — sem eles a mensagem diz que algo mudou e nao diz o que,
    e a primeira reacao vira apagar o cache, que destroi a evidencia.
    """
    falso = tmp_path / "tokenizer.json"
    falso.write_text('{"nao": "sou o tokenizador do estudo"}', encoding="utf-8")

    with pytest.raises(TokenizerDivergente) as exc:
        conta_tokens("qualquer coisa", caminho=falso)

    msg = str(exc.value)
    assert SHA256_ESPERADO in msg, "a mensagem nao diz qual hash era esperado"
    assert "obtido" in msg and "esperado" in msg
    assert str(falso) in msg, "a mensagem nao nomeia o arquivo concreto que falhou"


def test_arquivo_ausente_levanta_indisponivel(tmp_path: Path):
    """CONTROLE POSITIVO da trava de ausencia."""
    with pytest.raises(TokenizerIndisponivel) as exc:
        conta_tokens("texto", caminho=tmp_path / "nao_existe" / "tokenizer.json")
    assert "nao encontrado" in str(exc.value)


def test_conta_tokens_nunca_cai_para_contagem_por_palavra(tmp_path: Path):
    """O defeito que este modulo existe para impedir: um numero aproximado com cara de exato.

    Nao basta que a excecao exista — tem de NAO haver caminho que devolva int quando o
    tokenizador falta. Um `except` de conveniencia dentro de `conta_tokens` produziria um
    selo aparentemente valido, e selo aproximado passa no gate e contamina tudo depois.
    """
    texto = "cinco palavras neste texto aqui"
    ausente = tmp_path / "vazio" / "tokenizer.json"

    with pytest.raises(TokenizerIndisponivel):
        resultado = conta_tokens(texto, caminho=ausente)
        pytest.fail(f"degradou em silencio e devolveu {resultado!r} em vez de levantar")

    with pytest.raises(TokenizerIndisponivel):
        conta_tokens_lote([texto], caminho=ausente)

    # a aproximacao existe, da' outro numero, e so' vem quando chamada pelo nome
    assert conta_aproximada_por_palavra(texto) == 5


def test_disponivel_e_falso_por_ausencia_e_LEVANTA_por_divergencia(tmp_path: Path):
    """A assimetria de `tokenizer_disponivel`, nas duas direcoes.

    E' o ponto mais facil de quebrar do modulo: bastaria um `except TokenizerIndisponivel`
    devolvendo False para que um tokenizador TROCADO virasse `skip` verde no relatorio, ja'
    que o uso previsto e' `if not tokenizer_disponivel(): skip(...)`. Este teste congela que
    divergencia NAO e' pulavel.
    """
    assert tokenizer_disponivel(caminho=tmp_path / "nada" / "tokenizer.json") is False

    trocado = tmp_path / "tokenizer.json"
    trocado.write_bytes(b"{}")
    with pytest.raises(TokenizerDivergente):
        tokenizer_disponivel(caminho=trocado)


def test_divergente_e_capturavel_como_indisponivel():
    """A hierarquia e' contrato: quem so' quer saber 'da' para contar?' usa um `except` unico."""
    assert issubclass(TokenizerDivergente, TokenizerIndisponivel)
    assert TokenizerDivergente is not TokenizerIndisponivel


def test_lote_vazio_nao_carrega_nada(tmp_path: Path):
    """Lista vazia devolve [] sem exigir tokenizador — evita falha em banco vazio legitimo."""
    assert conta_tokens_lote([], caminho=tmp_path / "nao_existe.json") == []


# --- o tokenizador real -------------------------------------------------------
def test_hash_do_arquivo_real_confere():
    """O arquivo apontado por `IPS_TOKENIZER` e' mesmo aquele sobre o qual o estudo fixou."""
    import hashlib

    p = _tokenizer_real()
    obtido = hashlib.sha256(p.read_bytes()).hexdigest()
    assert obtido == SHA256_ESPERADO, (
        f"o tokenizador em {p} nao e' o do estudo: obtido {obtido}, esperado {SHA256_ESPERADO}"
    )


@pytest.mark.parametrize("texto,esperado", sorted(TEXTOS_CONHECIDOS.items()))
def test_contagem_de_texto_conhecido(texto: str, esperado: int):
    _tokenizer_real()
    assert conta_tokens(texto) == esperado


def test_lote_da_o_mesmo_que_item_a_item():
    _tokenizer_real()
    textos = list(TEXTOS_CONHECIDOS)
    assert conta_tokens_lote(textos) == [conta_tokens(t) for t in textos]


def test_selo_traz_bytes_caminho_e_proveniencia():
    p = _tokenizer_real()
    selo = selo_tokenizer()
    assert selo["sha256"] == SHA256_ESPERADO
    assert Path(selo["caminho"]) == p
    assert selo["vocab_size"] == 262144
    # revisao e' INFORMATIVA: sai do layout do cache e nao e' criterio de nada
    assert selo["revisao"] == p.parent.name


# --- o achado que este modulo carrega: revisao andou, tokenizador nao ----------
def _snapshots_do_modelo() -> list[Path]:
    raiz = Path(config.TOKENIZER_PATH).parent.parent
    if raiz.name != "snapshots":
        pytest.skip("tokenizador fora do layout de cache do HuggingFace")
    return sorted(p for p in raiz.glob("*/tokenizer.json") if p.is_file())


def test_os_dois_snapshots_dao_a_mesma_contagem():
    """A DERIVA DE REVISAO NAO MEXEU NO TOKENIZADOR — e e' por isso que a trava e' o hash.

    Em 2026-07-21 `refs/main` avancou e quase trocou o modelo debaixo do experimento. O cache
    guarda os dois snapshots, e entre eles `tokenizer_config.json` mudou de tamanho enquanto
    `tokenizer.json` ficou byte-identico. Uma trava por NOME DE REVISAO teria abortado o
    estudo por uma mudanca que nao move um unico numero medido — e guarda que para o trabalho
    a toa e' desligado na primeira vez que atrapalha.

    O teste e' pulado quando ha' um snapshot so'; nao e' pulado quando ha' dois e discordam.
    """
    snaps = _snapshots_do_modelo()
    if len(snaps) < 2:
        pytest.skip(f"apenas {len(snaps)} snapshot no cache; nada a comparar")

    textos = list(TEXTOS_CONHECIDOS)
    referencia = conta_tokens_lote(textos, caminho=snaps[0])

    # anti-vacuidade: se `textos` esvaziasse, duas listas vazias "coincidiriam" e o teste
    # passaria sem comparar nada — o modo de falha classico de um guarda de igualdade
    assert len(referencia) == len(textos) >= 3 and sum(referencia) > 0

    for snap in snaps[1:]:
        assert conta_tokens_lote(textos, caminho=snap) == referencia, (
            f"snapshot {snap.parent.name} conta diferente de {snaps[0].parent.name} — "
            "a revisao passou a importar e a constante de hash precisa ser revista"
        )


# --- equivalencia com o caminho `transformers` --------------------------------
def test_reproduz_o_manifesto_de_paridade_gerado_com_transformers():
    """A prova de que este caminho em CPU NAO e' uma aproximacao do `AutoTokenizer`.

    `corpora/PARIDADE.json` foi gerado com `transformers` num ambiente com GPU e esta'
    commitado. Recontar as mesmas 400 passagens por aqui tem de dar os mesmos totais. Se der
    diferente, todas as travas que contam token estao medindo numa unidade que nao e' a que o
    modelo consome — e a paridade publicada no pre-registro seria outra.
    """
    _tokenizer_real()
    manifesto = json.loads((REPO / "corpora" / "PARIDADE.json").read_text(encoding="utf-8"))

    for persona, ref in manifesto["personas"].items():
        linhas = (REPO / "corpora" / ref["arquivo"]).read_text(encoding="utf-8").splitlines()
        passagens = [json.loads(l)["passage"] for l in linhas if l.strip()]
        assert len(passagens) == ref["n_passagens"], f"{persona}: corpus mudou de tamanho"

        contagens = conta_tokens_lote(passagens)
        assert sum(contagens) == ref["tokens"], (
            f"{persona}: total {sum(contagens)} contra {ref['tokens']} no manifesto"
        )
        assert sorted(contagens)[len(contagens) // 2] == ref["tokens_por_passagem_mediana"], (
            f"{persona}: mediana por passagem divergiu do manifesto"
        )


def test_reproduz_os_numeros_de_preambulo_do_preregistro():
    """Os numeros que o pre-registro PUBLICA (Regra 3), remedidos por este caminho.

    1.379 contra 1.304 caracteres, 358 contra 330 tokens. Sao numeros que ja' estao escritos
    num documento publico: se este modulo os contradissesse, ou o documento esta' errado ou o
    instrumento esta'. Congelar aqui e' o que mantem os dois amarrados.
    """
    _tokenizer_real()
    from harness.persona_core import build_preamble, load_core

    esperado = {"leokadius": (1379, 358), "shadowclock": (1304, 330)}
    for persona, (chars, tokens) in esperado.items():
        preambulo = build_preamble(load_core(REPO / "core" / f"{persona}.core.json"))
        assert len(preambulo) == chars, f"{persona}: preambulo mudou de tamanho em caracteres"
        assert conta_tokens(preambulo) == tokens, (
            f"{persona}: {conta_tokens(preambulo)} tokens contra {tokens} publicados na Regra 3"
        )


# --- controle positivo com tokenizadores REAIS de outros modelos --------------
def _outros_tokenizadores() -> list[Path]:
    raiz = Path(config.TOKENIZER_PATH).parents[3]
    alvo = Path(config.TOKENIZER_PATH).parents[2].name
    if raiz.name != "hub":
        pytest.skip("cache fora do layout `hub/models--*/snapshots/*`")
    outros = [p for p in raiz.glob("models--*/snapshots/*/tokenizer.json")
              if p.parents[2].name != alvo]
    if not outros:
        pytest.skip("nenhum tokenizador de outro modelo no cache local")
    return sorted(outros)


def test_tokenizador_de_outro_modelo_e_recusado_mesmo_quando_conta_igual():
    """CONTROLE POSITIVO com arquivos reais — e a razao de a trava ser hash, nao amostragem.

    Ha' no cache tokenizadores de outros modelos, e eles se dividem em dois tipos:

    * os de outra familia (Qwen, Tucano) contam DIFERENTE — na frase de teste, 17 e 13 contra
      15. Usar um deles trocaria a unidade de toda paridade sem nenhum sinal visivel;
    * o do gemma-4-E4B-it ABLITERADO tem outro sha256 e, na mesma frase, conta IGUAL.

    O segundo e' o caso que justifica o desenho. Um guarda que conferisse "o tokenizador conta
    certo nesta frase?" aceitaria o arquivo do modelo abliterado — que e' outro modelo, e que
    o programa marca como nunca-deploy. So' o hash separa os dois. O teste exige que TODOS
    sejam recusados, o que conta igual inclusive.
    """
    _tokenizer_real()
    for outro in _outros_tokenizadores():
        with pytest.raises(TokenizerDivergente) as exc:
            conta_tokens("O sábio não se perturba com o que não depende dele.", caminho=outro)
        assert str(outro) in str(exc.value)
