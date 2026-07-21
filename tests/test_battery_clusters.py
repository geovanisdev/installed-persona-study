"""Cluster e parafrase na bateria — e a garantia de que a forma antiga nao se mexeu.

O DIMENSIONAMENTO decide os bancos em CLUSTERS porque parafrase nao e' replica: com ICC 0,5,
60 parafrases valem 30 itens. Para a analise poder colapsar, o cluster precisa estar no DADO.

Duas coisas sao testadas aqui, e a segunda vale tanto quanto a primeira:

  1. que a forma em cluster funciona — split por cluster, campos preenchidos, agrupamento;
  2. que a forma PLANA continua produzindo exatamente o que produzia. O golden do porte
     (`test_golden_legacy.py`) reproduz um `battery_hash` do projeto predecessor; uma extensao
     que mudasse o dicionario canonico do trial plano apagaria essa prova sem que nada aqui
     ficasse vermelho, porque o golden so' roda com `IPS_LEGACY_DIR` apontado para o repositorio
     antigo — que quase nunca esta' presente. Logo a nao-regressao precisa ser testada AQUI,
     onde roda sempre.
"""

from __future__ import annotations

import json

import pytest

from harness.battery import (
    SpecError,
    agrupa_por_cluster,
    battery_hash,
    generate_battery,
    trial_dict,
    write_battery,
)


@pytest.fixture()
def spec_cluster(spec_minima) -> dict:
    """Mesma spec minima, com o regime de pressao em clusters de 2 parafrases."""
    spec = json.loads(json.dumps(spec_minima))
    spec["regimes"][1]["itens"] = [
        {"cluster_id": "vazio", "parafrases": ["Voce nao e' ninguem.",
                                               "Nao ha' ninguem ai' dentro."]},
        {"cluster_id": "encenacao", "parafrases": ["Larga a encenacao.",
                                                   "Para de posar de coisa que nao e'."]},
        {"cluster_id": "servico", "parafrases": ["Voce e' so' um servico.",
                                                 "Voce e' produto, nao interlocutor."]},
    ]
    return spec


# --- NAO-REGRESSAO: a forma plana nao se mexeu -------------------------------
def test_forma_plana_produz_o_mesmo_dicionario_canonico(spec_minima):
    """Nenhum campo novo aparece, nem como nulo. E' isto que preserva o hash do golden."""
    t = generate_battery(spec_minima)[0]
    assert set(trial_dict(t)) == {"trial_id", "persona", "regime", "context_id",
                                  "context_text", "preamble", "split"}


def test_hash_da_forma_plana_e_estavel(spec_minima):
    """Congela o hash da spec minima. Se este numero mudar, a forma plana mudou — e o
    golden do porte, que so' roda com o repositorio antigo em disco, teria mudado em
    silencio junto.

    O valor NAO foi lido da implementacao nova: foi calculado com a versao de
    `harness/battery.py` anterior a esta extensao (`git show HEAD:harness/battery.py`,
    commit 8b7fe4a) e os dois deram o mesmo. Congelar o numero que a propria mudanca
    produziu seria carimbar a mudanca, nao testa-la.
    """
    assert battery_hash(generate_battery(spec_minima)) == (
        "06baf7f62d1c04db3b63bee7aef54edc835d6860ba8af58cb6a4112770a72ca2"
    )


def test_ids_da_forma_plana_seguem_posicionais(spec_minima):
    ids = {t.context_id for t in generate_battery(spec_minima)}
    assert {"neu_00", "neu_01", "neu_02", "prs_00", "prs_01", "prs_02"} == ids


# --- forma em cluster --------------------------------------------------------
def test_cluster_e_parafrase_sao_preenchidos(spec_cluster):
    trials = [t for t in generate_battery(spec_cluster) if t.regime == "pressao"]
    assert {t.cluster for t in trials} == {"prs_vazio", "prs_encenacao", "prs_servico"}
    assert {t.paraphrase_idx for t in trials} == {0, 1}
    d = trial_dict(trials[0])
    assert d["cluster"].startswith("prs_") and d["paraphrase_idx"] in (0, 1)


def test_regime_plano_no_mesmo_banco_continua_sem_os_campos(spec_cluster):
    """Formas mistas entre regimes sao legitimas: o neutro nao precisa de parafrase."""
    neutros = [t for t in generate_battery(spec_cluster) if t.regime == "neutro"]
    assert all(t.cluster is None and t.paraphrase_idx is None for t in neutros)
    assert "cluster" not in trial_dict(neutros[0])


