"""Constroi os corpora a partir das fontes de dominio publico.

PROVENIENCIA: adaptado de `build_conviccoes_corpus.py` do projeto predecessor. Preserva a
mecanica — front-matter, passagens por acumulacao de sentencas, filtro on-topic por
palavra-chave, descarte de ruido de conversao, dedup — e muda tres coisas:

1. **Movimento por PASSAGEM, nao por arquivo.** No original, cada arquivo-fonte declarava
   um movimento e todas as suas passagens o herdavam. Aqui cada persona tem cinco
   movimentos e apenas tres ou quatro obras: herdar por arquivo deixaria movimentos
   inteiros vazios. A atribuicao passa a ser por passagem, pela contagem de chaves do
   movimento, com desempate deterministico.
2. **Taxonomia vem do NUCLEO**, nao de constante de modulo — o codigo nao conhece persona.
3. **Proveniencia por passagem**: obra, autor, tradutor, ano e o sha256 da fonte viajam
   com o item. Um corpus publicado sem endereco por item e' citacao que ninguem confere.

RECORTE: uma obra pode entrar so' em parte (Diogenes Laercio entra apenas pelo Livro VII,
Zenao e os estoicos). O recorte e' feito aqui, e nao no download, para que o arquivo
baixado permaneca identico a' fonte e o sha256 continue verificavel.

Uso:
    python -m harness.build_corpus --core core/leokadius.core.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from harness import config
from harness.persona_core import normalize_text

# --- Chaves por movimento (fontes em ingles) ---------------------------------
# Uma passagem e' atribuida ao movimento com mais ocorrencias de chave. Chaves foram
# escolhidas para serem tematicas, nao estilisticas: o que se quer selecionar e' o
# ASSUNTO da passagem, nao o tom de quem a escreveu.
CHAVES: dict[str, tuple[str, ...]] = {
    # Leokadius — estoico
    "dicotomia_do_controle": ("in our power", "not in our power", "up to us", "our own power",
                              "depends on us", "within our control", "external things",
                              "things which are not", "not in thy power", "choice"),
    "memento_mori": ("death", "die", "dying", "mortal", "perish", "brief", "short life",
                     "transient", "grave", "tomb", "fleeting"),
    # apatheia e prosoche disputavam o mesmo vocabulario: "tranquil" aparece tanto na
    # discussao das paixoes quanto no tratado sobre a atencao (De Tranquillitate Animi), e
    # o argmax mandava tudo para apatheia. As listas foram desambiguadas — apatheia fica
    # com o dominio das PAIXOES, prosoche com o da ATENCAO E OCUPACAO.
    "apatheia": ("passion", "anger", "grief", "disturb", "unmoved", "desire",
                 "aversion", "perturb", "serenity", "indifferent things"),
    "prosoche": ("attention", "attend", "present moment", "vigilance", "watch over",
                 "the present", "here and now", "mindful", "guard thy", "peace of mind",
                 "tranquillity of mind", "tranquil", "distract", "wander", "occupied",
                 "busied", "engaged in", "employment", "steadiness"),
    "metodo_socratico": ("socrates", "question", "questioning", "dialectic", "inquiry",
                         "refute", "examine", "answer me", "asked him"),
    # Shadowclock — existencialista ateu
    "absurdo": ("absurd", "meaningless", "in vain", "vanity", "nothingness", "illusion",
                "indifferent", "no purpose", "without end", "nature cares"),
    "revolta": ("revolt", "rebel", "defiance", "struggle", "resist", "in spite of",
                "endure", "overcome", "against fate", "say yea"),
    "liberdade_radical": ("freedom", "free will", "free spirit", "choose", "creator",
                          "my own", "self-determination", "master of myself", "unique"),
    "ma_fe": ("self-deception", "deceive", "pretence", "hypocrisy", "excuse", "herd",
              "conform", "duty demands", "they say", "custom"),
    "sem_consolo": ("consolation", "comfort", "god", "heaven", "immortality", "faith",
                    "providence", "solace", "hope of", "eternal life"),
}

# --- Recortes: onde comeca e termina a OBRA dentro do arquivo ----------------
# Os arquivos do catalogo trazem, alem da obra, o aparato de quem a editou: esboco
# biografico, ensaio do tradutor, prefacio editorial, apendice de notas, indice. Passagens
# desse aparato ensinariam a persona a voz de um erudito COMENTANDO a filosofia, e nao a
# voz da filosofia — e o efeito seria confundido com a persona.
#
# O recorte e' aplicado aos DOIS lados: limpar um braco e deixar o outro sujo criaria
# exatamente a assimetria de input que a receita casada existe para impedir.
#
# Convencao: (regex_inicio | None, regex_fim | None). Usa-se a ULTIMA ocorrencia do
# marcador de inicio, porque a primeira costuma ser a entrada do sumario.
RECORTES: dict[str, tuple[str | None, str | None]] = {
    # Leokadius
    "diogenes_laercio_vidas": (r"BOOK\s+VII\b", r"BOOK\s+VIII\b"),          # so' Zenao/estoicos
    "marco_aurelio_pensamentos": (r"(?m)^THE THOUGHTS\s*$", r"(?m)^INDEX OF TERMS"),
    "seneca_dialogos_menores": (r"WHEN A PROVIDENCE EXISTS", r"(?m)^INDEX\.\s*$"),
    # A nota biografica de Long sobre Epicteto (~2.500 palavras de erudicao vitoriana sobre
    # a VIDA do filosofo) precede a obra. O titulo aparece duas vezes: no sumario, indentado,
    # e como cabecalho do corpo — a ancora de inicio de linha pega so' o segundo.
    "epicteto_discourses_enchiridion": (
        r"(?m)^A SELECTION FROM THE DISCOURSES OF EPICTETUS\.\s*$", None),
    # Shadowclock
    "nietzsche_zaratustra": (None, r"(?m)^APPENDIX\."),                     # apendice = notas do tradutor
    "nietzsche_gaia_ciencia": (r"PREFACE TO THE SECOND", r"(?m)^\s*APPENDIX\s*$"),
    "nietzsche_alem_do_bem_e_do_mal": (r"(?m)^PREFACE\s*$", None),
    "stirner_o_unico": (r"ALL THINGS ARE NOTHING TO ME", r"(?m)^INDEX\s*$"),
    "feuerbach_essencia_cristianismo": (r"(?m)^PREFACE TO THE SECOND EDITION", None),
    "dostoievski_subsolo": (r"(?m)^PART I\s*$", None),
    # O esboco biografico de Edwardes sobre Leopardi tem a mesma natureza da nota de Long:
    # um tradutor do sec. XIX contando a vida do autor. Fica de fora pelos dois lados.
    "leopardi_ensaios_dialogos": (r"(?m)^_HISTORY OF THE HUMAN RACE\._",
                                  r"(?m)^THE END\.\s*$"),
}

_NOISE = re.compile(
    r"^\s*(\d+[\.\)]|\[?\d+\]?\s|isbn|doi|http|vol\.|pp\.|chapter\s+\d+\s*$|"
    r"footnote|transcriber|illustration|contents\s*$)", re.IGNORECASE)
_SENT = re.compile(r"(?<=[\.\?\!])\s+")

MIN_PALAVRAS, MAX_PALAVRAS = 60, 400


def _norm(s: str) -> str:
    s = s.lower()
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def parse_front_matter(texto: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    corpo = texto
    if texto.lstrip().startswith("---"):
        partes = texto.split("---", 2)
        if len(partes) >= 3:
            for linha in partes[1].splitlines():
                if ":" in linha:
                    k, _, v = linha.partition(":")
                    meta[k.strip()] = v.strip()
            corpo = partes[2]
    return meta, corpo


def aplica_recorte(slug: str, corpo: str) -> str:
    """Corta a obra na secao relevante, quando ha' recorte declarado."""
    if slug not in RECORTES:
        return corpo
    ini_re, fim_re = RECORTES[slug]
    ini = 0
    if ini_re:
        mi = list(re.finditer(ini_re, corpo))
        if not mi:
            raise ValueError(
                f"recorte de {slug}: marcador de inicio {ini_re!r} nao encontrado. "
                "Um recorte que falha em silencio deixaria o aparato editorial no corpus."
            )
        # A ultima ocorrencia e' o corpo da obra; as anteriores costumam ser o sumario.
        ini = mi[-1].start()
    fim = len(corpo)
    if fim_re:
        mf = re.search(fim_re, corpo[ini:])
        if not mf:
            raise ValueError(f"recorte de {slug}: marcador de fim {fim_re!r} nao encontrado")
        fim = ini + mf.start()
    return corpo[ini:fim]


