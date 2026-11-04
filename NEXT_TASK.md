# Próxima Tarefa — CineHUB-ACERVO

## Estado e passagem — 2026-11-04 (autoridade: Run 1002)

- Branch: `develop/acervo-v2`; HEAD confirmado: `5e2150f3c0f48075edacb56b70111304f797d25d`.
- Run 1002 / `41744148492`: sucesso; 47 testes, 13 schemas, compilação, build integral, integridade e idempotência aprovados.
- Artefato `13283645574`; ZIP SHA-256 `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`.
- VOD: conflito de ID legado corrigido; zero IDs reutilizados entre identidades distintas. My Name (2021) canônico TMDB 110356; 8 episódios, 16 variantes únicas e provider refs agregados.
- Rádios: 257 itens históricos na quarentena; 255 resolvidos por referência exata e dois sem stream válido. Não confundir contagem histórica com falhas abertas.
- EPG: 60 mapeamentos ambíguos preservados, 18 correspondências únicas e zero programas locais. Não internalizar feed sem permissão de redistribuição.
- Logos: 2.271 associações externas; zero imagens locais/MIME/hash/licenças verificados.
- Fase B permanece EM ANDAMENTO. Não iniciar Fase C, não publicar, não alterar consumidores, não mesclar PRs ou alterar main.
- Relatório atual: [reports/phase-b-quality-audit-2026-11-04.md](reports/phase-b-quality-audit-2026-11-04.md). Os blocos Run 991 e anteriores abaixo são históricos.


## Pendências remanescentes para aceite da Fase B

1. Manter formalmente classificados os dois rádios sem correspondência na referência fixada; só recuperar após evidência de fonte/stream válida.
2. Manter os 60 mapeamentos EPG ambíguos sem associação forçada; avaliar IDs de provedor e aliases, sem escolher variante de qualidade por aproximação.
3. Resolver a política de internalização EPG com fonte/licença que permita uso; até lá, não copiar payload XMLTV de terceiros. O parser XMLTV e os canais compactos já existem, mas a programação local permanece vazia.
4. Definir storage de assets somente após inventário real de Cloudflare/Supabase e comprovação de licenças; validar bytes, MIME, hash e dimensões antes de promover logos.
5. Manter evidência de revisão dos quatro entrypoints/workflows VOD; CLI/help offline passou, mas os dois fluxos online TMDB não foram disparados.
6. Executar nova validação após esta consolidação documental e registrar o run resultante. Parar para aceite explícito; não iniciar Fase C.


## Regras permanentes
Não alterar main, TV, Mobile ou Web; não publicar OTA; não duplicar token TMDB; não excluir streams por falha pontual; não aplicar correspondência TMDB ambígua; não substituir catálogo ativo sem backup e validação.


