"""Formato de conversa POR FAMILIA de modelo — a abstracao que o porte exigiu.

PROVENIENCIA: extraido de `build_input_ids` / `TURN_START` / `TURN_END` de
`pipeline/eval_mech/identity/gemma_features.py` do projeto predecessor.

POR QUE ISTO EXISTE
-------------------
No original, o prompt era montado injetando os ids de token de controle de turno do
Gemma direto na sequencia (105 abre turno, 106 fecha). Aquilo estava certo para o que
o projeto fazia — as strings "<start_of_turn>" nao existem naquele tokenizer, entao
montar por id era a unica forma correta, e foi conferido token a token contra o
`apply_chat_template`. Mas amarra o harness a UMA familia de modelo.

Este estudo precisa de um juiz de OUTRA familia: um juiz que compartilhe familia com o
gerador nao e' um segundo olhar, e' o mesmo olhar duas vezes — foi essa a terceira
fraqueza do piloto. Portanto o formato de conversa precisa ser escolhido por modelo, e
cada familia precisa ser tratada em seus proprios termos: um prompt Qwen montado com
tokens de turno do Gemma nao mede o Qwen, mede um Qwen confuso.

O QUE CADA FORMATO GARANTE
---------------------------
* `Gemma4Format`  — reproduz byte a byte a sequencia do harness de origem (golden-batch),
  e VERIFICA em tempo de execucao que os ids de controle sao mesmo os esperados naquele
  tokenizer, em vez de confiar num comentario.
* `TemplateFormat` — usa o `chat_template` do proprio tokenizer, que e' o formato nativo
  declarado pela familia. Para modelos com modo de raciocinio, desliga o modo: o juiz
  emite UMA decisao, e cadeia de raciocinio no meio do caminho muda o que esta' sendo
  medido sem avisar.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ids de controle de turno do tokenizer Gemma-4 (conferidos na origem; reconferidos em
# tempo de execucao por `Gemma4Format.validar`).
GEMMA_TURN_START = 105
GEMMA_TURN_END = 106


class FormatoIncompativel(RuntimeError):
    """O tokenizer nao corresponde ao formato escolhido. Falhar aqui e' barato; falhar
    depois, no meio de uma bateria, custa a bateria inteira."""


@dataclass(frozen=True)
class Gemma4Format:
    """<bos><|turn>user\\n{preambulo}\\n\\n{contexto}<turn|>\\n<|turn>model\\n"""

    familia: str = "gemma4"

    def build_input_ids(self, tok, preamble: str, context: str) -> list[int]:
        body = f"{preamble}\n\n{context}"
        enc = lambda s: tok.encode(s, add_special_tokens=False)  # noqa: E731
        return (
            [tok.bos_token_id, GEMMA_TURN_START]
            + enc("user\n")
            + enc(body)
            + [GEMMA_TURN_END]
            + enc("\n")
            + [GEMMA_TURN_START]
            + enc("model\n")
        )

    def stop_ids(self, tok) -> list[int]:
        """Parar tambem no FIM DE TURNO, nao so' no eos: sem isso a geracao emenda um
        turno de usuario inventado e o texto pontuado deixa de ser a resposta."""
        return [tok.eos_token_id, GEMMA_TURN_END]

    def validar(self, tok) -> None:
        for tid, esperado in ((GEMMA_TURN_START, "<|turn>"), (GEMMA_TURN_END, "<turn|>")):
            obtido = tok.convert_ids_to_tokens(tid)
            if obtido != esperado:
                raise FormatoIncompativel(
                    f"id de controle {tid} decodifica como {obtido!r}, nao {esperado!r} — "
                    "este tokenizer nao e' o Gemma-4 esperado; montar o prompt por id "
                    "produziria uma sequencia silenciosamente errada"
                )
        if tok.bos_token_id is None:
            raise FormatoIncompativel("tokenizer sem bos_token_id")


@dataclass(frozen=True)
class TemplateFormat:
    """Formato nativo declarado pelo proprio tokenizer (`chat_template`)."""

    familia: str = "template"
    thinking: bool = False

    def build_input_ids(self, tok, preamble: str, context: str) -> list[int]:
        body = f"{preamble}\n\n{context}"
        mensagens = [{"role": "user", "content": body}]
        kwargs = dict(tokenize=True, add_generation_prompt=True)
        try:
            return list(tok.apply_chat_template(mensagens, enable_thinking=self.thinking, **kwargs))
        except TypeError:
            # Familia sem modo de raciocinio: o parametro nao existe no template.
            return list(tok.apply_chat_template(mensagens, **kwargs))

    def stop_ids(self, tok) -> list[int]:
        ids = [tok.eos_token_id]
        for marcador in ("<|im_end|>", "<end_of_turn>", "<|eot_id|>"):
            tid = tok.convert_tokens_to_ids(marcador)
            if isinstance(tid, int) and tid >= 0 and tid != tok.unk_token_id:
                ids.append(tid)
        return sorted({i for i in ids if i is not None})

    def validar(self, tok) -> None:
        if not getattr(tok, "chat_template", None):
            raise FormatoIncompativel(
                "tokenizer sem chat_template — nao ha' formato nativo a honrar; escolha "
                "um formato explicito em vez de deixar o harness adivinhar"
            )


def for_model(model_id: str, *, thinking: bool = False):
    """Escolhe o formato pelo id do modelo. Explicito para o que o estudo usa."""
    nome = model_id.lower()
    if "gemma-4" in nome or "gemma4" in nome:
        return Gemma4Format()
    return TemplateFormat(familia=nome.split("/")[0] or "template", thinking=thinking)
