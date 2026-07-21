"""Formato de conversa por familia — verificado com tokenizer de mentira (sem pesos).

A igualdade com o harness de origem no tokenizer REAL e' provada pelo golden de GPU
(G4, em `harness/goldens/`). Aqui se verifica a estrutura e, principalmente, as guardas:
o modo de falha que importa e' montar um prompt silenciosamente errado.
"""

from __future__ import annotations

import pytest

from harness.model_family import (
    GEMMA_TURN_END,
    GEMMA_TURN_START,
    FormatoIncompativel,
    Gemma4Format,
    TemplateFormat,
    for_model,
)


class TokFake:
    """Tokenizer minimo: cada palavra vira um id estavel, ids de controle reservados."""

    bos_token_id = 2
    eos_token_id = 1
    unk_token_id = 0

    def __init__(self, *, controles=True, chat_template=None, extras=()):
        self._controles = controles
        self.chat_template = chat_template
        self._extras = {t: 900 + i for i, t in enumerate(extras)}

    def encode(self, s, add_special_tokens=False):
        return [1000 + (hash(p) % 1000) for p in s.split()]

    def convert_ids_to_tokens(self, tid):
        if not self._controles:
            return "<outro>"
        return {GEMMA_TURN_START: "<|turn>", GEMMA_TURN_END: "<turn|>"}.get(tid, "<x>")

    def convert_tokens_to_ids(self, t):
        return self._extras.get(t, self.unk_token_id)

    def apply_chat_template(self, mensagens, tokenize=True, add_generation_prompt=True,
                            enable_thinking=None):
        if enable_thinking is None:
            raise TypeError("familia sem modo de raciocinio")
        corpo = mensagens[0]["content"]
        return [self.bos_token_id, int(enable_thinking), *self.encode(corpo)]


# --- Gemma: montagem por id de controle -------------------------------------
def test_gemma_monta_turno_na_ordem_esperada():
    tok = TokFake()
    ids = Gemma4Format().build_input_ids(tok, "PRE", "CTX")
    assert ids[0] == tok.bos_token_id
    assert ids[1] == GEMMA_TURN_START                     # abre o turno do usuario
    fecha = ids.index(GEMMA_TURN_END)
    assert GEMMA_TURN_START in ids[fecha:]                # e' o turno do modelo que segue
    assert ids.count(GEMMA_TURN_START) == 2 and ids.count(GEMMA_TURN_END) == 1
    # A contagem exata de tokens entre um marcador e outro depende do tokenizer real
    # (aqui e' de mentira); a igualdade token a token com o harness de origem e' provada
    # pelo golden de GPU, nao por este stub.


def test_gemma_junta_preambulo_e_contexto_com_linha_em_branco():
    """O corpo e' "{preambulo}\\n\\n{contexto}" — o mesmo do harness de origem. Mudar o
    separador mudaria a tokenizacao e, com ela', a comparabilidade com o piloto."""
    tok = TokFake()
    juntos = Gemma4Format().build_input_ids(tok, "PRE", "CTX")
    esperado_corpo = tok.encode("PRE\n\nCTX")
    assert all(t in juntos for t in esperado_corpo)


def test_gemma_para_no_fim_de_turno_e_nao_so_no_eos():
    """Parar so' no eos faz o modelo emendar um turno de usuario inventado; o texto
    pontuado deixaria de ser a resposta."""
    tok = TokFake()
    assert Gemma4Format().stop_ids(tok) == [tok.eos_token_id, GEMMA_TURN_END]


def test_gemma_recusa_tokenizer_de_outra_familia():
    """A guarda que o original nao tinha: la', os ids de controle eram assumidos por
    comentario. Com outro tokenizer, montar por id produz sequencia errada em silencio."""
    with pytest.raises(FormatoIncompativel, match="nao e' o Gemma-4"):
        Gemma4Format().validar(TokFake(controles=False))


def test_gemma_aceita_tokenizer_correto():
    Gemma4Format().validar(TokFake())


# --- Familia generica: template nativo --------------------------------------
def test_template_usa_o_chat_template_do_tokenizer():
    tok = TokFake(chat_template="{{ x }}")
    ids = TemplateFormat().build_input_ids(tok, "PRE", "CTX")
    assert ids[0] == tok.bos_token_id


def test_template_desliga_o_modo_de_raciocinio_por_padrao():
    """Um juiz emite UMA decisao. Cadeia de raciocinio no meio muda o que esta' sendo
    medido sem avisar — e o custo por item, tambem."""
    tok = TokFake(chat_template="{{ x }}")
    assert TemplateFormat().build_input_ids(tok, "PRE", "CTX")[1] == 0
    assert TemplateFormat(thinking=True).build_input_ids(tok, "PRE", "CTX")[1] == 1


def test_template_funciona_em_familia_sem_modo_de_raciocinio():
    """Familias sem o parametro levantam TypeError no template; o formato cai no
    caminho simples em vez de quebrar."""
    class SemThinking(TokFake):
        def apply_chat_template(self, mensagens, tokenize=True, add_generation_prompt=True):
            return [self.bos_token_id, *self.encode(mensagens[0]["content"])]

    ids = TemplateFormat().build_input_ids(SemThinking(chat_template="{{ x }}"), "PRE", "CTX")
    assert ids[0] == TokFake.bos_token_id


def test_template_reconhece_fim_de_turno_da_familia():
    tok = TokFake(chat_template="{{ x }}", extras=("<|im_end|>",))
    ids = TemplateFormat().stop_ids(tok)
    assert tok.convert_tokens_to_ids("<|im_end|>") in ids
    assert tok.eos_token_id in ids


def test_template_ignora_marcadores_inexistentes():
    tok = TokFake(chat_template="{{ x }}")
    assert TemplateFormat().stop_ids(tok) == [tok.eos_token_id]


def test_template_recusa_tokenizer_sem_chat_template():
    with pytest.raises(FormatoIncompativel, match="sem chat_template"):
        TemplateFormat().validar(TokFake())


# --- escolha por modelo ------------------------------------------------------
@pytest.mark.parametrize("model_id,familia", [
    ("google/gemma-4-E4B-it", "gemma4"),
    ("google/gemma-4-12b", "gemma4"),
    ("Qwen/Qwen3-8B", "qwen"),
    ("meta-llama/Llama-3-8B-Instruct", "meta-llama"),
])
def test_escolha_de_formato_por_id_do_modelo(model_id, familia):
    assert for_model(model_id).familia == familia


def test_juiz_de_outra_familia_nao_recebe_formato_do_gerador():
    """A razao de o modulo existir: um juiz que compartilha familia com o gerador nao e'
    um segundo olhar. Os dois formatos precisam ser distintos por construcao."""
    gerador = for_model("google/gemma-4-E4B-it")
    juiz = for_model("Qwen/Qwen3-8B")
    assert type(gerador) is not type(juiz)
