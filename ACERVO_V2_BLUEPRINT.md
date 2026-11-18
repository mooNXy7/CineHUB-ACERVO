# CineHUB-ACERVO V2 — Blueprint Técnico
**Estado:** blueprint inicial aprovado para orientar implementação; decisões de infraestrutura dependentes de verificação operacional estão explicitamente condicionadas.  
**Branch:** `develop/acervo-v2`  
**Documento complementar:** `ACERVO_V2_SPEC.md`

## 1. Princípios de implementação
1. Canonical-first: contratos internos são a fonte de verdade; formatos externos são adaptadores.
2. Independence-by-design: fontes externas são substituíveis; nenhum repositório de referência é runtime obrigatório.
3. Raw-before-transform: toda ingestão preserva o original antes de converter.
4. Deterministic and idempotent: repetir uma execução com a mesma entrada não cria duplicatas nem muda IDs.
5. Candidate-before-active: gerar e testar uma versão candidata antes de promovê-la.
6. Fail-safe: falha de coleta não equivale a conteúdo removido.
7. Observable: toda etapa informa o que leu, alterou, rejeitou, enriqueceu e publicou.
8. Consumer compatibility: contratos e artefatos de saída são explícitos; consumidores não acessam fontes de terceiros diretamente.

## 2. Arquitetura lógica
```
                   ┌────────────────────────────┐
                   │       Source Registry      │
                   │ fontes, formatos, políticas│
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │       Collectors           │
                   │ HTTP / Git / XMLTV / feeds │
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │       Raw Archive          │
                   │ payload + hash + provenance│
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │       Import Adapters      │
                   │ parsers por formato/fonte │
                   └─────────────┬──────────────┘
                                 │
            ┌────────────────────▼────────────────────┐
            │             Processing Engine           │
            │ normalize → identity → dedupe → validate│
            └────────────────────┬────────────────────┘
                                 │
            ┌────────────────────▼────────────────────┐
            │              Enrichment Engine          │
            │ TMDB / logos / EPG mapping / metadata    │
            └────────────────────┬────────────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │       Candidate Builder    │
                   │ schemas + indexes + report │
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │      Quality Gate          │
                   │ regression + thresholds    │
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │      Version Publisher     │
                   │ immutable snapshot/manifest│
                   └─────────────┬──────────────┘
                                 │
                   ┌─────────────▼──────────────┐
                   │     Consumer Delivery      │
                   │ API/static + cache/fallback│
                   └────────────────────────────┘
```

## 3. Organização de código proposta
A árvore abaixo define responsabilidades, não uma ordem para criar diretórios vazios. Implementar módulos somente quando houver código, fixtures ou testes reais.

```
config/
  sources/                 # registro declarativo de fontes
  policies/                # thresholds, retries, prioridades
schemas/
  common/                  # provenance, source, asset, stream
  vod/ channels/ radios/ logos/ epg/
adapters/
  <source_or_format>/      # coleta e parsing isolados
engine/
  collect/ parse/ normalize/
  identity/ deduplicate/ enrich/
  validate/ build/ publish/ recover/
catalog/
  canonical/               # registros de domínio
  indexes/                 # índices derivados
  exports/                 # formatos de compatibilidade
storage/
  raw/                     # configuração/manifestos; blobs no storage escolhido
reports/
  runs/ quality/ changes/
scripts/
tests/
  fixtures/ unit/ contract/ integration/ regression/
.github/workflows/
```

## 4. Contratos canônicos mínimos
Os schemas devem ser JSON Schema versionados e validados em CI. Campos ilustrativos abaixo são contratos conceituais; nomes finais serão definidos ao inspecionar os formatos existentes e consumidores.

### Entidade
- `id`: identificador interno estável.
- `type`: movie, series, season, episode, anime, dorama, channel ou radio.
- `title`, `aliases[]`, `language`, `country`, `categories[]`.
- `external_ids`: TMDB/IMDb e outros IDs tipados, opcionais.
- `provenance[]`: fonte, referência externa, coletado_em, hash/versão.
- `created_at`, `updated_at`, `schema_version`.

