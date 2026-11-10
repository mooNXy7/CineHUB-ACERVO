# CineHUB-ACERVO — Estado do Projeto

## Histórico de validação base — Run 1002

- Repositório: `mooNXy7/CineHUB-ACERVO`.
- Branch: `develop/acervo-v2`.
- HEAD: `5e2150f3c0f48075edacb56b70111304f797d25d`.
- `main` observado: `106dbb8aafa87cc14162c147732a7e185e185edb`.
- Run 1002 / `41744148492`: sucesso; 47 testes offline, 13 schemas, compilação, build integral, integridade e idempotência (11 arquivos) aprovados.
- Artefato `13283645574`: 73.111.225 bytes; ZIP SHA-256 `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`.
- VOD: 52.602 identidades; zero conflitos de IDs legados entre identidades distintas. A correção de My Name (2021) para TMDB 110356 está aplicada às duas referências afetadas; 8 episódios e 16 variantes únicas preservadas com provider refs agregados.
- Rádios: 1.026; 257 itens históricos de quarentena = 255 resolvidos + 2 sem stream válido. Os 255 recuperados permanecem como trilha de auditoria com resolução anexada.
- EPG: 1.014 canais, 78 mapeamentos (18 únicos, 60 ambíguos), 0 programas XMLTV locais.
- Logos: 2.271 associações externas (1.748 canais, 523 rádios), 0 imagens locais verificadas.
- Fase A: CONCLUÍDA. Fase B: **EM ANDAMENTO**, ainda não apresentada como 100% nem encerrada.
- PR #1 e PR #2 permanecem abertos, draft e não mesclados. Nenhum consumidor foi alterado; nenhuma publicação/OTA; Fase C não iniciada.
- Relatório atual: [reports/phase-b-quality-audit-2026-11-04.md](reports/phase-b-quality-audit-2026-11-04.md). Artefato e evidências no Run 1002.


## Missão e decisões aprovadas
ACERVO V2 é o núcleo independente de ingestão, normalização, identidade, enriquecimento, validação, publicação e recuperação de dados CineHUB. Fontes independentes são primárias; referências externas são adaptadores auxiliares. Falha de fonte não apaga a última versão válida. Reutilizar a integração TMDB existente no Supabase; não duplicar tokens.

## Evidência e histórico
- Run 930: baseline original, inventário e snapshot; artifact 13202372616.
- Run 931: validação intermediária da reconciliação documental; artifact 13202359615.
- Run 933: validação do HEAD anterior 9c938ed...; artifact 13202777349.
- Run 935: validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; artifact 13203323544; 25/25 testes.
- O run 935 não recalculou o snapshot original.

## Inventário do baseline (run 930)
- catalog/: 728 arquivos, 314.213.984 bytes; sources/: 3 arquivos, 2.353 bytes.
- Canais: 2.431. VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas.
- Rádios: 1.026; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; 0 IDs duplicados.
- EPG: 6 fontes; channel-map.json presente. Registry: 1 fonte. Logos locais: zero imagens.
- Quatro scripts VOD ausentes; update-catalog ainda clona fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB declarado diretamente. Valores de segredos Supabase não foram inspecionados.

## Snapshot e proteção
731 arquivos; 314.216.337 bytes; SHA-256 agregado bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e. Origem exclusiva: run 930, artefato 13202372616, manifesto catalog-snapshot.sha256. Snapshot preservado, não recalculado nos runs 931/933/935.
A comparação registrada no HEAD-base do run 935 contém 15 arquivos alterados e zero arquivos em catalog/ ou sources/. Após o commit documental, comparação esperada: 38 commits à frente, zero atrás; mesmos 15 arquivos e zero arquivos de catálogo/fontes.

## Próxima etapa
A Fase B está em implementação real, com contratos, importadores, testes e construção de candidato já publicados; a validação integral continua em andamento.


