# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** develop/acervo-v2  
**HEAD no início da Fase A:** 2e430447866d9d3e3f042fda4cc0338efa1cfe68  
**Base preservada:** main em c2176962dccc218cd17622f0acd786ff76b18a6d  
**Estado:** especificação aprovada; baseline executável em implementação e validação.

## Missão e escopo
Construir o núcleo independente de dados e distribuição do ecossistema CineHUB: On Demand, canais, rádios, logos e EPG. A operação deve manter identidade, procedência, validação, snapshots e rollback próprios.

## Decisões aprovadas
- Fontes independentes são primárias; referências externas são adaptadores auxiliares opcionais.
- ACERVO mantém IDs, catálogo, regras, índices, histórico e publicação próprios.
- Falha de uma fonte não apaga a última versão válida.
- Reutilizar a integração TMDB já configurada no Supabase; não duplicar token.
- main permanece preservada; desenvolvimento V2 ocorre exclusivamente em develop/acervo-v2.
- TV, Mobile e Web não serão modificados nesta fase.
- Nenhuma OTA ou publicação oficial.

## Baseline observado em 2026-11-03
- main continua em c2176962dccc218cd17622f0acd786ff76b18a6d; a branch V2 está 15 commits à frente e 0 atrás. A comparação líquida com main mostra somente os oito documentos V2 já registrados, sem diferenças de catálogo.
- Catálogo de rádios: 1.026 registros; 1.026 sem gênero; 754 sem logo; 2 sem stream; 253 URLs com extensão de imagem em stream_url; 0 IDs duplicados; 10 logos com URL não HTTPS.
- Formato real consultado em fki1976/SaimoPlayer/vod/radios.txt: nome|stream. O importador atual exigia pelo menos três colunas e lia nome/stream nos índices 1/2. Incompatibilidade confirmada.
- Manifesto VOD declara 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas (56.248 no total). A auditoria executável verificará arquivos e contagens reais.
- Registro EPG contém seis fontes. O último health report versionado é de 2026-10-26 e não representa uma sondagem em tempo real desta execução.
- Registry independente sources/sources.json contém uma fonte declarada de canais.
- Workflows VOD consultam a função CineHUB no Supabase e declaram SUPABASE_ANON_KEY; os próprios workflows dizem que TMDB_TOKEN permanece no Supabase. Valores de segredos não foram consultados.
- O workflow de atualização ainda clona a referência externa. Dependência operacional do passo de importação confirmada.
- Workflows de enriquecimento/IDs VOD apontam para audit/acervo-hardening-2026-10 e referenciam scripts ausentes na branch: enrich_vod_metadata.py, apply_vod_metadata_patch.py, suggest_vod_tmdb_matches.py, apply_vod_tmdb_id_candidates.py.

## Evidências e implementação da Fase A
- scripts/import_reference_catalog.py: parser de rádios ajustado para aceitar o formato real de duas colunas e manter compatibilidade com o layout legado; URLs com extensão de imagem não são aceitas como streams.
- tests/fixtures/radios_reference.txt: amostra pequena e representativa do formato real.
- tests/test_baseline.py: testes do parser, compatibilidade legada, rejeição de imagem como stream, linhas malformadas e preservação de IDs/contagem.
- scripts/audit_baseline.py: inventário somente de leitura de catálogos, workflows, scripts, fontes externas, logos e referências TMDB.
- .github/workflows/validate.yml: validação habilitada também para develop/acervo-v2, com execução do inventário e artefato de relatório.
- Nenhum catálogo ativo foi reescrito nesta etapa.

## Progresso
- [x] Confirmar repositório, branch, HEAD e base de main.
- [x] Ler os oito documentos normativos.
- [x] Comparar a branch V2 com main.
- [x] Reproduzir a incompatibilidade do formato de rádios e medir os defeitos estruturais observáveis.
- [x] Implementar parser compatível e fixtures/testes focados em rádios.
- [x] Implementar inventário executável somente de leitura.
- [ ] Executar CI na branch V2 e registrar resultado.
- [ ] Fechar inventário completo de canais, VOD, logos, EPG, dependências e todos os workflows com relatório gerado.
- [ ] Confirmar proteção/backup dos catálogos e fechar a baseline.

**Fase A:** em andamento. Não declarar concluída até CI e relatório executável serem verificados.
