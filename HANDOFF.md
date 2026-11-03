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
Fase A encerrada. Fase B é a próxima tarefa planejada e permanece não iniciada nesta correção.

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
A Fase B é a próxima tarefa planejada e permanece não iniciada nesta correção. Seguir NEXT_TASK.md e os documentos normativos antes de começar.

## Limites
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar token TMDB; não inserir branding externo; não remover conteúdo em massa; não promover candidato sem quality gate e rollback. PR #2 permanece aberto como draft e não mesclado.


## INSTRUÇÃO OBRIGATÓRIA PARA QUALQUER NOVA CONVERSA
Leia primeiro e integralmente [ROADMAP_V2.md](ROADMAP_V2.md). Esse documento guarda o cérebro arquitetural e o plano mestre completo do CineHUB-ACERVO V2, incluindo independência operacional, internalização e armazenamento dos dados autorizados, motores, contratos, fontes, todos os domínios, infraestrutura, fases e critérios para chegar a 100%.
Depois leia ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md, ARCHITECTURE.md (se existir), PROJECT_STATUS.md, NEXT_TASK.md e EXECUTION_LOG.md.
- Commit de criação do plano mestre: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`. Consultar o HEAD vivo da branch ao retomar.
- Fase A: CONCLUÍDA.
- Fase B: PRÓXIMA, NÃO INICIADA.
- O executor deve receber somente a próxima etapa liberada. Não deve reconstruir o plano por conta própria, pular fases, alterar arquitetura ou mexer em consumidores/main sem aprovação.
- Esta alteração apenas documenta continuidade; não inicia Fase B, não altera catálogos e não publica nada.
