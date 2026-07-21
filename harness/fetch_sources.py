"""Baixa as fontes de DOMINIO PUBLICO e as grava com selo de proveniencia.

Cada obra vira um `.md` em `corpora/sources/<persona>/` com front-matter contendo obra,
autor, tradutor, ano da traducao, idioma, URL de origem, id do catalogo e o sha256 do
arquivo baixado. Sem esse bloco, uma passagem no corpus seria uma citacao sem endereco —
e este estudo publica corpora justamente para que terceiros possam conferi-las.

VERIFICACAO DE TRADUTOR: para as obras em que o tradutor importa (a lista aprovada nomeia
tradutores especificos), o script confere se o nome aparece no cabecalho do arquivo e
ABORTA se nao aparecer. Baixar a traducao errada e' o tipo de erro que so' apareceria
muito depois, ja' dentro dos pesos.

Uso:
    python -m harness.fetch_sources            # baixa o que falta
    python -m harness.fetch_sources --forcar   # rebaixa tudo
"""

from __future__ import annotations

import hashlib
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

from harness import config

UA = "installed-persona-study/0.1 (public-domain corpus builder)"

# Lista APROVADA pelo Arquiteto em 2026-07-21. Acrescentar obra aqui e' mudanca de
# corpus e exige nova aprovacao.
FONTES = [
    # --- Leokadius (estoico) ---
    # A edicao #2680 ("Meditations") e' a mais conhecida, mas NAO atribui tradutor no
    # texto nem no catalogo. Como este estudo publica corpora com atribuicao por item — e
    # recusou fontes de terceiros pelo mesmo motivo —, usa-se a edicao ATRIBUIDA a George
    # Long, que e' o tradutor da lista aprovada.
    dict(persona="leokadius", slug="marco_aurelio_pensamentos", gid=15877,
         obra="Thoughts of Marcus Aurelius Antoninus", autor="Marcus Aurelius",
         tradutor="George Long", ano_traducao=1862, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/15877/15877-8.txt",
         movimentos_esperados=["dicotomia_do_controle", "memento_mori", "apatheia", "prosoche"]),
    dict(persona="leokadius", slug="epicteto_discourses_enchiridion", gid=10661,
         obra="A Selection from the Discourses of Epictetus with the Enchiridion",
         autor="Epictetus", tradutor="George Long", ano_traducao=1877, lingua="en",
         exige_tradutor=True,
         url="https://www.gutenberg.org/files/10661/10661-0.txt",
         movimentos_esperados=["dicotomia_do_controle", "prosoche", "metodo_socratico", "apatheia"]),
    dict(persona="leokadius", slug="diogenes_laercio_vidas", gid=57342,
         obra="The Lives and Opinions of Eminent Philosophers", autor="Diogenes Laertius",
         tradutor="Charles Duke Yonge", ano_traducao=1853, lingua="en",
         exige_tradutor=True,
         url="https://www.gutenberg.org/files/57342/57342-0.txt",
         movimentos_esperados=["dicotomia_do_controle", "apatheia"],
         nota="Apenas o Livro VII (Zenao e os estoicos) e' usado; o recorte e' feito no builder."),
    # --- Shadowclock (existencialista ateu) ---
    dict(persona="shadowclock", slug="nietzsche_zaratustra", gid=1998,
         obra="Thus Spake Zarathustra", autor="Friedrich Nietzsche",
         tradutor="Thomas Common", ano_traducao=1909, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/1998/1998-0.txt",
         movimentos_esperados=["revolta", "liberdade_radical", "sem_consolo"]),
    dict(persona="shadowclock", slug="nietzsche_alem_do_bem_e_do_mal", gid=4363,
         obra="Beyond Good and Evil", autor="Friedrich Nietzsche",
         tradutor="Helen Zimmern", ano_traducao=1907, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/4363/4363.txt",
         movimentos_esperados=["ma_fe", "liberdade_radical", "sem_consolo"]),
    dict(persona="shadowclock", slug="nietzsche_gaia_ciencia", gid=52881,
         obra="The Joyful Wisdom", autor="Friedrich Nietzsche", tradutor="Thomas Common",
         ano_traducao=1910, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/52881/52881-0.txt",
         movimentos_esperados=["absurdo", "sem_consolo", "revolta"]),
    dict(persona="shadowclock", slug="dostoievski_subsolo", gid=600,
         obra="Notes from the Underground", autor="Fyodor Dostoyevsky",
         tradutor="Constance Garnett", ano_traducao=1918, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/600/600-0.txt",
         movimentos_esperados=["liberdade_radical", "ma_fe", "revolta"]),
    dict(persona="shadowclock", slug="leopardi_ensaios_dialogos", gid=52356,
         obra="Essays and Dialogues", autor="Giacomo Leopardi", tradutor="Charles Edwardes",
         ano_traducao=1882, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/52356/52356-0.txt",
         movimentos_esperados=["absurdo", "sem_consolo"]),
    dict(persona="shadowclock", slug="stirner_o_unico", gid=34580,
         obra="The Ego and His Own", autor="Max Stirner", tradutor="Steven T. Byington",
         ano_traducao=1907, lingua="en", exige_tradutor=True,
         url="https://www.gutenberg.org/files/34580/34580-0.txt",
         movimentos_esperados=["liberdade_radical", "ma_fe"]),
    dict(persona="shadowclock", slug="feuerbach_essencia_cristianismo", gid=47025,
         obra="The Essence of Christianity", autor="Ludwig Feuerbach",
         tradutor="Marian Evans (George Eliot)", ano_traducao=1854, lingua="en",
         exige_tradutor=True,
         url="https://www.gutenberg.org/files/47025/47025-0.txt",
         movimentos_esperados=["sem_consolo", "ma_fe"],
         alias_tradutor=["Marian Evans", "George Eliot"]),
]