## Fonte mestre de verdade e retomada
**Antes de executar qualquer tarefa, leia integralmente [ROADMAP_V2.md](ROADMAP_V2.md).** Ele contém o plano integral, arquitetura, todos os domínios, decisões, fases futuras, critérios de aceite e regras de continuidade.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Sempre consultar o HEAD vivo da branch antes de executar.
- Fase A: CONCLUÍDA.
- Fase B: EM ANDAMENTO.
- A Fase B deve seguir o escopo descrito em ROADMAP_V2.md, especialmente auditoria complementar, schemas canônicos, parsers/importadores, fixtures e testes.
- Não iniciar Fase C nem qualquer etapa posterior automaticamente.
- Não tratar testes unitários isolados como aceite integral da Fase B.
> **RETOMADA VIGENTE — 2026-11-03 (autoridade sobre registros históricos abaixo)**  
> Branch: `develop/acervo-v2`  
> HEAD confirmado no GitHub: `3d8d143ae387f3340c1efb285fb3199393c25a99`  
> `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`  
> Comparação atual: **45 commits à frente, 0 atrás**, 15 arquivos no diff reportado; a comparação não mostra alterações em `catalog/` ou `sources/`.  
> PR #1 e PR #2 estão abertos em estado draft; nenhum está mesclado. Não alterar nem mesclar nenhum deles nesta etapa.  
> Fase A: CONCLUÍDA. Fase B: **NÃO INICIADA; AUTORIZADA PELO RESPONSÁVEL PARA INÍCIO PELO EXECUTOR**. Esta atualização é apenas documental e não conta como implementação da Fase B.  
> Próxima execução autorizada: somente Fase B — auditoria complementar, contratos canônicos, parsers/importadores, fixtures e testes. Não iniciar Fase C.  
> Sempre revalidar HEAD, main, comparação, PRs e workflows no início da execução; estes SHAs são fotografia desta retomada, não valores permanentes.  
> Escopo protegido: não alterar `main`, consumidores TV/Mobile/Web/Player, repositórios de referência, segredos, produção Supabase/Cloudflare, OTA ou publicação oficial. Não promover/substituir catálogo ativo.  
> Fontes de verdade: ler integralmente `ROADMAP_V2.md`, `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.  
> PR #1: https://github.com/mooNXy7/CineHUB-ACERVO/pull/1 — “Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”, draft, aberto, não mesclado.  
> PR #2: https://github.com/mooNXy7/CineHUB-ACERVO/pull/2 — “[DRAFT] ACERVO V2 — Fase A: baseline executável”, draft, aberto, não mesclado. Verificar seus SHAs/diffs ao executar; não assumir que qualquer PR representa a branch de trabalho.  
> 
## Ordem executável da Fase B
1. Fazer checkout/sincronização da branch `develop/acervo-v2`; confirmar que o HEAD corresponde ao remoto e registrar SHA real. Não usar o SHA deste documento como checkout obrigatório.
2. Ler integralmente todos os documentos normativos e o roadmap.
3. Inventariar no código atual os arquivos, formatos, schemas, scripts, workflows, fontes e consumidores internos por domínio: VOD, canais, rádios, logos e EPG. Registrar evidências de caminhos/linhas e separar “existe”, “funciona”, “parcial”, “ausente” e “não verificado”.
4. Auditar complementarmente os repositórios de referência autorizados, somente leitura, apenas nos pontos necessários para compreender formatos/contratos. Confirmar namespace/repositório; não presumir equivalência entre perfis. Não copiar aplicativos ou branding.
5. Definir schemas versionados e contratos canônicos compartilhados, incluindo provenance, source, entity IDs, variantes de stream, assets/logos, relações EPG, confiança/estado e relatórios. Contratos devem derivar dos dados reais e preservar campos desconhecidos em extensão/raw quando apropriado.
6. Implementar parsers/importadores pequenos e isoláveis para formatos reais identificados. Garantir normalização determinística, IDs estáveis, idempotência, deduplicação sem perder variantes e preservação da proveniência.
7. Criar fixtures sanitizadas representativas e testes para entradas válidas, inválidas, legadas, duplicadas, incompletas, falhas de fonte, provenance, IDs e idempotência. Testes não podem depender de rede nem de segredos.
8. Reconciliar os quatro entrypoints VOD históricos e workflows que os chamam: implementar somente com contrato definido e teste; se já existirem, auditar e corrigir. Não criar stubs vazios para deixar workflow verde.
9. Isolar saídas em staging/candidato. Preservar integralmente catálogos ativos, snapshots, fontes e registros válidos. Não publicar nem promover.
10. Rodar testes, validação, auditoria read-only e comparar métricas/arquivos antes e depois. Registrar limitações, incompatibilidades e decisões que exigem aprovação.
11. Atualizar roadmap e documentos operacionais com commits, testes, workflows/runs, artefatos, métricas e pendências reais. Marcar subitens individualmente; a Fase B só termina após todos os critérios de aceite do roadmap.
12. Parar ao final da Fase B e aguardar aprovação explícita antes de iniciar Fase C.

## Critérios mínimos de aceite
- Schemas versionados para os cinco domínios e tipos compartilhados, validados em CI.
- Fixtures cobrindo formatos reais observados e casos de falha.
- Parsers/importadores determinísticos, idempotentes e testados sem rede.
- IDs e provenance preservados; variantes não são descartadas por dedup.
- Dados inválidos isolados com motivo, sem exclusão silenciosa.
- Workflows não chamam entrypoints inexistentes; nenhum stub vazio.
- Nenhuma modificação de catálogo ativo, main, consumidores, infraestrutura de produção ou publicação.
- Relatório reproduzível com inventário, diffs, testes, evidências e pendências.


## Estado de execução e pendências — histórico Run 991 (superado pelo Run 1002)
- HEAD registrado: `9b869cd1705cd70550b87e7db95a8024496327af`.
- 13 schemas validados; 40 testes aprovados na última execução observada.
- Construção integral do candidato aprovada na etapa do workflow; validação integral em processamento no run 983 (41591165169).
- Correção recente do validador preserva o resolver de referências relativas em sub-schemas.
- Próximas ações: confirmar run 983 ou execução sucessora; comprovar idempotência do build; testar `--help` dos quatro entrypoints VOD fora do diretório do repositório; garantir artefato de CI com todos os documentos candidatos; registrar contagens reais e quarentena.
- Limites ainda não comprovados: MIME/licença de imagens (não há imagens locais); programação EPG completa (não há payload XMLTV local); workflows TMDB online (não foram disparados e não se alteraram segredos).
- Nenhuma alteração em main, catálogos/fontes ativos, consumidores, repositórios de referência ou produção. Não publicar e não iniciar Fase C.


### Última evidência — run 983
40 testes offline aprovados, compilação Python aprovada e construção integral do candidato aprovada. A validação integral de schemas/relações e o upload do artefato completo ainda precisam concluir. Não fechar Fase B antes disso.


## Histórico — validação integral Run 991 (superado pelo Run 1002)

Branch: `develop/acervo-v2`. HEAD de código validado: `0ff93e98ca3a1f167e9d3e53f1882d962ff2384b`.

### CI e evidências
- Run 990 / ID `41597574427`: sucesso no workflow `validate`.
- Run 991 / ID `41597580123`: sucesso no workflow `validate`; validação de referência para esta atualização.
- Run 991 aprovou: validação do catálogo ativo sem mutação; 13 JSON Schemas; 42 testes offline; compilação Python; construção integral do candidato; comparação byte a byte de duas construções; validação dos documentos candidatos e integridade entre domínios; upload do artefato.
- Testes: `Ran 42 tests`, todos aprovados. Não dependem de rede ou segredos.
- Idempotência integral: 11 arquivos comparados; `diff -qr` e hashes SHA-256 iguais entre duas construções com `SOURCE_DATE_EPOCH=1760000000`.
- Artefato completo do Run 991: `13213490340`; ZIP SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`.

