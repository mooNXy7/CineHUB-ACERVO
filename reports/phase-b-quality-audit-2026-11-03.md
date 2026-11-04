# CINEHUB-ACERVO V2 — Auditoria histórica da Fase B (Run 991)

> **HISTÓRICO SUPERADO:** este relatório descreve o candidato do Run 991, não o estado atual. A correção VOD, a classificação de rádio e as métricas foram reconciliadas no relatório vigente [phase-b-quality-audit-2026-11-04.md](phase-b-quality-audit-2026-11-04.md), baseado no Run 1002. Não usar os números abaixo como métricas atuais.

- Data da auditoria: 2026-11-03
- Branch: `develop/acervo-v2`
- HEAD documental de entrada: `e8806a65e3d252c5a2d917be2fb994d78a0c199e`
- Código validado de referência: `0ff93e98ca3a1f167e9d3e53f1882d962ff2384b`
- Run de referência: 991 / `41597580123`
- Artefato analisado: `13213490340`
- SHA-256 do ZIP: `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`
- Método: inspeção offline do artefato integral e dos arquivos-fonte da branch. Nenhuma sondagem de rede foi executada.

## 1. Identidade VOD

### Métricas reproduzidas do candidato

| Métrica | Resultado |
|---|---:|
| Entradas de índices | 56.248 |
| Identidades canônicas | 52.603 |
| Entradas consolidadas | 3.645 |
| Grupos com IDs legados repetidos | 3.598 |
| Grupos unidos por identidade de provedor entre IDs legados diferentes | 47 |
| IDs legados reutilizados entre identidades distintas | 1 |
| Grupos afetados pelo conflito | 2 |
| Registros VOD de saída | 52.603 |

### Conflito auditado: ID legado `series-my-name`

| Campo | Grupo A | Grupo B |
|---|---|---|
| ID canônico | `series-meu-nome-e` | `series-my-name` |
| Título | Meu Nome é | My Name |
| Tipo / ano | dorama / 2021 | dorama / 2021 |
| TMDB | 2317 | 110356 |
| IDs legados | `series-meu-nome-e`, `series-my-name` | `series-my-name` |
| Seções | `series`, `doramas` | `series` |
| Procedência | `series/M-007.json` e `doramas/M-000.json` | `series/M-013.json` |
| Episódios | 8 episódios, dub + leg | 8 episódios, dub + leg |
| Variantes de episódio | 16 | 16 |
| Provider refs por episódio | 33 | 24 |

Detalhes de procedência:
- Grupo A: `catalog/vod/index/series.json + catalog/vod/details/series/M-007.json`, SHA-256 de entrada `ac980d6c7f32d2afb66850d2f1cbd20a8cc82615015a0edae12fca6917cc2cd5`.
- Grupo A também preserva a referência alternativa `catalog/vod/index/doramas.json + catalog/vod/details/doramas/M-000.json`, SHA-256 `461f018a6d23b7a84ddd4d383c72e60eab6c92c03727643ebfd1954193a1da38`.
- Grupo B: `catalog/vod/index/series.json + catalog/vod/details/series/M-013.json`, SHA-256 `b1552d3b9b7c0faa2ab66bf9e6803372b9f7eb1fbba7da6bcc64977ecce6bd16`.

**Conclusão parcial:** o alocador preservou duas identidades canônicas distintas, não colapsando os dois TMDB IDs. O Grupo A conserva os dois IDs legados e a referência alternativa de índice/detalhe; ambos os grupos preservam procedência e 16 variantes cada.

**Pendência material:** as 16 URLs de variantes do Grupo A e as 16 do Grupo B são idênticas: oito em `mgeb.top` e oito em `nhdapi.com`, todas contendo `/2317/`. Ao mesmo tempo, os dois grupos contêm provider refs por episódio com referências `110356/1/1` até `110356/1/8`. Isso pode ser um identificador interno do provedor ou uma associação de fonte incorreta; o snapshot local não permite decidir. Não mesclar, excluir nem reatribuir essas variantes sem confirmação do provedor/dados externos.

### Persistência do relatório de identidade

