# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** \`develop/acervo-v2\`  
**HEAD auditado da branch:** \`3c4d2f7b2c4177e09745f6979860c95ffc8f39a3\`  
**Commit temporário do runner na validação 930:** \`d6266bbe5679546e39a63e2724b1460c5465ed4f\`  
**main preservada:** \`c2176962dccc218cd17622f0acd786ff76b18a6d\`  
**Comparação:** 34 commits à frente, 0 atrás; nenhum arquivo de catalog/ ou sources/ alterado.  
**Estado:** Fase A concluída; reconciliação documental baseada na execução 930.

## Missão e decisões aprovadas
ACERVO V2 é o núcleo independente de ingestão, normalização, identidade, enriquecimento, validação, publicação e recuperação de dados CineHUB. Fontes independentes são primárias; referências externas são adaptadores auxiliares. Falha de fonte não apaga a última versão válida. Reutilizar a integração TMDB existente no Supabase; não duplicar tokens. Não alterar main, TV, Mobile ou Web; não publicar OTA.

## Evidência canônica da Fase A
GitHub Actions **Validate catalog**, run **930**, ID **41573383428**:
- Branch: develop/acervo-v2.
- HEAD real da branch: 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3.
- Commit temporário do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Conclusão: success.
- Validador de catálogo: success.
- Auditor baseline: success.
- unittest: 25 testes aprovados, 0 falhas.
- py_compile: success.
- Upload de artefato: success.
- Artefato ID 13202372616; nome acervo-v2-baseline-d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Digest SHA-256 do ZIP: f7474e0132200ff522e8c82e2b85a20494c3776f4bd0c88b66a835a3c27ae690.
- Snapshot SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.

## Inventário executado no run 930
- catalog/: 728 arquivos, 314.213.984 bytes.
- sources/: 3 arquivos, 2.353 bytes.
- normalizer/: 1 arquivo, 311 bytes.
- scripts/: 6 arquivos, 79.560 bytes.
- tests/: 3 arquivos, 12.713 bytes.
- reports/: 3 arquivos, 7.600 bytes no checkout auditado pelo runner.
- .github/workflows/: 4 arquivos, 16.460 bytes.
- Nenhum manifesto de dependências/configuração padrão foi encontrado na raiz entre os nomes verificados.
- Canais: 2.431.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas; índices presentes e contagens conferem.
- Rádios: 1.026; 2 streams ausentes; 754 logos ausentes; 1.026 gêneros ausentes; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json presente.
- Registry de fontes: 1 entrada.
- Diretório de logos: 3 arquivos locais, mas zero imagens.
- Quatro scripts VOD ausentes em dois workflows.
- update-catalog ainda clona fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB declarado diretamente. Valores de segredos Supabase não foram inspecionados.

## Correção técnica incluída
Importador de rádios aceita o formato real nome|stream e mantém compatibilidade com o formato legado. URLs com extensão de imagem não são aceitas como streams novos. Catálogos existentes não foram reescritos.

## Proteção dos catálogos
Snapshot de 731 arquivos em catalog/ e sources/, total de 314.216.337 bytes.
SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
Manifesto individual incluído no artefato 13202372616. Nenhum catálogo foi alterado na diferença de 34 commits com main.

## Próxima etapa
A Fase B continua apenas como próxima tarefa planejada, conforme NEXT_TASK.md. Não foi iniciada nesta reconciliação documental.

## Limites permanentes
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar TMDB token; não remover conteúdo por falha pontual; não aplicar correspondências TMDB ambíguas; não promover catálogo candidato sem quality gate, snapshot e rollback.
