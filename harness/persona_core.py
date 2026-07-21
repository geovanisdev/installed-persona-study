"""Nucleo declarativo de uma PERSONA — schema, selo por hash e pontuacao lexical.

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/identity_core.py` do projeto
predecessor (privado). A mecanica de hash, a normalizacao de texto e a pontuacao de
invariantes sao PRESERVADAS byte a byte — o mesmo conteudo produz o mesmo `core_hash`
nos dois repositorios, e isso e' verificado por um teste de golden-batch.

MUDANCA ESTRUTURAL DO PORTE (a razao de existir deste modulo)
--------------------------------------------------------------
No original, o nucleo NAO era dado: era CODIGO. Uma funcao `build_core()` de ~340
linhas devolvia o nucleo de uma unica persona escrito inline, e o hash era tirado da
saida dessa funcao. Com uma persona so' isso funciona; com duas, cada nova persona
exigiria editar o modulo, e o "nucleo" deixaria de ser um artefato selavel e revisavel
para virar um trecho de programa.

Aqui a relacao se inverte: o nucleo e' um arquivo JSON, autorado e selado por pessoa,
e este modulo e' apenas o schema, o selo e a regua. Consequencias diretas:

- `--core caminho.json` passa a ser argumento de todo runner (nenhuma persona no codigo);
- selar vira um ato explicito e datado (`seal_core`), nao um efeito colateral de rodar;
- o Arquiteto e' dono do construto: revisa e sela o JSON, sem ler Python.

O que NAO mudou: `core_hash` continua sendo o sha256 do JSON canonico do conteudo
excluindo o proprio campo de hash, e `load_core` continua recusando um arquivo cujo
hash nao bata (deteccao de edicao a mao).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

SCHEMA_VERSION = 1

# Facetas pontuadas no estudo (ver batteries/CODEBOOK.md quando o S3 fechar).
FACETAS = ("F1_autorreferencia_nominal", "F2_postura", "F3_consistencia_nucleo", "F4_seguranca")


# ---------------------------------------------------------------------------
# Normalizacao — PRESERVADA do original (o lexico so' casa se for a mesma funcao)
# ---------------------------------------------------------------------------


def normalize_text(s: str) -> str:
    """minusculas, sem acento, so' alfanumerico e espaco, espacos colapsados."""
    s = s.lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = "".join(c if c.isalnum() or c.isspace() else " " for c in s)
    return " ".join(s.split())


# ---------------------------------------------------------------------------
# Hash / selo — algoritmo PRESERVADO (golden-batch depende disso)
# ---------------------------------------------------------------------------


def core_hash(core: dict) -> str:
    """sha256 do JSON canonico do conteudo, EXCLUINDO o proprio campo de hash."""
    payload = {k: v for k, v in core.items() if k != "core_hash"}
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_core(path: str | Path) -> dict:
    """Le o nucleo do disco e VERIFICA o selo. Levanta se o arquivo foi editado."""
    p = Path(path)
    core = json.loads(p.read_text(encoding="utf-8"))
    expected = core.get("core_hash")
    recomputed = core_hash(core)
    if expected is not None and recomputed != expected:
        raise ValueError(
            f"nucleo em {p} nao bate com o hash gravado ({expected}) — recomputado "
            f"{recomputed}; arquivo editado a mao ou corrompido. Um nucleo selado NAO "
            "se conserta: ou se restaura a versao selada, ou se sela uma nova versao "
            "com data e motivo."
        )
    return core


def seal_core(path: str | Path, *, overwrite: bool = False) -> str:
    """Valida, calcula o `core_hash` e grava. Ato deliberado (selo do Arquiteto).

    Recusa reselar um nucleo que ja' tem selo, a menos que `overwrite=True`: re-selar em
    silencio destruiria a rastreabilidade de todo artefato que cita o hash antigo.
    """
    p = Path(path)
    core = json.loads(p.read_text(encoding="utf-8"))
    if core.get("core_hash") and not overwrite:
        raise ValueError(
            f"{p} ja' esta' selado ({core['core_hash'][:12]}). Re-selar invalida todo "
            "artefato que cita esse hash; use overwrite=True so' com decisao registrada."
        )
    validate_core(core)
    core.pop("core_hash", None)
    h = core_hash(core)
    core["core_hash"] = h
    p.write_text(json.dumps(core, ensure_ascii=False, indent=2), encoding="utf-8")
    return h


# ---------------------------------------------------------------------------
# Validacao de schema
# ---------------------------------------------------------------------------