O `report.json` do candidato registra os totais acima, mas não inclui uma lista de cada grupo consolidado nem uma matriz detalhada do ID legado reutilizado. Os próprios registros VOD preservam `legacy_ids`, `catalog_sections`, `identity_resolution.legacy_id_conflict`, procedência, `raw.alternate_indexes` e `raw.alternate_details`. Isso permite reconstruir parte do histórico por entidade, mas não substitui um inventário de conflitos/consolidações no relatório de build.

**Pendência de implementação:** ampliar o relatório de identidade gerado pelo build com a lista determinística de conflitos e consolidações, sem alterar a regra conservadora de identidade.

## 2. Rádios

A quarentena atual contém 252 itens, todos com motivo `image_url_in_audio_stream`. Os 252 itens apontam para 252 entidades distintas e cada entidade está sem variante de áudio válida no candidato.

| Classificação por extensão da URL rejeitada | Quantidade |
|---|---:|
| .png | 165 |
| .jpg | 49 |
| .ico | 21 |
| .jpeg | 7 |
| .webp | 6 |
| .svg | 4 |
| **Total** | **252** |

Outros achados:
- 134 hosts distintos nas URLs rejeitadas.
- Em todos os 252 registros, o campo original `name` contém uma URL HTTP(S) com aparência de endpoint de áudio, enquanto `stream_url` contém uma URL de imagem.
- O `source_id` original nesses objetos é `reference-catalog`; o arquivo de entrada é `catalog/radios/radios.json`.
- Há mais 2 registros com `stream_url` ausente/vazio e URL no campo `name`; eles não estão atualmente na quarentena.
- Portanto, 254 dos 1.026 registros não têm stream válido no candidato; 772 têm ao menos uma variante válida.
- Os 252 objetos em quarentena preservam o conteúdo bruto, mas não carregam um campo `provenance` próprio; a procedência está no registro de rádio associado.

**Conclusão:** o problema observado é principalmente um deslocamento/inversão de campos na origem de referência: URL de áudio em `name` e URL de imagem em `stream_url`. Não é possível afirmar disponibilidade dos endpoints sem sondagem de rede, nem inventar nomes de estações. Não corrigir por troca automática de campos. Os 2 registros sem `stream_url` também precisam ser classificados como incompletos em uma revisão futura.

**Pendência de implementação:** anexar procedência diretamente aos itens de quarentena e classificar os 2 registros sem stream, mantendo todos os dados brutos.

## 3. EPG

### Feeds e índice de canais

O registry contém seis fontes: quatro feeds XMLTV e duas fontes HTML de programação.

| Fonte | Formato | Prioridade | Canais no índice local |
|---|---|---:|---:|
| `pluto-br-xmltv` | XMLTV | 5 | 179 |
| `meuguia-br` | HTML | 10 | — |
| `guia-de-tv-br` | HTML | 20 | — |
| `brazil-tv-epg` | XMLTV | 25 | 494 |
| `iptv-epg-br` | XMLTV | 30 | 182 |
| `open-epg-br` | XMLTV | 40 | 159 |
| **Total XMLTV** | | | **1.014** |

Os 1.014 registros preservam `source_id`, `provider_channel_id`, `display_names`, `fetched_at` e procedência. Não há colisões de chave `(source_id, provider_channel_id)` no índice analisado. As prioridades estão no registry; a correspondência atual não as utiliza para desempatar canais.

### Mapeamentos

| Estado | Quantidade |
|---|---:|
| Matched | 18 |
| Ambiguous | 60 |
| Unmatched | 0 |
| **Total** | **78** |

Os 60 ambíguos se distribuem em 46 `meuguia_codes`, 12 `xmltv_aliases` e 2 `guiadetv_slugs`. A comparação usa o normalizador do projeto sobre nome e aliases dos 2.437 canais CineHUB. Os conflitos decorrem de múltiplos IDs CineHUB com o mesmo nome normalizado — em geral, um registro `br.*` e variantes `ch-*` por qualidade. O status ambíguo é conservador e não deve ser convertido em associação forçada.

