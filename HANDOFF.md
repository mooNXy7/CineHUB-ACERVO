# Transferência de Contexto — CineHUB-ACERVO

## Repositório e estado
- Repositório: https://github.com/mooNXy7/CineHUB-ACERVO
- Branch: develop/acervo-v2
**HEAD-base validado:** 1908b9adf242129fe85b20731f60ff203e8e7cf4  
**main:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Comparação no HEAD-base:** 37 commits à frente, 0 atrás; 15 arquivos alterados; 0 em catalog/ ou sources/.  
**Validação desse HEAD-base:** Validate catalog, run 935, ID 41576192907, push, success; 25 testes aprovados, 0 falhas; validador, auditor, py_compile e upload success.  
**Artefato:** 13203323544; acervo-v2-baseline-1908b9adf242129fe85b20731f60ff203e8e7cf4; ZIP SHA-256 1abf5cb68741f5985f0a92a8748ee22fe6d249aa7b8d0e4ce7a0063b81ff53eb.  
Este alinhamento gera um único commit documental filho do HEAD-base acima; após ele, a comparação da branch passa a 38 commits à frente e 0 atrás, mantendo 15 arquivos alterados e zero em catalog/ ou sources/.  
Snapshot original do run 930: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto catalog-snapshot.sha256 no artefato 13202372616. O run 935 não recalculou o snapshot.  
Histórico: run 930 = baseline e origem do snapshot; run 931 = validação intermediária; run 933 = validação do HEAD anterior 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; run 935 = validação do HEAD-base documental atual.  
Fase A encerrada. Fase B está em implementação real na branch develop/acervo-v2.

## Documentos normativos
Ler ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md e ARCHITECTURE.md antes de mudar contratos. NEXT_TASK.md define a próxima tarefa; EXECUTION_LOG.md mantém evidências.

## Fase A — evidência e histórico
- Run 930 / ID 41573383428: baseline original e snapshot; artifact 13202372616.
- Run 931 / ID 41574547389: validação intermediária; artifact 13202359615.
- Run 933 / ID 41574703366: validação do HEAD anterior 9c938ed...; artifact 13202777349.
- Run 935 / ID 41576192907: validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; 25 testes aprovados, 0 falhas; artifact 13203323544.
- Snapshot original: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto no artefato 13202372616 do run 930. Não recalculado pelo run 935.

## Inventário e achados do baseline
- 2.431 canais.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas.
- Rádios: 1.026; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json existe. Registry: uma fonte.
- Diretório de logos: três arquivos locais, zero imagens.
- Quatro workflows VOD chamam quatro scripts ausentes; update-catalog ainda clona a referência fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB direto declarado. Valores de segredos Supabase não foram inspecionados.

## Próxima etapa
A Fase B já tem contratos, parsers, entrypoints VOD, testes e construção de candidato publicados. Continuar de NEXT_TASK.md e do HEAD remoto atual; não reiniciar o trabalho.

## Limites
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar token TMDB; não inserir branding externo; não remover conteúdo em massa; não promover candidato sem quality gate e rollback. PR #2 permanece aberto como draft e não mesclado.


## INSTRUÇÃO OBRIGATÓRIA PARA QUALQUER NOVA CONVERSA
Leia primeiro e integralmente [ROADMAP_V2.md](ROADMAP_V2.md). Esse documento guarda o cérebro arquitetural e o plano mestre completo do CineHUB-ACERVO V2, incluindo independência operacional, internalização e armazenamento dos dados autorizados, motores, contratos, fontes, todos os domínios, infraestrutura, fases e critérios para chegar a 100%.
Depois leia ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md, ARCHITECTURE.md (se existir), PROJECT_STATUS.md, NEXT_TASK.md e EXECUTION_LOG.md.
- Commit de criação do plano mestre: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Consultar o HEAD vivo da branch ao retomar.
- Fase A: CONCLUÍDA.
- Fase B: EM ANDAMENTO.
- O executor deve receber somente a próxima etapa liberada. Não deve reconstruir o plano por conta própria, pular fases, alterar arquitetura ou mexer em consumidores/main sem aprovação.
- A implementação da Fase B já foi publicada; a continuidade deve preservar catálogos ativos e manter saída apenas em staging.
> **RETOMADA VIGENTE — 2026-11-03 (autoridade sobre registros históricos abaixo)**  
> Branch: `develop/acervo-v2`  
> HEAD confirmado no GitHub: `3d8d143ae387f3340c1efb285fb3199393c25a99`  
> `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`  
> Comparação atual: **45 commits à frente, 0 atrás**, 15 arquivos no diff reportado; a comparação não mostra alterações em `catalog/` ou `sources/`.  
> PR #1 e PR #2 estão abertos em estado draft; nenhum está mesclado. Não alterar nem mesclar nenhum deles nesta etapa.  
> Fase A: CONCLUÍDA. Fase B: **EM ANDAMENTO**, com validação integral pendente. Esta atualização é apenas documental e não conta como implementação da Fase B.  
> Próxima execução autorizada: somente Fase B — auditoria complementar, contratos canônicos, parsers/importadores, fixtures e testes. Não iniciar Fase C.  
> Sempre revalidar HEAD, main, comparação, PRs e workflows no início da execução; estes SHAs são fotografia desta retomada, não valores permanentes.  
> Escopo protegido: não alterar `main`, consumidores TV/Mobile/Web/Player, repositórios de referência, segredos, produção Supabase/Cloudflare, OTA ou publicação oficial. Não promover/substituir catálogo ativo.  
> Fontes de verdade: ler integralmente `ROADMAP_V2.md`, `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.  
> PR #1: https://github.com/mooNXy7/CineHUB-ACERVO/pull/1 — “Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”, draft, aberto, não mesclado.  
> PR #2: https://github.com/mooNXy7/CineHUB-ACERVO/pull/2 — “[DRAFT] ACERVO V2 — Fase A: baseline executável”, draft, aberto, não mesclado. Verificar seus SHAs/diffs ao executar; não assumir que qualquer PR representa a branch de trabalho.  
> 
## Instrução direta ao executor
O responsável autorizou o início da Fase B. Execute a Fase B integralmente conforme o escopo e os critérios de `ROADMAP_V2.md` e `NEXT_TASK.md`, sem solicitar que o responsável repita o plano. A autorização não abrange Fase C, merge, consumidores ou publicação. Revalidar o estado remoto antes de editar.


## HANDOFF VIGENTE — Fase B (2026-11-03)
- HEAD registrado: `cf2148d6dbfa229e5e7fcda25def8aec779c567a`.
- 13 schemas validados; 39 testes aprovados na última execução observada.
- Construção integral do candidato passou; validação integral estava em andamento no run 980 / 41590601634.
- O VOD é processado por shard e o validador lê documentos grandes de forma incremental.
- EPG: 1.014 canais do índice local; sem payload local de programas.
- Assets: associação de logos por canal/rádio; sem imagens locais para MIME/conteúdo/licença.
- Quatro scripts VOD implementados; não executar workflows TMDB online sem a autorização/secret já existente, não alterar segredos.
- Nenhum catálogo ativo, consumidor, main, repositório Fki ou configuração de produção foi modificado. Nenhum merge, publicação ou OTA.
- Próxima ação: confirmar CI integral, idempotência, smoke tests dos quatro entrypoints, artefato completo e métricas. Encerrar somente Fase B; aguardar aprovação antes de Fase C.
