"""Conversa por ETAPA: o texto integral do que cada modelo disse, com o indicador da celula.

POR QUE ESTE MODULO EXISTE
--------------------------
`transcript_io` ja' preserva o RAW de uma RUN — arquivo vivo, copia duravel, indice
append-only — e responde a pergunta "o que a run T1 produziu". Ele NAO responde a pergunta
que o artefato pedido faz: "o que foi dito, em qual ETAPA, por qual braco, sob qual item".
O registro de la' e' por experimento e nao carrega o indicador de CELULA do desenho
cruzado (adapter x banco x polo x direcao x parafrase). Sem esse indicador o texto vira
anedota: bonito de ler, impossivel de atribuir a uma celula do desenho.

Esta camada e' construida POR CIMA daquela: reusa `run_metadata()` (selo de proveniencia:
commit, arvore suja, hash do nucleo) e a mesma disciplina de append-only. Nao substitui
nem altera `transcript_io`.

DEFEITOS QUE ESTE MODULO IMPEDE
-------------------------------
1. RESPOSTA CORTADA REGISTRADA COMO SE FOSSE COMPLETA. Medido neste programa: um teto de
   geracao uniforme NAO trata os bracos igualmente — uma persona escreveu 3,2x mais que a
   outra e, sob teto 90, truncou 23/24 contra 12/24. Uma resposta cortada guardada sem
   marca destroi a comparacao entre bracos e nao ha' como descobrir depois. Por isso
   `truncada` e' campo obrigatorio e booleano; quando o chamador nao sabe, e' None e o
   modulo AVISA nomeando o registro.
2. CAMPO COM NOME ERRADO VIRANDO SILENCIO. `cluster` em vez de `cluster_id` seria aceito
   por um dict e sumiria do artefato sem uma linha de erro. Aqui campo desconhecido
   LEVANTA, com sugestao do nome proximo.
3. PERDA DO ARQUIVO INTEIRO POR UMA QUEDA NO MEIO DA ESCRITA. Um JSON unico gravado no
   fim do run perde tudo se o processo morrer; um JSONL com flush por linha perde no
   maximo a ultima linha — e essa linha e' CONTADA na leitura, nao varrida para baixo do
   tapete.

O que este modulo NAO faz: nao trunca texto nunca (o pedido do Arquiteto e' "as respostas
completas"; qualquer corte na escrita e' defeito), nao pontua, nao julga e nao monta o
HTML. O HTML multi-abas por etapa e' construido a jusante, lendo `le_etapa`/`etapas`; o
`sha256_resposta` existe para que aquele HTML possa PROVAR que o texto exibido e' o texto
gravado.

Layout:
  runs/conversas/<etapa>.jsonl   um arquivo por etapa, APPEND-ONLY, uma conversa por linha
"""

from __future__ import annotations

import contextlib
import difflib
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, NamedTuple

from harness import config
from harness.transcript_io import run_metadata

SCHEMA = "conversa/1"

# Quem fala. "autor" e' o agente que CONSTROI o estudo (as conversas de trabalho), e nao
# um braco experimental — separa-lo dos demais impede que trabalho de bancada seja lido
# como dado do desenho.
PAPEIS = ("gerador", "juiz", "autor", "base_nua")

# Ordem canonica das chaves de um registro. E' a ordem em que elas saem no JSONL, para que
# o arquivo bruto seja legivel por humano sem ferramenta.
CAMPOS: tuple[str, ...] = (
    "schema", "id", "etapa", "ordem", "ts", "papel",
    # sujeito: qual modelo, em qual revisao, com qual adapter e persona, sob qual scrub
    "modelo", "revisao", "adapter", "persona", "scrub",
    "semente_treino", "semente_decodificacao",
    # celula do desenho cruzado: de qual banco veio o item e qual item exatamente
    "banco", "battery_hash", "cluster_id", "parafrase_idx", "item_id",
    "invariante", "polo", "direcao",
    # a conversa em si
    "preambulo", "prompt_completo", "resposta_completa", "parametros_decodificacao",
    "n_tokens_prompt", "n_tokens_resposta", "truncada", "sha256_resposta",
    # `turnos` guarda a TROCA INTEIRA quando ela existe — texto, raciocinio, chamada de
    # ferramenta e resultado, em ordem. Fica separado de `resposta_completa` de proposito:
    # aquele campo e' o que o modelo DISSE, e misturar chamada de ferramenta nele inflaria
    # qualquer contagem feita sobre o texto. Mas jogar a troca fora tambem nao serve: numa
    # sessao de autoria, 5 falas de uma linha e 31 chamadas de ferramenta sao a mesma
    # sessao, e um artefato que mostre so' as 5 nao mostra o trabalho. Vale None nas
    # geracoes do experimento, que nao tem ferramenta nenhuma.
    "turnos",
    # proveniencia do codigo (vem do selo de run)
    "core_hash", "git_commit", "git_dirty",
)

