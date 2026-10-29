# Plano seguro de enriquecimento de metadados VOD

## Objetivo

Completar metadados ausentes nos índices de filmes, séries, animes e doramas sem substituir informações válidas, alterar fontes de reprodução ou criar associações incertas. O plano e o relatório dry-run não executam enriquecimento.

## Relatório dry-run disponível

O comando `scripts/plan_vod_enrichment.py` inventaria registros com metadados ausentes e verifica a sintaxe óbvia dos IDs externos, além de agrupar IDs repetidos dentro de cada categoria. É somente leitura: não consulta rede, não altera os índices e não inclui URLs de fontes de reprodução no resultado.

```bash
python scripts/plan_vod_enrichment.py > vod-enrichment-plan.json
python scripts/plan_vod_enrichment.py --limit 100 --output /tmp/vod-enrichment-plan.json
```

O limite controla apenas quantos exemplos são incluídos por categoria; as contagens representam o catálogo inteiro. O relatório observa campos ausentes de pôster, ano e gêneros nos índices. Sinopses não são incluídas nesta primeira versão porque exigem confirmar a estrutura dos arquivos de detalhe antes de auditar esse campo. IDs externos são lidos apenas de uma lista explícita de campos comuns.

### Como interpretar os candidatos

- `provider_id_present`: há um ID externo no registro; ainda é necessário confirmar que ele corresponde à obra e à categoria.
- `title_year_type_candidate`: título, ano e tipo existem; é candidato para futura consulta, não uma correspondência aprovada.
- `manual_identity_review`: faltam evidências suficientes; revisão manual antes de consultar qualquer provedor.
- `invalid_external_id_occurrences`: o valor não corresponde ao padrão sintático básico esperado para aquele campo. Pode ser um formato local legítimo ou dado legado; revisar antes de alterar.
- `duplicate_external_id_groups`: o mesmo ID aparece em mais de um registro dentro da mesma categoria. É um alerta para revisão, não uma instrução para apagar ou mesclar registros.

Os testes de formato e duplicidade são heurísticos; **não provam** que um ID seja correto ou incorreto. O relatório não executa enriquecimento. Antes de qualquer consulta em lote, é necessário escolher um provedor autorizado, revisar os termos/licença e definir como IDs e procedência serão armazenados.

## Execução de enriquecimento em lotes

O fluxo `Build VOD metadata review patch` já concluiu o primeiro lote de 1.000 registros elegíveis (offset 0). Foram aplicadas 913 correções em registros com ID TMDB existente e título compatível, preenchendo 1.533 campos ausentes; 84 casos com divergência de ano foram mantidos para revisão, 3 registros já estavam completos e nenhum erro de consulta ou conflito de identidade ocorreu. O aplicador preservou campos existentes e fontes de reprodução. O lote seguinte parte do offset 1.000. As sugestões de IDs TMDB para registros sem ID permanecem em relatório separado e nunca são aplicadas automaticamente.

## Próximas etapas seguras

1. **Definir provedor e licença:** preferir API oficial ou fonte com termos documentados. Registrar o nome do provedor, data da consulta, licença/termos e campos obtidos. Não copiar chaves de API de repositórios de referência nem incluir credenciais em arquivos, URLs ou logs.
2. **Resolver identidade antes de enriquecer:** prioridade para ID externo existente; depois título normalizado + ano + tipo/categoria. Título sozinho nunca autoriza substituição automática quando há múltiplos resultados plausíveis.
3. **Prévia em lote:** produzir um diff separado com valor atual, valor proposto, provedor e motivo da correspondência. Não incluir URLs de reprodução nem credenciais nesse relatório.
4. **Aplicação conservadora:** preencher somente campos vazios por padrão. Não sobrescrever pôster, ano, sinopse, gêneros ou IDs já preenchidos sem revisão explícita. Não remover fontes, registros ou variantes de remake/temporada.
5. **Publicação atômica:** escrever para temporário no mesmo diretório, validar JSON e esquema, então substituir o arquivo; se qualquer etapa falhar, preservar a versão anterior. Para índices grandes, publicar detalhes/fragmentos primeiro e atualizar o manifesto por último.
6. **Validar antes de propor merge:** testar correspondências ambíguas, erros HTTP, limites de API, respostas vazias, interrupção durante escrita, contagem de registros e diffs inesperadamente grandes.

## Limites operacionais

- Respeitar limites de requisição, termos de uso e política de cache do provedor.
- Usar timeout, limite de tamanho, concorrência baixa e repetição limitada com espera.
- Não consultar páginas privadas, contornar login/DRM/paywall nem reutilizar tokens encontrados em outras fontes.
- Manter relatório de falhas por item sem despejar URLs sensíveis ou respostas completas de provedores.
- Começar com um lote pequeno de teste por categoria e revisar o diff antes de escalar para dezenas de milhares de itens.

## Critérios de aceite

- Nenhum registro removido e nenhuma fonte de reprodução alterada pelo processo de metadados.
- Nenhum campo preenchido por correspondência ambígua sem revisão.
- Nenhum segredo no repositório, artefatos ou logs.
- JSON e esquema válidos; contagens e IDs estáveis.
- A versão anterior continua recuperável e uma falha de lote não publica estado parcial.
- Os aplicativos consumidores continuam compatíveis com o formato atual; integração com TV/Mobile ocorre em trabalho separado e só após testes próprios.


## Patch TMDB com revisão (28/10/2026)

O script scripts/enrich_vod_metadata.py e o workflow manual .github/workflows/enrich-vod-metadata.yml adicionam um caminho opcional para enriquecer registros que **já possuem um TMDB ID numérico**.

- O script consulta o endpoint exato de filme/série; não faz busca por título nem atribui IDs novos.
- Exige confirmação do ID e correspondência de título normalizado. Divergência de título ou ano explícito no título vira revisão manual.
- Só propõe poster_url, year e genres quando o campo está vazio; nunca substitui metadados preenchidos.
- Usa cache SQLite durante a execução, timeout, tentativas limitadas e intervalo entre chamadas. Falhas transitórias não ficam cacheadas como resultado definitivo.
- Produz um JSON de patch revisável como artefato; não modifica catalog/. Aplicar qualquer patch é uma etapa separada, após revisão.
- O workflow é manual e limitado a 1–1000 registros por execução. Para habilitá-lo, adicione uma chave TMDB própria como secret TMDB_API_KEY em Settings → Secrets and variables → Actions. Não cole a chave no chat, não use nem copie a credencial encontrada no repositório de referência.
- A nova rotina foi adicionada com testes unitários de patch, correspondência de identidade, conflito de ano e ausência de credencial. A validação CI deve passar antes da primeira execução com rede.
