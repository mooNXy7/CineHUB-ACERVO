# EXECUTION LOG — CineHUB-ACERVO

## Estado atual e validação mais recente — 2026-11-04

- Branch: `develop/acervo-v2`; HEAD analisado: `5e2150f3c0f48075edacb56b70111304f797d25d`.
- `main` observado: `106dbb8aafa87cc14162c147732a7e185e185edb`.
- Run 1002 / `41744148492`, job `126292819734`: success.
- 47 testes offline; 13 schemas; compilação; build integral; integridade referencial; idempotência byte a byte de 11 arquivos — todos aprovados.
- Artefato `13283645574`, 73.111.225 bytes, 15 arquivos; ZIP SHA-256 `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`.
- VOD: 56.248 entradas -> 52.602 identidades; zero conflito de ID legado. Correção My Name (2021) aplicada a duas referências; oito episódios, 16 URLs de variantes únicas e 33 provider refs distintos no conjunto das três referências.
- Rádios: 257 itens de quarentena histórica, 255 resolvidos e dois não resolvidos; todos com procedência. 255 streams adicionados, 253 candidatos de logo promovidos.
- EPG: 1.014 canais, 78 mappings (18 matched, 60 ambiguous), 0 programmes locais.
- Logos: 2.271 associações, 0 arquivos de imagem locais e 0 MIME/hash/licenças verificados.
- `active_catalogs_modified=false`; `reference_network_used=false`. Nenhum consumidor, segredo, catálogo ativo ou main alterado.
- PR #1/#2 abertos, draft e não mesclados. Fase B continua EM ANDAMENTO.


## Registro consolidado das validações
- **Run 930 / 41573383428:** baseline original, inventário e snapshot; artifact 13202372616; success.
- **Run 931 / 41574547389:** validação intermediária da reconciliação; artifact 13202359615; success.
- **Run 933 / 41574703366:** validação do HEAD anterior 9c938ed...; artifact 13202777349; success.
- **Run 935 / 41576192907:** validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; artifact 13203323544; success; 25 testes aprovados, 0 falhas.
- O run 935 não recalculou o snapshot original.

## Snapshot original preservado
- Origem: run 930, artifact 13202372616.
- Manifesto: catalog-snapshot.sha256.
- 731 arquivos; 314.216.337 bytes.
- SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.

## Histórico cronológico anterior
Os registros abaixo descrevem o estado observado em cada data/execução; SHAs e comparações antigas são históricos, não representam o HEAD atual.

- Run 930: branch HEAD 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3; runner integration commit d6266bbe5679546e39a63e2724b1460c5465ed4f; baseline original.
- Run 931: HEAD 4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f; validação intermediária.
- Run 933: HEAD 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; validação do commit anterior ao alinhamento documental.
- Commit documental previamente validado pelo run 935: 1908b9adf242129fe85b20731f60ff203e8e7cf4. Esta entrada registra o HEAD-base; o commit atual desta correção é filho direto dele.

## Restrições mantidas
Nenhum catálogo ou fonte ativa foi alterado; nenhum consumidor, segredo, configuração de produção ou repositório de referência foi modificado; PRs permanecem draft/não mesclados; Fase B está em andamento.


---

