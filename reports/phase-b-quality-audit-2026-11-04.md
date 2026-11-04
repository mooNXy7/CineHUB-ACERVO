# CINEHUB-ACERVO V2 — Reconciliação da Fase B (Run 1002)

- Data: 2026-11-04
- Repositório: `mooNXy7/CineHUB-ACERVO`
- Branch: `develop/acervo-v2`
- HEAD analisado: `5e2150f3c0f48075edacb56b70111304f797d25d`
- Run: [1002 / 41744148492](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41744148492)
- Job: `validate`, ID `126292819734`, conclusão `success`
- Artefato: [acervo-v2-validation-5e2150f3c0f48075edacb56b70111304f797d25d](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41744148492/artifacts/13283645574)
- Artifact ID: `13283645574`; tamanho: 73.111.225 bytes; 15 arquivos; retenção configurada: 14 dias.
- SHA-256 do ZIP: `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`
- Método: inspeção offline do artefato real, dos shards/índices da branch, dos importadores, dos workflows e dos documentos normativos. O build do Run 1002 não fez chamadas à rede de referência.

## Resultado executivo

A base de build e integridade está aprovada. A auditoria VOD anterior estava desatualizada: o conflito de ID legado foi corrigido no candidato. A quarentena de rádios mantém histórico de 257 ocorrências, das quais 255 têm resolução documentada e duas continuam sem stream válido. EPG e logos permanecem incompletos por motivos explicitados abaixo; não foram inventados mapeamentos nem baixados assets sem licença comprovada.

**Estado da Fase B: EM ANDAMENTO, pronta para avaliação de aceite somente com as limitações e classificações deste relatório. Não é declaração de 100% do CineHUB-ACERVO.**

## 1. VOD — correção de identidade confirmada

### Métricas do candidato

| Métrica | Run 1002 |
|---|---:|
| Entradas de índices | 56.248 |
| Identidades canônicas | 52.602 |
| Grupos consolidados | 3.645 |
| Entradas de índice consolidadas | 3.646 |
| Grupos com IDs legados repetidos | 3.599 |
| Grupos unidos por identidade de provedor entre IDs legados diferentes | 47 |
| IDs legados reutilizados entre identidades distintas | **0** |
| Grupos afetados por conflito de ID legado | **0** |
| Referências de índice corrigidas pela regra explícita | 2 |
| Registros VOD no candidato | 52.602 |

### My Name (2021) — trilha da correção

O Run 1002 aplica a regra `my-name-2021-tmdb-correction` somente às duas referências CineHUB com tipo dorama, ano 2021, TMDB legado 2317 e os IDs legados especificados. A identidade canônica é `series-my-name`, título `My Name`, ano 2021 e TMDB `110356`, com oito episódios.

A referência fixada do SaimoPlayer em commit `41b2c62769fdf049165b2fedb19cc70473fe2c2d` associa TMDB 110356 a My Name (2021, oito episódios) e TMDB 2317 a Meu Nome é Earl (2005). A correção mantém os valores originais no material bruto e no relatório de auditoria.

| Referência | Arquivo de detalhe | ID legado | TMDB de origem |
|---|---|---|---:|
| Série | `series/M-007.json` | `series-meu-nome-e` | 2317 |
| Dorama | `doramas/M-000.json` | `series-my-name` | 2317 |
| Série canônica já existente | `series/M-013.json` | `series-my-name` | 110356 |

A inspeção dos três registros de origem encontrou, em cada um, uma temporada, oito números de episódio, 16 linhas `episódio × áudio` (dub/leg) e 16 URLs distintas. No conjunto dos três registros há 48 linhas de variantes, mas somente 16 URLs únicas — são variantes repetidas entre as referências, não 48 streams independentes. Foram encontrados 82 registros brutos de provider refs, dos quais 33 são distintos no conjunto.

O merge do importador agrupa episódios por temporada, número e áudio; une as fontes por chave de variante e agrega provider refs sem descartar referências diferentes. Assim, a consolidação preserva os oito episódios, as 16 variantes únicas, as referências de provedor distintas e os registros brutos alternativos. O relatório do candidato confirma zero conflitos de ID legado após a aplicação da regra.

Limite: a validação comprova integridade estrutural, identidade e preservação das referências; não é um teste de disponibilidade ao vivo dos endpoints dos provedores.

## 2. Rádios — classificação individual e reconciliação da contagem

O candidato contém 1.026 rádios e 257 itens históricos na quarentena. Todos os 257 itens têm procedência registrada. A classificação correta é:

| Motivo original | Total | Resolvidos pela referência | Sem resolução |
|---|---:|---:|---:|
| `image_url_in_audio_stream` | 255 | 253 | 2 |
| `missing_stream_url` | 2 | 2 | 0 |
| **Total** | **257** | **255** | **2** |

A recuperação fixada teve 255 registros esperados e aplicados, adicionou 255 streams, promoveu 253 candidatos de logo, resolveu 255 itens históricos de quarentena, não deixou correspondências de referência sem aplicação e não encontrou IDs de correspondência inválidos.

### Por que os 255 recuperados ainda aparecem na quarentena?

A quarentena é uma trilha histórica e não uma contagem exclusiva de falhas abertas. O importador não apaga o item original: acrescenta `resolution.status = recovered_from_pinned_reference`, a referência, o commit e o stream recuperado. Por isso o total histórico continua 257; a situação operacional atual é 255 resolvidos e dois sem stream válido. O candidato tem 1.024 registros com streams e dois sem streams válidos.

### Registro por item e procedência

O arquivo `acervo-v2-candidate/radios.json` dentro do artefato contém os 257 objetos individualizados com `entity_id`, `source_id`, `reason`, `provenance`, `raw` e, quando aplicável, `resolution`. O registro de rádio correspondente preserva o nome/URL original; os 255 registros recuperados também carregam `reference_recovery`, com URL original, URL recuperada, linha da referência e método de correspondência.

- Fonte original: `catalog/radios/radios.json`, registrada como `catalog-existing`.
- Referência de recuperação: `sources/reference/radio-recovery.json`, fonte `reference-radio-catalog`.
- Referência externa fixada: `fki1976/SaimoPlayer`, commit `41b2c62769fdf049165b2fedb19cc70473fe2c2d`, arquivo `vod/radios.txt`.
- Estratégia: comparação exata normalizada por casefold e remoção de barra final; cada correspondência exigiu `match_count = 1`.
- A recuperação preserva o campo bruto original; não substitui nem elimina silenciosamente o dado de origem.

### Dois casos ainda sem resolução

| ID | URL de stream que aparece no campo original `name` | Situação |
|---|---|---|
| `radio-https-hts02-brascast-com-9758-live` | `https://hts02.brascast.com:9758/live` | Sem correspondência na referência fixada; stream não validado |
| `radio-https-radiomec-stream-ebc-com-br-ebc-radiomec-playlist-m3u8` | `https://radiomec-stream.ebc.com.br/ebc/radiomec/playlist.m3u8` | Sem correspondência na referência fixada; stream não validado |

Os dois itens continuam com motivo `image_url_in_audio_stream`: o campo `stream_url` contém uma URL de imagem/proxy de imagem e o campo `name` contém a URL com aparência de stream. Não foram aprovados apenas por parecerem URLs de áudio; exigem fonte independente ou teste de stream autorizado.

A validação do Run 1002 foi offline. Não houve teste de conectividade dos 255 streams recuperados.

## 3. EPG — fontes, aliases e programação

### Fontes registradas

O registro possui quatro feeds XMLTV e duas fontes HTML. O índice local de canais conserva 1.014 registros XMLTV, 1.014 pares únicos fonte/ID de provedor, cinco IDs de provedor reutilizados entre feeds e 174 nomes normalizados reutilizados entre feeds.

| Fonte | Formato | Prioridade | Canais indexados no snapshot |
|---|---|---:|---:|
| Pluto TV Brasil | XMLTV | 5 | 179 |
| Meu Guia Brasil | HTML | 10 | 0 |
| Guia de TV Brasil | HTML | 20 | 0 |
| EPG Brasil — catálogo combinado | XMLTV | 25 | 494 |
| IPTV EPG Brasil | XMLTV | 30 | 182 |
| Open EPG Brasil | XMLTV | 40 | 159 |

O arquivo `catalog/epg/health.json` contém a última checagem local em 2026-10-26. O Run 1002 foi offline e não atualizou essa saúde; portanto os estados HTTP registrados ali são históricos, não prova de disponibilidade em 2026-11-04.

### 78 mapeamentos

- 18 correspondências com um único canal candidato.
- 60 mapeamentos ambíguos, preservados sem associação forçada.
- 0 sem correspondência.