### Métricas do candidato integral (Run 991)
- VOD: 56.248 entradas de índice -> 52.603 identidades canônicas; 3.645 entradas consolidadas; 3.598 grupos com IDs legados repetidos; 47 grupos unidos por identidade de provedor entre IDs legados diferentes; 1 ID legado reutilizado entre identidades distintas (2 grupos afetados). Nenhum registro foi removido em massa.
- Streams/variantes de episódio: 786.939; IDs únicos: 786.939.
- Canais: 2.437; rádios: 1.026; logos associados: 2.018.
- EPG: 1.014 canais, 78 mapeamentos (18 resolvidos, 60 ambíguos, 0 sem correspondência), 0 programas XMLTV locais.
- Quarentena: 252 rádios. Permanecem pendentes de classificação/correção; não foram descartados silenciosamente.
- Integridade final: 0 erros de IDs/variantes duplicados indevidos; todos os documentos gerados passaram pelos 13 schemas.
- Build report confirmou `active_catalogs_modified=false` e `reference_network_used=false`.

### SHA-256 por documento candidato
- `vod.json`: `3ca39d09bcc1c6d9ae0c1dc7fd2773c306a3e173d9adac58ca674c23b352438c`
- `channels.json`: `4704295fee3311621cc3abe57f6fb38080ce395ac01b33038658c0e9b0f2c57e`
- `radios.json`: `7476a340eb515cda6364e2f3863cf605c8727eb41668f63bc6eabf6c26db0792`
- `logos.json`: `384480406378613f2a01556b18c1b81063f4b51ac7b8866576a746a9f1c91784`
- `sources.json`: `d200887ea28752edd898da149f2c5f2b4886c2f5c0f2e19e629f794ca30043c4`
- `epg-sources.json`: `73fc11ff9f01c2d3f4357a0ab712f14943d821974a0ff08d1c4826b09959bb11`
- `epg-mappings.json`: `594a523e4e624ebb3dafd0ca74ac17ca91e9f10cb067c8fbcdf806b89d71fe05`
- `epg-channels.json`: `9a045d8a7a9501af85197b27bc28f5e1b6259359f96df9d268d362cbca2f2974`
- `epg-programmes.json`: `056e69cd15a3683cfd7517b63742a851deaef37673e2703935a0e872afebda2d`