## Retomada documental — 2026-11-03
- HEAD remoto confirmado de `develop/acervo-v2`: `3d8d143ae387f3340c1efb285fb3199393c25a99`.
- `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- Comparação: 45 commits à frente, 0 atrás; 15 arquivos reportados; zero alterações em `catalog/` e `sources/` nesta comparação.
- PR #1 e PR #2: ambos abertos, draft e não mesclados.
- Fase A continua encerrada. Fase B continua sem implementação iniciada; recebeu autorização explícita do responsável para o executor começar.
- Esta atualização apenas corrige a passagem operacional; não representa implementação, validação de código nem execução de workflow da Fase B.
- Não reutilizar os SHAs acima sem revalidar. Ver `NEXT_TASK.md` para o roteiro e os limites da execução.


## Execução da Fase B — 2026-11-03
### Commits
- `b7ff0b15b8713d944b8d857a7b822028ff18c9af`: contratos, parsers, staging e quatro entrypoints VOD.
- `6da90d372ce1c332317a7b429cfd1ff2745ef2d7`: expectativa correta para variante de áudio de episódio.
- `bb2dc858dedcec368e6311244c16888fd38a279c`: import path para scripts executados diretamente.
- `0b37cd73f8a0f52b3f4240ebdb31e92128bc03b8`: contagem correta da fixture M3U.
- `af4ee37ca4f538022b819b834226514a18028e4b`: parser do índice XMLTV local.
- `667a4529692de3807f3f544658de9f6c8e43dec8`: normalizador EPG explícito.
- `093921241ef57d8ae9f25dacf56a6fa88afb619a`: validação de integridade entre domínios.
- `638722caf78ffa5709bdf61d7fc2ebad661552c1`: import regex no validador.
- `98d77f89f6468c688fcd104473ecb9f78726677c`: construção VOD incremental por shard.
- `02b695f035de64ab68119915b88b22cbd7c8740a`: validação incremental via ijson.
- `9b869cd1705cd70550b87e7db95a8024496327af`: resolver de schemas relativo preservado.

### Runs e evidências
- Runs 960–965 falharam por expectativas de teste e importação de pacote; correções registradas nos commits correspondentes.
- Runs 976/977: construção integral do candidato passou; validação subsequente foi cancelada por atualização da branch.
- Runs 978/979: falha na resolução de referências relativas dos sub-schemas durante validação incremental; corrigida em `cf2148d`.
- Run 980 / `41590601634`: 40 testes offline aprovados, compilação Python aprovada, build integral do candidato aprovado; validação integral em andamento na última consulta.
- Artifact 13209354445 (run 976), ZIP SHA-256 `19d59e0b5a5ec3404b4d7182d156b9c50ded0525640d6ca5a34ec9772b26cdf9`, 69.908 bytes; incluía baseline, manifest e report, ainda sem os documentos candidatos completos. O workflow foi alterado para incluir a pasta integral do candidato em runs seguintes.

### Cobertura e limitações
- 13 schemas versionados.
- 40 testes aprovados; cinco domínios cobertos por fixtures/parsers e validação de integridade.
- Índice EPG local: 1.014 canais em quatro feeds normalizados. Sem payload XMLTV local de programas; programmes permanece vazio.
- Logos/assets: associações de canais e rádios; sem arquivos de imagem locais para validar MIME, conteúdo ou licença. Referências externas ficam não verificadas.
- Quatro entrypoints VOD existem; aplicação TMDB permanece em overlays/candidatos. Workflows online não foram executados, nem segredos foram alterados.
- Candidato é staging; nenhum arquivo de catálogo ativo foi substituído.

### Próximas ações
Concluir validação integral, comprovar idempotência, executar smoke tests CLI dos quatro scripts VOD, guardar o conjunto completo de artefatos e atualizar métricas reais/quarentena. Fase B continua EM ANDAMENTO; Fase C não iniciada.


## Atualização — commit `9b869cd1705cd70550b87e7db95a8024496327af`
- 40 testes na suíte: idempotência byte a byte do build com timestamp fixo e smoke test offline dos quatro entrypoints VOD.
- `.github/workflows/validate.yml` agora inclui a pasta completa do candidato no artefato.
- Run 983 / 41591165169: offline tests success; py_compile success; full candidate build success; candidate schema/integrity validation em andamento na última consulta.


## Histórico — validação integral Run 991 (2026-11-03; superado pelo Run 1002)

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


## Auditoria complementar Run 991 — histórico superado pelo Run 1002

Relatório detalhado persistido em `reports/phase-b-quality-audit-2026-11-03.md`, baseado no artefato integral do Run 991 (`13213490340`, SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`).