def passagens(corpo: str, alvo_palavras: int = 120) -> list[str]:
    """Passagens de tamanho-grounding por acumulacao de SENTENCAS.

    Acumular sentencas (em vez de cortar por linha ou paragrafo) e' robusto ao estilo de
    conversao: as fontes vem com quebras de linha fixas, sem paragrafos confiaveis.
    """
    fluxo = corpo.replace("-\n", "").replace("\r", " ")
    fluxo = re.sub(r"\s+", " ", fluxo).strip()
    if not fluxo:
        return []
    saida, buf, n = [], [], 0
    for s in _SENT.split(fluxo):
        s = s.strip()
        if not s:
            continue
        w = len(s.split())
        if w > MAX_PALAVRAS:      # sentenca gigante = lixo de conversao
            continue
        buf.append(s)
        n += w
        if n >= alvo_palavras:
            saida.append(" ".join(buf))
            buf, n = [], 0
    if buf and n >= MIN_PALAVRAS:
        saida.append(" ".join(buf))
    return saida


def _proporcao_digitos(s: str) -> float:
    return sum(c.isdigit() for c in s) / len(s) if s else 1.0


def atribui_movimento(passagem: str, movimentos: list[str]) -> tuple[str | None, int]:
    """Movimento com mais chaves presentes. Empate resolve pela ordem do nucleo."""
    norm = _norm(passagem)
    melhor, melhor_n = None, 0
    for mov in movimentos:
        n = sum(norm.count(_norm(k)) for k in CHAVES.get(mov, ()))
        if n > melhor_n:
            melhor, melhor_n = mov, n
    return melhor, melhor_n


