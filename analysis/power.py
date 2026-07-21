"""Planejamento de n: poder EXATO, na mesma aritmetica com que os gates decidem.

Por que existe: o handoff manda dimensionar as baterias antes de escreve-las. Escrever 40
itens porque 40 e' um numero redondo, e descobrir depois que o gate nunca teve chance de
passar, e' gastar GPU para produzir um intervalo largo demais para decidir qualquer coisa.

REGRA DE COERENCIA: este modulo planeja com a MESMA funcao que depois decide. O gate de
`stats_gates.pooled_winrate_gate` e' "limite inferior do IC exato de Clopper-Pearson acima
do limiar"; entao o poder aqui e' calculado sobre exatamente esse evento, e nao sobre uma
aproximacao normal que daria outro numero. Planejar com uma distribuicao e decidir com
outra e' como calibrar a balanca com um peso e vender com outro.

ACHADO DE NIVEL, que muda o n: `pooled_winrate_gate` chama `clopper_pearson(k, n, alpha)`,
que reparte `alpha` nos DOIS lados. O gate olha so' o limite inferior — logo o teste e'
unilateral a `alpha/2`. Com `alpha=0.05` o nivel efetivo e' **0,025**, nao 0,05. O gate e'
mais conservador do que o nome sugere, e o n necessario e' maior. Fica registrado aqui em
vez de virar surpresa na analise.

Uso:
    python -m analysis.power              # tabela de planejamento
"""

from __future__ import annotations

import math
from functools import lru_cache

from harness.stats_gates import clopper_pearson

# --- Binomial exata (stdlib; sem scipy, sem numpy) ---------------------------


def pmf(k: int, n: int, p: float) -> float:
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    return math.comb(n, k) * p**k * (1.0 - p) ** (n - k)


def sf(k: int, n: int, p: float) -> float:
    """P(K >= k)."""
    return sum(pmf(i, n, p) for i in range(k, n + 1))


# --- Regiao de rejeicao do gate de win-rate ----------------------------------
@lru_cache(maxsize=4096)
def k_critico(n: int, limiar: float, alpha: float = 0.05) -> int | None:
    """Menor k cujo limite INFERIOR do IC exato ultrapassa `limiar`.

    O limite inferior de Clopper-Pearson cresce monotonicamente em k para n fixo, o que
    permite busca binaria: k* existe e e' unico. `None` quando nem k=n passa — caso em que
    aquele n nao pode fazer o gate passar nem com acerto perfeito, e o unico conserto e'
    mais itens.
    """
    if clopper_pearson(n, n, alpha)[0] <= limiar:
        return None
    lo, hi = 0, n
    while lo < hi:
        meio = (lo + hi) // 2
        if clopper_pearson(meio, n, alpha)[0] > limiar:
            hi = meio
        else:
            lo = meio + 1
    return lo


def poder(n: int, p: float, *, limiar: float, alpha: float = 0.05) -> float:
    """P(o gate passar | taxa verdadeira p). Exato, sem aproximacao."""
    kc = k_critico(n, limiar, alpha)
    return 0.0 if kc is None else sf(kc, n, p)


def n_minimo(p: float, *, limiar: float, alpha: float = 0.05,
             poder_alvo: float = 0.80, n_max: int = 600) -> int | None:
    """Menor n com poder >= alvo, contra a taxa verdadeira assumida `p`.

    Varre em vez de inverter formula porque o poder NAO e' monotono em n: k* salta de
    inteiro em inteiro, e um n maior pode ter poder ligeiramente menor que o anterior
    (efeito de serrilha das discretas). A varredura devolve o primeiro n que atinge o alvo;
    quem quiser margem deve escolher um n acima do primeiro cruzamento.
    """
    for n in range(2, n_max + 1):
        if poder(n, p, limiar=limiar, alpha=alpha) >= poder_alvo:
            return n
    return None


def erro_tipo_i(n: int, *, limiar: float, alpha: float = 0.05) -> float:
    """Taxa de falso positivo do gate quando a verdade esta' exatamente no limiar.

    Deve ficar em torno de alpha/2, e nunca acima — se subir, o gate esta' mais frouxo do
    que anuncia.
    """
    return poder(n, limiar, limiar=limiar, alpha=alpha)


# --- McNemar pareado (exato condicional) -------------------------------------
def _rejeita_mcnemar(d: int, alpha: float) -> set[int]:
    """Numeros de discordancias num sentido que rejeitam H0 (binomial(d, 1/2) bilateral)."""
    if d == 0:
        return set()
    fora = set()
    for b in range(d + 1):
        cauda = min(sum(pmf(i, d, 0.5) for i in range(b, d + 1)),
                    sum(pmf(i, d, 0.5) for i in range(0, b + 1)))
        if min(1.0, 2.0 * cauda) <= alpha:
            fora.add(b)
    return fora


