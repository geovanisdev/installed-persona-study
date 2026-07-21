# `runs/` — raw evidence

**Everything generated is kept.** This directory is the answer to the predecessor study's fourth
weakness: raw generations that were scored but not preserved cannot be re-examined, and a finding
that cannot be re-examined is a historical record, not a result.

Structure, per the ported transcript archiver:

```
transcript_archive/<date>_<sha7>/   durable raw generations for one run
INDEX.md                            append-only index, one line per run
<run>/PROVENANCE.md                 subject sha, adapter, core hash, battery hash,
                                    judge prompt hash, decoding settings, seeds, timestamps
```

Rules:

- The index is **append-only**. Runs are never deleted or rewritten; a superseded run is marked
  superseded and stays.
- Every run names its **frozen subject** by SHA. A generation that cannot name its subject is not
  evidence.
- Raw text is archived **before** any scoring pass touches it.
- `runs/` is deliberately excluded from `.gitignore`.
