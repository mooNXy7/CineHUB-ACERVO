# CineHUB-ACERVO — Decisões Aprovadas

Este documento contém apenas decisões explicitamente aprovadas. Propostas e hipóteses devem ficar identificadas como tais até aprovação.

## D-001 — Estratégia de fontes (aprovada)
**Decisão:** Estratégia B.

- Priorizar fontes independentes para descoberta, ingestão e atualização.
- Permitir os repositórios de referência autorizados por Gabriel como fonte auxiliar de descoberta/importação.
- Não depender exclusivamente desses repositórios para operação, atualização ou distribuição.
- Não alterar os repositórios de Gabriel.

## D-002 — Branch isolada para V2 (aprovada)
**Decisão:** criar e usar `develop/acervo-v2`, derivada do `main` atual.

- `main` permanece estável.
- Implementação e validação ocorrem na branch de desenvolvimento.
- Integração à `main` somente após validação e aprovação explícita.

## D-003 — Continuidade independente de conversas (aprovada)
**Decisão:** GitHub é a fonte persistente de verdade para estado técnico e continuidade.

- Manter status, log de execução, próxima tarefa, arquitetura, decisões e transferência de contexto atualizados.
- Ao retomar em uma conversa nova, verificar branch, HEAD, commits e arquivos antes de executar.
- Não confiar exclusivamente no histórico ou memória de um chat.

## D-004 — Proteção dos consumidores (aprovada)
**Decisão:** nesta preparação do ACERVO V2, não modificar TV, Mobile ou Web e não publicar OTA sem autorização explícita.

## D-005 — Identidade CineHUB (aprovada)
**Decisão:** não incluir marca, identidade visual ou créditos Saimo na experiência, documentação pública ou identidade dos produtos CineHUB. A necessidade de proveniência técnica interna para auditoria deve ser discutida sem expor marcas na interface.

## D-006 — Especificação V2 antes da implementação (aprovada)
**Decisão:** discutir e documentar como o ACERVO V2 deverá funcionar antes de iniciar sua implementação funcional.

## Decisões ainda em aberto
- Modelo de dados canônico por tipo de conteúdo.
- Fontes independentes específicas e critérios de autorização.
- Estratégia de armazenamento de dados brutos e histórico.
- Contratos de distribuição e versionamento.
- Papel definitivo de GitHub Actions, Cloudflare e Supabase.
- Política de saúde, prioridade, fallback e revisão manual.
- Escopo e critérios de conclusão por domínio (logos, rádios, canais, VOD, EPG etc.).
