# sdd-task-analyzer

Módulo **TaskAnalyzer**: calcula tempo médio de conclusão, taxa de atraso e indicadores por prioridade a partir de uma lista de tarefas em memória. Desenvolvido com Spec-Driven Development (Bootcamp III).

**Autor:** Fred Gabriel — 22511576 — Análise e Desenvolvimento de Sistemas

## Estrutura
- `specs/` — SDD (PDF) e resumo do contrato (`requirements.yaml`)
- `CONTEXT_RULES.md` — regras para agentes de IA
- `src/task_analyzer.py` — implementação (gerada por IA e homologada)
- `tests/test_harness.py` — testes pytest (cenários de aceite)
- `Dockerfile`, `docker-compose.yml` — execução isolada
- `.github/workflows/ci.yml` — CI (GitHub Actions)

## Executar os testes
Local:
```bash
pip install -r requirements.txt
pytest tests/test_harness.py -v
```
Docker:
```bash
docker build -t task-analyzer .
docker run --rm task-analyzer
# ou
docker compose run --rm tests
```

## Uso
```python
from datetime import datetime, timezone
from src.task_analyzer import Tarefa, analisar_tarefas

relatorio = analisar_tarefas([...])  # lista de Tarefa
```
