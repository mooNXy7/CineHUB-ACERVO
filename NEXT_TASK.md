# Próxima Tarefa — CineHUB-ACERVO

## Estado
**Fase A concluída e reconciliada.** Não iniciar a Fase B nesta tarefa.

## Evidência canônica da Fase A
- Branch: develop/acervo-v2.
- HEAD real auditado: 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3.
- Commit temporário do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- GitHub Actions: Validate catalog, run 930, ID 41573383428 — success.
- Testes: 25 aprovados, 0 falhas.
- Validador, auditor, py_compile e upload do artefato: success.
- Artefato ID 13202372616; nome acervo-v2-baseline-d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Snapshot SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- Comparação com main: 34 commits à frente, zero atrás; nenhum arquivo catalog/ ou sources/ alterado.

## Próxima tarefa planejada — Fase B (não iniciada)
Quando houver autorização para avançar, implementar contratos e adaptadores canônicos guiados pelos formatos reais e pelo blueprint aprovado.

### Ordem técnica já registrada
1. Definir schemas versionados para VOD, canais, rádios, logos e EPG, com procedência e IDs estáveis.
2. Implementar os quatro entrypoints VOD ausentes somente depois de definir seus contratos reais:
   - scripts/enrich_vod_metadata.py
   - scripts/apply_vod_metadata_patch.py
   - scripts/suggest_vod_tmdb_matches.py
   - scripts/apply_vod_tmdb_id_candidates.py
3. Corrigir os workflows VOD para não depender de branch fixa antiga e validar todos os scripts chamados.
4. Desacoplar o clone fki1976/SaimoPlayer do caminho operacional obrigatório; manter referência apenas como adaptador auxiliar.
5. Criar pipeline de logos com validação de MIME/arquivo, origem e associação; atualmente existem zero imagens locais.
6. Enriquecer rádios sem apagar variantes, inventar gêneros ou atribuir logos ambíguos.
7. Preservar snapshot e catálogo ativo até cada candidato passar pelo quality gate.

## Regras permanentes
Não alterar main, TV, Mobile ou Web; não publicar OTA; não duplicar TMDB token; não excluir streams por falha pontual; não aplicar correspondência TMDB ambígua; não substituir catálogo ativo sem backup e validação.