Distribuição dos 60 ambíguos: 46 `meuguia_codes`, 12 `xmltv_aliases` e 2 `guiadetv_slugs`. Os candidatos incluem normalmente um ID base `br.*` e variantes `ch-*` por qualidade. Nome/código/alias sozinho não resolve qual variante deve receber a grade. A lista completa de IDs, valores e candidatos está em `quality_audit.epg.mappings.ambiguous` dentro de `acervo-v2-candidate/report.json`, no artefato.

### Disponibilidade pública e limite de internalização

A página atual do IPTV-EPG.org lista o feed brasileiro com 138 canais e 26.843 programas, atualizado recentemente: https://iptv-epg.org/guides. A página do Open-EPG lista Brazil 3 com 98 canais e data 19-10-2026, e avisa sobre uma migração ampla da plataforma: https://www.open-epg.com/app/epgguide.php. Esses sinais indicam feeds públicos disponíveis, mas não concedem por si só licença de redistribuição.

A fonte Pluto é especialmente restrita: os termos oficiais da Pluto TV proíbem reproduzir/distribuir o conteúdo sem consentimento prévio expresso por escrito: https://legal.paramount.com/br/pt-br/plutotv/terms-of-use?r=pluto.tv. Para o feed BrazilTV/EPG-Scrapper-BR e para IPTV-EPG.org/Open-EPG, não foi encontrada no material auditado uma autorização explícita que permita internalizar e redistribuir o payload completo. A ausência de uma licença encontrada não prova que não exista; significa que não há evidência suficiente para autorizar essa cópia.

A política atual de `catalog/epg/sources.json` manda publicar URLs e metadados compactos de canais, sem espelhar payload XMLTV completo. Isso mantém o catálogo dependente da disponibilidade externa para a programação. O parser XMLTV existe e tem teste offline, mas o candidato continua com **zero programas locais**. Para cumprir a independência operacional, será necessária uma fonte/termo que permita internalização ou uma decisão autorizada sobre um feed próprio/licenciado. Não declarar EPG concluído.

## 4. Logos e assets

| Propriedade | Resultado |
|---|---:|
| Associações lógicas | 2.271 |
| Logos de canais | 1.748 |
| Logos de rádios | 523 |
| URLs externas | 2.271 |
| HTTP | 1.429 |
| HTTPS | 842 |
| Arquivos locais de imagem | 0 |
| MIME presente/verificado | 0 / 0 |
| Hash de conteúdo presente/verificado | 0 / 0 |
| Licenças documentadas | 0 |

Todas as 2.271 associações estão com status `unverified`. Os 253 novos logos de rádio são candidatos promovidos a partir da referência de recuperação, não imagens locais baixadas ou verificadas. A árvore `catalog/logos` contém somente README e marcadores de diretório; nenhum byte de imagem.

A arquitetura prevê assets com ID, entidade associada, URL/caminho, MIME, dimensões, fonte, estado, validação e procedência. O blueprint prevê `storage/raw/` como configuração/manifestos para blobs no storage escolhido; a escolha de backend deve vir depois do inventário real de Cloudflare/Supabase. Nenhum R2, bucket ou Supabase Storage é presumido como existente.

A referência Fki usada no Run 1002 fornece URLs/candidatos de logo no arquivo de rádios, mas o snapshot registra `license_file_found: false`; isso não comprova armazenamento binário próprio. A documentação atual do ACERVO permite referenciar URLs externas sem download. Portanto, o estado correto é associação lógica externa, sem assets completos. A internalização depende de permissão/licença e da confirmação da camada de armazenamento.

## 5. Entry points VOD e workflows

Os quatro scripts existem e foram revisados:
- `scripts/enrich_vod_metadata.py`
- `scripts/apply_vod_metadata_patch.py`
- `scripts/suggest_vod_tmdb_matches.py`
- `scripts/apply_vod_tmdb_id_candidates.py`

Os quatro workflows relevantes foram inspecionados:
- `.github/workflows/enrich-vod-metadata.yml`
- `.github/workflows/suggest-vod-tmdb-ids.yml`
- `.github/workflows/update-catalog.yml`
- `.github/workflows/validate.yml`

A suíte executou o teste offline de CLI/help dos quatro entrypoints. Os workflows TMDB online exigem `SUPABASE_ANON_KEY` e chamam a função proxy existente no Supabase; seus resultados são patches/overlays e artefatos de staging. Não foram disparados nesta auditoria e nenhum segredo foi lido ou alterado. O workflow `update-catalog` constrói candidato isolado a partir dos dados locais; `validate` executa validação offline. Nenhum dos quatro workflows revisados promove ou publica automaticamente o catálogo.