INICIO = re.compile(r"\*\*\*\s*START OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.S)
FIM = re.compile(r"\*\*\*\s*END OF (THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", re.S)


class TradutorInesperado(RuntimeError):
    """O texto baixado nao confirma o tradutor aprovado."""


def baixar(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _decodifica(bruto: bytes) -> str:
    """UTF-8 quando valido; senao latin-1. Os arquivos `-8.txt` do catalogo sao 8-bit, e
    decodificar com `replace` trocaria acentos por U+FFFD dentro do proprio corpus."""
    try:
        return bruto.decode("utf-8")
    except UnicodeDecodeError:
        return bruto.decode("latin-1")


# Janela de busca do tradutor: cabecalho do catalogo MAIS o inicio do corpo. Varios
# arquivos do catalogo nao tem cabecalho algum e trazem a atribuicao na folha de rosto,
# ja' depois do marcador de inicio (ex.: "TRANSLATED BY GEORGE LONG").
JANELA_TRADUTOR = 20000


def _confere_tradutor(fonte: dict, texto: str) -> str:
    """Devolve o nome encontrado; levanta se nenhum alias aparecer na janela inicial."""
    alvos = fonte.get("alias_tradutor") or [fonte["tradutor"]]
    sobrenome = fonte["tradutor"].split()[-1].strip("()")
    janela = texto[:JANELA_TRADUTOR].lower()
    for alvo in [*alvos, sobrenome]:
        if alvo.lower() in janela:
            return alvo
    raise TradutorInesperado(
        f"{fonte['slug']}: nenhum de {alvos} aparece nos primeiros "
        f"{JANELA_TRADUTOR} caracteres. A lista aprovada nomeia tradutores especificos; "
        "baixar a traducao errada e' erro que so' apareceria depois, ja' dentro dos pesos."
    )


def corpo_sem_moldura(texto: str) -> tuple[str, str]:
    """Separa (cabecalho do catalogo, corpo da obra)."""
    mi = INICIO.search(texto)
    mf = FIM.search(texto)
    cabecalho = texto[:mi.start()] if mi else texto[:3000]
    ini = mi.end() if mi else 0
    fim = mf.start() if mf else len(texto)
    return cabecalho, texto[ini:fim].strip()


def escrever(fonte: dict, corpo: str, sha: str, tradutor_conferido: str) -> Path:
    destino = config.CORPORA_DIR / "sources" / fonte["persona"] / f"{fonte['slug']}.md"
    destino.parent.mkdir(parents=True, exist_ok=True)
    fm = [
        "---",
        f"obra: {fonte['obra']}",
        f"autor: {fonte['autor']}",
        f"tradutor: {fonte['tradutor']}",
        f"tradutor_conferido_no_texto: {tradutor_conferido}",
        f"ano_traducao: {fonte['ano_traducao']}",
        f"lingua: {fonte['lingua']}",
        f"persona: {fonte['persona']}",
        f"movimentos_esperados: {', '.join(fonte['movimentos_esperados'])}",
        "licenca: dominio publico",
        f"fonte_url: {fonte['url']}",
        f"gutenberg_id: {fonte['gid']}",
        f"sha256: {sha}",
        f"baixado_em: {date.today().isoformat()}",
    ]
    if fonte.get("nota"):
        fm.append(f"nota: {fonte['nota']}")
    fm.append("---")
    destino.write_text("\n".join(fm) + "\n\n" + corpo + "\n", encoding="utf-8")
    return destino


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    forcar = "--forcar" in argv
    total = 0
    for fonte in FONTES:
        destino = config.CORPORA_DIR / "sources" / fonte["persona"] / f"{fonte['slug']}.md"
        if destino.exists() and not forcar:
            print(f"  [pula] {fonte['slug']} (ja' existe)")
            continue
        print(f"  [baixa] {fonte['slug']} <- {fonte['url']}")
        bruto = baixar(fonte["url"])
        sha = hashlib.sha256(bruto).hexdigest()
        texto = _decodifica(bruto)
        _, corpo = corpo_sem_moldura(texto)
        conferido = _confere_tradutor(fonte, texto) if fonte.get("exige_tradutor") else "n/a"
        p = escrever(fonte, corpo, sha, conferido)
        total += len(corpo)
        print(f"          tradutor conferido: {conferido} | corpo {len(corpo)/1024:.0f} KB "
              f"| sha256 {sha[:12]} -> {p.relative_to(config.REPO_ROOT)}")
    print(f"\n{total/1024:.0f} KB de corpo util gravados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