### Pendências para aceite da Fase B
1. Investigar e classificar os 252 registros de rádio em quarentena, preservando os dados originais.
2. Resolver ou documentar as 60 associações EPG ambíguas; programação continua ausente do snapshot local e não deve ser inventada nem buscada durante validação offline.
3. Diferenciar referências de logos de arquivos de imagem locais efetivamente armazenados/verificados; não há imagens locais para validação de conteúdo/MIME/licença.
4. Fechar revisão de cobertura dos cinco domínios e comprovar em evidência os quatro entrypoints/workflows VOD, incluindo limites de execução online TMDB sem disparar integração externa nesta validação.
5. Revisar a identidade conservadora dos 2 grupos afetados por reutilização de ID legado e registrar decisões sem colapsar entidades distintas.
6. Revalidar PRs/diff e escopo protegido antes do encerramento; manter Fase B aberta até os critérios de aceite do roadmap estarem cobertos.

**Estado da Fase B: EM ANDAMENTO.** A integridade técnica e reprodutibilidade do candidato integral passaram no CI, mas as pendências de rádio, EPG, assets e revisão dos entrypoints impedem declarar 100% ou concluir a fase. Nenhum catálogo foi publicado/promovido; Fase C não iniciada.


## Auditoria complementar Run 991 — histórico superado pelo relatório Run 1002

Relatório detalhado persistido em `reports/phase-b-quality-audit-2026-11-03.md`, baseado no artefato integral do Run 991 (`13213490340`, SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`).

- VOD: o ID legado `series-my-name` afeta as identidades canônicas `series-meu-nome-e` (TMDB 2317) e `series-my-name` (TMDB 110356). A separação canônica foi preservada, mas os dois grupos compartilham as mesmas 16 URLs de episódio com `/2317/` e provider refs com `110356`; associação das fontes permanece pendente de confirmação. O `report.json` atual tem contadores, não inventário detalhado de conflitos/consolidações.
- Rádios: os 252 itens em quarentena são URLs de imagem em `stream_url`; em todos, `name` contém uma URL com aparência de stream. Há mais 2 registros com `stream_url` vazio/ausente e URL em `name`. Nenhum endpoint foi testado em rede.
- EPG: quatro feeds XMLTV indexam 1.014 canais (179/494/182/159; prioridades 5/25/30/40), além de duas fontes HTML. Os 60 mapeamentos ambíguos correspondem a múltiplos IDs CineHUB por canal/qualidade e permanecem sem associação forçada. Não há programação XMLTV local.
- Logos: 2.018 referências externas (1.748 canais, 270 rádios); 2.018 não verificadas, MIME desconhecido, zero arquivos locais de imagem e nenhuma licença registrada.
- Workflows: os quatro entrypoints e quatro workflows foram revisados. Os fluxos online de enriquecimento TMDB não foram executados. Nenhum workflow publica ou promove automaticamente.

O Run 991 permanece a evidência de validação integral de referência: 42 testes, 13 schemas, build integral, idempotência de 11 arquivos e integridade referencial aprovados. A Fase B continua aberta; não publicar, não mesclar e não iniciar a Fase C.
