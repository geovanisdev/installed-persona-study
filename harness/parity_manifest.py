"""Manifesto de PARIDADE dos corpora, medida em TOKENS.

Paridade de dose entre braços é medida em tokens, não em caracteres nem em palavras: é
token que entra no contexto e é token que o modelo consome. A diferença não é cosmética —
nestes corpora a ordem **inverte** entre as duas unidades, porque o vocabulário de um lado
fragmenta mais que o do outro.

O manifesto existe porque tokenizar exige o tokenizer do modelo, que não está no ambiente de
verificação em CPU. Ele é gerado aqui, com o tokenizer real, e a suíte de testes confere
**dois** fatos: que a paridade em tokens está dentro da tolerância, e que o manifesto
corresponde aos corpora atuais (por sha256). Um manifesto que descreve um corpus antigo seria
pior que nenhum.

Uso (ambiente com transformers):
    python -m harness.parity_manifest
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from harness import config

SAIDA = config.CORPORA_DIR / "PARIDADE.json"


def _corpus(persona: str) -> tuple[Path, list[dict]]:
    p = config.CORPORA_DIR / f"corpus_{persona}.jsonl"
    itens = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l]
    return p, itens


def medir(personas=("leokadius", "shadowclock")) -> dict:
    config.apply_hf_env()
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(config.BASE_MODEL)
    por_persona = {}
    for persona in personas:
        caminho, itens = _corpus(persona)
        tokens = [len(tok.encode(i["passage"], add_special_tokens=False)) for i in itens]
        por_persona[persona] = {
            "arquivo": caminho.name,
            "sha256": hashlib.sha256(caminho.read_bytes()).hexdigest(),
            "n_passagens": len(itens),
            "palavras": sum(len(i["passage"].split()) for i in itens),
            "tokens": sum(tokens),
            "tokens_por_passagem_mediana": sorted(tokens)[len(tokens) // 2],
            "por_movimento": dict(sorted(Counter(i["movimento"] for i in itens).items())),
            "por_obra": dict(Counter(i["locator"] for i in itens).most_common()),
        }
    a, b = (por_persona[p]["tokens"] for p in personas)
    return {
        "tokenizer": config.BASE_MODEL,
        "unidade": "tokens (paridade de dose e' medida em tokens, nao em palavras)",
        "personas": por_persona,
        "diferenca_tokens_fracao": abs(a - b) / max(a, b),
    }


def main() -> int:
    manifesto = medir()
    SAIDA.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    for persona, d in manifesto["personas"].items():
        print(f"  {persona:12s} {d['n_passagens']:4d} passagens | {d['palavras']:6d} palavras "
              f"| {d['tokens']:6d} tokens (mediana {d['tokens_por_passagem_mediana']}/passagem)")
    print(f"  diferenca em tokens: {manifesto['diferenca_tokens_fracao']*100:.1f}%")
    print(f"  -> {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