| Tipo | Canal | Valor de origem | IDs CineHUB candidatos |
|---|---|---|---|
| meuguia_codes | A&E | MDO | br.a-e; ch-a-e-4k; ch-a-e-fhd; ch-a-e-hd; ch-a-e-sd |
| meuguia_codes | Animal Planet | APL | br.animal-planet; ch-animal-planet-4k; ch-animal-planet-fhd; ch-animal-planet-hd; ch-animal-planet-sd |
| meuguia_codes | AXN | AXN | br.axn; ch-axn-fhd; ch-axn-hd; ch-axn-sd |
| meuguia_codes | Band Sports | BSP | br.band-sports-hd; ch-band-sports-4k; ch-band-sports-fhd; ch-band-sports-sd |
| meuguia_codes | Cartoon Network | CAR | br.cartoon-network; ch-cartoon-network-4k; ch-cartoon-network-fhd; ch-cartoon-network-hd; ch-cartoon-network-sd |
| meuguia_codes | Canal Brasil | CBR | br.canal-brasil; ch-canal-brasil-hd; ch-canal-brasil-sd |
| meuguia_codes | Canal Off | OFF | br.canal-off; ch-canal-off-fhd; ch-canal-off-hd; ch-canal-off-sd |
| meuguia_codes | Cinemax | MNX | br.cinemax; ch-cinemax-fhd; ch-cinemax-hd; ch-cinemax-sd |
| meuguia_codes | Combate | 135 | br.combate; ch-combate-4k; ch-combate-fhd; ch-combate-hd; ch-combate-sd |
| meuguia_codes | Discovery Channel | DIS | br.discovery-channel; ch-discovery-channel-4k; ch-discovery-channel-fhd; ch-discovery-channel-hd; ch-discovery-channel-sd |
| meuguia_codes | Discovery Home & Health | HEA | br.discovery-home-health; ch-discovery-home-health-fhd; ch-discovery-home-health-hd; ch-discovery-home-health-sd |
| meuguia_codes | Discovery Kids | DIK | br.discovery-kids; ch-discovery-kids-4k; ch-discovery-kids-fhd; ch-discovery-kids-hd; ch-discovery-kids-sd |
| meuguia_codes | Discovery Science | DSC | br.discovery-science; ch-discovery-science-4k; ch-discovery-science-fhd; ch-discovery-science-hd; ch-discovery-science-sd |
| meuguia_codes | Discovery Turbo | DTU | br.discovery-turbo; ch-discovery-turbo-4k; ch-discovery-turbo-fhd; ch-discovery-turbo-hd; ch-discovery-turbo-sd |
| meuguia_codes | Discovery World | DIW | br.discovery-world; ch-discovery-world-4k; ch-discovery-world-fhd; ch-discovery-world-hd; ch-discovery-world-sd |
| meuguia_codes | E! | EET | br.e; ch-e-4k; ch-e-fhd; ch-e-hd; ch-e-sd |
| meuguia_codes | ESPN | ESP | br.espn; ch-espn-4k; ch-espn-fhd; ch-espn-hd; ch-espn-sd |
| meuguia_codes | ESPN 2 | ES2 | br.espn-2; ch-espn-2-4k; ch-espn-2-fhd; ch-espn-2-hd; ch-espn-2-sd |
| meuguia_codes | ESPN 3 | ES3 | br.espn-3; ch-espn-3-4k; ch-espn-3-fhd; ch-espn-3-hd; ch-espn-3-sd |
| meuguia_codes | ESPN 4 | ES4 | br.espn-4; ch-espn-4-4k; ch-espn-4-fhd; ch-espn-4-hd; ch-espn-4-sd |
| meuguia_codes | ESPN 5 | ES5 | br.espn-5; ch-espn-5-4k; ch-espn-5-fhd; ch-espn-5-hd; ch-espn-5-sd |
| meuguia_codes | GNT | GNT | br.gnt; ch-gnt-4k; ch-gnt-fhd; ch-gnt-hd; ch-gnt-sd |
| meuguia_codes | Globo RJ | GRD | br.globo-rj; ch-globo-rj-fhd; ch-globo-rj-hd; ch-globo-rj-sd |
| meuguia_codes | Globo SP | GRD | br.globo-sp; ch-globo-sp-fhd; ch-globo-sp-hd; ch-globo-sp-sd |
| meuguia_codes | GloboNews | GLN | br.globonews; ch-globonews-fhd; ch-globonews-hd; ch-globonews-sd |
| meuguia_codes | Gloob | GOB | br.gloob; ch-gloob-4k; ch-gloob-fhd; ch-gloob-hd; ch-gloob-sd |
| meuguia_codes | HBO | HBO | br.hbo; ch-hbo-4k; ch-hbo-fhd; ch-hbo-hd; ch-hbo-sd |
| meuguia_codes | HBO Family | HFA | br.hbo-family; ch-hbo-family-4k; ch-hbo-family-fhd; ch-hbo-family-hd; ch-hbo-family-sd |
| meuguia_codes | HBO Plus | HPL | br.hbo-plus; ch-hbo-plus-4k; ch-hbo-plus-fhd; ch-hbo-plus-hd; ch-hbo-plus-sd |
| meuguia_codes | History | HIS | br.history; ch-history-4k; ch-history-fhd; ch-history-hd; ch-history-sd |
| meuguia_codes | Megapix | MPX | br.megapix; ch-megapix-fhd; ch-megapix-hd; ch-megapix-sd |
| meuguia_codes | Multishow | MSH | br.multishow; ch-multishow-4k; ch-multishow-fhd; ch-multishow-hd; ch-multishow-sd |
| meuguia_codes | Premiere Clubes | 121 | br.premiere-clubes; ch-premiere-clubes-4k; ch-premiere-clubes-fhd; ch-premiere-clubes-hd; ch-premiere-clubes-sd |
| meuguia_codes | Space | SPA | br.space; ch-space-fhd; ch-space-hd; ch-space-sd |
| meuguia_codes | SporTV | SPO | br.sportv; ch-sportv-4k; ch-sportv-fhd; ch-sportv-hd; ch-sportv-sd |
| meuguia_codes | SporTV 2 | SP2 | br.sportv-2; ch-sportv-2-4k; ch-sportv-2-fhd; ch-sportv-2-hd; ch-sportv-2-sd |
| meuguia_codes | SporTV 3 | SP3 | br.sportv-3; ch-sportv-3-fhd; ch-sportv-3-hd; ch-sportv-3-sd |
| meuguia_codes | Studio Universal | HAL | br.studio-universal; ch-studio-universal-fhd; ch-studio-universal-hd; ch-studio-universal-sd |
| meuguia_codes | Telecine Action | TC2 | br.telecine-action; ch-telecine-action-4k; ch-telecine-action-fhd; ch-telecine-action-hd; ch-telecine-action-sd |
| meuguia_codes | Telecine Pipoca | TC4 | br.telecine-pipoca; ch-telecine-pipoca-4k; ch-telecine-pipoca-fhd; ch-telecine-pipoca-hd; ch-telecine-pipoca-sd |
| meuguia_codes | Telecine Premium | TC1 | br.telecine-premium; ch-telecine-premium-4k; ch-telecine-premium-fhd; ch-telecine-premium-hd; ch-telecine-premium-sd |
| meuguia_codes | TNT | TNT | br.tnt; ch-tnt-4k; ch-tnt-fhd; ch-tnt-hd; ch-tnt-sd |
| meuguia_codes | TNT Séries | TBS | br.tnt-series; ch-tnt-series-fhd; ch-tnt-series-hd; ch-tnt-series-sd |
| meuguia_codes | Viva | VIV | ch-viva-fhd; ch-viva-hd; ch-viva-sd |
| meuguia_codes | Arte 1 | BQ5 | br.arte-1; ch-arte-1-4k; ch-arte-1-fhd; ch-arte-1-hd; ch-arte-1-sd |
| meuguia_codes | TLC | TRV | br.tlc; ch-tlc-4k; ch-tlc-fhd; ch-tlc-hd; ch-tlc-sd |
| guiadetv_slugs | Terra Viva | terra-viva | br.terra-viva; ch-terra-viva-hd; ch-terra-viva-sd |
| guiadetv_slugs | X Sports | xsports | br.x-sports; ch-x-sports-fhd; ch-x-sports-hd; ch-x-sports-sd |
| xmltv_aliases | Adult Swim | truTV / Adult Swim HD BR | br.adult-swim; ch-adult-swim-4k; ch-adult-swim-fhd; ch-adult-swim-hd; ch-adult-swim-sd |
| xmltv_aliases | History | History Channel | br.history; ch-history-4k; ch-history-fhd; ch-history-hd; ch-history-sd |
| xmltv_aliases | SporTV 2 | SporTV2 | br.sportv-2; ch-sportv-2-4k; ch-sportv-2-fhd; ch-sportv-2-hd; ch-sportv-2-sd |
| xmltv_aliases | SporTV 3 | SporTV3 | br.sportv-3; ch-sportv-3-fhd; ch-sportv-3-hd; ch-sportv-3-sd |
| xmltv_aliases | GNT | GNT HD | br.gnt; ch-gnt-4k; ch-gnt-fhd; ch-gnt-hd; ch-gnt-sd |
| xmltv_aliases | Canal Brasil | Canal Brasil | br.canal-brasil; ch-canal-brasil-hd; ch-canal-brasil-sd |
| xmltv_aliases | Canal Off | Canal Off | br.canal-off; ch-canal-off-fhd; ch-canal-off-hd; ch-canal-off-sd |
| xmltv_aliases | AMC | AMC Brasil | br.amc; ch-amc-fhd; ch-amc-hd; ch-amc-sd |
| xmltv_aliases | CNN Brasil Money | CNN Brasil Money HD BR | br.cnn-brasil-money; ch-cnn-brasil-money-4k; ch-cnn-brasil-money-fhd; ch-cnn-brasil-money-hd; ch-cnn-brasil-money-sd |
| xmltv_aliases | TNT Novelas | TNT Novelas BR | br.tnt-novelas; ch-tnt-novelas-fhd; ch-tnt-novelas-hd; ch-tnt-novelas-sd |
| xmltv_aliases | Trace Brazuca | Trace Brasil HD BR | br.trace-brazuca; ch-trace-brazuca-4k; ch-trace-brazuca-fhd; ch-trace-brazuca-hd; ch-trace-brazuca-sd |
| xmltv_aliases | Record SP | RecordTV SP | br.record-sp; ch-record-sp-fhd; ch-record-sp-hd; ch-record-sp-sd |

