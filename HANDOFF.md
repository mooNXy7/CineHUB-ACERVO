# Transferência de Contexto — CineHUB-ACERVO

Este arquivo permite retomar o trabalho em nova conversa sem recomeçar auditorias nem inverter a ordem.

## Repositório e branch
- Repositório: https://github.com/mooNXy7/CineHUB-ACERVO
- Desenvolvimento: `develop/acervo-v2`
- Linha estável: `main` (não alterar nesta fase).
- Consumidores: CineHUB-TV, CineHUB Mobile e CineHUB-WEB (não alterar nesta fase).

## Leia nesta ordem
1. `PROJECT_STATUS.md`
2. `DECISIONS.md`
3. `ACERVO_V2_SPEC.md`
4. `ACERVO_V2_BLUEPRINT.md`
5. `ARCHITECTURE.md`
6. `EXECUTION_LOG.md`
7. `NEXT_TASK.md`
8. Este arquivo.

## Protocolo obrigatório de retomada
1. Confirmar repositório e consultar HEAD real de `develop/acervo-v2`.
2. Ler os documentos na ordem acima.
3. Ler a última entrada de `EXECUTION_LOG.md` e comparar com commits/workflows atuais.
4. Executar apenas a próxima tarefa em `NEXT_TASK.md`; não repetir etapas comprovadas.
5. Antes de modificar qualquer dado, inspecionar o estado real, criar backup/diff e preparar rollback.
6. Registrar arquivos alterados, testes executados, resultados e SHA do commit.

## Contexto técnico já levantado (revalidar no código, não presumir)
- Há um pipeline de catálogo existente e importador de referência que precisa ser desacoplado.
- O formato de rádios da referência não é compatível diretamente com o importador atual.
- A amostra auditada de rádios apresentou registros sem gênero/logo e URLs de imagem em campo de stream; validar novamente na branch.
- Workflows VOD apontaram para scripts ausentes na branch auditada; confirmar antes de corrigir.
- Um cliente TV ainda foi identificado consultando índice do repositório de referência para resolver referências de VOD. Não tocar no consumidor agora; eliminar essa necessidade no contrato próprio antes da futura integração.
- TMDB já possui token integrado ao Supabase conforme informação do responsável; não duplicar segredo.
- Recursos Cloudflare/Supabase devem ser inventariados antes de assumir que Pages, Workers, R2, tabelas ou funções específicas estão ativos.

## Decisões permanentes
- Fontes independentes são primárias; repositórios de referência são adaptadores opcionais.
- ACERVO mantém seus próprios IDs, metadados, fontes, índices, versões e histórico.
- Não usar branding Saimo em produto/documentação pública.
- Nenhuma alteração em TV/Mobile/Web, nenhuma integração em produção e nenhuma OTA sem autorização expressa.
- Falha temporária não é motivo para remover conteúdo; publicação exige quality gate e rollback.

## Regra de continuidade
Não voltar ao planejamento do zero. Usar a especificação aprovada como contrato, atualizar somente quando evidência técnica demonstrar necessidade, registrar a razão e preservar decisões já aprovadas.