def _registro(passagem: str) -> str:
    return "dialogico" if passagem.count("?") >= 2 else "argumentativo"


def extrai(caminho: Path, movimentos: list[str]) -> list[dict]:
    meta, corpo = parse_front_matter(caminho.read_text(encoding="utf-8"))
    corpo = aplica_recorte(caminho.stem, corpo)
    vistos: set[str] = set()
    saida = []
    for p in passagens(corpo):
        n = len(p.split())
        if n < MIN_PALAVRAS or n > MAX_PALAVRAS:
            continue
        if _NOISE.match(p) or _proporcao_digitos(p) > 0.20:
            continue
        mov, forca = atribui_movimento(p, movimentos)
        if mov is None:
            continue
        chave = normalize_text(p)[:80]
        if chave in vistos:
            continue
        vistos.add(chave)
        saida.append({
            "source_type": "filosofia",
            "source": meta.get("obra", caminho.stem),
            "author": meta.get("autor", "?"),
            "tradutor": meta.get("tradutor", "?"),
            "ano_traducao": meta.get("ano_traducao", "?"),
            "lingua": meta.get("lingua", "?"),
            "movimento": mov,
            "forca_movimento": forca,
            "registro": _registro(p),
            "passage": p,
            "locator": caminho.stem,
            "sha256_fonte": meta.get("sha256", ""),
        })
    return saida