**Limitação de associação:** o algoritmo atual compara nome normalizado com nomes/aliases CineHUB; não usa os códigos/slugs/aliases de origem nem os provider IDs dos quatro feeds para resolver esses 60 conflitos. Os IDs candidatos acima foram reconstruídos offline com o mesmo normalizador e devem permanecer como candidatos, não como decisões automáticas.

Não há payload XMLTV de programação local válido no snapshot: `epg-programmes.json` permanece com 0 registros. Não buscar nem inventar programação.

## 4. Logos e assets

| Estado do asset | Resultado |
|---|---:|
| Associações lógicas | 2.018 |
| Logos de canais | 1.748 |
| Logos de rádios | 270 |
| URLs externas HTTP | 1.420 |
| URLs externas HTTPS | 598 |
| Registros com status `unverified` | 2.018 |
| MIME conhecido/verificado | 0 |
| Conteúdo de imagem verificado | 0 |
| Arquivos locais de imagem | 0 |
| Licenças documentadas nos registros | 0 |

O diretório `catalog/logos` contém apenas `README.md` e dois `.gitkeep`; não contém bytes de imagem. Os registros preservam URL e procedência do catálogo de origem, mas isso comprova somente a associação lógica e a referência externa. Não comprova download, disponibilidade, MIME, conteúdo, dimensões nem licença.

