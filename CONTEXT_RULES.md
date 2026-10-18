# CONTEXT_RULES — TaskAnalyzer

Fonte da verdade para agentes de IA. Contexto obrigatório: `specs/system_design_document.pdf` (SDD) + este arquivo.

## 1. Diretrizes arquiteturais (obrigatórias)
- Python 3.11 ou superior.
- Type hints em todas as funções e métodos.
- Single Responsibility (SRP) e PEP 8; funções pequenas, coesas, com um único propósito.
- Docstrings no padrão Google style (módulos, classes, funções, parâmetros).
- Exceções específicas, com classes próprias (ex.: `TarefaInvalidaError`) e mensagens claras.
- Logs com o módulo padrão `logging`; sem `print` para depuração.
- Nomes descritivos, em português ou inglês de forma consistente.

## 2. Proibições explícitas
- Nenhuma biblioteca externa além da biblioteca padrão (e `pytest` para testes).
- Não alterar, remover ou adaptar os cenários de aceite (SDD, seção 2.1).
- Não modificar a estrutura de pastas do repositório.
- Não persistir dados em arquivos ou bancos: tudo em memória.
- Não alterar assinatura de funções públicas sem autorização registrada.
- Não gerar código sem testes automatizados correspondentes.
- Não inserir código duplicado ou desnecessário (sem over-engineering).
- Não assumir comportamentos não especificados no contrato.

## 3. Regras de interação com a IA
- Fornecer o contexto completo antes de pedir código.
- Validar o entendimento da IA (pedir resumo) antes da geração.
- Pedir justificativa para decisões de design não cobertas pelo SDD.
- Revisar criticamente todo código; nada é versionado sem homologação humana.
- Rejeitar e pedir nova geração se houver violação das proibições ou do contrato.

## 4. Decisões registradas (ambiguidades do SDD resolvidas na homologação)
| # | Ambiguidade | Decisão |
|---|-------------|---------|
| 1 | Cenário 2 cita divisão por zero como exceção; regra 1.3.3 manda retornar `0.0` | Prevalece a regra 1.3.3 (e o Cenário 3): sem tarefas concluídas, retorna `0.0`. Exceção só para entradas inválidas. |
| 2 | `quantidade` por prioridade: inclui canceladas? | Sim, conta todas as tarefas da prioridade, como `quantidade_tarefas`. |
| 3 | Concluída sem `data_inicio` (campo opcional) | Entra na taxa de atraso, fica fora do tempo médio. |
| 4 | Datas sem fuso | Interpretadas como UTC; datas com fuso diferente de UTC são rejeitadas (sem conversão). |
| 5 | Prioridades ausentes na entrada | Não aparecem em `indicadores_por_prioridade`. |
