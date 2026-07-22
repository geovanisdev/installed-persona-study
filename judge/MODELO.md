# Cross-family judge — pinned weights

The judge is an **instrument**. An instrument that cannot name the bytes it ran on is not an
instrument, so its weights are pinned here the same way the tokenizer is pinned in
`harness/tokenizacao.py`: by **content hash**, not by a mutable pointer.

Downloaded 2026-07-22 for S4 stage 1. Nothing has been judged with it yet.

| | |
|---|---|
| repo | `Qwen/Qwen3-8B` |
| revision | `b968826d9c46dd6066d109eabc6255188de91218` |
| cache | `G:\hf_cache` (`IPS_HF_HOME`) |
| total | 15,27 GiB across 15 files |
| licence | Apache-2.0 (`LICENSE`, sha256 `832dd9e0…`) |

## Why the revision alone is not the pin

`refs/main` is a **mutable pointer**. On 2026-07-21 the base model's `refs/main` moved online and
very nearly swapped the model out from under a running experiment. The snapshot directory name
above is a commit sha and therefore immutable, but nothing forces a future run to resolve to it —
so the files are hashed here as well.

Shards are recorded by size only: hashing 15 GiB on every check would make the guard expensive
enough to be skipped, and a guard that gets skipped is not a guard. The small files below are the
ones a wrong-revision load would change first, and they are cheap to verify.

| file | bytes | sha256 |
|---|---|---|
| `config.json` | 4 011 | `f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30` |
| `generation_config.json` | 239 | `2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2` |
| `tokenizer.json` | 11 422 654 | `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4` |
| `tokenizer_config.json` | 9 731 | `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101` |
| `vocab.json` | 2 776 833 | `ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910` |
| `merges.txt` | 1 671 853 | `8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5` |
| `model.safetensors.index.json` | 30 900 | `f9fdbcb91c23971c13ec5d5f2573d2349e8f61f2f049371ec699281748fdb1bc` |
| `model-0000{1..5}-of-00005.safetensors` | 3 996 264 kB · 3 993 168 kB · 3 959 616 kB · 3 188 384 kB · 1 244 528 kB | size only |

## Two things about the download itself, because both would bite a re-runner

**The cache is chosen by `IPS_HF_HOME`, and it has to be set in the launcher's environment.**
This machine ships `HF_HOME=F:\hf_cache` ambiently, and `C:` has 9,3 GB free — a 15 GiB download
with neither variable set breaks partway through, on the wrong disk. `harness/config.py` gives
`IPS_HF_HOME` declared precedence, but only for processes that see it.

**TLS interception.** The first attempt died on `CERTIFICATE_VERIFY_FAILED`. The cause was
measured, not guessed: Norton re-signs TLS on this machine with `Norton Web/Mail Shield Root`,
which lives in the Windows trust store and **not** in the `certifi` bundle that `httpx` uses by
default. A context built from certifi fails; `ssl.create_default_context()` — the Windows store —
connects.

The fix is not to disable verification. It is to hand `huggingface_hub` a client whose SSL
context comes from the machine's own trust store, via `set_client_factory`, whose docstring names
this case. Verification stays on; only the list of trusted roots changes.

```python
import ssl, httpx
from huggingface_hub.utils._http import hf_request_event_hook, set_client_factory

set_client_factory(lambda: httpx.Client(
    verify=ssl.create_default_context(),      # Windows roots; verification ON
    event_hooks={"request": [hf_request_event_hook]},
    follow_redirects=True, timeout=None))
```

`HF_HUB_OFFLINE` was cleared only inside the downloading process. The ambient environment was
never modified, and `harness/config.apply_hf_env` still forces offline for every run.
