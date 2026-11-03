# Transferência de Contexto — CineHUB-ACERVO

## Repositório e estado
- Repositório: https://github.com/mooNXy7/CineHUB-ACERVO
- Branch: develop/acervo-v2
**HEAD-base validado:** 1908b9adf242129fe85b20731f60ff203e8e7cf4  
**main:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Comparação no HEAD-base:** 37 commits à frente, 0 atrás; 15 arquivos alterados; 0 em catalog/ ou sources/.  
**Validação desse HEAD-base:** Validate catalog, run 935, ID 41576192907, push, success; 25 testes aprovados, 0 falhas; validador, auditor, py_compile e upload success.  
**Artefato:** 13203323544; acervo-v2-baseline-1908b9adf242129fe85b20731f60ff203e8e7cf4; ZIP SHA-256 1abf5cb68741f5985f0a92a8748ee22fe6d249aa7b8d0e4ce7a0063b81ff53eb.  
Este alinhamento gera um único commit documental filho do HEAD-base acima; após ele, a comparação da branch passa a 38 commits à frente e 0 atrás, mantendo 15 arquivos alterados e zero em catalog/ ou sources/.  
Snapshot original do run 930: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto catalog-snapshot.sha256 no artefato 13202372616. O run 935 não recalculou o snapshot.  
Histórico: run 930 = baseline e origem do snapshot; run 931 = validação intermediária; run 933 = validação do HEAD anterior 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; run 935 = validação do HEAD-base documental atual.  
Fase A encerrada. Fase B está em implementação real na branch develop/acervo-v2.

## Documentos normativos
Ler ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md e ARCHITECTURE.md antes de mudar contratos. NEXT_TASK.md define a próxima tarefa; EXECUTION_LOG.md mantém evidências.

## Fase A — evidência e histórico
- Run 930 / ID 41573383428: baseline original e snapshot; artifact 13202372616.
- Run 931 / ID 41574547389: validação intermediária; artifact 13202359615.
- Run 933 / ID 41574703366: validação do HEAD anterior 9c938ed...; artifact 13202777349.
- Run 935 / ID 41576192907: validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; 25 testes aprovados, 0 falhas; artifact 13203323544.
- Snapshot original: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto no artefato 13202372616 do run 930. Não recalculado pelo run 935.

## Inventário e achados do baseline
- 2.431 canais.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas.
- Rádios: 1.026; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json existe. Registry: uma fonte.
- Diretório de logos: três arquivos locais, zero imagens.
- Quatro workflows VOD chamam quatro scripts ausentes; update-catalog ainda clona a referência fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB direto declarado. Valores de segredos Supabase não foram inspecionados.

## Próxima etapa
A Fase B já tem contratos, parsers, entrypoints VOD, testes e construção de candidato publicados. Continuar de NEXT_TASK.md e do HEAD remoto atual; não reiniciar o trabalho.

## Limites
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar token TMDB; não inserir branding externo; não remover conteúdo em massa; não promover candidato sem quality gate e rollback. PR #2 permanece aberto como draft e não mesclado.


