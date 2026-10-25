# Relatório acionável de qualidade do catálogo

O comando `python scripts/catalog_quality_report.py` produz um JSON somente de leitura para priorizar correções no ACERVO.

## O que ele lista

- Canais sem logo, grupo, associação `epg_id` ou lista de fontes.
- Rádios sem logo, gênero ou URL de stream.
- Filmes, séries, animes e doramas sem poster, ano, gêneros ou referência de detalhe.
- IDs duplicados dentro do mesmo catálogo (canais, rádios ou seção VOD).
- Candidatos a títulos duplicados após normalização de acentos e pontuação.

Os itens são identificados por ID, título e categoria. **URLs de stream, logo e fontes não são incluídas no relatório**, evitando vazar endpoints em artefatos de CI.

## Como interpretar

- É um inventário de lacunas estruturais, não uma validação de reprodução nem uma prova de que um logo está acessível.
- Títulos normalizados iguais são apenas candidatos a revisão. Remakes, versões, temporadas e obras com o mesmo nome podem ser legítimos; não deduplicar automaticamente com base apenas no título.
- Campos ausentes não são preenchidos por adivinhação. Enriquecimento deve usar uma fonte identificável e correspondência de confiança alta (título, ano e tipo), mantendo proveniência.
- As listas de exemplos são limitadas por regra para manter os artefatos de CI manejáveis; as contagens refletem o total encontrado, e `items_included`/`groups_included` indicam quantos exemplos foram incluídos. O campo `truncated` sinaliza quando há resultados omitidos.
- O relatório não faz chamadas de rede e não modifica nenhum arquivo do catálogo.

O workflow `Validate catalog` publica o relatório junto às auditorias de integridade e cobertura como artefato de CI por 14 dias.