Limite: CLI/help e revisão estática dos workflows não substituem execução online dos fluxos TMDB. Essa execução permanece separada, sem alterar segredos ou serviços.

## 6. Validação integral — Run 1002

O job `validate` concluiu com sucesso:
- 47 testes offline aprovados (`Ran 47 tests`, 0 falhas).
- 13 JSON Schemas validados.
- Compilação Python dos scripts e importadores aprovada.
- Build integral do candidato aprovado.
- Idempotência byte a byte: 11 arquivos comparados, hashes iguais nas duas construções.
- Integridade do candidato: 52.602 VOD, 2.437 canais, 1.026 rádios, 1.014 canais EPG, 78 mapeamentos (18 matched/60 ambiguous), 2.271 logos, 0 programas XMLTV locais, 257 itens históricos de quarentena e 787.175 streams/variantes de episódio com 787.175 IDs únicos.
- `active_catalogs_modified=false`; `reference_network_used=false`.

### SHA-256 dos documentos candidatos

| Documento | SHA-256 |
|---|---|
| `vod.json` | `a22f409307c9528e7d9150eb55de528ee5c51ac5fbcecce252db14441675d16c` |
| `channels.json` | `4704295fee3311621cc3abe57f6fb38080ce395ac01b33038658c0e9b0f2c57e` |
| `radios.json` | `3a2f1e6ca4afc4ae26a62b8fb1e541da00d01f2fd2843f0762114196fe71dafd` |
| `logos.json` | `ac266a06ad026ccda0db74611c784347e39cbf641d5d4a666cabfb0cc2eb1950` |
| `sources.json` | `31090b070bdbc2de2f1a4d70522be7cb9bf9d57f7b4c95d1f766e331c9e105e1` |
| `epg-sources.json` | `73fc11ff9f01c2d3f4357a0ab712f14943d821974a0ff08d1c4826b09959bb11` |
| `epg-mappings.json` | `5380a7e921f61a842a8cd31ecbe4f9e06bdc1abbbb992d8ffdd733ce98fd0a62` |
| `epg-channels.json` | `b3229c16330f37c1def406870527b99288d97adf9417853fae17931a0d66af30` |
| `epg-programmes.json` | `056e69cd15a3683cfd7517b63742a851deaef37673e2703935a0e872afebda2d` |

## 7. Estado de aceite e proteções

### Implementado e validado
- Correção explícita de identidade My Name (2021) aplicada a duas referências.
- Consolidação VOD determinística, preservação de variantes, provider refs e dados brutos alternativos.
- Recuperação exata de 255 rádios, com procedência e resolução anexadas aos itens históricos de quarentena.
- Classificação individual dos 257 itens preservada no candidato.
- 60 mapeamentos EPG ambíguos mantidos sem associação forçada.
- 2.271 associações de logos auditadas e separadas de arquivos locais.
- Quatro entrypoints e workflows VOD revisados.
- Testes, schemas, compilação, build, integridade e idempotência aprovados.

### Formalmente classificados, ainda sem conclusão funcional
- Dois rádios sem correspondência na referência fixada e sem stream validado.
- 60 mapeamentos EPG ambíguos; não há critério único que distinga os canais-base das variantes de qualidade.
- Programação EPG local ausente; política atual não espelha payload XMLTV e permissões de redistribuição não estão comprovadas para as fontes avaliadas.
- 2.271 logos são referências externas não verificadas; nenhum arquivo local, MIME, hash de conteúdo ou licença está comprovado.
- Execução online dos fluxos TMDB não realizada; exige segredo já existente, sem necessidade de alterá-lo.

### Proteções verificadas
- Branch de trabalho: `develop/acervo-v2`; HEAD analisado: `5e2150f3c0f48075edacb56b70111304f797d25d`.
- `main` observado: `106dbb8aafa87cc14162c147732a7e185e185edb`; não alterado.
- PR #1 e PR #2 permanecem abertos, draft e não mesclados.
- Nenhum consumidor TV/Mobile/Web/PLAYER foi alterado.
- Nenhum catálogo ativo foi publicado/promovido; nenhum OTA; nenhum segredo alterado; Fase C não iniciada.

**Conclusão:** Run 1002 remove a antiga pendência de conflito VOD, e a base técnica do candidato passa na validação integral. As limitações remanescentes estão individualizadas e justificadas acima. A Fase B permanece aberta até apresentação e aprovação explícita do responsável; não declarar 100% nem iniciar a Fase C.
