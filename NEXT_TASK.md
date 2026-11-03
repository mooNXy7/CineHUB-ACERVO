# Próxima Tarefa — CineHUB-ACERVO

## Tarefa atual
**Concluir a Fase A — baseline executável e protegida.**

## Trabalho já iniciado
- Parser de rádios agora aceita nome|stream e mantém compatibilidade com o formato legado.
- Fixture real representativa e testes de regressão adicionados.
- Auditoria executável somente de leitura criada para inventariar catálogos, workflows, scripts ausentes, dependências externas e referências TMDB.
- Workflow de validação preparado para executar na branch develop/acervo-v2 e publicar artefato do baseline.

## Próximos passos executáveis
1. Verificar resultado real do GitHub Actions após o commit desta etapa.
2. Corrigir falhas dos testes sem reescrever catálogos.
3. Registrar o relatório completo gerado pelo auditor, incluindo contagens reais de canais/VOD/logos e referências de scripts por workflow.
4. Revisar proteção/backup: snapshot lógico e hash dos catálogos antes de qualquer migração de dados.
5. Fechar a lista de bloqueios e atualizar o handoff.

## Bloqueios já confirmados
- Quatro entrypoints VOD referenciados por workflows não existem na branch.
- Workflows VOD ainda usam branch fixa antiga.
- Atualizador principal ainda depende do clone da referência para concluir a etapa de importação.
- Catálogo de rádios contém URLs com extensão de imagem no campo de stream e metadados incompletos; nenhuma correção em massa deve ser aplicada sem proveniência/backup.

## Regras
- Não alterar main, TV, Mobile ou Web.
- Não publicar OTA.
- Não remover streams/fontes por falha pontual.
- Não aplicar TMDB ambíguo.
- Não sobrescrever catálogo ativo.
- Registrar cada execução, resultado e SHA.

## Depois da Fase A
Avançar para **Fase B — schemas e importadores compatíveis com os formatos reais**, usando a baseline como referência e mantendo o catálogo atual como fonte protegida.
