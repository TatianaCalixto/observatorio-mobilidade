# Instruções

> Renderizado a partir de `observatorio_mobilidade_planejamento_sprints.xlsx` (aba **Instruções**).

Observatório de Mobilidade — Documentação Verdade das Sprints
Esta planilha é a fonte única de verdade para a execução do projeto. O chat do Claude Code que vai trabalhar nas tarefas deve usá-la como roteiro, registrar evolução nela e nunca tomar decisões de escopo fora dela.

Como o Claude Code deve usar esta planilha
1. Sempre comece a sessão lendo a aba 'Visão Geral' para entender o estado macro.
2. Em seguida, abra a aba 'Backlog' e localize a próxima tarefa com status 'Pendente' respeitando a coluna 'Dependências' (não pular ordem).
3. Marque a tarefa como 'Em andamento' e preencha 'Data Início'.
4. Implemente a tarefa seguindo exatamente o que está em 'Descrição' e 'Critérios de Aceitação'. Não adicionar features extras.
5. Escrever os testes listados em 'Testes Obrigatórios' ANTES de marcar como concluída. Sem testes verdes a tarefa não é concluída.
6. Rodar a suíte completa de testes (pytest + dbt test quando aplicável) para garantir que nada regrediu antes de concluir.
7. Mudar status para 'Em teste' quando o código estiver pronto e os testes estiverem rodando; mudar para 'Concluída' quando tudo passar.
8. Preencher 'Data Fim' e qualquer 'Observação' relevante (decisões tomadas, arquivos criados, comandos úteis para rodar).
9. Se houver dúvida que mude o escopo ou comportamento esperado da tarefa, marcar 'Impedimento? = Sim', escrever a dúvida e PARAR. Perguntar para o humano via mensagem. Nunca decidir sozinho.

Regras inegociáveis
• Toda tarefa que toca regra de negócio (cálculo da métrica de atraso/demanda, construção de features, idempotência de ingestão) DEVE ter testes que travam a regressão.
• A bateria de regressão da métrica de atraso/demanda (S04-T01) e do dataset de ML sem vazamento temporal (S05-T01) deve continuar verde em todas as sprints seguintes. Se quebrar, parar e investigar.
• Cobertura de testes do código Python deve permanecer ≥ 80% a partir da Sprint 7.
• Nunca commitar dados brutos pesados nem segredos. Sempre usar .env e .env.example e manter data/ no .gitignore.
• Transformações de dados sempre via dbt (camadas) — não criar marts manualmente fora do dbt.
• Ingestões devem ser idempotentes — reexecutar não pode duplicar dados.
• Para qualquer decisão técnica não trivial, registrar na aba 'Decisões'.

Sobre a aba 'Plano de Testes'
Lista de checks de teste que precisam existir ao final do projeto. Marcar como 'Concluída' assim que o teste correspondente estiver no repositório e verde no CI.

Sobre a aba 'Impedimentos'
Registrar QUALQUER bloqueio antes de prosseguir. Cada linha tem ID, sprint/tarefa relacionada, descrição do problema, o que tentou e a pergunta para o humano.

Sobre a aba 'Decisões'
Registrar decisões técnicas não óbvias: por que escolheu biblioteca X, por que estrutura Y, grão do fato, etc. Garante que o próximo Claude entenda o porquê.

Convenções
• IDs de tarefa no formato S##-T## (ex.: S05-T03).
• Status válidos: Pendente, Em andamento, Bloqueada, Em teste, Concluída, Cancelada (dropdown na coluna Status).
• Datas no formato AAAA-MM-DD.
• Observações curtas e úteis, sem narrativa longa.
