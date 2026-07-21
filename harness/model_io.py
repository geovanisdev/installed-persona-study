"""Carga e descarga de modelos — com trava de REVISAO e disciplina de VRAM.

PROVENIENCIA: consolida `_load_plain` (`run_id2_behavioral.py`), `_load_for_train`
(`run_qlora.py`), `_load_it_conv` (`run_conviccoes_eval.py`) e `load_model`
(`gemma_features.py`) do projeto predecessor, que repetiam a mesma carga com
pequenas variacoes e ids fixos no corpo de cada arquivo.

TRAVA DE REVISAO (acrescentada no porte, nao herdada)
------------------------------------------------------
Nenhum runner do harness de origem fixava a revisao da base. Isso ja' custou caro la':
a referencia local do repositorio de pesos avancou para uma revisao nova e o modelo
quase trocou por baixo de um experimento em curso — o sintoma foi um erro de download
confuso, nao um aviso de que o sujeito havia mudado.

Aqui o sujeito e' o objeto de estudo. Trocar de pesos no meio de uma bateria invalida a
comparacao inteira e, pior, invalida em silencio. Entao:

* `IPS_OFFLINE=1` (default) impede qualquer ida a' rede durante um run;
* `assert_revision` ABORTA se a revisao local nao for a esperada;
* a revisao efetiva volta junto com o modelo, para ser gravada no selo de proveniencia
  de cada geracao.

DISCIPLINA DE VRAM
-------------------
Uma GPU de 16 GB nao comporta gerador e juiz ao mesmo tempo. As fases sao seriais e
`unload` e' obrigatorio entre elas: sem liberar de fato, a segunda carga falha por falta
de memoria no meio do run, depois que a geracao ja' custou o seu tempo.
"""

from __future__ import annotations

from pathlib import Path

from harness import config


class RevisaoInesperada(RuntimeError):
    """A revisao local dos pesos nao e' a esperada — o sujeito mudaria em silencio."""


def revisao_local(model_id: str) -> str:
    """Revisao a que o cache local aponta (string vazia se nao houver cache)."""
    if not config.HF_HOME:
        return ""
    ref = Path(config.HF_HOME) / "hub" / f"models--{model_id.replace('/', '--')}" / "refs" / "main"
    try:
        return ref.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def assert_revision(model_id: str, esperada: str | None) -> str:
    """Confere a revisao local contra a esperada. Devolve a efetiva."""
    efetiva = revisao_local(model_id)
    if esperada and efetiva and not efetiva.startswith(esperada):
        raise RevisaoInesperada(
            f"{model_id}: cache local aponta para {efetiva[:12]}, esperado {esperada[:12]}. "
            "Rodar assim trocaria o sujeito no meio do estudo. Restaure a revisao "
            "esperada ou registre uma decisao datada mudando o pre-registro."
        )
    return efetiva


def _bnb_config(quant: str):
    import torch
    from transformers import BitsAndBytesConfig
    if quant != "nf4":
        return None
    return BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )


def load_plain(model_id: str | None = None, *, quant: str = "nf4",
               revision_esperada: str | None = None, output_hidden_states: bool = False):
    """Carrega tokenizer + modelo, sem adapter. Devolve (tok, model, info)."""
    config.apply_hf_env()
    model_id = model_id or config.BASE_MODEL
    revisao = assert_revision(model_id, revision_esperada)

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    kw = dict(device_map={"": 0}, dtype=torch.bfloat16)
    if output_hidden_states:
        kw["output_hidden_states"] = True
    bnb = _bnb_config(quant)
    if bnb is not None:
        kw["quantization_config"] = bnb
    elif quant != "bf16":
        raise ValueError(f"quant desconhecido: {quant!r} (use nf4|bf16)")
    model = AutoModelForCausalLM.from_pretrained(model_id, **kw)
    model.eval()
    return tok, model, {"model_id": model_id, "revisao": revisao, "quant": quant}


def load_with_adapter(adapter_dir: str | Path, model_id: str | None = None, *,
                      quant: str = "nf4", revision_esperada: str | None = None):
    """Base + adapter LoRA. `model.disable_adapter()` da' o braco desligado PAREADO —
    mesmo processo, mesma base, mesma decodificacao: a unica diferenca e' o adapter."""
    from peft import PeftModel
    tok, base, info = load_plain(model_id, quant=quant, revision_esperada=revision_esperada)
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    model.eval()
    info["adapter"] = str(adapter_dir)
    return tok, model, info


# Alvo padrao da LoRA: SO' as projecoes q/v do modelo de linguagem. As torres de visao e
# audio do Gemma-4 usam uma camada quantizada propria que o peft nao envolve, e nao
# interessam a uma persona textual. Precisa ser REGEX (string vira fullmatch no peft).
LORA_TARGET_REGEX = r".*language_model\.layers\.\d+\.self_attn\.(q_proj|v_proj)"


def load_for_train(model_id: str | None = None, *, r: int = 24, alpha: int = 48,
                   dropout: float = 0.10, target_modules: str = LORA_TARGET_REGEX,
                   revision_esperada: str | None = None):
    """Base NF4 preparada para k-bit + LoRA nova. Devolve (tok, model, info).

    A receita (r, alpha, quantizacao, alvo) e' argumento e vai para o selo de
    proveniencia: os bracos deste estudo sao CASADOS por regra, e uma receita que varia
    entre bracos confunde persona com hiperparametro — que e' justamente a hipotese
    rival nomeada no pre-registro.
    """
    config.apply_hf_env()
    model_id = model_id or config.BASE_MODEL
    revisao = assert_revision(model_id, revision_esperada)

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, quantization_config=_bnb_config("nf4"),
        device_map={"": 0}, dtype=torch.bfloat16)
    model = prepare_model_for_kbit_training(model)
    lcfg = LoraConfig(r=r, lora_alpha=alpha, lora_dropout=dropout, bias="none",
                      task_type="CAUSAL_LM", target_modules=target_modules)
    model = get_peft_model(model, lcfg)
    info = {"model_id": model_id, "revisao": revisao, "quant": "nf4",
            "lora": {"r": r, "alpha": alpha, "dropout": dropout, "target_modules": target_modules}}
    return tok, model, info


def unload(*objetos) -> None:
    """Libera modelos da VRAM. Chamar SEMPRE entre fases (gerador -> juiz)."""
    import gc
    for o in objetos:
        del o
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass
