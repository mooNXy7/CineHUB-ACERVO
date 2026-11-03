# Próxima Tarefa — CineHUB-ACERVO

## Estado e passagem
**HEAD-base validado:** 1908b9adf242129fe85b20731f60ff203e8e7cf4  
**main:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Comparação no HEAD-base:** 37 commits à frente, 0 atrás; 15 arquivos alterados; 0 em catalog/ ou sources/.  
**Validação desse HEAD-base:** Validate catalog, run 935, ID 41576192907, push, success; 25 testes aprovados, 0 falhas; validador, auditor, py_compile e upload success.  
**Artefato:** 13203323544; acervo-v2-baseline-1908b9adf242129fe85b20731f60ff203e8e7cf4; ZIP SHA-256 1abf5cb68741f5985f0a92a8748ee22fe6d249aa7b8d0e4ce7a0063b81ff53eb.  
Este alinhamento gera um único commit documental filho do HEAD-base acima; após ele, a comparação da branch passa a 38 commits à frente e 0 atrás, mantendo 15 arquivos alterados e zero em catalog/ ou sources/.  
Snapshot original do run 930: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto catalog-snapshot.sha256 no artefato 13202372616. O run 935 não recalculou o snapshot.  
Histórico: run 930 = baseline e origem do snapshot; run 931 = validação intermediária; run 933 = validação do HEAD anterior 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; run 935 = validação do HEAD-base documental atual.  
Fase A encerrada. Fase B é a próxima tarefa planejada e permanece não iniciada nesta correção.

## Próxima tarefa planejada — Fase B
A Fase B é a próxima etapa do projeto. **Não foi iniciada nesta correção**. Ao iniciar, seguir ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md e ARCHITECTURE.md; não improvisar contratos nem substituir o fluxo de referência aprovado.

### Ordem técnica registrada
1. Definir schemas versionados para VOD, canais, rádios, logos e EPG, com procedência e IDs estáveis.
2. Implementar os quatro entrypoints VOD ausentes somente após definir contratos reais:
   - scripts/enrich_vod_metadata.py
   - scripts/apply_vod_metadata_patch.py
   - scripts/suggest_vod_tmdb_matches.py
   - scripts/apply_vod_tmdb_id_candidates.py
3. Corrigir workflows VOD para não depender de branch fixa antiga e validar todos os scripts chamados.
4. Desacoplar o clone fki1976/SaimoPlayer do caminho operacional obrigatório; manter a referência como adaptador auxiliar, conforme arquitetura aprovada.
5. Criar pipeline de logos com validação de MIME/arquivo, origem e associação.
6. Enriquecer rádios sem apagar variantes, inventar gêneros ou atribuir logos ambíguos.
7. Preservar snapshot e catálogo ativo até cada candidato passar pelo quality gate.

## Regras permanentes
Não alterar main, TV, Mobile ou Web; não publicar OTA; não duplicar token TMDB; não excluir streams por falha pontual; não aplicar correspondência TMDB ambígua; não substituir catálogo ativo sem backup e validação.


## Fonte mestre de verdade e retomada
**Antes de executar qualquer tarefa, leia integralmente [ROADMAP_V2.md](ROADMAP_V2.md).** Ele contém o plano integral, arquitetura, todos os domínios, decisões, fases futuras, critérios de aceite e regras de continuidade.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Sempre consultar o HEAD vivo da branch antes de executar.
- Fase A: CONCLUÍDA.
- Fase B: próxima; NÃO INICIADA.
- A Fase B deve seguir o escopo descrito em ROADMAP_V2.md, especialmente auditoria complementar, schemas canônicos, parsers/importadores, fixtures e testes.
- Não iniciar Fase C nem qualquer etapa posterior automaticamente.
- Não tratar esta consolidação documental como implementação da Fase B.
> **RETOMADA VIGENTE — 2026-11-03 (autoridade sobre registros históricos abaixo)**  
> Branch: `develop/acervo-v2`  
> HEAD confirmado no GitHub: `3d8d143ae387f3340c1efb285fb3199393c25a99`  
> `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`  
> Comparação atual: **45 commits à frente, 0 atrás**, 15 arquivos no diff reportado; a comparação não mostra alterações em `catalog/` ou `sources/`.  
> PR #1 e PR #2 estão abertos em estado draft; nenhum está mesclado. Não alterar nem mesclar nenhum deles nesta etapa.  
> Fase A: CONCLUÍDA. Fase B: **NÃO INICIADA; AUTORIZADA PELO RESPONSÁVEL PARA INÍCIO PELO EXECUTOR**. Esta atualização é apenas documental e não conta como implementação da Fase B.  
> Próxima execução autorizada: somente Fase B — auditoria complementar, contratos canônicos, parsers/importadores, fixtures e testes. Não iniciar Fase C.  
> Sempre revalidar HEAD, main, comparação, PRs e workflows no início da execução; estes SHAs são fotografia desta retomada, não valores permanentes.  
> Escopo protegido: não alterar `main`, consumidores TV/Mobile/Web/Player, repositórios de referência, segredos, produção Supabase/Cloudflare, OTA ou publicação oficial. Não promover/substituir catálogo ativo.  
> Fontes de verdade: ler integralmente `ROADMAP_V2.md`, `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.  
> PR #1: https://github.com/mooNXy7/CineHUB-ACERVO/pull/1 — “Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”, draft, aberto, não mesclado.  
> PR #2: https://github.com/mooNXy7/CineHUB-ACERVO/pull/2 — “[DRAFT] ACERVO V2 — Fase A: baseline executável”, draft, aberto, não mesclado. Verificar seus SHAs/diffs ao executar; não assumir que qualquer PR representa a branch de trabalho.  
> 
## Ordem executável da Fase B
1. Fazer checkout/sincronização da branch `develop/acervo-v2`; confirmar que o HEAD corresponde ao remoto e registrar SHA real. Não usar o SHA deste documento como checkout obrigatório.
2. Ler integralmente todos os documentos normativos e o roadmap.
3. Inventariar no código atual os arquivos, formatos, schemas, scripts, workflows, fontes e consumidores internos por domínio: VOD, canais, rádios, logos e EPG. Registrar evidências de caminhos/linhas e separar “existe”, “funciona”, “parcial”, “ausente” e “não verificado”.
4. Auditar complementarmente os repositórios de referência autorizados, somente leitura, apenas nos pontos necessários para compreender formatos/contratos. Confirmar namespace/repositório; não presumir equivalência entre perfis. Não copiar aplicativos ou branding.
5. Definir schemas versionados e contratos canônicos compartilhados, incluindo provenance, source, entity IDs, variantes de stream, assets/logos, relações EPG, confiança/estado e relatórios. Contratos devem derivar dos dados reais e preservar campos desconhecidos em extensão/raw quando apropriado.
6. Implementar parsers/importadores pequenos e isoláveis para formatos reais identificados. Garantir normalização determinística, IDs estáveis, idempotência, deduplicação sem perder variantes e preservação da proveniência.
7. Criar fixtures sanitizadas representativas e testes para entradas válidas, inválidas, legadas, duplicadas, incompletas, falhas de fonte, provenance, IDs e idempotência. Testes não podem depender de rede nem de segredos.
8. Reconciliar os quatro entrypoints VOD históricos e workflows que os chamam: implementar somente com contrato definido e teste; se já existirem, auditar e corrigir. Não criar stubs vazios para deixar workflow verde.
9. Isolar saídas em staging/candidato. Preservar integralmente catálogos ativos, snapshots, fontes e registros válidos. Não publicar nem promover.
10. Rodar testes, validação, auditoria read-only e comparar métricas/arquivos antes e depois. Registrar limitações, incompatibilidades e decisões que exigem aprovação.
11. Atualizar roadmap e documentos operacionais com commits, testes, workflows/runs, artefatos, métricas e pendências reais. Marcar subitens individualmente; a Fase B só termina após todos os critérios de aceite do roadmap.
12. Parar ao final da Fase B e aguardar aprovação explícita antes de iniciar Fase C.

## Critérios mínimos de aceite
- Schemas versionados para os cinco domínios e tipos compartilhados, validados em CI.
- Fixtures cobrindo formatos reais observados e casos de falha.
- Parsers/importadores determinísticos, idempotentes e testados sem rede.
- IDs e provenance preservados; variantes não são descartadas por dedup.
- Dados inválidos isolados com motivo, sem exclusão silenciosa.
- Workflows não chamam entrypoints inexistentes; nenhum stub vazio.
- Nenhuma modificação de catálogo ativo, main, consumidores, infraestrutura de produção ou publicação.
- Relatório reproduzível com inventário, diffs, testes, evidências e pendências.
