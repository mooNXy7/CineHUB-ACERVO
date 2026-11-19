# Etapa 2 — Sistema Central de Fontes e Provedores

**Branch:** `develop/acervo-v3`  
**Status:** implementação consolidada; validação integral do CI pendente para aceite.  
**Escopo protegido:** nenhuma alteração em `main`, V2, aplicativos consumidores, segredos, infraestrutura de produção ou publicação.

## Entrega implementada

1. Registro central versionado em `sources/sources.json`, com nove entradas rastreáveis:
   - M3U local curada de emissoras públicas;
   - snapshots locais de canais e rádios;
   - manifesto local VOD;
   - fixture TXT de teste desabilitada;
   - quatro fontes XMLTV legadas em `pending_review` e desabilitadas.
2. Cada registro contém ID estável, provedor, domínio, formato, origem, prioridade, idioma/região, autorização/termos, status, frequência, última execução, erros/histórico, referência lógica de credencial, adaptador e opções.
3. Schema compartilhado `schemas/common/source-v1.schema.json` ampliado para exigir provedor e descrever os campos de ciclo de vida.
4. Adaptadores independentes para M3U, JSON de canais/rádios, TXT (rádio e variantes VOD explícitas), XMLTV e catálogo VOD hierárquico existente.
5. Leitura de origens locais restrita à raiz do repositório, com arquivo existente obrigatório e bloqueio de path traversal/symlink escape. A M3U curada é carregada da própria branch, sem depender do arquivo em `main`.
6. Validação de URLs HTTP(S): rejeição de esquemas não suportados, hosts locais, IPs não públicos, credenciais embutidas, portas inválidas, fragmentos e parâmetros de query sensíveis. A validação de respostas DNS está disponível separadamente.
7. Detecção de IDs duplicados e origens duplicadas por domínio/formato, com normalização de host e portas padrão.
8. Quarentena para entradas inválidas, ausentes ou duplicadas; redação de valores sensíveis nos dados brutos apresentados em relatórios.
9. Integração do contrato com importadores canônicos: provedor e metadados de ciclo de vida preservados; fontes `pending_review` não são marcadas como importáveis.

## Segurança e limites

- Nenhuma fonte remota foi baixada ou consultada por estes adaptadores.
- As quatro fontes XMLTV externas permanecem desabilitadas até revisão de autorização/termos.
- Um cliente remoto futuro ainda deverá validar DNS resolvido e cada redirecionamento imediatamente antes de conectar; não há fetcher remoto ativado nesta etapa.
- `credentials_ref` aceita apenas um identificador lógico, nunca o valor de uma credencial.
- Nenhum catálogo ativo foi substituído e nenhuma publicação/atualização automática foi habilitada.

## Testes

Os testes offline cobrem URLs públicas/privadas, credenciais e redaction, path traversal, origem local ausente, IDs/origens duplicados, status de revisão, metadados de provedor e dispatch dos adaptadores. A validação completa também inclui catálogo, schemas, compilação, build de candidata e idempotência.

**Aceite final:** registrar o Run do CI correspondente ao HEAD mais recente, confirmar todos os passos verdes e atualizar este relatório com SHA, contagem real de testes e artefato. Até lá, não marcar a Etapa 2 como concluída.