def poder_mcnemar(n_pares: int, p01: float, p10: float, alpha: float = 0.05) -> float:
    """Poder exato do McNemar, condicionando no numero de pares DISCORDANTES.

    `p01` e `p10` sao as probabilidades de discordancia em cada sentido. O par concordante
    nao carrega informacao: e' por isso que o n que importa aqui e' o de discordantes, e por
    isso duas condicoes muito parecidas exigem MUITO mais itens do que a intuicao sugere.
    """
    pd = p01 + p10
    if pd <= 0:
        return 0.0
    vies = p10 / pd
    total = 0.0
    for d in range(0, n_pares + 1):
        pr_d = pmf(d, n_pares, pd)
        if pr_d < 1e-12:
            continue
        regiao = _rejeita_mcnemar(d, alpha)
        total += pr_d * sum(pmf(b, d, vies) for b in regiao)
    return total


# --- Desenho: itens agrupados em clusters de parafrase -----------------------
def n_efetivo(n_itens: int, por_cluster: int, icc: float) -> float:
    """n efetivo sob efeito de desenho: n / (1 + (m-1) * ICC).

    As parafrases de um mesmo item NAO sao replicas independentes — o modelo tende a
    responder as tres do mesmo jeito. Tratar 3 parafrases de 20 clusters como n=60 infla o
    n e estreita o IC artificialmente. Com ICC alto, 60 parafrases valem pouco mais que os
    20 clusters; com ICC=0, valem 60. A conta e' declarada aqui para que o pre-registro
    escolha o n de ITENS ja' sabendo quanto dele sobrevive.
    """
    if not 0.0 <= icc <= 1.0:
        raise ValueError("ICC fora de [0,1]")
    return n_itens / (1.0 + (por_cluster - 1) * icc)


# --- Orcamento de Holm -------------------------------------------------------
def alphas_holm(n_endpoints: int, alpha_familia: float = 0.05) -> list[float]:
    """Alphas de Holm por posicao (do menor p-valor ao maior): alpha/(m-i+1).

    O endpoint mais forte da familia e' testado ao alpha MAIS RIGOROSO, nao ao mais frouxo.
    Planejar o n com `alpha_familia` e testar sob Holm e' o erro que faz um estudo nascer
    subdimensionado: o poder cai justamente no endpoint principal.
    """
    return [alpha_familia / (n_endpoints - i) for i in range(n_endpoints)]


# --- Tabela de planejamento --------------------------------------------------
GRADE_P = (0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


def tabela(limiar: float, alpha: float, poder_alvo: float = 0.80) -> list[tuple]:
    return [(p, n_minimo(p, limiar=limiar, alpha=alpha, poder_alvo=poder_alvo))
            for p in GRADE_P]


def main() -> int:
    print(__doc__.splitlines()[0])
    print()
    print("Gate de win-rate: limite inferior do IC exato acima do limiar.")
    print("Lembrete de nivel: o IC e' bilateral, o gate olha um lado -> nivel = alpha/2.\n")

    for limiar, rotulo in ((0.50, "supera o acaso"), (0.70, "claim forte")):
        for alpha, quantos in ((0.05, 1), (0.05 / 4, 4)):
            print(f"limiar {limiar:.2f} ({rotulo}) | alpha={alpha:.4f} "
                  f"[{'sem correcao' if quantos == 1 else f'Holm, {quantos} endpoints, pior caso'}]"
                  f" | poder alvo 80%")
            for p, n in tabela(limiar, alpha):
                if n is None:
                    print(f"    p={p:.2f}  ->  n > 600 (inviavel)")
                else:
                    kc = k_critico(n, limiar, alpha)
                    print(f"    p={p:.2f}  ->  n={n:3d}  (precisa de k>={kc}, "
                          f"erro tipo I no limiar = {erro_tipo_i(n, limiar=limiar, alpha=alpha):.3f})")
            print()

    print("Efeito de desenho - 3 parafrases por cluster:")
    for icc in (0.0, 0.3, 0.5, 0.7, 0.9):
        print(f"    ICC={icc:.1f}  ->  60 parafrases valem n_efetivo={n_efetivo(60, 3, icc):5.1f}")
    print()
    print("McNemar pareado (2x2), alpha=0.05, poder alvo 80%:")
    for p01, p10 in ((0.05, 0.25), (0.10, 0.30), (0.10, 0.25), (0.15, 0.30)):
        for n in range(10, 401, 5):
            if poder_mcnemar(n, p01, p10, 0.05) >= 0.80:
                print(f"    discordancia {p01:.2f}/{p10:.2f}  ->  n={n} pares")
                break
        else:
            print(f"    discordancia {p01:.2f}/{p10:.2f}  ->  n > 400 pares")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
