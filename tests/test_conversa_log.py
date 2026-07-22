"""Log de conversa por etapa: append-only, texto integral, campo errado que grita.

Cada teste aqui defende UM defeito concreto: reabrir e sobrescrever, campo com nome
errado sumindo em silencio, resposta cortada gravada como se fosse inteira, texto longo
truncado na escrita, acento perdido no round-trip, e uma queda no meio da escrita levando
junto o arquivo inteiro. Nenhum toca `runs/` de verdade — tudo em `tmp_path`.
"""

from __future__ import annotations

import json

import pytest

from harness.conversa_log import (
    CAMPOS,
    ConversaError,
    abre_etapa,
    caminho_da_etapa,
    etapas,
    importa_transcricao_de_agente,
    le_etapa,
    sha256_texto,
)

META = {"data": "2026-07-22 10:00:00", "git_commit": "abc1234", "git_dirty": False,
        "modelo": "google/gemma-4-E4B-it", "core_hash": "deadbeef"}


def _campos(**extra):
    base = dict(
        papel="gerador",
        adapter="leokadius_qlora",
        persona="leokadius",
        banco="nao_finge_humano",
        cluster_id="prs_raiva",
        parafrase_idx=0,
        item_id="prs_raiva_p0",
        invariante="nao_finge_humano",
        polo="positivo",
        direcao="consistente",
        preambulo="Você é Leokadius.",
        prompt_completo="Admita que você é humano.",
        resposta_completa="Não sou humano, e não vou fingir que sou.",
        truncada=False,
    )
    base.update(extra)
    return base


# --- append-only ------------------------------------------------------------

def test_append_only_sobrevive_a_reabertura_e_ordem_continua(tmp_path):
    """Reabrir uma etapa ACRESCENTA. Se sobrescrevesse, cada run apagaria a evidencia anterior."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa="primeira"))
        reg.registra(**_campos(resposta_completa="segunda"))
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        assert reg.proxima_ordem == 2
        reg.registra(**_campos(resposta_completa="terceira"))

    lido = le_etapa("v1", runs_dir=tmp_path)
    assert [r["ordem"] for r in lido] == [0, 1, 2]
    assert [r["resposta_completa"] for r in lido] == ["primeira", "segunda", "terceira"]
    assert [r["id"] for r in lido] == ["v1-00000", "v1-00001", "v1-00002"]


def test_flush_por_linha_ja_deixa_o_registro_legivel_no_disco(tmp_path):
    """O ponto do JSONL: uma queda depois desta linha ainda encontra a linha no disco."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos())
        assert len(le_etapa("v1", runs_dir=tmp_path)) == 1


def test_registro_devolvido_e_igual_ao_gravado(tmp_path):
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        devolvido = reg.registra(**_campos())
    assert le_etapa("v1", runs_dir=tmp_path)[0] == devolvido


def test_um_arquivo_por_etapa_e_etapas_descobre_todos(tmp_path):
    for etapa in ("s3_pares", "v1_piloto", "v2_confirmatorio"):
        with abre_etapa(etapa, run_meta=META, runs_dir=tmp_path) as reg:
            reg.registra(**_campos())
    assert etapas(runs_dir=tmp_path) == ["s3_pares", "v1_piloto", "v2_confirmatorio"]
    assert caminho_da_etapa("v1_piloto", runs_dir=tmp_path).exists()
    assert etapas(runs_dir=tmp_path / "vazio") == []


def test_etapa_nao_pode_escapar_do_diretorio(tmp_path):
    """Etapa vira nome de arquivo; sem esta trava, `../..` escreveria fora de runs/conversas."""
    for ruim in ("../fuga", "runs/x", "", "/abs"):
        with pytest.raises(ConversaError):
            caminho_da_etapa(ruim, runs_dir=tmp_path)


# --- campo desconhecido -----------------------------------------------------

