# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** develop/acervo-v2  
**HEAD inicial da Fase A:** 2e430447866d9d3e3f042fda4cc0338efa1cfe68  
**Último HEAD registrado:** e92af3fc861d359aa95b96e2cc7820f89ce69c1f  
**main preservada:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Estado:** Fase A concluída e validada no GitHub Actions.

## Missão e decisões aprovadas
ACERVO V2 é o núcleo independente de ingestão, normalização, identidade, enriquecimento, validação, publicação e recuperação de dados CineHUB. Fontes independentes são primárias; referências externas são adaptadores auxiliares. Falha de fonte não apaga a última versão válida. Reutilizar a integração TMDB existente no Supabase; não duplicar tokens. Não alterar main, TV, Mobile ou Web; não publicar OTA.

## Fase A — concluída em 2026-11-03
GitHub Actions run 921 (ID 41573214240): success.
- Validador do catálogo: aprovado.
- Auditor baseline: aprovado.
- unittest: 25 testes aprovados, 0 falhas.
- py_compile scripts/*.py: aprovado.
- Artefato ID 13202222754 com baseline.json, baseline.md e catalog-snapshot.sha256.
- Relatório permanente: reports/baseline/2026-11-03.md e .json.

## Inventário executado
- catalog/: 728 arquivos, 314.213.984 bytes.
- sources/: 3 arquivos, 2.353 bytes.
- normalizer/: 1 arquivo, 311 bytes.
- scripts/: 6 arquivos, 79.560 bytes.
- tests/: 3 arquivos, 12.713 bytes.
- reports/: 1 arquivo no momento do snapshot, antes dos dois relatórios permanentes da baseline.
- .github/workflows/: 4 arquivos, 16.460 bytes.
- Nenhum manifesto de dependências/configuração padrão foi encontrado na raiz entre os nomes verificados.
- Canais: 2.431 registros.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas; todos os quatro índices existem e as contagens reais correspondem ao manifesto.
- EPG: 6 fontes e channel-map.json presente.
- Registry de fontes: 1 entrada.
- Logos locais: zero imagens; existem README e dois .gitkeep.

## Qualidade de rádios
1.026 registros; 0 IDs duplicados; 2 streams ausentes; 754 logos ausentes; 1.026 gêneros ausentes; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS.
O formato real da referência autorizada é nome|stream. O importador foi corrigido para esse formato e mantém compatibilidade com o formato legado. Imagens não são aceitas como streams novos; registros existentes não foram apagados.

## Workflows e dependências
Quatro workflows inventariados; todos os scripts referenciados foram verificados.
- enrich-vod-metadata.yml: faltam scripts/enrich_vod_metadata.py e scripts/apply_vod_metadata_patch.py.
- suggest-vod-tmdb-ids.yml: faltam scripts/suggest_vod_tmdb_matches.py e scripts/apply_vod_tmdb_id_candidates.py.
- update-catalog.yml: scripts presentes, mas o job ainda clona fki1976/SaimoPlayer e seu filtro push é main/master.
- validate.yml: scripts presentes e validação também habilitada para develop/acervo-v2.
Workflows têm duas referências a funções Supabase; nenhum segredo TMDB está declarado diretamente. Valores de segredos Supabase não foram inspecionados.

## Proteção dos catálogos
Snapshot executado sobre 731 arquivos em catalog/ e sources/, total 314.216.337 bytes.
SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
Manifesto por arquivo no artefato do run 921. Os catálogos não foram alterados durante a Fase A. A comparação com main não contém arquivos de catálogo.

## Arquivos relevantes da Fase A
- scripts/import_reference_catalog.py
- scripts/audit_baseline.py
- tests/fixtures/radios_reference.txt
- tests/test_baseline.py
- .github/workflows/validate.yml
- reports/baseline/2026-11-03.md
- reports/baseline/2026-11-03.json

## Próxima etapa
Fase B — schemas e importadores compatíveis com os formatos reais, priorizando contratos canônicos e corrigindo os bloqueios VOD sem inventar scripts vazios. Tratar logos e rádios com proveniência e sem perdas. Tornar referências externas opcionais conforme a arquitetura aprovada.

## Limites permanentes
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar TMDB token; não remover conteúdo por falha pontual; não aplicar correspondências TMDB ambíguas; não promover catálogo candidato sem quality gate, snapshot e rollback.