### Stream/source variant
- `id`, `entity_id`, `kind`, `url` ou referência protegida.
- `protocol`, `priority`, `source_id`, `status`, `last_checked_at`.
- `failure_count`, `last_error`, `validation_evidence`.
Não colocar URLs de imagens no campo de stream. Credenciais privadas não podem estar em URLs/logs.

### Asset/logo
- `id`, `entity_id`, `asset_url`, `mime_type`, `width`, `height`.
- `source_id`, `status`, `is_primary`, `validated_at`.

### EPG mapping/program
- Mapeamento explícito entre `channel_id` e `epg_channel_id`, com alias e procedência.
- Programa com início/fim timezone-aware, título, descrição e fonte.
- Rejeitar intervalos inválidos e normalizar timezone sem perder valor original.

### Provenance
Cada campo importado/enriquecido deve permitir rastrear fonte, método, timestamp e confiança. Atualizações manuais devem registrar autor/motivo quando suportado.

## 5. Identidade e deduplicação
- IDs internos não dependem da ordem dos arquivos, posição na lista, URL do provedor ou título.
- Resolver por IDs externos confiáveis quando tipo/idioma/ano correspondem; caso contrário usar matching composto.
- Matching composto pode considerar título normalizado, ano, tipo, idioma, temporada/episódio e duração quando disponível.
- Resultado do matcher contém score, evidências e decisão: auto-match apenas acima de threshold conservador; faixa intermediária vai para revisão; abaixo do threshold cria candidato separado.
- Não fundir streams, logos ou procedências: agregar variantes.
- Mudanças de identidade geram evento/audit trail e aliases de IDs antigos.

## 6. Enriquecimento TMDB
- Reutilizar a integração/token já configurada no Supabase; nunca duplicar token em arquivo, workflow ou log.
- Um serviço de enriquecimento consulta por ID confirmado primeiro; busca textual é sugestão, não confirmação automática.
- Cache por consulta/entidade, rate limit, retry/backoff e checkpoint.
- Atualizar apenas campos permitidos e ausentes/desatualizados segundo política; preservar valores manuais e procedência.
- Salvar candidatos, score e diferenças antes de aplicar correspondências ambíguas.
- Processamento incremental por lotes; checkpoint durável para retomar sem recomeçar.
- Relatório final separa enriquecidos, já atualizados, não encontrados, ambíguos, falhas e ignorados.

## 7. Saúde de streams e fontes
- Verificações classificam reachable, timeout, HTTP error, invalid content, unsupported protocol e unknown.
- Teste pontual não apaga variante. Desativação requer múltiplas falhas em janelas separadas e política por fonte.
- Respeitar rate limits e evitar sondagem agressiva.
- Fallback escolhe próxima variante válida por prioridade, sem reescrever a entidade.
- Guardar último sucesso e último erro para distinguir indisponibilidade temporária de fonte morta.

## 8. Execução, orquestração e workflows
- Workflows chamam módulos/scripts existentes e falham cedo se entrypoint não existir.
- Um workflow por domínio ou rotina pesada; dependências entre jobs são explícitas.
- Lock/concurrency group evita duas publicações simultâneas.
- Timeout, retry, checkpoint e cancelamento seguro.
- Agendamento não substitui execução manual reproduzível.
- Cada run publica artefatos: log resumido, relatório JSON, diff de catálogo, métricas e versão candidata.
- Segredos são referenciados por nome; ausência de secret deve falhar com mensagem clara, sem fallback inseguro.
- Workflows de TMDB, rádio, logos, canais e EPG não podem depender de scripts inexistentes.