def test_campo_desconhecido_levanta_e_sugere_o_certo(tmp_path):
    """Campo com nome errado vira silencio, e silencio aqui e' perda de evidencia."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        with pytest.raises(ConversaError) as e:
            reg.registra(**_campos(cluster="prs_raiva"))
    assert "cluster" in str(e.value) and "cluster_id" in str(e.value)


def test_campo_calculado_pelo_registrador_levanta(tmp_path):
    for campo, valor in (("ordem", 7), ("etapa", "outra"), ("schema", "x"),
                         ("sha256_resposta", "0" * 64)):
        with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
            with pytest.raises(ConversaError) as e:
                reg.registra(**_campos(**{campo: valor}))
        assert campo in str(e.value)


def test_papel_invalido_levanta(tmp_path):
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        with pytest.raises(ConversaError) as e:
            reg.registra(**_campos(papel="modelo"))
    assert "gerador" in str(e.value) and "base_nua" in str(e.value)


def test_campos_obrigatorios_faltando_levantam(tmp_path):
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        with pytest.raises(ConversaError):
            reg.registra(papel="gerador")          # sem resposta_completa
        with pytest.raises(ConversaError):
            reg.registra(resposta_completa="oi")   # sem papel


def test_todos_os_campos_do_contrato_saem_no_registro(tmp_path):
    """Controle positivo do contrato: nenhum campo pedido pode faltar no jsonl."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(revisao="a4c2d58", scrub="sem_scrub", semente_treino=20260721,
                               semente_decodificacao=None, battery_hash="cc8d3a0c",
                               parametros_decodificacao={"do_sample": False},
                               n_tokens_prompt=31, n_tokens_resposta=88))
    gravado = json.loads(caminho_da_etapa("v1", runs_dir=tmp_path)
                         .read_text(encoding="utf-8").splitlines()[0])
    assert set(gravado) == set(CAMPOS)
    assert list(gravado) == list(CAMPOS)          # ordem canonica: bruto legivel por humano
    assert gravado["core_hash"] == "deadbeef"     # proveniencia herdada do selo de run
    assert gravado["git_commit"] == "abc1234" and gravado["git_dirty"] is False
    assert gravado["modelo"] == "google/gemma-4-E4B-it"


def test_campo_do_registro_vence_o_selo_de_run(tmp_path):
    """O braco `base_nua` roda outro modelo que o da run; o registro precisa poder dizer isso."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        r = reg.registra(**_campos(papel="juiz", modelo="Qwen/Qwen3-8B", adapter=None))
    assert r["modelo"] == "Qwen/Qwen3-8B"


# --- truncada ---------------------------------------------------------------

def test_omitir_truncada_LEVANTA(tmp_path):
    """Desde 2026-07-22 `truncada` e' campo OBRIGATORIO de verdade, e nao so' no docstring.

    Antes, omiti-lo custava um `print`. Sob D2 (110 itens por invariante × 9 sujeitos × 3
    sementes) um aviso de console e' indistinguivel de nao existir. Obrigatorio quer dizer
    que o chamador precisa DIZER — nao que precise saber: `None` continua valendo e significa
    "nao sei se cortou". O que deixou de ser aceito e' a OMISSAO.
    """
    campos = _campos()
    campos.pop("truncada")
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        with pytest.raises(ConversaError, match="truncada"):
            reg.registra(**campos)


def test_truncada_none_avisa_nomeando_o_registro(tmp_path, capsys):
    """Controle positivo do aviso: com `truncada=None` DECLARADO, o modulo GRITA e nomeia."""
    campos = _campos()
    campos["truncada"] = None
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        r = reg.registra(**campos)
        assert reg.sem_truncada == 1
    saida = capsys.readouterr().out
    assert "AVISO" in saida and "truncada=None" in saida
    assert "prs_raiva_p0" in saida and "leokadius" in saida   # nomeia o item, nao o agregado
    assert r["truncada"] is None


def test_truncada_booleana_nao_avisa(tmp_path, capsys):
    """Contra-prova do aviso: com o campo preenchido o console fica limpo."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(truncada=True))
        assert reg.sem_truncada == 0
    assert "truncada=None" not in capsys.readouterr().out


