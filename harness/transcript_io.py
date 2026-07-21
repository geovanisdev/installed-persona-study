"""Preservacao do RAW: transcricao integral, arquivo duravel, indice append-only e selo.

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/transcript_io.py` do projeto
predecessor. A mecanica (arquivo vivo + arquivamento por carimbo + indice idempotente)
e' preservada; o que mudou foi tirar do corpo do modulo o id do modelo, o diretorio de
dados e a origem do `core_hash`, que estavam fixos.

POR QUE ESTE MODULO EXISTE
---------------------------
E' a resposta a' quarta fraqueza do estudo-piloto: geracoes pontuadas mas nao guardadas.
Sem o texto bruto nao ha' como reexaminar um julgamento, recontar sob outra regua, nem
mostrar a um terceiro o que de fato foi emitido — o achado vira registro historico, nao
resultado. Por isso o arquivamento nao e' opcional nem "logging": e' a evidencia.

Regras que o modulo garante:
  * o indice e' APPEND-ONLY e idempotente por (exp, carimbo);
  * todo registro carrega o SHA do sujeito, o hash do nucleo e o commit do codigo — uma
    geracao que nao sabe dizer de qual sujeito veio nao e' evidencia de nada;
  * falha de arquivamento nunca derruba o run em curso, mas grita no console.

Layout:
  runs/<exp>_transcript.json                       arquivo vivo (ultima run, sobrescrito)
  runs/transcript_index.json                       indice append-only de todas as runs
  runs/transcript_archive/<data>_<sha7>/<exp>.json copia duravel (nunca sobrescrita)
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from harness import config


def turn(papel: str, texto: str, rotulo: str = "") -> dict:
    """Um turno. `rotulo` distingue turnos PARALELOS (ex.: adapter on vs off)."""
    return {"papel": papel, "rotulo": rotulo, "texto": texto or ""}


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=str(config.REPO_ROOT),
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def run_metadata(extra: dict | None = None, *, core_path: Path | None = None,
                 modelo: str | None = None) -> dict:
    """Selo de proveniencia de uma run.

    `git_dirty` e' gravado de proposito: uma geracao produzida com a arvore suja nao e'
    reproduzivel a partir do commit citado, e e' melhor que isso apareca no artefato do
    que seja descoberto meses depois.
    """
    core_hash = ""
    if core_path is not None:
        try:
            core_hash = json.loads(Path(core_path).read_text(encoding="utf-8")).get("core_hash", "")
        except Exception:
            core_hash = ""
    meta = {
        "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "modelo": modelo or config.BASE_MODEL,
        "core_hash": core_hash,
    }
    if extra:
        meta.update(extra)
    return meta


def dump(exp: str, records: list[dict], *, smoke: bool = False,
         run_meta: dict | None = None, runs_dir: Path | None = None) -> Path:
    """Grava o arquivo vivo e, fora de smoke, ARQUIVA e indexa.

    Runs de smoke nao entram no arquivo duravel: o indice e' o registro do que foi
    medido, e enche-lo de fumaca destroi seu valor como manifesto.
    """
    d = Path(runs_dir or config.RUNS_DIR)
    d.mkdir(parents=True, exist_ok=True)
    rm = run_meta if run_meta is not None else run_metadata()
    body = {"exp": exp, "run": rm, "smoke": smoke, "n": len(records), "registros": records}
    live = d / f"{exp.lower()}_transcript{'_SMOKE' if smoke else ''}.json"
    live.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[transcript] {live} ({len(records)} conversas)")
    if not smoke:
        archive_and_index(exp, body, rm, runs_dir=d)
    return live


def _load_index(index_path: Path) -> list[dict]:
    if index_path.exists():
        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def archive_and_index(exp: str, body: dict, rm: dict, *, runs_dir: Path | None = None) -> None:
    """APPEND-ONLY, idempotente por (exp, carimbo), e defensivo: nunca derruba o run."""
    d = Path(runs_dir or config.RUNS_DIR)
    index_path = d / "transcript_index.json"
    try:
        stamp = f"{rm['data'][:10]}_{rm.get('git_commit') or 'nocommit'}"
        idx = _load_index(index_path)
        if any(e.get("exp") == exp and e.get("stamp") == stamp for e in idx):
            return
        alvo = d / "transcript_archive" / stamp
        alvo.mkdir(parents=True, exist_ok=True)
        arquivo = alvo / f"{exp.lower()}.json"
        arquivo.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        idx.append({
            "exp": exp, "stamp": stamp, "data": rm["data"],
            "git_commit": rm.get("git_commit"), "git_dirty": rm.get("git_dirty"),
            "core_hash": rm.get("core_hash"), "modelo": rm.get("modelo"),
            "adapter": rm.get("adapter"), "sujeito_sha": rm.get("sujeito_sha"),
            "veredito": rm.get("veredito"), "n": body["n"],
            "arquivo": str(arquivo.relative_to(d)).replace("\\", "/"),
        })
        index_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[transcript] arquivado {arquivo} + indice ({len(idx)} runs)")
    except Exception as e:  # noqa: BLE001 — perder o arquivamento nao pode perder o run
        print(f"[transcript] AVISO: arquivamento falhou (nao-fatal): {e}")