# Campos que o Registrador calcula. Aceita-los do chamador criaria duas fontes de verdade
# para a mesma coisa — e a que perdesse seria descoberta so' no artefato final.
CAMPOS_DO_REGISTRADOR = ("schema", "etapa", "ordem", "sha256_resposta")
CAMPOS_ACEITOS = tuple(c for c in CAMPOS if c not in CAMPOS_DO_REGISTRADOR)
# `truncada` entrou aqui em 2026-07-22, depois de uma auditoria apontar que o docstring do
# modulo o chamava de OBRIGATORIO e o codigo so' imprimia um aviso quando ele faltava. Sob 110
# itens por invariante, um aviso no console e' indistinguivel de nao existir.
#
# Obrigatorio quer dizer que o chamador precisa DIZER — nao que ele precise saber. `None` e'
# valor legitimo e significa "nao sei se cortou"; o que deixou de ser aceito e' a OMISSAO, que
# e' silencio disfarcado de ausencia de problema.
CAMPOS_OBRIGATORIOS = ("papel", "resposta_completa", "truncada")

# Nome de etapa vira NOME DE ARQUIVO. Sem esta trava, `etapa="../../qualquer"` escreveria
# fora de runs/conversas.
_ETAPA_OK = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")

# Avisar duas mil vezes e' a mesma coisa que nao avisar: o console vira ruido e ninguem le'.
# Os primeiros avisos nomeiam o registro concreto; o resto vira um total no fechamento.
MAX_AVISOS_TRUNCADA = 3


class ConversaError(ValueError):
    """Violacao do contrato do log de conversa (campo, papel ou tipo)."""


# --- utilitarios ------------------------------------------------------------

def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sha256_texto(texto: str) -> str:
    """SHA-256 do texto EXATO, em utf-8. E' a prova de integridade que o HTML exibe."""
    return hashlib.sha256((texto or "").encode("utf-8")).hexdigest()


def dir_conversas(runs_dir: Path | str | None = None) -> Path:
    return Path(runs_dir or config.RUNS_DIR) / "conversas"


def caminho_da_etapa(etapa: str, *, runs_dir: Path | str | None = None) -> Path:
    if not isinstance(etapa, str) or not _ETAPA_OK.fullmatch(etapa):
        raise ConversaError(
            f"etapa {etapa!r} nao serve como nome de arquivo: use [A-Za-z0-9_.-], comecando "
            "por letra ou digito (a etapa vira runs/conversas/<etapa>.jsonl)"
        )
    d = dir_conversas(runs_dir)
    # COLISAO POR CAIXA. O estudo roda em Windows, onde o sistema de arquivos e'
    # case-insensitive: `V1_teto` e `v1_teto` sao duas etapas para o codigo e UM arquivo para o
    # disco, e a segunda anexaria em cima da primeira sem uma palavra. Apontado por auditoria
    # em 2026-07-22. Abortar e' o comportamento correto: as duas etapas existem no desenho de
    # quem escreveu, e fundi-las perde a separacao que o campo `etapa` existe para manter.
    if d.is_dir():
        for existente in d.glob("*.jsonl"):
            nome = existente.stem
            if nome != etapa and nome.casefold() == etapa.casefold():
                raise ConversaError(
                    f"etapa {etapa!r} colide por CAIXA com {nome!r}, que ja' existe em {d}. "
                    "Neste sistema de arquivos as duas viram o mesmo arquivo e uma anexaria "
                    "sobre a outra em silencio. Escolha um nome distinto de verdade."
                )
    return d / f"{etapa}.jsonl"


