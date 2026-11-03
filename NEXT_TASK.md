# Próxima Tarefa — CineHUB-ACERVO

## Estado
**Fase A concluída.** A baseline foi inventariada, testada, executada e protegida por snapshot.

## Próxima tarefa executável — Fase B
Implementar contratos e adaptadores canônicos, guiados pelos formatos reais e pelo blueprint aprovado.

### Ordem técnica
1. Definir schemas versionados para VOD, canais, rádios, logos e EPG, com procedência e IDs estáveis.
2. Implementar os quatro entrypoints VOD ausentes somente depois de definir seu contrato real:
   - scripts/enrich_vod_metadata.py
   - scripts/apply_vod_metadata_patch.py
   - scripts/suggest_vod_tmdb_matches.py
   - scripts/apply_vod_tmdb_id_candidates.py
3. Corrigir os workflows VOD para não depender de branch fixa antiga e validar que cada script chamado existe.
4. Desacoplar o clone fki1976/SaimoPlayer do caminho operacional obrigatório; a referência permanece auxiliar.
5. Criar pipeline de logos com validação de MIME/arquivo, origem e associação; atualmente existem zero imagens locais.
6. Planejar enriquecimento de rádios sem apagar variantes, preencher gêneros por inferência não confirmada ou atribuir logos ambíguos.
7. Preservar snapshot e catálogo ativo até que cada candidato passe pelo quality gate.

## Evidências de referência da Fase A
- GitHub Actions run 921 / ID 41573214240: success.
- 25 testes passaram; validador, auditor e compilação Python aprovados.
- Relatório: reports/baseline/2026-11-03.md e .json.
- Snapshot: 731 arquivos, 314.216.337 bytes, SHA-256 agregado bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- Branch: develop/acervo-v2. main permanece em c2176962dccc218cd17622f0acd786ff76b18a6d.

## Regras
Não alterar main, TV, Mobile ou Web; não publicar OTA; não duplicar TMDB token; não excluir streams por falha pontual; não aplicar TMDB ambíguo; não substituir catálogo ativo sem backup e validação.
