# CineHUB-ACERVO — Estado do Projeto

## Estado atual
**HEAD-base validado:** 1908b9adf242129fe85b20731f60ff203e8e7cf4  
**main:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Comparação no HEAD-base:** 37 commits à frente, 0 atrás; 15 arquivos alterados; 0 em catalog/ ou sources/.  
**Validação desse HEAD-base:** Validate catalog, run 935, ID 41576192907, push, success; 25 testes aprovados, 0 falhas; validador, auditor, py_compile e upload success.  
**Artefato:** 13203323544; acervo-v2-baseline-1908b9adf242129fe85b20731f60ff203e8e7cf4; ZIP SHA-256 1abf5cb68741f5985f0a92a8748ee22fe6d249aa7b8d0e4ce7a0063b81ff53eb.  
Este alinhamento gera um único commit documental filho do HEAD-base acima; após ele, a comparação da branch passa a 38 commits à frente e 0 atrás, mantendo 15 arquivos alterados e zero em catalog/ ou sources/.  
Snapshot original do run 930: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto catalog-snapshot.sha256 no artefato 13202372616. O run 935 não recalculou o snapshot.  
Histórico: run 930 = baseline e origem do snapshot; run 931 = validação intermediária; run 933 = validação do HEAD anterior 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; run 935 = validação do HEAD-base documental atual.  
Fase A encerrada. Fase B é a próxima tarefa planejada e permanece não iniciada nesta correção.

## Missão e decisões aprovadas
ACERVO V2 é o núcleo independente de ingestão, normalização, identidade, enriquecimento, validação, publicação e recuperação de dados CineHUB. Fontes independentes são primárias; referências externas são adaptadores auxiliares. Falha de fonte não apaga a última versão válida. Reutilizar a integração TMDB existente no Supabase; não duplicar tokens.

## Evidência e histórico
- Run 930: baseline original, inventário e snapshot; artifact 13202372616.
- Run 931: validação intermediária da reconciliação documental; artifact 13202359615.
- Run 933: validação do HEAD anterior 9c938ed...; artifact 13202777349.
- Run 935: validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; artifact 13203323544; 25/25 testes.
- O run 935 não recalculou o snapshot original.

## Inventário do baseline (run 930)
- catalog/: 728 arquivos, 314.213.984 bytes; sources/: 3 arquivos, 2.353 bytes.
- Canais: 2.431. VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas.
- Rádios: 1.026; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; 0 IDs duplicados.
- EPG: 6 fontes; channel-map.json presente. Registry: 1 fonte. Logos locais: zero imagens.
- Quatro scripts VOD ausentes; update-catalog ainda clona fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB declarado diretamente. Valores de segredos Supabase não foram inspecionados.

## Snapshot e proteção
731 arquivos; 314.216.337 bytes; SHA-256 agregado bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e. Origem exclusiva: run 930, artefato 13202372616, manifesto catalog-snapshot.sha256. Snapshot preservado, não recalculado nos runs 931/933/935.
A comparação registrada no HEAD-base do run 935 contém 15 arquivos alterados e zero arquivos em catalog/ ou sources/. Após o commit documental, comparação esperada: 38 commits à frente, zero atrás; mesmos 15 arquivos e zero arquivos de catálogo/fontes.

## Próxima etapa
A Fase B é a próxima tarefa planejada, conforme NEXT_TASK.md. Continua não iniciada por esta correção documental.


## Plano mestre integral — continuidade obrigatória
O plano completo do início ao aceite final está em [ROADMAP_V2.md](ROADMAP_V2.md). Este é o documento mestre de fases, arquitetura, dependências, critérios de aceite e retomada. Leia-o integralmente antes de iniciar qualquer nova tarefa.
- Commit que criou o roadmap: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- HEAD atual após consolidação: `42ab0bd8e275adfc413b7049b83882204fb502fb`.
- Fase A: CONCLUÍDA conforme evidências históricas acima.
- Fase B: PRÓXIMA, NÃO INICIADA.
- O roadmap preserva os achados, motores, armazenamento próprio, ingestão de arquivos, independência de repositórios externos, domínios e fases até o aceite final.
- Esta consolidação foi documental: não alterou catálogos, fontes, consumidores, infraestrutura nem publicação.
