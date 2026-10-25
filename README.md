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

## Integração e proveniência

A estrutura de dados foi adaptada a partir de um repositório de referência autorizado pelo mantenedor. O projeto CineHUB mantém nomenclatura, identidade, formatos e rotinas próprios. Dados importados passam por validação técnica e revisão de permissão antes de serem considerados prontos para produção.

## Enriquecimento de metadados VOD

O plano para completar metadados ausentes de filmes, séries, animes e doramas está em [`docs/VOD_METADATA_ENRICHMENT.md`](docs/VOD_METADATA_ENRICHMENT.md). O fluxo previsto começa com dry-run e revisão de correspondências; não sobrescreve metadados válidos, não altera fontes de reprodução e exige provedor/termos aprovados antes de consultar dados em lote.

## Auditoria de qualidade

A validação do pull request executa duas auditorias somente de leitura e publica os relatórios JSON como artefato do GitHub Actions por 14 dias:

- `audit-catalog.json`: integridade de IDs, contagens, referências a detalhes, campos de metadados ausentes e URLs estruturalmente suspeitas.
- `stream-epg-coverage.json`: cobertura estrutural de referências de streams e associações de EPG.

Esses relatórios não fazem requisições de rede e não modificam os catálogos. Uma URL presente não comprova que o stream reproduz; uma associação EPG não comprova programação atual. Os relatórios podem conter nomes/IDs públicos de registros para facilitar revisão, mas não devem conter credenciais.

Para executar localmente:

```bash
python scripts/audit_catalog.py > audit-catalog.json
python scripts/audit_stream_epg_coverage.py > stream-epg-coverage.json
python -m unittest discover -s tests -v
python scripts/validate_catalog.py
```

## Status

Versão de estrutura: **0.1.0**. A integração com os aplicativos CineHUB TV/Mobile deve ser feita por URLs estáveis e validada em cada app antes de trocar a fonte atual.