## INSTRUÇÃO OBRIGATÓRIA PARA QUALQUER NOVA CONVERSA
Leia primeiro e integralmente [ROADMAP_V2.md](ROADMAP_V2.md). Esse documento guarda o cérebro arquitetural e o plano mestre completo do CineHUB-ACERVO V2, incluindo independência operacional, internalização e armazenamento dos dados autorizados, motores, contratos, fontes, todos os domínios, infraestrutura, fases e critérios para chegar a 100%.
Depois leia ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md, ARCHITECTURE.md (se existir), PROJECT_STATUS.md, NEXT_TASK.md e EXECUTION_LOG.md.
- Commit de criação do plano mestre: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Consultar o HEAD vivo da branch ao retomar.
- Fase A: CONCLUÍDA.
- Fase B: EM ANDAMENTO.
- O executor deve receber somente a próxima etapa liberada. Não deve reconstruir o plano por conta própria, pular fases, alterar arquitetura ou mexer em consumidores/main sem aprovação.
- A implementação da Fase B já foi publicada; a continuidade deve preservar catálogos ativos e manter saída apenas em staging.
> **RETOMADA VIGENTE — 2026-11-03 (autoridade sobre registros históricos abaixo)**  
> Branch: `develop/acervo-v2`  
> HEAD confirmado no GitHub: `3d8d143ae387f3340c1efb285fb3199393c25a99`  
> `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`  
> Comparação atual: **45 commits à frente, 0 atrás**, 15 arquivos no diff reportado; a comparação não mostra alterações em `catalog/` ou `sources/`.  
> PR #1 e PR #2 estão abertos em estado draft; nenhum está mesclado. Não alterar nem mesclar nenhum deles nesta etapa.  
> Fase A: CONCLUÍDA. Fase B: **EM ANDAMENTO**, com validação integral pendente. Esta atualização é apenas documental e não conta como implementação da Fase B.  
> Próxima execução autorizada: somente Fase B — auditoria complementar, contratos canônicos, parsers/importadores, fixtures e testes. Não iniciar Fase C.  
> Sempre revalidar HEAD, main, comparação, PRs e workflows no início da execução; estes SHAs são fotografia desta retomada, não valores permanentes.  
> Escopo protegido: não alterar `main`, consumidores TV/Mobile/Web/Player, repositórios de referência, segredos, produção Supabase/Cloudflare, OTA ou publicação oficial. Não promover/substituir catálogo ativo.  
> Fontes de verdade: ler integralmente `ROADMAP_V2.md`, `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.  
> PR #1: https://github.com/mooNXy7/CineHUB-ACERVO/pull/1 — “Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”, draft, aberto, não mesclado.  
> PR #2: https://github.com/mooNXy7/CineHUB-ACERVO/pull/2 — “[DRAFT] ACERVO V2 — Fase A: baseline executável”, draft, aberto, não mesclado. Verificar seus SHAs/diffs ao executar; não assumir que qualquer PR representa a branch de trabalho.  
> 
## Instrução direta ao executor
O responsável autorizou o início da Fase B. Execute a Fase B integralmente conforme o escopo e os critérios de `ROADMAP_V2.md` e `NEXT_TASK.md`, sem solicitar que o responsável repita o plano. A autorização não abrange Fase C, merge, consumidores ou publicação. Revalidar o estado remoto antes de editar.


## HANDOFF VIGENTE — Fase B (2026-11-03)
- HEAD registrado: `9b869cd1705cd70550b87e7db95a8024496327af`.
- 13 schemas validados; 40 testes aprovados na última execução observada.
- Construção integral do candidato passou; validação integral estava em andamento no run 983 / 41590601634.
- O VOD é processado por shard e o validador lê documentos grandes de forma incremental.
- EPG: 1.014 canais do índice local; sem payload local de programas.
- Assets: associação de logos por canal/rádio; sem imagens locais para MIME/conteúdo/licença.
- Quatro scripts VOD implementados; não executar workflows TMDB online sem a autorização/secret já existente, não alterar segredos.
- Nenhum catálogo ativo, consumidor, main, repositório Fki ou configuração de produção foi modificado. Nenhum merge, publicação ou OTA.
- Próxima ação: confirmar CI integral, idempotência, smoke tests dos quatro entrypoints, artefato completo e métricas. Encerrar somente Fase B; aguardar aprovação antes de Fase C.


### Evidência mais recente
Commit `9b869cd1705cd70550b87e7db95a8024496327af`: 40 testes (incluindo idempotência e CLI offline VOD), artefato configurado para incluir todos os documentos candidatos. Run 983 / 41591165169 passou testes, compilação e build integral; validação integral ainda pendente.

## Atualização autoritativa — validação integral de identidade e reprodutibilidade (2026-11-03)

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


## Auditoria complementar da Fase B — 2026-11-03

Relatório detalhado persistido em `reports/phase-b-quality-audit-2026-11-03.md`, baseado no artefato integral do Run 991 (`13213490340`, SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`).

- VOD: o ID legado `series-my-name` afeta as identidades canônicas `series-meu-nome-e` (TMDB 2317) e `series-my-name` (TMDB 110356). A separação canônica foi preservada, mas os dois grupos compartilham as mesmas 16 URLs de episódio com `/2317/` e provider refs com `110356`; associação das fontes permanece pendente de confirmação. O `report.json` atual tem contadores, não inventário detalhado de conflitos/consolidações.
- Rádios: os 252 itens em quarentena são URLs de imagem em `stream_url`; em todos, `name` contém uma URL com aparência de stream. Há mais 2 registros com `stream_url` vazio/ausente e URL em `name`. Nenhum endpoint foi testado em rede.
- EPG: quatro feeds XMLTV indexam 1.014 canais (179/494/182/159; prioridades 5/25/30/40), além de duas fontes HTML. Os 60 mapeamentos ambíguos correspondem a múltiplos IDs CineHUB por canal/qualidade e permanecem sem associação forçada. Não há programação XMLTV local.
- Logos: 2.018 referências externas (1.748 canais, 270 rádios); 2.018 não verificadas, MIME desconhecido, zero arquivos locais de imagem e nenhuma licença registrada.
- Workflows: os quatro entrypoints e quatro workflows foram revisados. Os fluxos online de enriquecimento TMDB não foram executados. Nenhum workflow publica ou promove automaticamente.

O Run 991 permanece a evidência de validação integral de referência: 42 testes, 13 schemas, build integral, idempotência de 11 arquivos e integridade referencial aprovados. A Fase B continua aberta; não publicar, não mesclar e não iniciar a Fase C.