class Leitura(list):
    """Lista dos registros lidos que TAMBEM sabe dizer quantas linhas nao foram lidas.

    E' `list[dict]` de verdade (indexa, itera e compara como lista), com `.invalidas` e
    `.linhas_invalidas` ao lado. Devolver so' a lista esconderia a perda; devolver so' a
    contagem obrigaria todo chamador a desempacotar uma tupla para o caso comum.
    """

    def __init__(self, registros: list[dict] | None = None,
                 linhas_invalidas: tuple[int, ...] = ()) -> None:
        super().__init__(registros or [])
        self.linhas_invalidas = tuple(linhas_invalidas)

    @property
    def invalidas(self) -> int:
        return len(self.linhas_invalidas)

    @property
    def registros(self) -> list[dict]:
        return list(self)


# --- validacao --------------------------------------------------------------

def _valida(campos: dict, *, etapa: str, ordem: int) -> None:
    onde = f"etapa {etapa!r} ordem {ordem}"
    for nome in campos:
        if nome in CAMPOS_DO_REGISTRADOR:
            raise ConversaError(
                f"{onde}: o campo {nome!r} e' calculado pelo Registrador e nao pode vir do "
                "chamador — duas fontes para o mesmo campo e' como um registro fica mentindo"
            )
        if nome not in CAMPOS_ACEITOS:
            proximos = difflib.get_close_matches(nome, CAMPOS_ACEITOS, n=3, cutoff=0.6)
            dica = (" — voce quis dizer " + " ou ".join(repr(p) for p in proximos) + "?"
                    if proximos else "")
            raise ConversaError(
                f"{onde}: campo desconhecido {nome!r}{dica}. Campo com nome errado seria "
                "aceito em silencio e sumiria do artefato; por isso ele levanta aqui. "
                f"Campos validos: {', '.join(CAMPOS_ACEITOS)}"
            )
    faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in campos]
    if faltando:
        raise ConversaError(f"{onde}: faltam campos obrigatorios: {', '.join(faltando)}")

    papel = campos.get("papel")
    if papel not in PAPEIS:
        raise ConversaError(
            f"{onde}: papel {papel!r} nao existe — use um de {', '.join(PAPEIS)}"
        )
    resposta = campos.get("resposta_completa")
    if not isinstance(resposta, str):
        raise ConversaError(
            f"{onde}: resposta_completa precisa ser str (recebi {type(resposta).__name__}). "
            "Resposta vazia e' um dado legitimo e se escreve como \"\"; None nao diz se o "
            "modelo calou ou se o chamador esqueceu"
        )
    truncada = campos.get("truncada", None)
    if truncada is not None and not isinstance(truncada, bool):
        raise ConversaError(
            f"{onde}: truncada={truncada!r} nao e' booleano nem None. Este campo e' a defesa "
            "contra comparar um braco cortado com um braco inteiro; 0/1/\"nao\" nao servem"
        )


# --- escrita ----------------------------------------------------------------