def equilibra(itens: list[dict], por_movimento: int, teto_por_obra: float) -> list[dict]:
    """Seleciona ate' `por_movimento` itens de cada movimento, respeitando o teto por obra.

    Ordena por forca do movimento (passagem mais on-topic primeiro) e depois pelo locator,
    para ser deterministico. O teto por obra existe porque uma unica obra dominando o
    corpus faria a persona aprender aquele autor, e nao o movimento.
    """
    movimentos = sorted({i["movimento"] for i in itens})

    def seleciona(max_por_obra: int) -> list[dict]:
        escolhidos: list[dict] = []
        usados: Counter = Counter()
        for mov in movimentos:
            candidatos = sorted((i for i in itens if i["movimento"] == mov),
                                key=lambda i: (-i["forca_movimento"], i["locator"],
                                               i["passage"][:40]))
            n = 0
            for item in candidatos:
                if n >= por_movimento:
                    break
                if usados[item["locator"]] >= max_por_obra:
                    continue
                escolhidos.append(item)
                usados[item["locator"]] += 1
                n += 1
        return escolhidos

    # O teto por obra vale sobre o corpus REALIZADO, nao sobre a meta: quando um movimento
    # nao atinge a meta, o total encolhe e uma obra que cabia na meta passa a exceder o
    # teto no corpus que de fato existe. Ponto fixo em poucas rodadas (o total so' cai).
    total = por_movimento * len(movimentos)
    escolhidos = seleciona(int(total * teto_por_obra))
    for _ in range(5):
        realizado = len(escolhidos)
        novos = seleciona(int(realizado * teto_por_obra))
        if len(novos) == realizado:
            return novos
        escolhidos = novos
    return escolhidos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--core", required=True, help="nucleo da persona (define os movimentos)")
    ap.add_argument("--sources", default=None, help="diretorio das fontes")
    ap.add_argument("--out", default=None, help="jsonl de saida")
    ap.add_argument("--por-movimento", type=int, default=40,
                    help="passagens por movimento. 40 e' o valor em uso: e' o maior numero "
                         "que os DOIS lados alcancam em TODOS os movimentos, o que torna os "
                         "corpora balanceados por construcao em vez de por sorte")
    ap.add_argument("--teto-por-obra", type=float, default=0.30,
                    help="fracao maxima do corpus vinda de uma unica obra")
    args = ap.parse_args(argv)

    core = json.loads(Path(args.core).read_text(encoding="utf-8"))
    persona = core["persona_id"]
    movimentos = core["movimentos"]
    src = Path(args.sources) if args.sources else config.CORPORA_DIR / "sources" / persona
    # UM corpus por persona. O plano herdou do projeto de origem a divisao em dois corpora
    # (destilacao e conviccoes), que la' existia porque as duas fontes eram diferentes —
    # cancoes para a voz, filosofia para a postura. Aqui as duas viriam das MESMAS
    # passagens com dois eixos de rotulo, e o desenho treina UM adapter por braco
    # (persona x scrub), nao dois. Dois arquivos com o mesmo conteudo dobrariam a
    # contabilidade de paridade sem acrescentar controle.
    out = Path(args.out) if args.out else config.CORPORA_DIR / f"corpus_{persona}.jsonl"

    arquivos = sorted(src.glob("*.md"))
    if not arquivos:
        raise SystemExit(f"nenhuma fonte em {src}")

    brutos: list[dict] = []
    for f in arquivos:
        got = extrai(f, movimentos)
        brutos.extend(got)
        print(f"  {f.stem:38s} +{len(got):4d} passagens")

    itens = equilibra(brutos, args.por_movimento, args.teto_por_obra)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for i in itens:
            fh.write(json.dumps(i, ensure_ascii=False) + "\n")

    dist = Counter(i["movimento"] for i in itens)
    obras = Counter(i["locator"] for i in itens)
    palavras = sum(len(i["passage"].split()) for i in itens)
    corpus_sha = hashlib.sha256(out.read_bytes()).hexdigest()
    print("-" * 66)
    print(f"persona={persona} | {len(itens)} passagens | {palavras} palavras -> {out.name}")
    print(f"por movimento: {dict(sorted(dist.items()))}")
    print(f"por obra     : {dict(obras.most_common())}")
    print(f"sha256 corpus: {corpus_sha[:16]}")
    faltando = set(movimentos) - set(dist)
    if faltando:
        print(f"  !! movimentos SEM passagens: {sorted(faltando)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
