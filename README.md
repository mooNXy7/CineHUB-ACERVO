# CineHUB ACERVO

Repositório central de dados do CineHUB TV e CineHUB Mobile. Mantém fontes, índices e metadados versionados de forma independente dos aplicativos.

> **Estado inicial:** estrutura de acervo e automação. As fontes de terceiros precisam ser validadas antes de entrar em produção; este repositório não presume que uma URL esteja funcional ou que haja autorização para redistribuir um conteúdo.

## Objetivos

- Catálogo compartilhado para TV e Mobile, sem duplicar a lógica dos apps.
- Canais ao vivo com fontes alternativas, grupos, logos e identificadores estáveis.
- Filmes, séries, animes e doramas por índices e metadados leves.
- Rádios com nome, stream, estilo e logo.
- Fontes M3U/M3U8, EPG/XMLTV e catálogos externos com origem e licença documentadas.
- Normalização de nomes, logos, grupos e duplicatas.
- Atualizações agendadas com validação, relatório de falhas e publicação apenas de resultados válidos.
- Compatibilidade retroativa: manter os formatos consumidos pelos apps até cada integração ser testada.

## Estrutura

```text
catalog/
  channels/       catálogo normalizado de canais
  radios/         catálogo de rádios
  vod/            índices de filmes, séries, animes e doramas
  epg/            fontes e configuração de programação
  logos/          logos próprios ou redistribuíveis, organizados por tipo
sources/
  sources.json    registro de fontes, categoria, prioridade e última verificação
  m3u/            listas de origem e listas consolidadas geradas
normalizer/
  rules.json      aliases, regras de nomes e grupos
scripts/
  update_catalog.py
  normalize_catalog.py
  validate_catalog.py
  check_sources.py
tests/
.github/workflows/
  update-catalog.yml
  validate.yml
docs/
  DATA_FORMATS.md
  SOURCES_POLICY.md
reports/          relatórios automáticos; sem segredos
```

## Formatos

- Catálogo JSON versionado para TV e Mobile.
- M3U/M3U8 preservados quando a fonte permitir redistribuição; não embutir listas privadas.
- Rádio: `id`, `name`, `stream_url`, `logo_url`, `genre`, `source_id`.
- Canal: `id`, `name`, `group`, `logo_url`, `epg_id`, `sources[]`.
- VOD: metadados e identificadores públicos; URLs de reprodução só de fontes autorizadas e documentadas.

## Atualização automática

O GitHub Actions executará a rotina agendada e manualmente. A rotina deve:
1. Baixar fontes com timeout e limite de tamanho.
2. Validar HTTP, formato e conteúdo antes de processar.
3. Normalizar nomes e identificadores sem apagar dados válidos.
4. Detectar duplicatas, links mortos e alterações bruscas de volume.
5. Preservar a última versão válida se uma fonte falhar.
6. Gerar relatório e artefatos; publicar alterações somente após os testes.
7. Evitar commits quando não houver mudanças.

**Segurança:** nunca armazenar tokens, senhas ou URLs privadas com credenciais. Não usar fontes que exijam contornar DRM, autenticação ou controles de acesso.

## Relação com Saimo TV

A estrutura de referência foi estudada a partir de [SaimoTV-Android](https://github.com/gabrielsaimo/SaimoTV-Android) e do repositório de catálogo [SaimoPlayer](https://github.com/gabrielsaimo/SaimoPlayer). A organização é inspirada nos conceitos de catálogo compartilhado, dados VOD, rádios e scripts de manutenção; este repositório é próprio do CineHUB e não copia automaticamente dados ou credenciais.

## Status

Versão de estrutura: **0.1.0**. A integração com os aplicativos CineHUB TV/Mobile deve ser feita por URLs estáveis e validada em cada app antes de trocar a fonte atual.