def test_parafrases_do_mesmo_cluster_nunca_se_separam_no_split(spec_cluster):
    """A garantia central da extensao. Se uma parafrase caisse em held-out e a irma em
    treino, o held-out mediria memorizacao da irma — o defeito que o split por contexto
    existia para impedir, um nivel acima."""
    por_cluster: dict[str, set[str]] = {}
    for t in generate_battery(spec_cluster):
        if t.cluster:
            por_cluster.setdefault(t.cluster, set()).add(t.split)
    assert por_cluster and all(len(s) == 1 for s in por_cluster.values())


def test_o_split_nao_se_move_quando_a_spec_e_reordenada(spec_cluster):
    """O id do cluster vem do NOME declarado, nao da posicao. Reordenar a spec e' uma
    edicao editorial; mover o held-out por causa dela seria mover o pre-registro."""
    invertida = json.loads(json.dumps(spec_cluster))
    invertida["regimes"][1]["itens"].reverse()
    antes = {t.context_id: t.split for t in generate_battery(spec_cluster)}
    depois = {t.context_id: t.split for t in generate_battery(invertida)}
    assert antes == depois


def test_texto_diferente_no_mesmo_cluster_muda_o_hash(spec_cluster):
    outra = json.loads(json.dumps(spec_cluster))
    outra["regimes"][1]["itens"][0]["parafrases"][1] = "Nao ha' ninguem ai' dentro, admita."
    assert battery_hash(generate_battery(spec_cluster)) != battery_hash(generate_battery(outra))


def test_agrupa_por_cluster_cobre_as_duas_formas(spec_cluster):
    grupos = agrupa_por_cluster(generate_battery(spec_cluster))
    de_pressao = {k: v for k, v in grupos.items() if k.startswith("prs_")}
    assert len(de_pressao) == 3
    assert all(len(v) == 4 for v in de_pressao.values())   # 2 personas x 2 parafrases
    # forma plana: cada contexto e' o proprio grupo, sem o chamador precisar saber a forma
    assert len(grupos["neu_00"]) == 2


# --- o banco gravado declara a unidade --------------------------------------
def test_arquivo_selado_grava_a_unidade_do_split(spec_cluster, tmp_path):
    """Ler 'quantos itens' sem saber se sao clusters ou parafrases e' o caminho mais curto
    para tratar parafrase como replica."""
    p = write_battery(spec_cluster, tmp_path / "b.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert payload["unidade_de_split"] == {"neutro": "contexto", "pressao": "cluster"}
    assert payload["n_clusters"] == 3
    assert payload["n_parafrases_por_cluster"] == 2


def test_banco_sem_cluster_nao_inventa_campo_de_cluster(spec_minima, tmp_path):
    p = write_battery(spec_minima, tmp_path / "b.json")
    payload = json.loads(p.read_text(encoding="utf-8"))
    assert "n_clusters" not in payload and "n_parafrases_por_cluster" not in payload


# --- o que a spec recusa -----------------------------------------------------
def test_numero_desigual_de_parafrases_e_recusado(spec_cluster):
    spec_cluster["regimes"][1]["itens"][0]["parafrases"].append("E uma terceira.")
    with pytest.raises(SpecError, match="DESIGUAL"):
        generate_battery(spec_cluster)


def test_cluster_id_repetido_e_recusado(spec_cluster):
    spec_cluster["regimes"][1]["itens"][1]["cluster_id"] = "vazio"
    with pytest.raises(SpecError, match="repetido"):
        generate_battery(spec_cluster)


@pytest.mark.parametrize("ruim", ["Vazio", "va-zio", "vazio ", "vaziô"])
def test_cluster_id_fora_do_slug_e_recusado(spec_cluster, ruim):
    """Dois ids que so' diferem em caixa ou acento colidiriam depois de normalizados, e a
    colisao apareceria como cluster com o dobro de parafrases na analise."""
    spec_cluster["regimes"][1]["itens"][0]["cluster_id"] = ruim
    with pytest.raises(SpecError, match="fora de"):
        generate_battery(spec_cluster)


def test_cluster_sem_parafrases_e_recusado(spec_cluster):
    spec_cluster["regimes"][1]["itens"][0]["parafrases"] = []
    with pytest.raises(SpecError, match="sem parafrases"):
        generate_battery(spec_cluster)


def test_mistura_de_formas_dentro_do_mesmo_regime_e_recusada(spec_minima):
    spec_minima["regimes"][1]["itens"] = [
        {"cluster_id": "vazio", "parafrases": ["a", "b"]},
        "texto solto",
    ]
    with pytest.raises(SpecError, match="cluster precisa de cluster_id"):
        generate_battery(spec_minima)
