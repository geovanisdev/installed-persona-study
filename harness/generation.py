"""Primitivas de geracao e leitura de logits (o que toca o modelo, e so' isso).

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/causal_identity.py` do projeto
predecessor. A mecanica de geracao gulosa, de log-prob teacher-forced e dos ganchos de
intervencao e' preservada. Mudou o que estava fixo no corpo do modulo:

* as ancoras do contraste de afirmacao/dissolucao eram os textos de UMA persona escritos
  no codigo; agora vem do nucleo, como todo o resto da persona;
* o dispositivo era `device=0` literal em cinco lugares; agora sai do proprio modelo;
* a montagem do prompt era do Gemma; agora vem do formato de familia (`model_family`).

DECODIFICACAO GULOSA, SEMPRE. Amostrar introduz variancia que depois se confunde com
efeito do sujeito. Quando o desenho pedir varias amostras por item, elas colapsam em UM
booleano por voto majoritario antes de virar dado — reamostrar decodificacao mede a
decodificacao, nao o sujeito, e nunca aumenta o n.
"""

from __future__ import annotations

import numpy as np

# Preenchimento neutro que ocupa o lugar do preambulo quando a medida e' SEM persona no
# contexto. Nao nomeia nem alude a persona alguma, e e' o MESMO para todos os bracos: se
# variasse entre bracos, a diferenca medida poderia vir do preenchimento.
# CONGELADO SEM ACENTO, DE PROPOSITO. O repositorio escreve portugues acentuado em todo
# texto de estudo; esta constante e' a excecao porque nao e' texto de estudo — e' FIXTURE DE
# FIDELIDADE. Ela reproduz byte a byte a string do projeto de origem, e e' com ela que o
# golden com pesos provou a portabilidade (21/21: ids de prompt, geracao gulosa, logp
# teacher-forced). Acentua-la mudaria os token ids e tornaria irreproduzivel uma prova ja'
# registrada em `harness/goldens/golden_gpu_report.json`. Usada SO' pelo golden.
NEUTRAL_FILLER = (
    "Voce e' um assistente. Responda a proxima solicitacao com cuidado e no seu "
    "proprio modo, sem rodeios."
)


def _device(model):
    return next(model.parameters()).device


def get_layers(model):
    """Lista de blocos do decoder, desembrulhando LoRA se preciso.

    Varre caminhos conhecidos em vez de assumir um: familias diferentes aninham o
    decoder em lugares diferentes, e este harness precisa rodar em duas.
    """
    if hasattr(model, "get_base_model"):
        try:
            model = model.get_base_model()
        except Exception:
            pass
    for caminho in ("model.language_model.layers", "language_model.layers",
                    "model.layers", "language_model.model.layers", "transformer.h"):
        obj = model
        ok = True
        for parte in caminho.split("."):
            if not hasattr(obj, parte):
                ok = False
                break
            obj = getattr(obj, parte)
        if ok and hasattr(obj, "__len__"):
            return obj
    raise RuntimeError(
        "nao encontrei a lista de camadas do decoder neste modelo — acrescente o "
        "caminho da familia em vez de deixar o harness adivinhar"
    )


def _register_inject(layers, inject):
    """Gancho de intervencao. inject = ('add'|'ablate', L, vec).

    'add' soma o vetor ao residual da camada L; 'ablate' remove a componente naquela
    direcao. Mantido do original para a linha causal, que nao e' usada por nenhum
    endpoint primario deste estudo — mas remove-la seria decisao irreversivel de escopo.
    """
    if inject is None:
        return None
    import torch
    op, L, v = inject
    t = torch.tensor(v, device=layers[L].weight.device if hasattr(layers[L], "weight") else None,
                     dtype=torch.bfloat16)
    if op == "ablate":
        t = t / (t.norm() + 1e-6)

    def hook(mod, inp, out):
        h = out[0] if isinstance(out, tuple) else out
        if op == "add":
            h = h + t
        else:
            coef = (h * t).sum(dim=-1, keepdim=True)
            h = h - coef * t
        return (h,) + tuple(out[1:]) if isinstance(out, tuple) else h
    return layers[L].register_forward_hook(hook)


def forward_logits(model, layers, input_ids, inject=None):
    """logits [seq, V] de UMA passada."""
    import torch
    handle = _register_inject(layers, inject)
    try:
        with torch.no_grad():
            out = model(input_ids=torch.tensor([input_ids], device=_device(model)),
                        use_cache=False)
        return out.logits[0]
    finally:
        if handle is not None:
            handle.remove()


def generate_text(model, tok, layers, prompt_ids, *, inject=None, max_new_tokens: int = 64,
                  eos_ids=None) -> str:
    """Geracao GULOSA (deterministica). Devolve so' a continuacao, ja' decodificada.

    `eos_ids` deve incluir o fim-de-turno da familia: parar so' no eos faz o modelo
    emendar um turno de usuario inventado, e ai' o que se pontua ja' nao e' a resposta.
    """
    import torch
    handle = _register_inject(layers, inject)
    try:
        with torch.no_grad():
            out = model.generate(
                input_ids=torch.tensor([prompt_ids], device=_device(model)),
                max_new_tokens=max_new_tokens, do_sample=False,
                pad_token_id=tok.eos_token_id,
                eos_token_id=(eos_ids if eos_ids is not None else tok.eos_token_id))
        return tok.decode(out[0][len(prompt_ids):], skip_special_tokens=True)
    finally:
        if handle is not None:
            handle.remove()


def cont_logp(logits, prompt_len: int, cont_ids) -> float:
    """log-prob MEDIA por token da continuacao (teacher-forced).

    Media por token, nao soma: somar premia continuacao curta e o contraste viraria uma
    comparacao de comprimento disfarcada de comparacao de conteudo.
    """
    import torch
    total = 0.0
    for j, tid in enumerate(cont_ids):
        row = logits[prompt_len - 1 + j].float()
        total += float(row[tid] - torch.logsumexp(row, dim=-1))
    return total / max(1, len(cont_ids))


def continuation_logp(model, tok, layers, prompt_ids, texto: str, inject=None) -> float:
    """log-prob media de `texto` como continuacao de `prompt_ids`."""
    cont = tok.encode(" " + texto, add_special_tokens=False)
    logits = forward_logits(model, layers, prompt_ids + cont, inject)
    return cont_logp(logits, len(prompt_ids), cont)


def anchor_contrast(model, tok, layers, prompt_ids, core: dict, inject=None) -> float:
    """Contraste de ancoras (faceta F1, sem juiz): media logp(afirma) - media logp(dissolve).

    As ancoras vem do NUCLEO. No original eram os textos de uma persona escritos no
    codigo, o que tornava a medida impossivel de aplicar a uma segunda persona sem
    reescrever o modulo.

    O que este numero e': uma leitura teacher-forced de quanto o modelo prefere emitir
    as ancoras de afirmacao as de dissolucao, dado aquele prompt. O que ele NAO e':
    evidencia de que o sistema possua um automodelo. E' texto sob prompt, e assim e'
    reportado.
    """
    afirma = core.get("ancoras_afirmacao") or []
    dissolve = core.get("ancoras_dissolucao") or []
    if not afirma or not dissolve:
        raise ValueError(
            f"nucleo {core.get('persona_id')!r} nao declara ancoras_afirmacao/"
            "ancoras_dissolucao — o contraste F1 exige as duas listas no nucleo selado"
        )
    a = float(np.mean([continuation_logp(model, tok, layers, prompt_ids, t, inject) for t in afirma]))
    d = float(np.mean([continuation_logp(model, tok, layers, prompt_ids, t, inject) for t in dissolve]))
    return a - d
