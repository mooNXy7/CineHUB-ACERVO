# Contratos canônicos CineHUB ACERVO

Schemas JSON Schema Draft 2020-12 versionados. Os contratos preservam extensões e campos de origem em `raw` e aceitam propriedades adicionais para evitar perda de informação durante a migração.

- `common/`: provenance, fontes, variantes de transmissão e assets.
- `vod/v1.schema.json`: filmes, séries, animes, doramas, temporadas e episódios.
- `channels/v1.schema.json`: canais, aliases, streams e relações EPG.
- `radios/v1.schema.json`: estações e variantes de áudio.
- `logos/v1.schema.json`: assets referenciados e associações.
- `epg/`: fontes, mapeamentos e programas.

Mudanças incompatíveis devem criar nova versão; não editar silenciosamente o contrato publicado. Os schemas descrevem candidatos canônicos, não autorizam promoção de catálogo.