class Registrador:
    """Escritor de UMA etapa. Numera `ordem`, sela cada resposta e da' flush por linha."""

    def __init__(self, etapa: str, caminho: Path, arquivo, run_meta: dict,
                 proxima_ordem: int) -> None:
        self.etapa = etapa
        self.caminho = caminho
        self.run_meta = dict(run_meta or {})
        self._arquivo = arquivo
        self._proxima_ordem = proxima_ordem
        self.n = 0
        self.sem_truncada = 0

    @property
    def proxima_ordem(self) -> int:
        return self._proxima_ordem

    def registra(self, **campos: Any) -> dict:
        """Grava UMA conversa e devolve o registro exatamente como ele foi gravado."""
        ordem = self._proxima_ordem
        _valida(campos, etapa=self.etapa, ordem=ordem)

        reg: dict[str, Any] = {c: None for c in CAMPOS}
        reg.update(campos)
        reg["schema"] = SCHEMA
        reg["etapa"] = self.etapa
        reg["ordem"] = ordem
        reg["ts"] = campos.get("ts") or _agora()
        reg["id"] = campos.get("id") or f"{self.etapa}-{ordem:05d}"
        for herdado in ("modelo", "core_hash", "git_commit", "git_dirty"):
            if reg.get(herdado) is None:
                reg[herdado] = self.run_meta.get(herdado)
        # Selo do texto EXATO que vai para o disco, calculado depois de tudo o mais: o HTML
        # confere este hash contra o texto que exibe.
        reg["sha256_resposta"] = sha256_texto(reg["resposta_completa"])

        # ensure_ascii=False para que o arquivo bruto seja legivel em portugues acentuado.
        self._arquivo.write(json.dumps(reg, ensure_ascii=False) + "\n")
        self._arquivo.flush()
        try:
            os.fsync(self._arquivo.fileno())
        except Exception:  # noqa: BLE001 — fsync indisponivel nao pode derrubar o run
            pass

        self._proxima_ordem = ordem + 1
        self.n += 1
        if reg["truncada"] is None:
            self._avisa_truncada(reg)
        return dict(reg)

    def _avisa_truncada(self, reg: dict) -> None:
        self.sem_truncada += 1
        if self.sem_truncada <= MAX_AVISOS_TRUNCADA:
            print(
                f"[conversa] AVISO: etapa {self.etapa!r} ordem {reg['ordem']} "
                f"(id={reg['id']!r}, item_id={reg['item_id']!r}, persona={reg['persona']!r}, "
                f"adapter={reg['adapter']!r}): truncada=None - sem esse campo nao ha' como "
                "saber se a resposta foi cortada pelo teto, e a comparacao entre bracos fica "
                "sem defesa (medido: 23/24 contra 12/24 sob o mesmo teto)"
            )

    def _resumo(self) -> None:
        print(f"[conversa] etapa {self.etapa!r}: +{self.n} registro(s) -> {self.caminho}")
        if self.sem_truncada:
            print(
                f"[conversa] AVISO: etapa {self.etapa!r}: {self.sem_truncada} de {self.n} "
                "registro(s) foram gravados com truncada=None"
            )


def _fecha_linha_parcial(caminho: Path, etapa: str) -> None:
    """Se o arquivo terminou no meio de uma linha, fecha a linha ANTES de anexar.

    Uma queda no meio de uma escrita deixa a ultima linha pela metade e sem `\\n`. Anexar
    logo em seguida colaria o registro novo no rabo do quebrado e destruiria DOIS registros
    em vez de um. Fechar a linha e' um append de um byte: nada existente e' reescrito, e a
    linha quebrada continua no arquivo para ser contada na leitura.
    """
    if not caminho.exists() or caminho.stat().st_size == 0:
        return
    with caminho.open("rb") as f:
        f.seek(-1, os.SEEK_END)
        if f.read(1) == b"\n":
            return
    with caminho.open("ab") as f:
        f.write(b"\n")
    print(f"[conversa] AVISO: etapa {etapa!r}: a ultima linha estava incompleta (queda no "
          "meio da escrita?); ela foi FECHADA para nao contaminar o proximo registro e "
          "sera' contada como invalida na leitura")


@contextlib.contextmanager
def abre_etapa(etapa: str, *, run_meta: dict | None = None,
               runs_dir: Path | str | None = None) -> Iterator[Registrador]:
    """Abre a etapa para escrita APPEND-ONLY e devolve o `Registrador`.

    `ordem` continua de onde o arquivo parou: o jsonl existente e' relido na abertura. Nada
    e' reescrito e nada e' apagado — reabrir uma etapa acrescenta, nunca substitui.
    """
    caminho = caminho_da_etapa(etapa, runs_dir=runs_dir)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    anterior = le_etapa(etapa, runs_dir=runs_dir, silencioso=True)
    if anterior.invalidas:
        print(f"[conversa] AVISO: etapa {etapa!r} ja' tinha {anterior.invalidas} linha(s) "
              f"invalida(s) (linhas {list(anterior.linhas_invalidas)}); elas permanecem no "
              "arquivo: este log e' append-only e nao reescreve historia")
    proxima = max((r.get("ordem", -1) for r in anterior
                   if isinstance(r.get("ordem"), int)), default=-1) + 1
    _fecha_linha_parcial(caminho, etapa)

    rm = run_meta if run_meta is not None else run_metadata()
    arquivo = caminho.open("a", encoding="utf-8", newline="\n")
    registrador = Registrador(etapa, caminho, arquivo, rm, proxima)
    try:
        yield registrador
    finally:
        try:
            arquivo.close()
        finally:
            registrador._resumo()


