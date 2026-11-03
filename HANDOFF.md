# Transferência de Contexto — CineHUB-ACERVO

## Repositório e branch
- Repositório: https://github.com/mooNXy7/CineHUB-ACERVO
- Desenvolvimento: develop/acervo-v2
- Linha estável: main (não alterar).
- Consumidores: CineHUB-TV, CineHUB Mobile e CineHUB-WEB (não alterar).

## Documentos normativos
Leia PROJECT_STATUS.md, DECISIONS.md, ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, ARCHITECTURE.md, NEXT_TASK.md, EXECUTION_LOG.md e este arquivo. Não reiniciar o planejamento.

## Estado técnico confirmado em 2026-11-03
- HEAD inicial da branch: 2e430447866d9d3e3f042fda4cc0338efa1cfe68.
- main: c2176962dccc218cd17622f0acd786ff76b18a6d; branch V2 15 commits à frente e 0 atrás.
- Comparação líquida com main: oito documentos V2; catálogos não divergiam na comparação.
- Referência autorizada consultada: fki1976/SaimoPlayer, arquivo vod/radios.txt. Formato observado: nome|stream.
- O importador antigo exigia 3 campos e lia nome/stream em posições incompatíveis. Parser foi corrigido na branch V2 para duas colunas e formato legado.
- Rádios na branch: 1.026; 1.026 sem gênero; 754 sem logo; 2 sem stream; 253 URLs com extensão de imagem no campo stream; zero IDs duplicados; 10 logos não HTTPS.
- Manifesto VOD declara 56.248 itens distribuídos em filmes/séries/animes/doramas. Conferir contagens reais com auditor.
- EPG registry tem seis fontes; health report versionado em 2026-10-26 não é health atual.
- sources/sources.json declara uma fonte independente de canais.
- Workflows VOD têm quatro referências a scripts ausentes e branch fixa audit/acervo-hardening-2026-10.
- Workflow de atualização ainda clona a referência externa antes de importar. Isso é dependência operacional do job, embora exista uma fonte M3U independente cadastrada.
- Workflows TMDB apontam para função Supabase e usam SUPABASE_ANON_KEY; não copiar nem criar token TMDB. O segredo não foi lido.

## Arquivos adicionados/alterados na baseline
- scripts/import_reference_catalog.py: parser de rádios compatível com o formato real e proteção contra extensão de imagem em stream.
- tests/fixtures/radios_reference.txt: amostra curta real.
- tests/test_baseline.py: testes de contrato do importador.
- scripts/audit_baseline.py: auditor somente leitura.
- .github/workflows/validate.yml: CI também em develop, relatório como artefato.

## Protocolo de continuidade
1. Consultar HEAD real antes de qualquer gravação.
2. Conferir Actions e recuperar o artefato de baseline.
3. Corrigir falhas de testes sem mexer nos dados ativos.
4. Gerar e registrar snapshot/hash de proteção antes de qualquer migração.
5. Atualizar log/status/próxima tarefa com evidência e SHA.

## Limites permanentes
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não inserir branding externo; não excluir grandes volumes; não promover catálogo candidato sem quality gate e rollback.