**Conclusão:** assets não estão completos. Não marcar nenhuma imagem como armazenada ou verificada.

## 5. Entry points e workflows

### Quatro entrypoints VOD

- `scripts/enrich_vod_metadata.py`
- `scripts/apply_vod_metadata_patch.py`
- `scripts/suggest_vod_tmdb_matches.py`
- `scripts/apply_vod_tmdb_id_candidates.py`

A suíte contém teste de `--help` offline para os quatro executado a partir de diretório temporário fora da raiz do checkout. Há testes unitários adicionais para as operações de aplicação de patches/candidatos, incluindo rejeição de candidatos ambíguos. Os scripts resolvem imports adicionando a raiz do projeto ao `sys.path`.

### Workflows

| Workflow | Gatilho observado | Ação | Publica/promove? |
|---|---|---|---|
| `validate.yml` | push, pull request e manual | testes, compilação, baseline, build candidato, schemas/integridade, idempotência e artefato | Não |
| `update-catalog.yml` | manual | build isolado, validação e upload de artefato | Não |
| `enrich-vod-metadata.yml` | manual | consulta Supabase Edge Function/TMDB e gera patch de revisão | Não |
| `suggest-vod-tmdb-ids.yml` | manual | consulta Supabase Edge Function/TMDB e gera candidatos de revisão | Não |