## Plano mestre integral — continuidade obrigatória
O plano completo do início ao aceite final está em [ROADMAP_V2.md](ROADMAP_V2.md). Este é o documento mestre de fases, arquitetura, dependências, critérios de aceite e retomada. Leia-o integralmente antes de iniciar qualquer nova tarefa.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Para o HEAD atual, consultar a branch diretamente; não reutilizar SHA histórico como se fosse atual.
- Fase A: CONCLUÍDA conforme evidências históricas acima.
- Fase B: EM ANDAMENTO; ver adendo técnico vigente.
- O roadmap preserva os achados, motores, armazenamento próprio, ingestão de arquivos, independência de repositórios externos, domínios e fases até o aceite final.
- Esta consolidação foi documental: não alterou catálogos, fontes, consumidores, infraestrutura nem publicação.
> **RETOMADA VIGENTE — 2026-11-03 (autoridade sobre registros históricos abaixo)**  
> Branch: `develop/acervo-v2`  
> HEAD confirmado no GitHub: `3d8d143ae387f3340c1efb285fb3199393c25a99`  
> `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`  
> Comparação atual: **45 commits à frente, 0 atrás**, 15 arquivos no diff reportado; a comparação não mostra alterações em `catalog/` ou `sources/`.  
> PR #1 e PR #2 estão abertos em estado draft; nenhum está mesclado. Não alterar nem mesclar nenhum deles nesta etapa.  
> Fase A: CONCLUÍDA. Fase B: **EM ANDAMENTO**, com commits reais publicados e validação integral pendente. Esta atualização é apenas documental e não conta como implementação da Fase B.  
> Próxima execução autorizada: somente Fase B — auditoria complementar, contratos canônicos, parsers/importadores, fixtures e testes. Não iniciar Fase C.  
> Sempre revalidar HEAD, main, comparação, PRs e workflows no início da execução; estes SHAs são fotografia desta retomada, não valores permanentes.  
> Escopo protegido: não alterar `main`, consumidores TV/Mobile/Web/Player, repositórios de referência, segredos, produção Supabase/Cloudflare, OTA ou publicação oficial. Não promover/substituir catálogo ativo.  
> Fontes de verdade: ler integralmente `ROADMAP_V2.md`, `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.  
> PR #1: https://github.com/mooNXy7/CineHUB-ACERVO/pull/1 — “Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”, draft, aberto, não mesclado.  
> PR #2: https://github.com/mooNXy7/CineHUB-ACERVO/pull/2 — “[DRAFT] ACERVO V2 — Fase A: baseline executável”, draft, aberto, não mesclado. Verificar seus SHAs/diffs ao executar; não assumir que qualquer PR representa a branch de trabalho.  
> 
## Situação técnica a confirmar na Fase B
Os quatro entrypoints VOD foram implementados e estão em auditoria/testes; os workflows VOD foram reconciliados para staging. A validação de execução online permanece separada e não foi disparada, pois exigiria a integração/segredo já existente no Supabase.


## Estado técnico histórico — Fase B (2026-11-03; superado pelo Run 1002)
- Branch: `develop/acervo-v2`; último commit registrado nesta atualização: `9b869cd1705cd70550b87e7db95a8024496327af`.
- Schemas: 13/13 validados.
- Testes: 39 aprovados na última execução observada.
- Construção integral: etapa aprovada em runs 976/977; validação foi interrompida por atualização subsequente. Run 980 repetiu os testes e build com sucesso; validação integral ainda estava em andamento.
- Candidato: VOD processado por shard e escrito incrementalmente; validador usa ijson para documentos grandes.
- EPG: 1.014 canais do índice local normalizados; programação completa não está presente localmente.
- Logos: associações por entidade/canal/rádio são geradas; arquivos locais de imagem ausentes, portanto MIME/licença/availability continuam não verificados.
- Segurança: sem alterações em main, catálogos/fontes ativos, consumidores, segredos ou produção; nenhuma publicação.
- Estado da Fase B: EM ANDAMENTO (~65%); não declarar 100%.
- Próxima tarefa: fechar validação integral, comprovar idempotência e smoke tests dos quatro entrypoints, atualizar evidências/artefatos e encerrar somente a Fase B.


### Atualização de execução — commit `9b869cd1705cd70550b87e7db95a8024496327af`
- Testes ampliados para 40, incluindo idempotência byte a byte do candidato e CLI offline dos quatro entrypoints VOD.
- Workflow passou a arquivar todos os documentos candidatos.
- Run 983 / 41591165169: testes, compilação e build integral aprovados; validação integral pendente.


## Histórico de validação — Run 991 (2026-11-03; superado pelo Run 1002)

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


## Reconciliação vigente — Run 1002 (2026-11-04)

Consultar o relatório [phase-b-quality-audit-2026-11-04.md](reports/phase-b-quality-audit-2026-11-04.md). As métricas de Run 991 e anteriores são históricas, não atuais. A correção VOD de My Name está resolvida; a quarentena de rádio é 255 resolvidos e dois não resolvidos; EPG permanece sem programação local e com 60 mapeamentos ambíguos; logos permanecem referências externas sem bytes locais verificados. A Fase B continua aberta até apresentação e aprovação explícita.


## Atualização vigente — 2026-11-04 (auditoria de proteção)

- HEAD de entrada: `94ad349d455b336d63d4aab345c0d3409a26650c`; `main` observada: `106dbb8aafa87cc14162c147732a7e185e185edb`.
- Runs 1004 e 1005 concluídos com sucesso (47 testes, 13 schemas, 11 arquivos idempotentes). Eles validaram snapshots diferentes: branch e merge virtual do PR #2 com main.
- O workflow legado da main faz commit/push automático direto na main. Foi criado antes da Fase B, mas conflita com D-002; nenhuma alteração foi feita nele.
- A atualização Run211 reduziu o índice de filmes em 8.301 entradas e removeu 87 shards antigos; deduplicação é provável pelo código, mas preservação registro a registro ainda precisa ser demonstrada.
- O merge PR identificou 148 IDs XMLTV duplicados de `open-epg-br`. My Name (2021) está canônico (TMDB110356), com 8 episódios, 16 URLs e 55 provider refs no snapshot de merge.
- Rádios: 255 recuperados mas `unverified`; 2 pendentes. EPG: 60 ambiguidades e 0 programas locais. Logos: 2.271 associações, sem assets locais/licenças verificadas.
- **Fase B não encerrada e não apresentada para aceite.** Detalhes: [relatório de proteção](reports/phase-b-protection-audit-2026-11-04.md).
