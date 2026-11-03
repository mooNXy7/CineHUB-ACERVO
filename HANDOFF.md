# Transferência de Contexto — CineHUB-ACERVO

## Repositório
- https://github.com/mooNXy7/CineHUB-ACERVO
- Branch de execução: develop/acervo-v2
- main preservada em c2176962dccc218cd17622f0acd786ff76b18a6d.
- TV, Mobile e WEB não foram modificados.

## Documentos normativos
Ler ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md e ARCHITECTURE.md antes de mudar contratos. NEXT_TASK.md define a próxima tarefa; EXECUTION_LOG.md mantém evidências.

## Fase A — concluída
- HEAD de branch antes do registro final: 6f7c01240da3cf263875cddcb5ef006acce15a7c.
- GitHub Actions run 921, ID 41573214240: success.
- 25 testes passaram; validador, auditor e py_compile passaram.
- Relatório permanente: reports/baseline/2026-11-03.md e .json.
- Artefato de snapshot: ID 13202222754; contém baseline.json, baseline.md e catalog-snapshot.sha256.
- Snapshot: 731 arquivos de catalog/ e sources/, 314.216.337 bytes, SHA-256 agregado bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.

## Inventário e achados
- 2.431 canais.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas; todos os índices existem e contagens conferem.
- 1.026 rádios; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json existe.
- Registry de fontes: uma fonte.
- Logos locais: zero imagens, apenas README e dois .gitkeep.
- Quatro workflows; dois workflows VOD chamam quatro scripts ausentes (dois cada).
- update-catalog ainda clona a referência fki1976/SaimoPlayer.
- Workflows referenciam duas funções Supabase; nenhum secret TMDB direto declarado. Não inspecionar nem duplicar valores de segredos.
- Nenhum manifesto de dependências/configuração padrão foi encontrado entre os nomes raiz verificados.

## Correção feita
Importador de rádios aceita o formato real nome|stream e o formato legado. URLs com extensão de imagem são rejeitadas como streams importados e ficam em revisão. Catálogos existentes não foram reescritos.

## Próxima etapa
Fase B: schemas e importadores canônicos. Seguir NEXT_TASK.md. Construir entrypoints VOD faltantes com base nos contratos reais, corrigir workflows, tornar referência externa opcional e criar pipeline próprio de logos. Preservar dados ativos e snapshot.

## Limites
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não inserir branding externo; não remover conteúdo em massa; não promover candidato sem quality gate e rollback.