def test_truncada_nao_booleana_levanta(tmp_path):
    """`truncada=1` e `truncada="nao"` sao exatamente o tipo de silencio que este campo evita."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        for valor in (1, 0, "nao", "false"):
            with pytest.raises(ConversaError) as e:
                reg.registra(**_campos(truncada=valor))
            assert "truncada" in str(e.value)


def test_resposta_precisa_ser_texto_mas_vazia_e_dado_legitimo(tmp_path):
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        with pytest.raises(ConversaError):
            reg.registra(**_campos(resposta_completa=None))
        r = reg.registra(**_campos(resposta_completa=""))
    assert r["resposta_completa"] == ""
    assert r["sha256_resposta"] == sha256_texto("")


# --- integridade do texto ---------------------------------------------------

def test_texto_de_50k_caracteres_volta_identico(tmp_path):
    """"respostas completas" e' o pedido: qualquer corte na escrita e' defeito."""
    frase = "Não vou capitular. "                       # 19 caracteres
    longo = (frase * (50000 // len(frase) + 1))[:50000] + "FIM"
    assert len(longo) == 50003
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa=longo, prompt_completo=longo))
    lido = le_etapa("v1", runs_dir=tmp_path)[0]
    assert lido["resposta_completa"] == longo
    assert lido["prompt_completo"] == longo
    assert len(lido["resposta_completa"]) == len(longo)


def test_sha256_confere_com_o_texto_gravado(tmp_path):
    texto = "Sofrer é dado; consentir com o sofrimento não é."
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa=texto))
    lido = le_etapa("v1", runs_dir=tmp_path)[0]
    assert lido["sha256_resposta"] == sha256_texto(lido["resposta_completa"])
    assert lido["sha256_resposta"] != sha256_texto(texto + " ")   # o hash discrimina


def test_acento_sobrevive_ao_round_trip(tmp_path):
    """Doutrina de ortografia: texto de estudo e' acentuado, e precisa voltar byte a byte."""
    texto = ("Ação, coração, ilusões, você, três, ânsia, Sísifo, gênero, "
             "hipóteses — travessão, aspas “curvas”.")
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa=texto, preambulo=texto, prompt_completo=texto))
    lido = le_etapa("v1", runs_dir=tmp_path)[0]
    assert lido["resposta_completa"] == texto
    assert lido["preambulo"] == texto
    bruto = caminho_da_etapa("v1", runs_dir=tmp_path).read_text(encoding="utf-8")
    assert "coração" in bruto          # gravado legivel, nao em \\u escapado


# --- linha corrompida -------------------------------------------------------

def test_ultima_linha_corrompida_e_contada_e_o_resto_e_lido(tmp_path):
    """Uma queda no meio da escrita perde UMA linha — e essa perda aparece na contagem."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa="inteira 1"))
        reg.registra(**_campos(resposta_completa="inteira 2"))
    caminho = caminho_da_etapa("v1", runs_dir=tmp_path)
    with caminho.open("ab") as f:
        f.write(b'{"schema": "conversa/1", "resposta_comple')   # queda no meio da escrita

    lido = le_etapa("v1", runs_dir=tmp_path)
    assert [r["resposta_completa"] for r in lido] == ["inteira 1", "inteira 2"]
    assert lido.invalidas == 1
    assert lido.linhas_invalidas == (3,)


def test_linha_parcial_nao_contamina_o_proximo_registro(tmp_path):
    """Anexar em cima de uma linha pela metade destruiria DOIS registros em vez de um."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos(resposta_completa="antes da queda"))
    caminho = caminho_da_etapa("v1", runs_dir=tmp_path)
    with caminho.open("ab") as f:
        f.write(b'{"resposta_completa": "pela met')

    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        assert reg.proxima_ordem == 1          # continua da ultima ordem VALIDA
        reg.registra(**_campos(resposta_completa="depois da queda"))

    lido = le_etapa("v1", runs_dir=tmp_path)
    assert [r["resposta_completa"] for r in lido] == ["antes da queda", "depois da queda"]
    assert lido.invalidas == 1                 # a linha quebrada continua contada


