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

    Gate de NAO-INFERIORIDADE: o LIMITE SUPERIOR do IC95 do drop fica sob a margem — nunca o
    ponto estimado. Um drop pontual de 1 p.p. com intervalo ate' 20 p.p. nao demonstra
    ausencia de dano; demonstra que o n nao foi suficiente para saber.

    NOME CORRIGIDO EM 2026-07-21. A chave devolvida se chamava `gate_equivalencia`, e o nome
    convidava ao uso errado. Este gate e' UNILATERAL: olha so' `hi <= margem`, isto e', so'
    responde "o braco `on` piorou?". Ele nao responde "os dois bracos sao equivalentes", e
    usa-lo para isso da' resultado invertido:

        on = 40/40, off = 10/40  ->  drop = -0,75, IC [-0,875, -0,625],  hi <= 0,05  ->  TRUE

    A divergencia MAXIMA possivel entre dois bracos seria reportada como equivalencia
    confirmada — e, pior, trocar a ordem dos argumentos inverte o veredito. Para afirmar
    COINCIDENCIA use `gate_coincidencia`, que e' bilateral e simetrico.

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
        # UNILATERAL, e o nome diz isso agora. Ver docstring: a chave antiga
        # (`gate_equivalencia`) foi removida de proposito, para que nenhum runner novo a
        # leia como resposta a uma pergunta bilateral.
        "gate_nao_inferioridade": bool(hi <= margem),
        "mcnemar_b_off_certo_on_errado": b, "mcnemar_c_off_errado_on_certo": c,
        "mcnemar_p": p_mcnemar,
    }


def gate_coincidencia(a_correct: list[bool], b_correct: list[bool], *,
                      margem: float = 0.10, n_boot: int = 10000, seed: int = 1234) -> dict:
    """COINCIDENCIA entre dois bracos: equivalencia BILATERAL (TOST), nos mesmos itens.

    Existe porque a metade `coincidem` da predicao pre-declarada — F1, F3 e F4 — e' uma
    afirmacao de AUSENCIA DE DIFERENCA, e ausencia de diferenca nao se demonstra com um teste
    unilateral nem com um p-valor alto. Aqui a regra e' explicita: **os DOIS limites do IC
    precisam caber dentro de [-margem, +margem]**.

    Duas propriedades que o gate unilateral nao tinha:

      SIMETRIA      trocar a ordem dos bracos nao muda o veredito. Coincidencia e' relacao
                    simetrica; um gate que depende de quem foi chamado primeiro nao esta'
                    medindo coincidencia.
      HONESTIDADE   n pequeno produz intervalo largo, intervalo largo estoura a margem, e o
                    veredito e' NAO-DEMONSTRADO — nao "coincidem". E' o oposto do
                    comportamento de um teste de diferenca, onde n pequeno *ajuda* a
                    conclusao de igualdade.

    A `margem` NAO tem default defensavel fora do pre-registro: ela e' a maior diferenca que
    o estudo aceita chamar de "mesma coisa", e sai selada. O valor aqui e' de conveniencia de
    teste, e o laudo devolve a margem para que ela seja impressa junto da palavra
    "coincidem", sempre.
    """
    a = np.array([bool(x) for x in a_correct], dtype=float)
    b = np.array([bool(x) for x in b_correct], dtype=float)
    if len(a) != len(b) or len(a) == 0:
        raise ValueError("os dois bracos precisam ser pareados e nao-vazios")
    d = a - b
    n = len(d)
    rng = np.random.default_rng(seed)
    boot = d[rng.integers(0, n, size=(n_boot, n))].mean(axis=1)
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    dentro = bool(lo >= -margem and hi <= margem)
    return {
        "n": n, "acc_a": float(a.mean()), "acc_b": float(b.mean()),
        "diferenca_a_menos_b": float(d.mean()),
        "ci95_bootstrap": [lo, hi],
        "margem": margem,
        "gate_coincidencia": dentro,
        # Quando o gate reprova, a leitura correta quase nunca e' "divergem": e' "nao
        # demonstramos coincidencia dentro desta margem". A distincao vai no laudo para nao
        # depender de quem escreve o texto depois.
        "veredito": ("COINCIDEM_DENTRO_DA_MARGEM" if dentro else
                     "DIVERGEM" if (lo > margem or hi < -margem) else
                     "NAO_DEMONSTRADO"),
    }


def inversao_categorica(off_acc: float, on_acc: float, *,
                        piso_off: float = 0.80, teto_on: float = 0.50) -> bool:
    """Categoria que ia bem sem o adapter e desaba com ele.

    Existe porque uma media global esconde colapso localizado: perder uma categoria
    inteira pode custar pouco na media e ser, ainda assim, o resultado mais importante
    do run.
    """
    return off_acc >= piso_off and on_acc <= teto_on


