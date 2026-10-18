"""Test harness do TaskAnalyzer (cenários de aceite do SDD, seção 2.1)."""
from datetime import datetime, timedelta, timezone

import pytest

from src.task_analyzer import Tarefa, TarefaInvalidaError, analisar_tarefas

BASE = datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc)


def criar_tarefa(id_tarefa: int = 1, **kwargs) -> Tarefa:
    """Cria uma tarefa válida (pendente) com possibilidade de sobrescrever campos."""
    dados = {
        "id_tarefa": id_tarefa,
        "titulo": "Tarefa",
        "prioridade": "media",
        "data_criacao": BASE,
        "prazo": BASE + timedelta(hours=10),
        "status": "pendente",
    }
    dados.update(kwargs)
    return Tarefa(**dados)


def concluida(id_tarefa: int, prioridade: str, minutos: int, atrasada: bool) -> Tarefa:
    """Cria tarefa concluída que durou `minutos`, no prazo ou em atraso."""
    inicio = BASE + timedelta(hours=1)
    conclusao = inicio + timedelta(minutes=minutos)
    prazo = conclusao - timedelta(minutes=1) if atrasada else conclusao + timedelta(minutes=1)
    return criar_tarefa(
        id_tarefa, prioridade=prioridade, status="concluida",
        data_inicio=inicio, data_conclusao=conclusao, prazo=prazo,
    )


# ---------------- Cenário 1: sucesso ----------------
@pytest.fixture
def tarefas_validas() -> list[Tarefa]:
    return [
        concluida(1, "alta", 60, atrasada=False),
        concluida(2, "alta", 120, atrasada=True),
        concluida(3, "baixa", 30, atrasada=False),
        criar_tarefa(4, prioridade="media"),
        criar_tarefa(5, prioridade="baixa", status="cancelada"),
    ]


def test_cenario1_metricas_gerais(tarefas_validas):
    r = analisar_tarefas(tarefas_validas)
    assert r["quantidade_tarefas"] == 5
    assert r["tempo_medio_conclusao_min"] == pytest.approx(70.0)
    assert r["taxa_atraso_percentual"] == pytest.approx(100 / 3)


def test_cenario1_indicadores_por_prioridade(tarefas_validas):
    ind = analisar_tarefas(tarefas_validas)["indicadores_por_prioridade"]
    assert ind["alta"]["tempo_medio_conclusao_min"] == pytest.approx(90.0)
    assert ind["alta"]["taxa_atraso_percentual"] == pytest.approx(50.0)
    assert ind["alta"]["quantidade"] == 2
    assert ind["baixa"]["taxa_atraso_percentual"] == pytest.approx(0.0)
    assert ind["baixa"]["quantidade"] == 2  # inclui a cancelada
    assert ind["media"]["tempo_medio_conclusao_min"] == 0.0
    assert ind["media"]["quantidade"] == 1


def test_tarefa_concluida_no_prazo_nao_e_atraso():
    r = analisar_tarefas([concluida(1, "alta", 10, atrasada=False)])
    assert r["taxa_atraso_percentual"] == 0.0


def test_tarefa_concluida_em_atraso():
    r = analisar_tarefas([concluida(1, "alta", 10, atrasada=True)])
    assert r["taxa_atraso_percentual"] == 100.0


def test_tarefa_cancelada_conta_na_quantidade_mas_nao_nas_metricas():
    r = analisar_tarefas([criar_tarefa(1, status="cancelada")])
    assert r["quantidade_tarefas"] == 1
    assert r["tempo_medio_conclusao_min"] == 0.0
    assert r["taxa_atraso_percentual"] == 0.0


def test_prioridade_case_insensitive():
    r = analisar_tarefas([concluida(1, "ALTA", 10, atrasada=False)])
    assert "alta" in r["indicadores_por_prioridade"]


def test_reabertura_zera_data_conclusao():
    reaberta = criar_tarefa(1, status="pendente", data_conclusao=BASE + timedelta(hours=2))
    r = analisar_tarefas([reaberta])
    assert r["tempo_medio_conclusao_min"] == 0.0
    assert r["taxa_atraso_percentual"] == 0.0


def test_entrada_nao_e_modificada():
    reaberta = criar_tarefa(1, status="pendente", data_conclusao=BASE + timedelta(hours=2))
    analisar_tarefas([reaberta])
    assert reaberta.data_conclusao is not None


def test_datas_naive_sao_tratadas_como_utc():
    t = criar_tarefa(1, data_criacao=datetime(2025, 1, 1), prazo=datetime(2025, 1, 2))
    assert analisar_tarefas([t])["quantidade_tarefas"] == 1


# ---------------- Cenário 2: exceções ----------------
def test_cenario2_prazo_anterior_a_criacao():
    t = criar_tarefa(1, prazo=BASE - timedelta(days=1))
    with pytest.raises(TarefaInvalidaError, match="prazo anterior"):
        analisar_tarefas([t])


def test_cenario2_nenhuma_concluida_retorna_zero_sem_erro():
    # Regra 1.3.3: divisão por zero retorna 0.0 (nunca erro de aritmética).
    r = analisar_tarefas([criar_tarefa(1), criar_tarefa(2)])
    assert r["tempo_medio_conclusao_min"] == 0.0
    assert r["taxa_atraso_percentual"] == 0.0


@pytest.mark.parametrize(
    "campos",
    [
        {"id_tarefa": 0},
        {"id_tarefa": -3},
        {"titulo": "   "},
        {"prioridade": "urgente"},
        {"status": "atrasada"},
        {"status": "concluida"},  # sem data_conclusao
        {"data_criacao": "2025-01-01"},
        {"data_criacao": datetime(2025, 1, 1, tzinfo=timezone(timedelta(hours=-3)))},
    ],
)
def test_cenario2_campos_invalidos(campos):
    with pytest.raises(TarefaInvalidaError):
        analisar_tarefas([criar_tarefa(**campos)])


def test_cenario2_conclusao_anterior_ao_inicio():
    t = criar_tarefa(
        1, status="concluida",
        data_inicio=BASE + timedelta(hours=3), data_conclusao=BASE + timedelta(hours=2),
    )
    with pytest.raises(TarefaInvalidaError):
        analisar_tarefas([t])


def test_cenario2_id_repetido():
    with pytest.raises(TarefaInvalidaError, match="repetido"):
        analisar_tarefas([criar_tarefa(1), criar_tarefa(1)])


# ---------------- Cenário 3: borda ----------------
def test_cenario3_colecao_vazia():
    assert analisar_tarefas([]) == {
        "tempo_medio_conclusao_min": 0.0,
        "taxa_atraso_percentual": 0.0,
        "quantidade_tarefas": 0,
        "indicadores_por_prioridade": {},
    }