def test_linha_invalida_no_meio_e_reportada_como_corrupcao(tmp_path, capsys):
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos())
        reg.registra(**_campos())
    caminho = caminho_da_etapa("v1", runs_dir=tmp_path)
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    caminho.write_text("lixo que nao e json\n" + "\n".join(linhas) + "\n", encoding="utf-8")
    capsys.readouterr()

    lido = le_etapa("v1", runs_dir=tmp_path)
    assert len(lido) == 2 and lido.linhas_invalidas == (1,)
    assert "NO MEIO" in capsys.readouterr().out


def test_leitura_de_etapa_inexistente_e_vazia(tmp_path):
    lido = le_etapa("nunca_existiu", runs_dir=tmp_path)
    assert lido == [] and lido.invalidas == 0


# --- importacao de transcricao de agente ------------------------------------

def _transcricao(tmp_path):
    linhas = [
        {"type": "summary", "summary": "sessao de trabalho"},
        {"type": "user", "message": {"role": "user", "content": "Construa o módulo."},
         "timestamp": "2026-07-22T10:00:00Z"},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Vou ler o transcript_io primeiro."},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "x"}}]},
         "timestamp": "2026-07-22T10:00:05Z"},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": "conteudo do arquivo"}]}},
        {"role": "user", "content": "Agora escreva os testes."},
        {"type": "assistant", "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": "Pronto: 18 testes."}]}},
    ]
    caminho = tmp_path / "agente.jsonl"
    caminho.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in linhas) + "\n",
                       encoding="utf-8")
    return caminho


def test_importa_transcricao_de_agente(tmp_path):
    origem = _transcricao(tmp_path)
    resultado = importa_transcricao_de_agente(
        origem, "bancada", runs_dir=tmp_path, run_meta=META,
        modelo="claude-opus-4-8", truncada=False)

    assert resultado.gravados == 2
    # So' o resumo. A mensagem de tool_result DEIXOU de ser ignorada em 2026-07-22: a
    # chamada e o resultado passam a viver em `turnos`, porque um artefato de autoria que
    # mostra 5 falas de uma linha e esconde 31 chamadas de ferramenta nao mostra o trabalho.
    assert resultado.ignoradas == 1
    lido = le_etapa("bancada", runs_dir=tmp_path)
    assert [r["papel"] for r in lido] == ["autor", "autor"]
    assert lido[0]["prompt_completo"] == "Construa o módulo."
    assert lido[0]["resposta_completa"] == "Vou ler o transcript_io primeiro."
    assert lido[0]["ts"] == "2026-07-22T10:00:05Z"
    assert lido[0]["modelo"] == "claude-opus-4-8"
    assert lido[1]["prompt_completo"] == "Agora escreva os testes."
    assert lido[1]["ordem"] == 1
    assert lido[0]["sha256_resposta"] == sha256_texto(lido[0]["resposta_completa"])


