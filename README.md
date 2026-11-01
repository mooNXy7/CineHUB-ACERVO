# CineHUB ACERVO

Repositório de dados do **CineHUB TV**. Nesta fase, o ACERVO atende exclusivamente à versão TV; CineHUB Mobile e CineHUB Web mantêm seus próprios acervos e não fazem parte desta integração.

> **Estado do projeto:** estrutura de catálogo e automações em auditoria. Fontes de terceiros precisam passar por validação técnica e revisão de permissão antes de serem consideradas prontas para produção. Uma URL cadastrada não é garantia de reprodução nem de autorização para redistribuição.

## Escopo desta fase

- Catálogo de canais ao vivo com fontes alternativas, grupos, logos e identificadores estáveis.
- Filmes, séries, animes e doramas por índices e metadados leves.
- Rádios com nome, stream, estilo e logo.
- Fontes M3U/M3U8, EPG/XMLTV e catálogos externos com proveniência e permissões documentadas.
- Normalização de nomes, metadados e grupos, sem apagar registros ou alterar identificadores e fontes válidas.
- Atualizações automatizadas com validação, relatórios e preservação da última versão válida em caso de falha.
- Compatibilidade com o consumidor CineHUB TV, mantendo formatos existentes até a integração ser testada.

## Fora do escopo desta fase

- Não integrar nem alterar os acervos próprios do CineHUB Mobile ou CineHUB Web.
- Não publicar OTA, release ou alteração nos aplicativos sem autorização explícita.
- Não importar credenciais, cookies, tokens privados, cabeçalhos de autenticação ou material protegido por DRM.

## Estrutura

```text
catalog/
  channels/       catálogo de canais
  radios/         catálogo de rádios
  vod/            índices de filmes, séries, animes e doramas
  epg/            fontes e configuração de programação
  logos/          logos próprios ou redistribuíveis
sources/
  sources.json    registro de fontes, categoria, prioridade e proveniência
  m3u/            listas de origem e listas consolidadas permitidas
normalizer/
  rules.json      aliases e regras de nomes/grupos
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
reports/          relatórios automáticos sem segredos
```

## Formatos e compatibilidade

- JSON versionado para o consumidor CineHUB TV.
- M3U/M3U8 somente quando a fonte permitir redistribuição.
- Rádio: `id`, `name`, `stream_url`, `logo_url`, `genre`, `source_id`.
- Canal: `id`, `name`, `group`, `logo_url`, `epg_id`, `sources[]`.
- VOD: metadados e identificadores públicos; URLs de reprodução apenas de fontes autorizadas e documentadas.

## Atualização automática

O GitHub Actions executa rotinas agendadas e manuais para:

1. Buscar fontes registradas com timeout e limite de tamanho.
2. Validar HTTP, formato, conteúdo e limites de qualidade.
3. Normalizar textos e identificadores sem apagar dados válidos.
4. Detectar duplicatas, links indisponíveis e alterações bruscas de volume.
5. Preservar a última versão válida quando uma fonte falhar.
6. Gerar relatórios e executar testes antes de gravar alterações.
7. Evitar commits quando não houver mudanças reais.

## Segurança, proveniência e identidade

O projeto utiliza referências autorizadas como insumo técnico, mas mantém a identidade, nomenclatura e experiência CineHUB. Dados importados são submetidos a filtros de segurança, compatibilidade e revisão de permissões. Não são importados segredos, credenciais, cookies, mecanismos de autenticação ou fontes que exijam contornar DRM ou controles de acesso.

## Status

A auditoria, normalização e validação estão em andamento em branches de trabalho isolados. A branch `main` não deve ser considerada atualizada com as alterações em revisão. Nenhuma publicação OTA ou alteração nos aplicativos está autorizada por esta documentação.
