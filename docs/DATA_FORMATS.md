# Formatos de dados CineHUB ACERVO

## Canal
```json
{
  "id": "br.sbt",
  "name": "SBT",
  "group": "TV Aberta",
  "logo_url": "https://exemplo.invalid/sbt.png",
  "epg_id": "sbt.br",
  "sources": [{"url": "https://exemplo.invalid/live.m3u8", "priority": 1, "source_id": "fonte-exemplo"}]
}
```

IDs são estáveis e independem da URL de stream. URLs de exemplo são inválidas de propósito.

## Rádio
```json
{"id":"radio.exemplo","name":"Rádio Exemplo","stream_url":"https://exemplo.invalid/radio","logo_url":null,"genre":"Pop","source_id":"fonte-exemplo"}
```

## VOD
Separar filmes, séries, animes e doramas. Guardar metadados, identificadores externos, imagens e fontes autorizadas. Séries devem manter temporadas e episódios hierarquizados; não achatar episódios como filmes independentes.

## M3U
O importador deve interpretar EXTINF, tvg-id, tvg-name, tvg-logo, group-title e URL. Validar cada item, normalizar nomes e preservar múltiplas fontes. Não colocar tokens ou credenciais em URLs versionadas.
