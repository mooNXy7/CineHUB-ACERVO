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


## Enriquecimento VOD via Supabase (somente revisão)

O ACERVO reutiliza a Edge Function existente `cinehub-catalog` do projeto Supabase CINEHUB para consultas ao TMDB. O token privado `TMDB_TOKEN` permanece no ambiente do Supabase; ele não deve ser copiado para o GitHub nem para relatórios.

Para executar os workflows manuais de revisão no GitHub Actions, configure o segredo `SUPABASE_ANON_KEY` com a chave pública (anon/publishable) do projeto. Não use a chave `service_role` nesse segredo. A URL da função já está definida nos workflows e pode ser alterada caso a função seja migrada.

- `Build VOD metadata review patch`: consulta IDs TMDB que já existem no catálogo e sugere pôster, ano e gêneros somente quando a identidade bate.
- `Build VOD TMDB ID review candidates`: procura candidatos para registros sem ID TMDB, usando título normalizado exato e conferência de ano quando disponível.
- Ambos geram artefatos de revisão; nenhum deles altera os JSONs do catálogo ou associa IDs automaticamente.
- Antes de aceitar candidatos, confirme título, ano, tipo de mídia e identidade (remakes/edições diferentes podem compartilhar nomes).

O endpoint `cinehub-catalog` precisa estar acessível pelo GitHub Actions. Se o segredo `SUPABASE_ANON_KEY` não estiver configurado no repositório, os workflows param com uma mensagem clara; não é necessário configurar outro token TMDB no GitHub.

## Sugestões de logos e gêneros (somente revisão)

A validação também gera dois relatórios sem alterar os catálogos:

- `channel-logo-suggestions.json`: sugestões de logos a partir da referência sanitizada do Saimo Android TV. Correspondências por nome normalizado exato são separadas das correspondências de menor confiança que ignoram marcadores como HD/SD; as duas categorias exigem revisão humana.
- `radio-genre-suggestions.json`: sugere gênero apenas quando as palavras-chave do nome da estação apontam para uma categoria única. Casos ambíguos são separados e não recebem sugestão automática.

Os relatórios não importam streams, cabeçalhos, DRM nem dados de reprodução. Uma sugestão nunca altera o registro por si só. Para executar localmente:

```bash
python scripts/suggest_channel_logo_matches.py --output channel-logo-suggestions.json
python scripts/suggest_radio_genres.py --output radio-genre-suggestions.json
```