# --- leitura ----------------------------------------------------------------

def le_etapa(etapa: str, *, runs_dir: Path | str | None = None,
             silencioso: bool = False) -> Leitura:
    """Le uma etapa inteira. Linha invalida e' CONTADA e reportada, nunca varrida.

    Le bytes e decodifica linha a linha de proposito: um unico byte corrompido nao pode
    impedir a leitura das outras milhares de conversas.
    """
    caminho = caminho_da_etapa(etapa, runs_dir=runs_dir)
    registros: list[dict] = []
    invalidas: list[int] = []
    adulteradas: list[int] = []
    total_linhas = 0
    if caminho.exists():
        bruto = caminho.read_bytes()
        pedacos = bruto.split(b"\n")
        total_linhas = len(pedacos)
        for numero, linha_bruta in enumerate(pedacos, start=1):
            linha = linha_bruta.decode("utf-8", errors="replace").strip()
            if not linha:
                continue
            try:
                obj = json.loads(linha)
            except Exception:  # noqa: BLE001 — linha truncada/corrompida
                invalidas.append(numero)
                continue
            if not isinstance(obj, dict):
                invalidas.append(numero)
                continue
            # SELO CONFERIDO NA LEITURA. Ate' 2026-07-22 `sha256_resposta` era calculado na
            # escrita e NUNCA verificado por nada — auditoria trocou um byte dentro de uma
            # linha JSON valida e `le_etapa` devolveu o texto adulterado com invalidas=0.
            # Um selo que ninguem confere nao e' selo, e' decoracao.
            selo = obj.get("sha256_resposta")
            if isinstance(selo, str) and selo:
                if sha256_texto(obj.get("resposta_completa") or "") != selo:
                    adulteradas.append(numero)
            registros.append(obj)

    leitura = Leitura(registros, tuple(invalidas))
    leitura.linhas_adulteradas = tuple(adulteradas)
    if adulteradas and not silencioso:
        print(
            f"[conversa] ALERTA: etapa {etapa!r}: {len(adulteradas)} registro(s) com "
            f"sha256_resposta que NAO bate com o texto, nas linhas {adulteradas} de "
            f"{caminho}. Isto nao e' queda de escrita: e' texto alterado depois de gravado."
        )
    if invalidas and not silencioso:
        # `total_linhas` conta o pedaco vazio depois do ultimo "\n"; por isso o limite e' -1.
        so_no_fim = all(n >= total_linhas - 1 for n in invalidas)
        print(
            f"[conversa] AVISO: etapa {etapa!r}: {len(invalidas)} linha(s) invalida(s) nas "
            f"linhas {invalidas} de {caminho}"
            + (" - no fim do arquivo, compativel com queda no meio da escrita"
               if so_no_fim else
               " - NO MEIO do arquivo, o que nao e' queda de escrita e sim corrupcao")
        )
    return leitura


def etapas(*, runs_dir: Path | str | None = None) -> list[str]:
    """Etapas que existem em disco, em ordem alfabetica."""
    d = dir_conversas(runs_dir)
    if not d.exists():
        return []
    return sorted(p.stem for p in d.glob("*.jsonl") if p.is_file())


# --- importacao de transcricao de agente ------------------------------------

class Importacao(NamedTuple):
    """Resultado de uma importacao: quantas conversas entraram e quantas linhas nao."""
    gravados: int
    ignoradas: int


