"""Módulo TaskAnalyzer: análise de tarefas e produtividade.

Calcula, de forma determinística e em memória, métricas de andamento a partir
de uma lista de tarefas, conforme o contrato definido no SDD (seção 1.3).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

PRIORIDADES_VALIDAS: tuple[str, ...] = ("baixa", "media", "alta")
STATUS_VALIDOS: tuple[str, ...] = ("concluida", "pendente", "cancelada")


class TarefaInvalidaError(ValueError):
    """Erro lançado quando uma tarefa (ou a coleção) viola o contrato do SDD."""


@dataclass(frozen=True)
class Tarefa:
    """Representa uma tarefa de entrada (SDD, seção 1.3.1).

    Attributes:
        id_tarefa: Identificador único (> 0).
        titulo: Título não vazio.
        prioridade: 'baixa', 'media' ou 'alta' (case-insensitive).
        data_criacao: Data/hora de criação (UTC).
        prazo: Data/hora limite prevista (UTC).
        status: 'concluida', 'pendente' ou 'cancelada'.
        data_inicio: Início da execução, se houver (UTC).
        data_conclusao: Conclusão; obrigatória se status='concluida' (UTC).
    """

    id_tarefa: int
    titulo: str
    prioridade: str
    data_criacao: datetime
    prazo: datetime
    status: str
    data_inicio: datetime | None = None
    data_conclusao: datetime | None = None


def _normalizar_data(valor: datetime | None, campo: str, id_tarefa: Any) -> datetime | None:
    """Garante que a data esteja em UTC, sem converter outros fusos.

    Args:
        valor: Data a validar (naive é interpretada como UTC).
        campo: Nome do campo, usado na mensagem de erro.
        id_tarefa: Identificador da tarefa, usado na mensagem de erro.

    Returns:
        Data com tzinfo UTC, ou None se o valor for None.

    Raises:
        TarefaInvalidaError: Se não for datetime ou tiver fuso diferente de UTC.
    """
    if valor is None:
        return None
    if not isinstance(valor, datetime):
        raise TarefaInvalidaError(f"Tarefa {id_tarefa}: '{campo}' deve ser datetime.")
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    if valor.utcoffset() != timedelta(0):
        raise TarefaInvalidaError(f"Tarefa {id_tarefa}: '{campo}' deve estar em UTC.")
    return valor


def _validar_campos_basicos(tarefa: Tarefa) -> tuple[str, str]:
    """Valida id, título, prioridade e status.

    Args:
        tarefa: Tarefa a validar.

    Returns:
        Tupla (prioridade, status) normalizados em minúsculas.

    Raises:
        TarefaInvalidaError: Se algum campo for inválido.
    """
    id_tarefa = tarefa.id_tarefa
    if isinstance(id_tarefa, bool) or not isinstance(id_tarefa, int) or id_tarefa <= 0:
        raise TarefaInvalidaError(f"id_tarefa inválido: {id_tarefa!r} (deve ser int > 0).")
    if not isinstance(tarefa.titulo, str) or not tarefa.titulo.strip():
        raise TarefaInvalidaError(f"Tarefa {id_tarefa}: título vazio.")
    prioridade = str(tarefa.prioridade).strip().lower()
    if prioridade not in PRIORIDADES_VALIDAS:
        raise TarefaInvalidaError(f"Tarefa {id_tarefa}: prioridade inválida {tarefa.prioridade!r}.")
    status = str(tarefa.status).strip().lower()
    if status not in STATUS_VALIDOS:
        raise TarefaInvalidaError(f"Tarefa {id_tarefa}: status inválido {tarefa.status!r}.")
    return prioridade, status


def validar_tarefa(tarefa: Tarefa) -> Tarefa:
    """Valida uma tarefa e devolve uma cópia normalizada.

    Aplica a regra de reabertura: tarefa 'pendente' tem data_conclusao zerada.

    Args:
        tarefa: Tarefa de entrada.

    Returns:
        Nova Tarefa com prioridade/status em minúsculas e datas em UTC.

    Raises:
        TarefaInvalidaError: Se a tarefa violar o contrato do SDD.
    """
    prioridade, status = _validar_campos_basicos(tarefa)
    idt = tarefa.id_tarefa
    criacao = _normalizar_data(tarefa.data_criacao, "data_criacao", idt)
    prazo = _normalizar_data(tarefa.prazo, "prazo", idt)
    inicio = _normalizar_data(tarefa.data_inicio, "data_inicio", idt)
    conclusao = _normalizar_data(tarefa.data_conclusao, "data_conclusao", idt)
    if criacao is None or prazo is None:
        raise TarefaInvalidaError(f"Tarefa {idt}: data_criacao e prazo são obrigatórios.")
    if prazo < criacao:
        raise TarefaInvalidaError(f"Tarefa {idt}: prazo anterior à data de criação.")
    if status == "concluida":
        if conclusao is None:
            raise TarefaInvalidaError(f"Tarefa {idt}: concluída sem data_conclusao.")
        if inicio is not None and conclusao < inicio:
            raise TarefaInvalidaError(f"Tarefa {idt}: conclusão anterior ao início.")
    elif status == "pendente" and conclusao is not None:
        logger.info("Tarefa %s reaberta: data_conclusao zerada.", idt)
        conclusao = None
    return replace(
        tarefa, prioridade=prioridade, status=status, data_criacao=criacao,
        prazo=prazo, data_inicio=inicio, data_conclusao=conclusao,
    )


def _validar_colecao(tarefas: list[Tarefa]) -> list[Tarefa]:
    """Valida todas as tarefas e a unicidade dos ids.

    Args:
        tarefas: Lista de tarefas de entrada.

    Returns:
        Lista de tarefas normalizadas.

    Raises:
        TarefaInvalidaError: Se alguma tarefa for inválida ou houver id repetido.
    """
    normalizadas = [validar_tarefa(t) for t in tarefas]
    ids = [t.id_tarefa for t in normalizadas]
    if len(ids) != len(set(ids)):
        raise TarefaInvalidaError("id_tarefa repetido na coleção.")
    return normalizadas


def _media(valores: list[float]) -> float:
    """Média aritmética; retorna 0.0 se a lista estiver vazia (sem divisão por zero)."""
    return sum(valores) / len(valores) if valores else 0.0


def _calcular_metricas(tarefas: list[Tarefa]) -> dict[str, float | int]:
    """Calcula tempo médio, taxa de atraso e quantidade de um grupo de tarefas.

    Somente tarefas concluídas entram no tempo médio e na taxa de atraso.
    Tarefas concluídas sem data_inicio ficam fora do tempo médio.

    Args:
        tarefas: Tarefas já validadas e normalizadas.

    Returns:
        Dicionário com tempo_medio_conclusao_min, taxa_atraso_percentual e quantidade.
    """
    concluidas = [t for t in tarefas if t.status == "concluida"]
    duracoes = [
        (t.data_conclusao - t.data_inicio).total_seconds() / 60
        for t in concluidas
        if t.data_inicio is not None and t.data_conclusao is not None
    ]
    atrasadas = sum(1 for t in concluidas if t.data_conclusao > t.prazo)
    taxa = atrasadas / len(concluidas) * 100 if concluidas else 0.0
    return {
        "tempo_medio_conclusao_min": _media(duracoes),
        "taxa_atraso_percentual": taxa,
        "quantidade": len(tarefas),
    }


def analisar_tarefas(tarefas: list[Tarefa]) -> dict[str, Any]:
    """Gera o relatório de métricas (SDD, seção 1.3.2).

    Args:
        tarefas: Lista de tarefas a analisar (pode ser vazia).

    Returns:
        Dicionário com tempo_medio_conclusao_min, taxa_atraso_percentual,
        quantidade_tarefas e indicadores_por_prioridade.

    Raises:
        TarefaInvalidaError: Se alguma tarefa violar o contrato.
    """
    validas = _validar_colecao(tarefas)
    geral = _calcular_metricas(validas)
    por_prioridade = {
        prioridade: _calcular_metricas([t for t in validas if t.prioridade == prioridade])
        for prioridade in PRIORIDADES_VALIDAS
        if any(t.prioridade == prioridade for t in validas)
    }
    logger.info("Análise concluída: %d tarefas.", len(validas))
    return {
        "tempo_medio_conclusao_min": geral["tempo_medio_conclusao_min"],
        "taxa_atraso_percentual": geral["taxa_atraso_percentual"],
        "quantidade_tarefas": len(validas),
        "indicadores_por_prioridade": por_prioridade,
    }