# --- F3: transicoes de ESTADO, e nao acertos ---------------------------------
# Acrescentado em 2026-07-21, depois de o endpoint anterior ser medido e reprovado.
#
# O PROBLEMA. F3 lia acerto por criterio E: escolher o texto consistente NAS DUAS ORDENS. O
# endpoint era McNemar sobre esses acertos, adapter contra base. Parece pareado e simetrico.
# Nao e'.
#
# Cada item, em cada braco, esta' em um de tres estados:
#
#     CONS   escolheu o mesmo TEXTO (o consistente) nas duas ordens   ('1','2')
#     VIOL   escolheu o mesmo TEXTO (o violador) nas duas ordens      ('2','1')
#     POS    escolheu o mesmo ROTULO nas duas ordens, ou nao escolheu ('1','1'), ('2','2'), None
#
# Num item em que a BASE esta' em POS, o criterio E ja' falha, logo `c` (o adapter perde um
# item que a base tinha) e' IMPOSSIVEL por construcao — so' `b` pode ocorrer. Medido no V0:
# 5 de 16 itens, 31%, estavam nesse estado.
#
# Consequencia: um adapter que apenas ficou mais DECIDIDO quanto ao formato — sem construto
# nenhum — converte esses itens, e ao acaso metade cai no lado consistente. Resultado b ~ R/2,
# c = 0, e McNemar acende. Mais itens PIORAM: a taxa de falso positivo cresce com n.
#
# A CORRECAO. Contar TRANSICOES DE DIRECAO, nao acertos:
#
#     PRO    = itens que o adapter levou A CONS e a base nao tinha em CONS
#     CONTRA = itens que o adapter levou A VIOL e a base nao tinha em VIOL
#
# Sob decisividade de formato pura, as conversoes de POS caem 50/50 entre CONS e VIOL: PRO ~
# CONTRA e o teste nao rejeita. Sob construto, PRO >> CONTRA. O teste passa a ser binomial
# exato de PRO contra PRO+CONTRA sob 1/2 — que e' exatamente a pergunta "a mudanca teve
# DIRECAO?", e nao "houve mudanca?".
#
# T2 (o McNemar de sempre) e' MANTIDO em conjuncao, porque T1 sozinho nao penaliza o adapter
# que PERDE itens que a base tinha (CONS -> POS). Custa pouco poder e fecha o flanco.


def estado_do_par(escolhas) -> str:
    """CONS / VIOL / POS a partir do par de rotulos emitidos nas duas ordens.

    `apresenta` poe a consistente como rotulo "1" na ordem 0 e como "2" na ordem 1. Logo
    ('1','2') e' o mesmo TEXTO escolhido duas vezes — o consistente — e ('2','1') e' o
    violador escolhido duas vezes. Os demais casos sao aderencia ao ROTULO, nao ao texto.
    """
    a, b = (escolhas[0], escolhas[1]) if len(escolhas) == 2 else (None, None)
    if a is None or b is None:
        return "POS"
    if (a, b) == ("1", "2"):
        return "CONS"
    if (a, b) == ("2", "1"):
        return "VIOL"
    return "POS"


def _sf_binom(k: int, n: int, p: float = 0.5) -> float:
    """P(K >= k) exata. Sem scipy, pelo mesmo motivo do resto do modulo."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def gate_transicoes(estados_adapter: list[str], estados_base: list[str], *,
                    alpha: float = 0.05) -> dict:
    """Gate de F3: a mudanca do adapter em relacao a' base teve DIRECAO consistente?

    Pareado por item. Devolve os dois testes e a conjuncao; nenhum deles sozinho e' o gate.
    """
    if len(estados_adapter) != len(estados_base) or not estados_adapter:
        raise ValueError("estados precisam ser pareados e nao-vazios")

    pro = contra = b = c = 0
    for sa, sb in zip(estados_adapter, estados_base):
        if sa == "CONS" and sb != "CONS":
            pro += 1
        if sa == "VIOL" and sb != "VIOL":
            contra += 1
        if sa == "CONS" and sb != "CONS":
            b += 1
        elif sa != "CONS" and sb == "CONS":
            c += 1

    p_t1 = _sf_binom(pro, pro + contra) if (pro + contra) else 1.0
    p_t2 = _sf_binom(b, b + c) if (b + c) else 1.0
    return {
        "n": len(estados_adapter),
        "pro": pro, "contra": contra, "b": b, "c": c,
        "p_direcao": p_t1, "p_mcnemar": p_t2,
        "alpha": alpha,
        "t1_direcao": bool(p_t1 <= alpha),
        "t2_nao_perdeu": bool(p_t2 <= alpha),
        "gate": bool(p_t1 <= alpha and p_t2 <= alpha),
    }
