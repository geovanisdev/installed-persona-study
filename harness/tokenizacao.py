"""Contagem de tokens em CPU — e a trava que pina o tokenizador pelos BYTES, nao pela revisao.

POR QUE ESTE MODULO EXISTE
--------------------------
As travas que conferem paridade, indice e sequestro de preambulo contam TOKENS, e o
equalizador tambem. Nenhuma delas rodava: o ambiente de verificacao em CPU nao tem
`transformers`, e o unico caminho ate' o tokenizador era `AutoTokenizer.from_pretrained`,
que arrasta a biblioteca inteira. O efeito pratico era que nenhum banco podia ser selado —
a medida existia no papel e nao tinha instrumento.

`tokenizers.Tokenizer.from_file` resolve isso: le um `tokenizer.json` sozinho, offline, sem
pesos e sem `transformers`. O que este modulo acrescenta e' a garantia de que o arquivo lido
e' o mesmo de sempre.

POR QUE A TRAVA E' O HASH, E NAO A REVISAO
-------------------------------------------
Ha' uma divida registrada no programa: nenhum runner pinava a revisao da base no
HuggingFace, e em 2026-07-21 `refs/main` avancou para uma revisao nova e quase trocou o
modelo debaixo do experimento. `harness/model_io.assert_revision` foi a resposta para os
PESOS, e continua correta la'.

Para o TOKENIZADOR ela seria a resposta errada, e a maquina mostra o porque. O cache tem os
dois snapshots, o antigo e o novo. Entre eles:

    tokenizer_config.json    2.095 bytes  ->  3.082 bytes    MUDOU
    tokenizer.json          32.169.626 bytes, sha256 cc8d3a0c...  IDENTICO nos dois

Ou seja: a revisao andou, e nem um token mudou de contagem. Pinar por nome de revisao
abortaria um estudo inteiro por uma alteracao que nao move o numero medido — e um guarda que
para o trabalho sem motivo e' desligado na primeira vez que atrapalha. Na outra direcao, nome
de revisao e' ponteiro mutavel: `refs/main` e' exatamente a coisa que se mexeu sozinha. Ele
nao pode ser a autoridade sobre a propria integridade.

O sha256 do arquivo nao tem nenhum dos dois problemas. Ele identifica os bytes que produzem a
contagem, que e' precisamente o que precisa ficar constante. A revisao continua no selo, mas
como PROVENIENCIA — informacao para quem le o artefato depois —, nunca como criterio.

POR QUE NAO EXISTE DEGRADACAO SILENCIOSA
-----------------------------------------
Se o tokenizador falta, `conta_tokens` LEVANTA. Nao ha' queda para contagem por palavra.
Um selo emitido com contagem aproximada e' pior que selo nenhum: selo nenhum bloqueia o
banco, e um numero aproximado com cara de exato passa pelo gate e contamina tudo que vier
depois. Quem quiser a aproximacao chama `conta_aproximada_por_palavra` pelo nome, e o nome
aparece no diff.

A mesma logica cria uma assimetria deliberada em `tokenizer_disponivel()`, e ela e' o
ponto mais facil de errar neste modulo — ver o docstring da funcao.

CONVENCAO DE CONTAGEM
---------------------
Conta-se com `add_special_tokens=False`, igual a `harness/parity_manifest.py`. Neste
tokenizador o post-processor nao acrescenta nada, entao hoje as duas formas dao o mesmo
numero; fixar a flag e' o que impede que um tokenizador futuro com BOS no post-processor
desloque em silencio toda contagem em +1 e faca a paridade ja' publicada parecer errada.

EQUIVALENCIA PROVADA, NAO SUPOSTA
----------------------------------
Este caminho em CPU nao e' um substituto aproximado do `transformers`: reproduz numero a
numero o que ele produziu. `corpora/PARIDADE.json` foi gerado com `AutoTokenizer` num
ambiente com GPU; recontar as mesmas 400 passagens por aqui da' 36.841 e 37.139 tokens, os
mesmos totais e as mesmas medianas. `tests/test_tokenizacao.py` congela essa igualdade.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from harness import config

# sha256 do `tokenizer.json` do Gemma-4-E4B-it. Conferido em 2026-07-22 nos DOIS snapshots
# presentes no cache local, que sao byte-identicos neste arquivo (ver docstring do modulo).
SHA256_ESPERADO = "cc8d3a0ce36466ccc1278bf987df5f71db1719b9ca6b4118264f45cb627bfe0f"

# Fixada de proposito, e nao deixada no default da biblioteca. Ver "CONVENCAO DE CONTAGEM".
ADD_SPECIAL_TOKENS = False

# Cache do objeto Tokenizer por caminho resolvido. Sao 32 MB de JSON e ~0,9 s de parse:
# carregar por item tornaria inviavel qualquer trava que percorra um banco inteiro.
_CACHE: dict[str, object] = {}


class TokenizerIndisponivel(RuntimeError):
    """Nao ha' tokenizador utilizavel — e a contagem NAO sera' aproximada por baixo do pano.

    Nome proprio porque este erro tem de ser distinguivel na captura: quem chama pode
    legitimamente pular um teste quando o arquivo nao esta' na maquina, e nao pode pular
    quando o arquivo esta' e e' outro. Essa segunda situacao e' `TokenizerDivergente`.
    """


class TokenizerDivergente(TokenizerIndisponivel):
    """O arquivo existe, carrega, e NAO e' o do estudo — as contagens seriam de outro modelo.

    Subclasse de `TokenizerIndisponivel` para que quem so' quer saber "da' para contar?"
    continue com um `except` unico, mas com tipo e mensagem proprios para quem precisa
    separar ausencia de troca. As duas coisas pedem acoes opostas: ausencia se resolve
    apontando o caminho, troca se resolve investigando por que os bytes mudaram.
    """


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _resolve(caminho: str | Path | None) -> Path:
    """Argumento explicito manda; senao, o que `config` leu do ambiente.

    Lido a cada chamada, e nao congelado no import, porque `config.TOKENIZER_PATH` e'
    constante de modulo: os testes recarregam `config` sob ambiente controlado e um valor
    congelado aqui ignoraria a recarga — o mesmo defeito que `test_config_env.py` documenta.
    """
    return Path(caminho) if caminho is not None else Path(config.TOKENIZER_PATH)


def carrega_tokenizer(caminho: str | Path | None = None):
    """Devolve o Tokenizer, conferindo o sha256 ANTES de aceitar o arquivo.

    A conferencia roda no arquivo que sera' de fato carregado — o resolvido agora —, e nao
    no default declarado em `config`. Se alguem apontar `IPS_TOKENIZER` para outro lugar, e'
    esse outro lugar que precisa bater; um guarda que confere o caminho padrao enquanto o
    codigo carrega outro nao guarda nada.

    O hash e' calculado uma vez por caminho, junto com a carga, e o resultado fica no cache.
    Refazer a soma dos 32 MB a cada item custaria mais que a propria tokenizacao.
    """
    p = _resolve(caminho)
    chave = str(p.resolve()) if p.exists() else str(p)
    if chave in _CACHE:
        return _CACHE[chave]

    if not p.is_file():
        raise TokenizerIndisponivel(
            f"tokenizer.json nao encontrado em {p}. Aponte `IPS_TOKENIZER` para o arquivo "
            "do Gemma-4-E4B-it no cache local. A contagem NAO sera' aproximada por palavra: "
            "veja `conta_aproximada_por_palavra` se a aproximacao for mesmo o que se quer."
        )

    obtido = _sha256(p)
    if obtido != SHA256_ESPERADO:
        raise TokenizerDivergente(
            f"sha256 do tokenizador diverge em {p}:\n"
            f"  obtido    {obtido}\n"
            f"  esperado  {SHA256_ESPERADO}\n"
            "Este nao e' o tokenizador sobre o qual as contagens do estudo foram fixadas — "
            "toda paridade, todo indice e todo teto de geracao mudariam de unidade em "
            "silencio. Restaure o arquivo esperado ou registre uma decisao datada mudando o "
            "pre-registro (e refaca `corpora/PARIDADE.json` junto)."
        )

    try:
        from tokenizers import Tokenizer
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise TokenizerIndisponivel(
            "pacote `tokenizers` ausente no ambiente; e' ele que permite contar token em CPU "
            "sem `transformers`"
        ) from exc

    tok = Tokenizer.from_file(str(p))
    _CACHE[chave] = tok
    return tok


def tokenizer_disponivel(caminho: str | Path | None = None) -> bool:
    """Ha' tokenizador para contar? Responde False por AUSENCIA — e LEVANTA por DIVERGENCIA.

    A assimetria e' deliberada e e' a parte deste modulo que mais parece um descuido sem
    esta nota. O uso previsto desta funcao e' `if not tokenizer_disponivel(): skip(...)`.
    Se ela respondesse False tambem quando o hash diverge, um tokenizador TROCADO viraria um
    teste PULADO — verde no relatorio, silencioso, e exatamente o desfecho que a trava existe
    para impedir. Ausencia e' condicao de maquina e merece pulo; troca e' um achado e tem de
    parar o run.

    E' o mesmo criterio de `config.apply_hf_env`, onde o `HF_HOME` da maquina e' respeitado
    porque o estudo nao opina, mas o modo offline e' escrito por cima porque o estudo opina.
    """
    try:
        carrega_tokenizer(caminho)
        return True
    except TokenizerDivergente:
        raise
    except TokenizerIndisponivel:
        return False


def conta_tokens(texto: str, caminho: str | Path | None = None) -> int:
    """Numero de tokens de `texto`. Levanta `TokenizerIndisponivel` se nao houver como contar."""
    tok = carrega_tokenizer(caminho)
    return len(tok.encode(texto, add_special_tokens=ADD_SPECIAL_TOKENS).ids)


def conta_tokens_lote(textos, caminho: str | Path | None = None) -> list[int]:
    """Contagem de uma lista, em uma passada (`encode_batch`).

    Mesmo resultado de chamar `conta_tokens` item a item — `tests/test_tokenizacao.py`
    confere isso —, mas e' a forma usada pelas travas, que percorrem bancos inteiros.
    """
    textos = list(textos)
    if not textos:
        return []
    tok = carrega_tokenizer(caminho)
    return [len(e.ids) for e in tok.encode_batch(textos, add_special_tokens=ADD_SPECIAL_TOKENS)]


def selo_tokenizer(caminho: str | Path | None = None) -> dict:
    """Selo de proveniencia da contagem: com que bytes, de que arquivo, de que revisao.

    Vai junto de todo artefato que reporte numero de tokens. Sem ele, um banco selado nao
    diz com o que foi medido, e a unica forma de descobrir depois e' adivinhar.
    """
    tok = carrega_tokenizer(caminho)
    p = _resolve(caminho)
    return {
        "sha256": SHA256_ESPERADO,  # ja' conferido contra o arquivo por `carrega_tokenizer`
        "caminho": str(p),
        "vocab_size": tok.get_vocab_size(with_added_tokens=True),
        "revisao": _revisao_do_caminho(p),
    }


def _revisao_do_caminho(p: Path) -> str:
    """Revisao inferida do layout do cache (`.../snapshots/<revisao>/tokenizer.json`).

    INFORMATIVA, e so'. Entra no selo como proveniencia legivel; nao e' conferida contra
    nada e nao pode virar criterio — se pudesse, este modulo teria trocado uma trava sobre
    bytes por uma trava sobre o nome de um ponteiro que ja' se mexeu sozinho uma vez.
    """
    pai = p.parent
    return pai.name if pai.parent.name == "snapshots" else ""


def conta_aproximada_por_palavra(texto: str) -> int:
    """Aproximacao por palavras. NUNCA e' usada como reserva automatica — chame pelo nome.

    Existe para que a degradacao tenha um nome que apareca no diff e no code review, em vez
    de acontecer dentro de um `except` em `conta_tokens`. NAO pode alimentar selo, gate nem
    paridade: nestes corpora a razao medida e' de 1,22 a 1,27 token por palavra, e a razao
    DIFERE entre os dois bracos — usar palavra como proxy de token nao adiciona ruido
    parelho, adiciona vies na direcao do braco cujo vocabulario fragmenta menos, que e'
    justamente a comparacao em jogo.
    """
    return len(texto.split())


def limpa_cache() -> None:
    """Esvazia o cache de Tokenizer. Para testes que trocam o caminho entre casos."""
    _CACHE.clear()
