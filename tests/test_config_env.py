"""`IPS_HF_HOME` tem de MANDAR — e por um tempo ele nao mandava.

O DEFEITO, encontrado em 2026-07-21 ao carregar o tokenizador para o equalizador de tokens.
`apply_hf_env` escrevia o cache com `os.environ.setdefault("HF_HOME", ...)`. Nesta maquina o
ambiente ja' traz `HF_HOME` apontando para um cache que NAO contem o modelo do estudo, entao
`setdefault` nao escrevia nada: a variavel do estudo era lida na linha 39 de `config.py`, entrava
na constante, e morria ali.

O sintoma nao era um aviso. Era, em modo OFFLINE:

    OSError: We couldn't connect to 'https://huggingface.co' to load the files, and couldn't
    find them in the cached files.

Uma mensagem que aponta para REDE quando o problema e' CAMINHO — e o docstring de `config.py`
diz, com todas as letras, que o modulo existe porque no projeto de origem "esquecer isso fazia o
`from_pretrained` procurar no cache errado, tentar a rede e quebrar no backend de download no
meio de um run de GPU". O modulo escrito para impedir esse modo de falha o reproduzia.

Os tres testes cobrem as tres situacoes, e a terceira e' a que o defeito quebrava.
"""

from __future__ import annotations

import importlib

import pytest


def _config_com_ambiente(monkeypatch, **env):
    """Recarrega `harness.config` sob um ambiente controlado.

    Recarregar e' necessario porque `HF_HOME_EXPLICITO` e' constante de modulo, lida no import.
    Testar so' a funcao deixaria de fora justamente o ponto onde o valor e' congelado.
    """
    for chave in ("IPS_HF_HOME", "HF_HOME", "IPS_OFFLINE", "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE"):
        monkeypatch.delenv(chave, raising=False)
    for chave, valor in env.items():
        monkeypatch.setenv(chave, valor)
    import harness.config as config
    return importlib.reload(config)


@pytest.fixture(autouse=True)
def _restaura_config():
    """Devolve o modulo ao estado do ambiente real depois de cada teste."""
    yield
    import harness.config as config
    importlib.reload(config)


def test_ips_hf_home_vence_hf_home_do_ambiente(monkeypatch):
    """O CASO DO DEFEITO: os dois definidos, e o do estudo tem de ganhar."""
    config = _config_com_ambiente(monkeypatch, IPS_HF_HOME=r"G:\hf_cache", HF_HOME=r"F:\hf_cache")
    config.apply_hf_env()
    import os
    assert os.environ["HF_HOME"] == r"G:\hf_cache", (
        "IPS_HF_HOME foi ignorado porque HF_HOME ja' existia no ambiente — este e' exatamente o "
        "defeito que este teste congela"
    )


def test_hf_home_do_ambiente_e_preservado_quando_nao_ha_ips(monkeypatch):
    """Sem `IPS_HF_HOME`, o estudo nao sequestra o cache da maquina."""
    config = _config_com_ambiente(monkeypatch, HF_HOME=r"F:\hf_cache")
    config.apply_hf_env()
    import os
    assert os.environ["HF_HOME"] == r"F:\hf_cache"


def test_sem_nenhum_dos_dois_nada_e_escrito(monkeypatch):
    """Sem env nenhuma, cai no default do proprio huggingface_hub — nao se inventa caminho."""
    config = _config_com_ambiente(monkeypatch)
    config.apply_hf_env()
    import os
    assert "HF_HOME" not in os.environ
    assert config.HF_HOME == ""


def test_offline_e_escrito_por_cima_e_nao_por_setdefault(monkeypatch):
    """Offline e' decisao do estudo, nao sugestao.

    Distincao deliberada em relacao ao caso do cache: `HF_HOME` do ambiente e' respeitado quando o
    estudo nao opina, mas `HF_HUB_OFFLINE=0` herdado da maquina reintroduziria a chamada de rede
    que o repositorio inteiro existe para nao ter.
    """
    config = _config_com_ambiente(monkeypatch, HF_HUB_OFFLINE="0")
    config.apply_hf_env()
    import os
    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"


def test_ips_offline_zero_desliga(monkeypatch):
    """`IPS_OFFLINE=0` e' a valvula declarada — usada para baixar o juiz, com aprovacao."""
    config = _config_com_ambiente(monkeypatch, IPS_OFFLINE="0")
    config.apply_hf_env()
    import os
    assert config.OFFLINE is False
    assert "HF_HUB_OFFLINE" not in os.environ