_REQUIRED_TOP = ("schema_version", "persona_id", "nome", "postura", "idioma",
                 "natureza_substrato", "invariantes_sob_pressao", "valores_tracos",
                 "movimentos", "sobreposicao_predita")


class CoreSchemaError(ValueError):
    """Nucleo malformado. Sempre nomeia o campo e o porque."""


def validate_core(core: dict) -> None:
    """Valida um nucleo AUTORAL (antes do selo). Erra alto e cedo, com o campo no texto.

    Alem da checagem de tipos, valida duas coisas que no original falhavam em SILENCIO:

    1. Marcadores `viola_se` fora da forma normalizada. A pontuacao casa marcadores
       contra o texto ja' normalizado; um marcador com acento ou maiuscula NUNCA casa.
       No original isso nao era checado — um marcador morto parecia um invariante
       cumprido, o que e' o pior modo de falhar num instrumento de medida.
    2. Ids repetidos em invariantes ou valores, que fariam a fracao de invariantes
       violados usar um denominador que nao corresponde ao numero de invariantes reais.
    """
    if not isinstance(core, dict):
        raise CoreSchemaError("nucleo precisa ser um objeto JSON")

    faltando = [k for k in _REQUIRED_TOP if k not in core]
    if faltando:
        raise CoreSchemaError(f"campos obrigatorios ausentes: {faltando}")

    if core["schema_version"] != SCHEMA_VERSION:
        raise CoreSchemaError(
            f"schema_version {core['schema_version']!r} != {SCHEMA_VERSION} suportado"
        )

    pid = core["persona_id"]
    if not isinstance(pid, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", pid):
        raise CoreSchemaError(f"persona_id {pid!r} deve ser ascii minusculo [a-z][a-z0-9_]*")

    nome = core["nome"]
    if not isinstance(nome, str) or not nome.isascii() or not nome.strip():
        raise CoreSchemaError(f"nome {nome!r} deve ser ascii nao-vazio (evita colisao de encoding)")

    if not isinstance(core["natureza_substrato"], str) or len(core["natureza_substrato"]) < 20:
        raise CoreSchemaError("natureza_substrato deve declarar o substrato honesto da persona")

    _validate_invariantes(core["invariantes_sob_pressao"])
    _validate_valores(core["valores_tracos"])
    _validate_movimentos(core["movimentos"])
    _validate_sobreposicao(core["sobreposicao_predita"])


def _validate_invariantes(invs) -> None:
    if not isinstance(invs, list) or not invs:
        raise CoreSchemaError("invariantes_sob_pressao deve ser lista nao-vazia")
    vistos = set()
    for i, inv in enumerate(invs):
        if not isinstance(inv, dict) or not {"id", "descricao", "viola_se"} <= set(inv):
            raise CoreSchemaError(f"invariante #{i} precisa de id/descricao/viola_se")
        if inv["id"] in vistos:
            raise CoreSchemaError(f"invariante id duplicado: {inv['id']!r}")
        vistos.add(inv["id"])
        marcadores = inv["viola_se"]
        if not isinstance(marcadores, list) or not marcadores:
            raise CoreSchemaError(f"invariante {inv['id']!r}: viola_se vazio")
        for m in marcadores:
            if not isinstance(m, str) or not m.strip():
                raise CoreSchemaError(f"invariante {inv['id']!r}: marcador vazio")
            if m != normalize_text(m):
                raise CoreSchemaError(
                    f"invariante {inv['id']!r}: marcador {m!r} nao esta' na forma "
                    f"normalizada (esperado {normalize_text(m)!r}) — como e' casado "
                    "contra texto normalizado, ele jamais casaria e o invariante "
                    "pareceria sempre cumprido"
                )


def _validate_valores(vals) -> None:
    if not isinstance(vals, list) or not vals:
        raise CoreSchemaError("valores_tracos deve ser lista nao-vazia")
    vistos = set()
    for i, v in enumerate(vals):
        if not isinstance(v, dict) or not {"id", "nome", "descricao"} <= set(v):
            raise CoreSchemaError(f"valor #{i} precisa de id/nome/descricao")
        if v["id"] in vistos:
            raise CoreSchemaError(f"valor id duplicado: {v['id']!r}")
        vistos.add(v["id"])


def _validate_movimentos(movs) -> None:
    """Taxonomia de movimentos: casa com o front-matter `movimento:` dos corpora."""
    if not isinstance(movs, list) or not movs:
        raise CoreSchemaError("movimentos deve ser lista nao-vazia")
    for m in movs:
        if not isinstance(m, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", m):
            raise CoreSchemaError(f"movimento {m!r} deve ser ascii minusculo [a-z][a-z0-9_]*")
    if len(set(movs)) != len(movs):
        raise CoreSchemaError("movimentos com repeticao")


def _validate_sobreposicao(sob) -> None:
    """Predicao de sobreposicao entre as duas personas, PRE-DECLARADA.

    Sem isto o 2x2 nao e' falsificavel: qualquer resultado — divergirem em tudo,
    coincidirem em tudo — poderia ser narrado como sucesso depois do fato.
    """
    if not isinstance(sob, dict) or not {"divergem", "coincidem"} <= set(sob):
        raise CoreSchemaError("sobreposicao_predita precisa de 'divergem' e 'coincidem'")
    for chave in ("divergem", "coincidem"):
        facetas = sob[chave]
        if not isinstance(facetas, list) or not facetas:
            raise CoreSchemaError(f"sobreposicao_predita.{chave} deve ser lista nao-vazia")
        desconhecidas = [f for f in facetas if f not in FACETAS]
        if desconhecidas:
            raise CoreSchemaError(
                f"sobreposicao_predita.{chave}: facetas desconhecidas {desconhecidas} "
                f"(validas: {list(FACETAS)})"
            )
    ambos = set(sob["divergem"]) & set(sob["coincidem"])
    if ambos:
        raise CoreSchemaError(
            f"facetas em 'divergem' E 'coincidem' ao mesmo tempo: {sorted(ambos)} — "
            "uma predicao que cobre os dois lados nao e' predicao"
        )


# ---------------------------------------------------------------------------
# Derivados do nucleo (o que antes eram constantes de modulo)
# ---------------------------------------------------------------------------


def scrub_pattern(core: dict, *, mode: str = "full") -> re.Pattern:
    """Regex anti-tag-leak DERIVADA do nucleo (no original era uma constante literal).

    `full`     — apaga o nome da persona e os nomes de contraste. Mede quanto do efeito
                 e' memorizacao do nome proprio (braco `scrub` do 2x2).
    `contraste`— apaga so' os nomes de contraste, preservando o nome da persona.

    Os dois bracos treinam com a MESMA maquinaria e o MESMO volume; a unica diferenca e'
    esta substituicao. E' isso que torna a dissociacao nome-postura interpretavel.
    """
    if mode not in ("full", "contraste"):
        raise ValueError(f"mode deve ser full|contraste (got {mode!r})")
    nomes = list(core.get("personas_contraste", {}).get("nomes", []))
    if mode == "full":
        nomes = [core["nome"], *nomes]
    if not nomes:
        # Sem nome algum para apagar: padrao que nunca casa (explicito e' melhor que
        # um regex vazio, que casaria em toda posicao).
        return re.compile(r"(?!x)x")
    alternativas = "|".join(re.escape(n.lower()) for n in nomes)
    return re.compile(rf"\b({alternativas})\b", re.IGNORECASE)


def build_preamble(core: dict) -> str:
    """Preambulo do PROFESSOR na destilacao de contexto (o aluno treina sem ele).

    Generico por construcao: le do nucleo, nao contem persona. O original montava a
    frase com os campos de uma persona especifica escritos no proprio codigo.
    """
    vals = "; ".join(v["nome"] for v in core["valores_tracos"])
    partes = [f"Voce e' {core['nome']}. {core['natureza_substrato']}"]
    if core.get("frase_ancora"):
        partes.append(f'Uma frase que te ancora: "{core["frase_ancora"]}".')
    postura = core.get("superficie_postura") or {}
    if postura:
        partes.append("Sua postura: " + " ".join(postura[k] for k in sorted(postura)))
    partes.append(f"Seus valores: {vals}.")
    return " ".join(partes)


# ---------------------------------------------------------------------------
# Pontuacao lexical (F3) — PRESERVADA do original
# ---------------------------------------------------------------------------


def invariant_violations(continuation: str, core: dict) -> list[str]:
    """Ids dos invariantes violados, casador por SUBSTRING (regua original).

    Mantida por fidelidade e para comparacao: a regua usada nas medidas do estudo e' a
    de `core_scorer`, que e' consciente de negacao. Ver o porque la'.
    """
    norm = normalize_text(continuation)
    return [inv["id"] for inv in core["invariantes_sob_pressao"]
            if any(m in norm for m in inv["viola_se"])]


def core_consistency_score(continuation: str, core: dict) -> float:
    """Fracao de invariantes NAO violados (1.0 = totalmente consistente)."""
    n = len(core["invariantes_sob_pressao"])
    if n == 0:
        return 1.0
    return 1.0 - len(invariant_violations(continuation, core)) / n