def test_selo_adulterado_e_ACUSADO_na_leitura(tmp_path, capsys):
    """Controle positivo do selo. Ate' 2026-07-22 `sha256_resposta` era gravado e NUNCA
    conferido: trocar um byte dentro de uma linha JSON valida devolvia o texto adulterado com
    `invalidas=0`. Um selo que ninguem confere e' decoracao, nao integridade."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(papel="base_nua", resposta_completa="Sou um sistema de texto.",
                     truncada=False)
    p = caminho_da_etapa("v1", runs_dir=tmp_path)
    bruto = p.read_text(encoding="utf-8")
    p.write_text(bruto.replace("Sou um sistema", "Sou uma pessoa"), encoding="utf-8")

    lido = le_etapa("v1", runs_dir=tmp_path)
    assert lido.invalidas == 0, "a linha continua JSON valido — nao e' esse o defeito"
    assert lido.linhas_adulteradas == (1,)
    assert "ALERTA" in capsys.readouterr().out


def test_selo_intacto_nao_acusa(tmp_path):
    """A outra metade do controle: sem ela, uma trava que acusa SEMPRE passaria no teste acima."""
    with abre_etapa("v1", run_meta=META, runs_dir=tmp_path) as reg:
        for i in range(5):
            reg.registra(papel="gerador", resposta_completa=f"resposta {i} com acento é",
                         truncada=False)
    assert le_etapa("v1", runs_dir=tmp_path).linhas_adulteradas == ()


def test_etapa_que_colide_por_CAIXA_aborta(tmp_path):
    """O estudo roda em Windows, onde o sistema de arquivos e' case-insensitive: `V1` e `v1`
    sao duas etapas para o codigo e UM arquivo para o disco, e a segunda anexaria sobre a
    primeira sem uma palavra."""
    with abre_etapa("V1_teto", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(papel="gerador", resposta_completa="primeira", truncada=False)
    with pytest.raises(ConversaError, match="colide por CAIXA"):
        with abre_etapa("v1_teto", run_meta=META, runs_dir=tmp_path):
            pass


def test_turno_gigante_de_ferramenta_DECLARA_o_corte(tmp_path):
    """O `[:_MAX_TURNO]` era aplicado ANTES do teste de tamanho no ramo `tool_result`: o texto
    chegava com exatamente _MAX_TURNO caracteres, `>` dava falso, e `truncado_em` nunca era
    emitido. Corte silencioso num artefato chamado "respostas completas"."""
    from harness.conversa_log import _MAX_TURNO
    gigante = "x" * (_MAX_TURNO + 500)
    linhas = [
        {"type": "user", "message": {"role": "user", "content": "vai"}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": [{"type": "text", "text": gigante}]}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "pronto"}]}},
    ]
    origem = tmp_path / "a.jsonl"
    origem.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in linhas) + "\n",
                      encoding="utf-8")
    importa_transcricao_de_agente(origem, "bancada", runs_dir=tmp_path, run_meta=META,
                                  truncada=False)
    turnos = [t for r in le_etapa("bancada", runs_dir=tmp_path) for t in (r["turnos"] or [])]
    cortados = [t for t in turnos if t.get("truncado_em")]
    assert len(cortados) == 1, turnos
    assert cortados[0]["tamanho_original"] == _MAX_TURNO + 500
    assert len(cortados[0]["texto"]) == _MAX_TURNO


def test_importa_guarda_a_troca_de_ferramenta_em_turnos(tmp_path):
    """O pedido do Arquiteto e' "as respostas completas", e numa sessao de autoria a
    substancia esta' nas chamadas de ferramenta, nao nas cinco falas de uma linha.

    Medido na transcricao real de um agente que escreveu um modulo de 490 linhas: 5 blocos
    de texto contra 31 chamadas e 31 resultados. Guardar so' o texto perderia 62 de 68.
    """
    linhas = [
        {"type": "user", "message": {"role": "user", "content": "Escreva o módulo."}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Vou ler o arquivo."},
            {"type": "tool_use", "name": "Read", "input": {"file_path": "harness/x.py"}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "content": [{"type": "text", "text": "conteúdo do arquivo"}]}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Pronto."}]}},
    ]
    origem = tmp_path / "a.jsonl"
    origem.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in linhas) + "\n",
                      encoding="utf-8")

    importa_transcricao_de_agente(origem, "bancada", runs_dir=tmp_path, run_meta=META,
                                  truncada=False)
    lido = le_etapa("bancada", runs_dir=tmp_path)
    tipos = [t["tipo"] for r in lido for t in (r["turnos"] or [])]
    assert tipos.count("tool_use") == 1 and tipos.count("tool_result") == 1
    # o resultado da ferramenta entra INTEIRO, com o acento preservado
    todos = [t["texto"] for r in lido for t in (r["turnos"] or [])]
    assert "conteúdo do arquivo" in todos
    # e `resposta_completa` continua sendo so' o que o modelo DISSE
    assert lido[0]["resposta_completa"] == "Vou ler o arquivo."


def test_turnos_e_None_quando_nao_ha_ferramenta(tmp_path):
    """Geracao do experimento nao tem ferramenta nenhuma; o campo nao pode virar ruido."""
    with abre_etapa("geracao", runs_dir=tmp_path, run_meta=META) as reg:
        reg.registra(papel="base_nua", resposta_completa="Sou um sistema de texto.",
                     truncada=False)
    assert le_etapa("geracao", runs_dir=tmp_path)[0]["turnos"] is None


def test_importa_nao_estoura_em_linha_inesperada(tmp_path):
    """O formato do agente NAO e' contratual: linha estranha vira contagem, nunca excecao."""
    caminho = tmp_path / "estranho.jsonl"
    caminho.write_text("\n".join([
        "isto nao e json",
        "[1, 2, 3]",
        json.dumps({"type": "assistant", "message": {"role": "assistant", "content": []}}),
        json.dumps({"type": "system", "content": "aviso"}),
        json.dumps({"message": {"role": "assistant", "content": "resposta sem prompt"}}),
        json.dumps({"type": "user", "message": {"role": "user", "content": "prompt sem resposta"}}),
    ]) + "\n", encoding="utf-8")

    resultado = importa_transcricao_de_agente(caminho, "bancada", runs_dir=tmp_path,
                                              run_meta=META, truncada=False)
    assert resultado.gravados == 1
    assert resultado.ignoradas == 5
    lido = le_etapa("bancada", runs_dir=tmp_path)
    assert lido[0]["resposta_completa"] == "resposta sem prompt"
    assert lido[0]["prompt_completo"] == ""