- VOD: o ID legado `series-my-name` afeta as identidades canônicas `series-meu-nome-e` (TMDB 2317) e `series-my-name` (TMDB 110356). A separação canônica foi preservada, mas os dois grupos compartilham as mesmas 16 URLs de episódio com `/2317/` e provider refs com `110356`; associação das fontes permanece pendente de confirmação. O `report.json` atual tem contadores, não inventário detalhado de conflitos/consolidações.
- Rádios: os 252 itens em quarentena são URLs de imagem em `stream_url`; em todos, `name` contém uma URL com aparência de stream. Há mais 2 registros com `stream_url` vazio/ausente e URL em `name`. Nenhum endpoint foi testado em rede.
- EPG: quatro feeds XMLTV indexam 1.014 canais (179/494/182/159; prioridades 5/25/30/40), além de duas fontes HTML. Os 60 mapeamentos ambíguos correspondem a múltiplos IDs CineHUB por canal/qualidade e permanecem sem associação forçada. Não há programação XMLTV local.
- Logos: 2.018 referências externas (1.748 canais, 270 rádios); 2.018 não verificadas, MIME desconhecido, zero arquivos locais de imagem e nenhuma licença registrada.
- Workflows: os quatro entrypoints e quatro workflows foram revisados. Os fluxos online de enriquecimento TMDB não foram executados. Nenhum workflow publica ou promove automaticamente.

O Run 991 permanece a evidência de validação integral de referência: 42 testes, 13 schemas, build integral, idempotência de 11 arquivos e integridade referencial aprovados. A Fase B continua aberta; não publicar, não mesclar e não iniciar a Fase C.


## Reconciliação e evidência — Run 1002 (2026-11-04)

Relatório consolidado: [reports/phase-b-quality-audit-2026-11-04.md](reports/phase-b-quality-audit-2026-11-04.md).

### VOD
O Run 1002 reporta `legacy_ids_reused_across_distinct_identities=0` e `identity_groups_affected_by_legacy_id_conflict=0`. A regra `my-name-2021-tmdb-correction` atualiza duas referências para TMDB 110356. As referências series/M-007, doramas/M-000 e series/M-013 contêm oito episódios e 16 linhas episódio/áudio cada; as 48 linhas representam 16 URLs únicas repetidas entre três referências. O merge une provider refs sem perda e preserva os originais. A antiga pendência VOD do Run 991 está resolvida.

### Rádios
257 itens de quarentena históricos, todos com proveniência: 255 `image_url_in_audio_stream` (253 resolvidos, 2 não resolvidos) e dois `missing_stream_url` (ambos resolvidos). Total recuperado: 255; streams adicionados: 255; logo candidates promovidos: 253; registros sem stream válido: 2. Os 255 continuam na contagem porque a resolução é anexada à ocorrência histórica, sem apagá-la. IDs não resolvidos: `radio-https-hts02-brascast-com-9758-live` e `radio-https-radiomec-stream-ebc-com-br-ebc-radiomec-playlist-m3u8`.

### EPG e logos
EPG: quatro feeds XMLTV (179/494/182/159 canais no índice local), duas fontes HTML, 78 mapeamentos (18 únicos, 60 ambíguos; 46 códigos Meu Guia, 12 aliases XMLTV, dois slugs Guia de TV), zero programas locais. A saúde local dos feeds é de 2026-10-26 e não foi atualizada no build offline. Permissões de redistribuição não comprovadas; não internalizar payload sem autorização.
Logos: 2.271 associações (1.748 canais, 523 rádios), 1.429 HTTP e 842 HTTPS, zero arquivos locais, MIME, hash de conteúdo ou licenças documentadas.

### CI e artefato
47 testes; 13 schemas; py_compile; build; integridade; idempotência de 11 arquivos; 787.175 streams/variantes com 787.175 IDs únicos. Artefato `13283645574`; ZIP SHA-256 `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`.

Nenhuma publicação, promoção de catálogo, OTA, alteração de consumidor/segredo ou merge. Fase C não iniciada. Aguardar aceite explícito.
