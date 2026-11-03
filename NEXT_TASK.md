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