## 9. Publicação, versionamento e rollback
- Criar snapshot imutável identificado por versão/hash.
- Executar validação de schema, integridade referencial, thresholds de contagem, links e regressões.
- Comparar candidato com versão ativa e exigir aprovação/threshold para mudanças massivas.
- Publicar todos os artefatos primeiro; atualizar o manifesto ativo por último (promoção atômica).
- Consumidores usam manifesto e cache com fallback para última versão válida.
- Rollback altera o ponteiro ativo para snapshot anterior; não reescreve dados históricos.
- Retenção e limpeza de snapshots são políticas separadas da publicação.

## 10. Papel das plataformas
A responsabilidade lógica não fica presa ao fornecedor:
- GitHub: código, schemas, testes, workflows, documentação e artefatos pequenos.
- Supabase: integração TMDB já existente e, se confirmados recursos/configuração adequados, estado operacional, fila/checkpoints e segredos.
- Cloudflare: se os recursos ativos e permissões forem confirmados, distribuição estática/API/cache e armazenamento de objetos.
- Nenhuma destas responsabilidades deve ser presumida como já implantada. Antes de usar Pages, Workers, R2, tabelas ou Edge Functions, inventariar o que existe e registrar configuração real.
- O sistema deve permitir substituir a camada de storage/hosting sem reescrever normalização, identidade ou regras de catálogo.

## 11. Testes obrigatórios
1. Unitários: normalização, parser, matching, regras de validação e prioridade.
2. Fixtures: amostras reais sanitizadas de cada formato de fonte, incluindo rádios no formato de referência identificado.
3. Contrato: JSON Schema e integridade dos relacionamentos.
4. Integração: ingestão até catálogo candidato com dependências simuladas.
5. Regressão: catálogo atual não perde registros válidos sem justificativa.
6. Falha: timeout, fonte vazia, JSON truncado, API limitada, imagem em campo de stream, IDs conflitantes.
7. Publicação: candidato inválido não promove; falha durante upload não altera manifesto; rollback restaura versão.
8. Independência: desligar adaptador de referência não impede build, validação ou entrega do catálogo importado.

## 12. Sequência de implementação com saída verificável
A sequência é um fluxo de engenharia, não uma autorização para parar após cada microtarefa:
- **Fase A — Baseline executável:** snapshot do estado atual, inventário de scripts/workflows, fixtures e testes de regressão. Saída: baseline reproduzível e lista fechada de falhas.
- **Fase B — Contratos e importadores:** schemas canônicos e adaptadores para formatos reais (incluindo canais, rádios, VOD, logos e EPG). Saída: importação determinística e relatório de incompatibilidades.
- **Fase C — Núcleo de catálogo:** identidade, deduplicação, normalização, variantes e procedência. Saída: catálogo canônico sem perda silenciosa.
- **Fase D — Enriquecimento e qualidade:** TMDB, logos, EPG, saúde de streams, quarentena e revisão de ambiguidades. Saída: jobs retomáveis e métricas por domínio.
- **Fase E — Build e entrega:** índices/exportações de compatibilidade, snapshots, manifesto, cache e rollback. Saída: publicação testada em ambiente de desenvolvimento.
- **Fase F — Operação autônoma:** workflows completos, observabilidade, alertas, runbooks e teste de independência. Saída: atualização de ponta a ponta repetível.
- **Fase G — Integração consumidora:** só após V2 aprovado; mapear e migrar consumidores separadamente, sem OTA até autorização expressa.

As fases podem avançar em paralelo quando independentes. Não declarar uma fase encerrada apenas por criar arquivos: executar os testes e demonstrar os resultados.

## 13. Limites e critérios de pronto
- Sem alteração em TV/Mobile/Web nesta implementação do núcleo.
- Sem alteração em `main`, OTA ou distribuição oficial sem aprovação separada.
- Não remover conteúdo/variantes em massa durante normalização ou saúde.
- Não publicar automaticamente se thresholds de qualidade falharem.
- “Pronto” significa catálogo validado, build reproduzível, workflows íntegros, publicação/rollback demonstrados e documentação de operação atualizada.
- A independência é comprovada por teste: bloquear/desativar todos os adaptadores de referência e ainda gerar, validar e servir o catálogo importado anteriormente.
