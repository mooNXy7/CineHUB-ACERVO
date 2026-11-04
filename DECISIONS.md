# CineHUB-ACERVO — Decisões Aprovadas

Este documento contém decisões explicitamente aprovadas. Propostas e hipóteses permanecem identificadas como tais até aprovação.

## D-001 — Estratégia de fontes (aprovada)
**Decisão:** Estratégia B.
- Priorizar fontes independentes para descoberta, ingestão e atualização.
- Permitir repositórios de referência autorizados como fonte auxiliar de descoberta/importação.
- Não depender exclusivamente dessas referências para operação, atualização ou distribuição.
- Não alterar os repositórios de referência.

## D-002 — Branch isolada para V2 (aprovada)
**Decisão:** usar `develop/acervo-v2`, derivada de `main`.
- `main` permanece estável.
- Implementação e validação ocorrem na branch V2.
- Integração à `main` somente após validação e aprovação explícita.

## D-003 — Continuidade independente de conversas (aprovada)
GitHub é a fonte persistente de verdade para estado técnico e continuidade. Status, log, próxima tarefa, arquitetura, decisões e handoff devem ser atualizados. Toda retomada começa pela verificação do HEAD e dos documentos atuais.

## D-004 — Proteção dos consumidores (aprovada)
Nesta fase, não modificar TV, Mobile ou Web e não publicar OTA. Integrações consumidoras serão uma etapa posterior, com autorização própria.

## D-005 — Identidade CineHUB (aprovada)
Não incluir marca, identidade visual ou créditos Saimo na experiência, documentação pública ou identidade dos produtos CineHUB. Proveniência técnica pode ser mantida internamente para auditoria, sem branding de terceiros.

## D-006 — Especificação V2 antes da implementação (concluída)
A especificação e o blueprint devem orientar a implementação funcional.

## D-007 — Aprovação do cérebro ACERVO V2 (aprovada em 2026-11-03)
O responsável aprovou a construção do ACERVO V2 e autorizou registrar no Git os documentos:
- `ACERVO_V2_SPEC.md` — missão, domínios, pipeline, contratos, segurança, distribuição e critérios de aceite.
- `ACERVO_V2_BLUEPRINT.md` — arquitetura lógica, módulos, contratos, identidade, TMDB, saúde, workflows, publicação, rollback e testes.

A aprovação autoriza desenvolver o núcleo na branch `develop/acervo-v2`; não autoriza alterar consumidores, integrar à `main` ou publicar OTA.

## Decisões de implementação ainda condicionadas à verificação técnica
- Recursos efetivamente ativos e permissões de Cloudflare/Supabase.
- Fontes independentes específicas e formatos/licenças.
- Modelo final de armazenamento bruto e estado operacional.
- Thresholds numéricos de qualidade por domínio.
- Contratos exatos de saída exigidos pelos consumidores atuais.

Essas verificações não suspendem o desenvolvimento do núcleo; decisões dependentes devem ser isoladas por interfaces e adaptadores substituíveis.
