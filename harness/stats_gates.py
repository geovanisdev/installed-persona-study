"""Matematica dos gates: IC binomial exato, win-rate agrupado e delta pareado.

PROVENIENCIA: adaptado de `pipeline/eval_mech/identity/stats_gates.py` do projeto
predecessor. As funcoes sao preservadas; os LIMIARES, que la' estavam escritos dentro do
corpo das funcoes, viraram argumentos — porque neste estudo eles nascem do pre-registro
(`thresholds.yaml` selado no S3) e nao podem ser um default escondido no codigo.

LIVRE DE TORCH de proposito: os runners importam este modulo no topo, entao o caminho de
verificacao roda sem carregar modelo nenhum. Depende de stdlib + numpy.

Nota de leitura: toda funcao aqui devolve o INTERVALO, nao so' o ponto. Os gates deste
estudo sao definidos sobre limites de intervalo — um ponto estimado que cruza um limiar
enquanto seu intervalo o abraca dos dois lados nao decidiu coisa alguma.
"""

from __future__ import annotations

import math

import numpy as np


# --- Clopper-Pearson ---------------------------------------------------------
def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """IC binomial EXATO via distribuicao Beta (quantil por bisecao, sem dependencia).

    Exato no sentido de Clopper-Pearson: cobertura garantida >= 1-alpha, conservador.
    Preferido a' aproximacao normal porque os n deste estudo sao pequenos e as taxas
    ficam perto de 0 ou 1, exatamente onde a aproximacao normal mente.
    """
    def beta_ppf(q, a, b):
        def betainc(a, b, x):
            if x <= 0:
                return 0.0
            if x >= 1:
                return 1.0
            if x > (a + 1) / (a + b + 2):
                return 1.0 - betainc(b, a, 1.0 - x)
            lbeta = (math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b))
            front = math.exp(a * math.log(x) + b * math.log(1 - x) - lbeta) / a
            f, c, d = 1.0, 1.0, 0.0
            for i in range(200):
                m = i // 2
                if i == 0:
                    num = 1.0
                elif i % 2 == 0:
                    num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
                else:
                    num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
                d = 1.0 + num * d
                d = 1.0 / (d if abs(d) > 1e-30 else 1e-30)
                c = 1.0 + num / (c if abs(c) > 1e-30 else 1e-30)
                f *= c * d
                if abs(1.0 - c * d) < 1e-10:
                    break
            return front * (f - 1.0)
        lo, hi = 0.0, 1.0
        for _ in range(80):
            mid = (lo + hi) / 2
            if betainc(a, b, mid) < q:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    lo = 0.0 if k == 0 else beta_ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta_ppf(1 - alpha / 2, k + 1, n - k)
    return lo, hi


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    return clopper_pearson(k, n, alpha)[1]


def majority_vote(votes) -> bool:
    """Voto majoritario de k amostras booleanas de UM item.

    Empate resolve para False (conservador). Colapsar as k amostras de decodificacao de
    um item em UM booleano e' o que impede que reamostrar a decodificacao infle o n: o
    n do endpoint e' o numero de ITENS, nao de geracoes.
    """
    votes = list(votes)
    return sum(bool(v) for v in votes) * 2 > len(votes)


# --- Endpoint de taxa de acerto agrupada -------------------------------------
def pooled_winrate_gate(item_pass: list[bool], *, nulo: float = 0.5,
                        piso_forte: float = 0.70, alpha: float = 0.05) -> dict:
    """Win-rate agrupado + IC95 exato, com os dois gates SEPARADOS.

    `item_pass` = um booleano por ITEM (ja' colapsado por voto majoritario).

      gate_supera_nulo — limite INFERIOR do IC acima de `nulo`. Responde "e' distinguivel
                         do acaso?", que e' uma pergunta mais fraca do que costuma parecer.
      claim_forte      — limite inferior acima de `piso_forte`. E' o unico dos dois que
                         autoriza uma afirmacao de magnitude.

    Os limiares sao argumentos porque vem do pre-registro. Um limiar que se ajusta depois
    de ver o resultado nao e' um limiar.
    """
    n = len(item_pass)
    k = sum(bool(x) for x in item_pass)
    lo, hi = clopper_pearson(k, n, alpha) if n else (0.0, 1.0)
    return {
        "n": n, "k": k, "winrate": (k / n) if n else 0.0, "ci95": [lo, hi],
        "nulo": nulo, "piso_forte": piso_forte,
        "gate_supera_nulo": bool(lo > nulo),
        "claim_forte": bool(lo >= piso_forte),
    }


# --- Delta pareado + bootstrap + McNemar -------------------------------------
def paired_delta_gate(on_correct: list[bool], off_correct: list[bool], *,
                      n_boot: int = 10000, seed: int = 1234,
                      margem: float = 0.05) -> dict:
    """Regressao PAREADA nos MESMOS itens: d_i = off_i - on_i (>0 = o adapter piorou).

    Gate de equivalencia: o LIMITE SUPERIOR do IC95 do drop fica sob a margem — nunca o
    ponto estimado. Um drop pontual de 1 p.p. com intervalo ate' 20 p.p. nao demonstra
    ausencia de dano; demonstra que o n nao foi suficiente para saber.

    Reporta tambem McNemar exato sobre os discordantes, que e' o teste apropriado para
    pares binarios e nao supoe normalidade.
    """
    on = np.array([bool(x) for x in on_correct], dtype=float)
    off = np.array([bool(x) for x in off_correct], dtype=float)
    if len(on) != len(off) or len(on) == 0:
        raise ValueError("on/off precisam ser pareados e nao-vazios")
    d = off - on
    n = len(d)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = d[idx].mean(axis=1)
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    b = int(np.sum((off == 1) & (on == 0)))   # off certo, on errado (o adapter perdeu)
    c = int(np.sum((off == 0) & (on == 1)))   # off errado, on certo (o adapter ganhou)
    nd = b + c
    if nd == 0:
        p_mcnemar = 1.0
    else:
        p_mcnemar = float(min(1.0, 2 * sum(math.comb(nd, i) for i in range(min(b, c) + 1)) / 2 ** nd))
    return {
        "n": n, "acc_on": float(on.mean()), "acc_off": float(off.mean()),
        "drop_off_menos_on": float(d.mean()),
        "drop_ci95_bootstrap": [lo, hi],
        "margem": margem,
        "gate_equivalencia": bool(hi <= margem),
        "mcnemar_b_off_certo_on_errado": b, "mcnemar_c_off_errado_on_certo": c,
        "mcnemar_p": p_mcnemar,
    }


def inversao_categorica(off_acc: float, on_acc: float, *,
                        piso_off: float = 0.80, teto_on: float = 0.50) -> bool:
    """Categoria que ia bem sem o adapter e desaba com ele.

    Existe porque uma media global esconde colapso localizado: perder uma categoria
    inteira pode custar pouco na media e ser, ainda assim, o resultado mais importante
    do run.
    """
    return off_acc >= piso_off and on_acc <= teto_on
