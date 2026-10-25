# Plano seguro de enriquecimento de metadados VOD

## Objetivo

Completar metadados ausentes nos índices de filmes, séries, animes e doramas sem substituir informações válidas, alterar fontes de reprodução ou criar associações incertas. Este documento define a sequência de implementação; não significa que o enriquecimento já foi executado.

## Estado observado

O índice VOD usa `catalog/vod/index.json` como manifesto e arquivos separados por categoria. O relatório `catalog_quality_report.py` identifica pôster, ano, gêneros, caminho de detalhe e possíveis duplicatas. Presença de campo não garante que a informação ou imagem seja correta.

## Ordem de implementação

1. **Inventário somente de leitura:** registrar por categoria os campos ausentes, IDs existentes, contagem de duplicatas candidatas e cobertura de IDs externos. Salvar um relatório versionado como artefato de CI, sem escrever no catálogo.
2. **Definir provedor e licença:** preferir API oficial ou fonte com termos documentados. Registrar o nome do provedor, data da consulta, licença/termos e campos obtidos. Não copiar chaves de API de repositórios de referência nem incluir credenciais em arquivos, URLs ou logs.
3. **Resolver identidade antes de enriquecer:** prioridade para ID externo já existente; depois título normalizado + ano + tipo/categoria. Título sozinho nunca autoriza substituição automática quando há múltiplos resultados plausíveis.
4. **Prévia em lote:** produzir um diff separado com valor atual, valor proposto, provedor e confiança/motivo da correspondência. Não incluir URLs de reprodução nem credenciais nesse relatório.
5. **Aplicação conservadora:** preencher somente campos vazios por padrão. Não sobrescrever pôster, ano, sinopse, gêneros ou IDs já preenchidos sem revisão explícita. Não remover fontes, registros ou variantes de remake/temporada.
6. **Publicação atômica:** escrever para temporário no mesmo diretório, validar JSON e esquema, então substituir o arquivo; se qualquer etapa falhar, preservar a versão anterior. Para índices grandes, publicar detalhes/fragmentos primeiro e atualizar o manifesto por último.
7. **Validar antes de propor merge:** testar correspondências ambíguas, erros HTTP, limites de API, respostas vazias, interrupção durante escrita, contagem de registros e diffs inesperadamente grandes. Produzir relatório antes/depois e manter a alteração em PR separada.

## Regras de correspondência

- ID de provedor existente e compatível com a categoria: evidência forte.
- Título + ano + tipo compatíveis: candidato forte, mas ainda precisa de verificação de campos conflitantes.
- Título sem ano, traduções alternativas, remakes, temporadas, especiais e obras homônimas: revisão manual.
- Uma resposta sem resultado, erro de rede ou limite de API nunca deve ser armazenada como metadado vazio definitivo.
- Não inferir ano, gênero, pôster ou sinopse a partir do nome do arquivo ou da URL de stream.

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

## Próxima etapa

Implementar um comando de **dry-run** que gere candidatos e diffs, usando apenas o provedor aprovado e credenciais guardadas em secrets de CI. Até essa validação, não executar enriquecimento em massa nem alterar os índices VOD automaticamente.