def _texto_de_conteudo(conteudo: Any) -> str:
    """Texto de um `content` de mensagem. So' blocos de texto — nunca tool_use/tool_result.

    Chamada de ferramenta e resultado de ferramenta nao sao o que o modelo DISSE; entrariam
    no artefato como se fossem resposta e inflariam qualquer leitura do texto.
    """
    if isinstance(conteudo, str):
        return conteudo
    if isinstance(conteudo, dict):
        texto = conteudo.get("text")
        return texto if isinstance(texto, str) else ""
    if isinstance(conteudo, list):
        partes: list[str] = []
        for bloco in conteudo:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict):
                tipo = bloco.get("type")
                texto = bloco.get("text")
                if tipo in (None, "text") and isinstance(texto, str):
                    partes.append(texto)
        return "\n".join(p for p in partes if p)
    return ""


_MAX_TURNO = 20000   # um resultado de ferramenta pode ter megabytes; o artefato nao precisa


def _turnos_de_conteudo(papel: str, conteudo: Any) -> list[dict]:
    """A troca inteira, em ordem, sem julgar o que e' importante.

    Ao contrario de `_texto_de_conteudo`, aqui NADA e' descartado por tipo. O corte e' de
    TAMANHO, e ele e' declarado no proprio turno (`truncado_em`) — um corte silencioso num
    artefato que se chama "respostas completas" seria exatamente a fraude que o campo
    `truncada` existe para impedir do outro lado.
    """
    if isinstance(conteudo, str):
        conteudo = [{"type": "text", "text": conteudo}]
    if not isinstance(conteudo, list):
        return []
    saida: list[dict] = []
    for bloco in conteudo:
        if isinstance(bloco, str):
            bloco = {"type": "text", "text": bloco}
        if not isinstance(bloco, dict):
            continue
        tipo = bloco.get("type") or "text"
        nome = bloco.get("name")
        if tipo == "text":
            texto = bloco.get("text") or ""
        elif tipo == "thinking":
            texto = bloco.get("thinking") or ""
        elif tipo == "tool_use":
            texto = json.dumps(bloco.get("input"), ensure_ascii=False, indent=1)
        elif tipo == "tool_result":
            # O `[:_MAX_TURNO]` estava AQUI, antes do teste de tamanho la' embaixo. Com isso o
            # texto chegava ao teste com exatamente _MAX_TURNO caracteres, `>` dava falso, e as
            # marcas `truncado_em`/`tamanho_original` NUNCA eram emitidas neste ramo — corte
            # silencioso num artefato chamado "respostas completas". Achado por auditoria em
            # 2026-07-22; o corte agora acontece num lugar so', e ele se declara.
            texto = _texto_de_conteudo(bloco.get("content")) or json.dumps(
                bloco.get("content"), ensure_ascii=False)
        else:
            texto = json.dumps(bloco, ensure_ascii=False)
        if not isinstance(texto, str) or not texto.strip():
            continue
        turno = {"papel": papel, "tipo": tipo, "nome": nome, "texto": texto[:_MAX_TURNO]}
        if len(texto) > _MAX_TURNO:
            turno["truncado_em"] = _MAX_TURNO
            turno["tamanho_original"] = len(texto)
        saida.append(turno)
    return saida


def _mensagem_da_linha(obj: Any) -> tuple[str, str, str | None, list[dict]] | None:
    """(papel_bruto, texto, ts, turnos) de uma linha, ou None se a linha nao for mensagem."""
    if not isinstance(obj, dict):
        return None
    msg = obj.get("message")
    if not isinstance(msg, dict):
        msg = obj if ("role" in obj and "content" in obj) else None
    if not isinstance(msg, dict):
        return None
    papel = msg.get("role") or obj.get("type")
    if papel not in ("user", "assistant"):
        return None
    ts = obj.get("timestamp") or msg.get("timestamp")
    conteudo = msg.get("content")
    return (papel, _texto_de_conteudo(conteudo), ts if isinstance(ts, str) else None,
            _turnos_de_conteudo(papel, conteudo))