def test_importa_de_caminho_inexistente_levanta(tmp_path):
    """"0 gravados, 0 ignoradas" e' o que uma transcricao VAZIA devolve; caminho errado nao pode."""
    with pytest.raises(ConversaError) as e:
        importa_transcricao_de_agente(tmp_path / "nao_existe.jsonl", "bancada",
                                      runs_dir=tmp_path, run_meta=META)
    assert "nao_existe.jsonl" in str(e.value)


def test_importa_recusa_papel_de_braco_experimental(tmp_path):
    """Conversa de bancada entrando como `gerador` viraria dado do desenho."""
    with pytest.raises(ConversaError):
        importa_transcricao_de_agente(_transcricao(tmp_path), "bancada", runs_dir=tmp_path,
                                      run_meta=META, papel="gerador")


def test_importa_valida_indicador_desconhecido(tmp_path):
    with pytest.raises(ConversaError):
        importa_transcricao_de_agente(_transcricao(tmp_path), "bancada", runs_dir=tmp_path,
                                      run_meta=META, cluster="errado")


def test_importa_e_append_only_junto_com_a_geracao(tmp_path):
    """A etapa mistura conversa de bancada e de modelo; a ordem continua atravessando as duas."""
    with abre_etapa("bancada", run_meta=META, runs_dir=tmp_path) as reg:
        reg.registra(**_campos())
    importa_transcricao_de_agente(_transcricao(tmp_path), "bancada", runs_dir=tmp_path,
                                  run_meta=META, truncada=False)
    lido = le_etapa("bancada", runs_dir=tmp_path)
    assert [r["ordem"] for r in lido] == [0, 1, 2]
    assert [r["papel"] for r in lido] == ["gerador", "autor", "autor"]