Os dois workflows online não foram disparados nesta auditoria. Eles dependem de `SUPABASE_ANON_KEY` e de serviço externo; não foi inspecionado nem alterado valor de segredo. O token TMDB permanece no ambiente servidor do Supabase conforme a implementação. Nenhum workflow analisado promove candidato ou publica catálogo automaticamente.

## 6. Validação e integridade

O Run 991 de referência aprovou:
- 42 testes offline;
- 13 JSON Schemas;
- compilação Python;
- construção integral do candidato;
- duas construções comparadas byte a byte;
- idempotência de 11 arquivos;
- validação de integridade referencial e IDs/variantes;
- artefato integral.

Totais do candidato: VOD 52.603; canais 2.437; rádios 1.026; logos 2.018; EPG sources 6; EPG mappings 78; EPG channels 1.014; EPG programmes 0. A quarentena de rádio do Run 991 é 252, antes da inclusão futura dos 2 registros incompletos identificados nesta auditoria.

Hashes dos documentos candidatos e evidências integrais permanecem no artefato Run 991 indicado no cabeçalho. O baseline foi somente leitura; o build confirmou `catalog_mutated=false`, `active_catalogs_modified=false` e `reference_network_used=false`.

## 7. Resultado de aceite parcial

### Implementado e validado
- Normalização VOD com alocação determinística de IDs canônicos e preservação de IDs legados.
- Separação das duas identidades que compartilham `series-my-name`.
- Preservação de procedência, índices/detalhes alternativos, episódios e variantes no candidato.
- Quarentena preserva o bruto dos 252 streams com URL de imagem.
- Índice EPG de 1.014 canais com provider IDs e procedência; prioridades das seis fontes no registry.
- Referências de logo separadas de imagens locais; status não verificado.
- Quatro entrypoints e quatro workflows revisados; nenhum fluxo de promoção automática identificado.
- Build, schemas, testes e idempotência aprovados no Run 991.

### Implementado, mas depende de dados externos
- Confirmação de que os endpoints de rádio em `name` são streams ativos e identificação dos nomes corretos das estações.
- Confirmação da relação entre TMDB 2317, TMDB 110356, provider refs e URLs repetidas das variantes.
- Disponibilidade, MIME, conteúdo e licenças das URLs externas de logos.
- Payloads de programação dos feeds XMLTV/HTML.

### Em quarentena ou pendente de decisão
- 252 URLs de imagem indevidamente colocadas em `stream_url`, com aparente URL de áudio em `name`.
- 2 registros adicionais sem `stream_url`, também com URL em `name`.
- 60 mapeamentos EPG ambíguos; não forçar associação.
- Associação das variantes VOD dos dois grupos conflitantes até confirmação do provedor.

### Ainda não implementado / insuficiente
- Inventário determinístico de conflitos e consolidações dentro do `report.json` gerado pelo build.
- Procedência explícita em cada objeto de quarentena de rádio.
- Lista persistente de IDs candidatos nos próprios registros/relatório de mapeamentos EPG.
- Download/armazenamento e verificação de conteúdo/MIME/licença dos assets.
- Ingestão local autorizada de payload XMLTV válido.

## 8. Proteções e próximos bloqueios

Nenhuma alteração foi feita em `main`, consumidores, segredos ou catálogos ativos. Nenhum catálogo foi publicado, nenhum PR foi mesclado e a Fase C não foi iniciada.

A Fase B permanece **EM ANDAMENTO**. A base técnica do Run 991 está aprovada, mas os pontos de identidade VOD, quarentena de rádio, ambiguidade EPG e assets reais impedem aceite integral. A auditoria não autoriza resolver ambiguidades por inferência nem substituir dados externos ausentes.
