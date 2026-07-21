"""Preservacao do raw: arquivo vivo, arquivamento duravel e indice append-only."""

from __future__ import annotations

import json

from harness.transcript_io import archive_and_index, dump, run_metadata, turn


def _registro(i: int) -> dict:
    return {
        "exp": "T1", "id": f"item_{i}", "grupo": "teste", "veredito": "n/a",
        "meta": {"item": i},
        "turnos": [turn("user", "provocacao"), turn("model", "resposta", rotulo="adapter_on")],
    }


def _meta(stamp_commit: str = "abc1234") -> dict:
    return {"data": "2026-07-21 10:00:00", "git_commit": stamp_commit,
            "core_hash": "deadbeef", "modelo": "modelo-x", "sujeito_sha": "sha-do-sujeito"}


def test_dump_grava_arquivo_vivo_e_arquiva(tmp_path):
    dump("T1", [_registro(0), _registro(1)], run_meta=_meta(), runs_dir=tmp_path)
    vivo = tmp_path / "t1_transcript.json"
    assert vivo.exists()
    body = json.loads(vivo.read_text(encoding="utf-8"))
    assert body["n"] == 2 and len(body["registros"]) == 2
    assert (tmp_path / "transcript_archive" / "2026-07-21_abc1234" / "t1.json").exists()
    assert (tmp_path / "transcript_index.json").exists()


def test_texto_integral_sobrevive_ao_arquivamento(tmp_path):
    """O ponto do modulo: o texto bruto chega inteiro ao arquivo duravel, sem truncar."""
    longo = "palavra " * 5000
    reg = _registro(0)
    reg["turnos"][1]["texto"] = longo
    dump("T1", [reg], run_meta=_meta(), runs_dir=tmp_path)
    arq = json.loads((tmp_path / "transcript_archive" / "2026-07-21_abc1234" / "t1.json")
                     .read_text(encoding="utf-8"))
    assert arq["registros"][0]["turnos"][1]["texto"] == longo


def test_smoke_nao_entra_no_indice(tmp_path):
    """Fumaca nao e' evidencia; o indice e' o manifesto do que foi medido."""
    dump("T1", [_registro(0)], smoke=True, run_meta=_meta(), runs_dir=tmp_path)
    assert (tmp_path / "t1_transcript_SMOKE.json").exists()
    assert not (tmp_path / "transcript_index.json").exists()
    assert not (tmp_path / "transcript_archive").exists()


def test_indice_e_idempotente_para_a_mesma_run(tmp_path):
    for _ in range(3):
        dump("T1", [_registro(0)], run_meta=_meta(), runs_dir=tmp_path)
    idx = json.loads((tmp_path / "transcript_index.json").read_text(encoding="utf-8"))
    assert len(idx) == 1


def test_indice_e_append_only_entre_runs(tmp_path):
    dump("T1", [_registro(0)], run_meta=_meta("aaa1111"), runs_dir=tmp_path)
    dump("T1", [_registro(1)], run_meta=_meta("bbb2222"), runs_dir=tmp_path)
    dump("T2", [_registro(2)], run_meta=_meta("bbb2222"), runs_dir=tmp_path)
    idx = json.loads((tmp_path / "transcript_index.json").read_text(encoding="utf-8"))
    assert len(idx) == 3
    assert [e["exp"] for e in idx] == ["T1", "T1", "T2"]


def test_arquivo_duravel_de_run_anterior_nao_e_sobrescrito(tmp_path):
    dump("T1", [_registro(0)], run_meta=_meta("aaa1111"), runs_dir=tmp_path)
    dump("T1", [_registro(1), _registro(2)], run_meta=_meta("bbb2222"), runs_dir=tmp_path)
    antigo = json.loads((tmp_path / "transcript_archive" / "2026-07-21_aaa1111" / "t1.json")
                        .read_text(encoding="utf-8"))
    assert antigo["n"] == 1


def test_indice_registra_a_proveniencia_do_sujeito(tmp_path):
    """Uma geracao que nao sabe dizer de qual sujeito veio nao e' evidencia de nada."""
    dump("T1", [_registro(0)], run_meta=_meta(), runs_dir=tmp_path)
    entrada = json.loads((tmp_path / "transcript_index.json").read_text(encoding="utf-8"))[0]
    assert entrada["core_hash"] == "deadbeef"
    assert entrada["sujeito_sha"] == "sha-do-sujeito"
    assert entrada["modelo"] == "modelo-x"


def test_falha_de_arquivamento_nao_derruba_o_run(tmp_path, capsys):
    """Perder o arquivamento e' ruim; perder o run em curso por causa disso e' pior."""
    archive_and_index("T1", {"n": 1}, {"data": "2026-07-21 10:00:00"},
                      runs_dir=tmp_path / "inexistente" / "\0invalido")
    assert "AVISO" in capsys.readouterr().out


def test_run_metadata_le_o_hash_do_nucleo(tmp_path, dummy_core_path):
    from harness.persona_core import seal_core
    h = seal_core(dummy_core_path)
    meta = run_metadata(core_path=dummy_core_path, modelo="modelo-y")
    assert meta["core_hash"] == h
    assert meta["modelo"] == "modelo-y"
    assert "data" in meta and "git_dirty" in meta