def importa_transcricao_de_agente(caminho_jsonl: Path | str, etapa: str, *,
                                  runs_dir: Path | str | None = None,
                                  run_meta: dict | None = None,
                                  **indicadores: Any) -> Importacao:
    """Converte a transcricao de um agente do Claude Code em conversas com papel="autor".

    O FORMATO DA TRANSCRICAO NAO E' CONTRATUAL. Ele e' de outra ferramenta, muda entre
    versoes e nao e' versionado por este estudo. Por isso a leitura aqui e' defensiva por
    principio: nenhuma linha inesperada estoura, cada linha que nao virou conversa e'
    CONTADA e o total volta em `Importacao.ignoradas`. Uma importacao que "deu certo" mas
    ignorou 400 de 500 linhas precisa parecer diferente de uma que ignorou 3.

    Pareamento: cada turno do assistente vira um registro cujo `prompt_completo` sao os
    turnos de usuario acumulados desde o registro anterior. Linhas que nao sao mensagem
    (resumo, sistema, meta), blocos de ferramenta sem texto e um prompt final sem resposta
    contam como ignoradas.

    `indicadores` sao os campos de celula a carimbar em todos os registros (modelo, adapter,
    persona, banco...); passam pela MESMA validacao de campo desconhecido.
    """
    caminho = Path(caminho_jsonl)
    if not caminho.exists():
        # Silencio aqui seria o pior resultado possivel: "0 gravados, 0 ignoradas" e' o que
        # uma transcricao vazia devolve, e a conversa perdida nunca seria procurada.
        raise ConversaError(f"transcricao de agente nao existe: {caminho}")
    papel_pedido = indicadores.pop("papel", "autor")
    if papel_pedido != "autor":
        raise ConversaError(
            f"importa_transcricao_de_agente grava papel='autor'; recebi papel={papel_pedido!r}. "
            "Conversa de bancada nao pode entrar no arquivo com papel de braco experimental"
        )

    linhas = caminho.read_bytes().split(b"\n")
    gravados = 0
    ignoradas = 0
    pendentes: list[str] = []
    pendentes_linhas = 0
    ts_pendente: str | None = None
    turnos_pendentes: list[dict] = []

    with abre_etapa(etapa, run_meta=run_meta, runs_dir=runs_dir) as registrador:
        for linha_bruta in linhas:
            linha = linha_bruta.decode("utf-8", errors="replace").strip()
            if not linha:
                continue
            try:
                msg = _mensagem_da_linha(json.loads(linha))
            except Exception:  # noqa: BLE001 — o formato nao e' contratual; linha ruim conta
                msg = None
            if msg is None:
                ignoradas += 1
                continue
            papel_bruto, texto, ts, turnos = msg
            turnos_pendentes.extend(turnos)
            if not texto.strip():
                # Mensagem so' de ferramenta. Ela NAO e' mais ignorada: a chamada e o
                # resultado ficam em `turnos`, que e' onde mora a troca inteira. So' conta
                # como ignorada se nem turno ela produziu.
                if not turnos:
                    ignoradas += 1
                continue
            if papel_bruto == "user":
                pendentes.append(texto)
                pendentes_linhas += 1
                ts_pendente = ts_pendente or ts
                continue
            registrador.registra(
                papel="autor",
                ts=ts or ts_pendente,
                prompt_completo="\n\n".join(pendentes),
                resposta_completa=texto,
                turnos=turnos_pendentes or None,
                **indicadores,
            )
            gravados += 1
            pendentes, pendentes_linhas, ts_pendente = [], 0, None
            turnos_pendentes = []
        # Cauda que terminou em FERRAMENTA (e nao num prompt pendurado) vira registro
        # proprio: e' onde costuma estar o trabalho da ultima etapa. A condicao e' haver
        # turno do ASSISTENTE — sem ela, um prompt final sem resposta seria contado duas
        # vezes, como ignorado e como registro, e as duas contagens ficariam sem sentido.
        if any(t["papel"] == "assistant" for t in turnos_pendentes):
            registrador.registra(
                papel="autor", ts=ts_pendente,
                prompt_completo="\n\n".join(pendentes),
                resposta_completa="", turnos=turnos_pendentes, **indicadores,
            )
            gravados += 1
        else:
            ignoradas += pendentes_linhas  # prompt final que nunca recebeu resposta

    print(f"[conversa] importacao de {caminho}: {gravados} conversa(s), "
          f"{ignoradas} linha(s) ignorada(s)")
    return Importacao(gravados, ignoradas)
