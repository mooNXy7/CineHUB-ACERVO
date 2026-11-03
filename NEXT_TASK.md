# Próxima Tarefa — CineHUB-ACERVO

## Estado
**Fase A tecnicamente encerrada e documentalmente alinhada.** Não iniciar a Fase B nesta tarefa.

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


## Verificação da reconciliação
- Run 931 / ID 41574547389: success.
- HEAD validado: 4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f.
- 25 testes aprovados; validador, auditor, py_compile e upload aprovados.
- Artefato ID 13202359615; snapshot SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- A Fase B não foi iniciada.


## Validação final disponível — execução 933
- Workflow: **Validate catalog**; run number **933**; Run ID **41574703366**.
- Evento: `push`; branch: `develop/acervo-v2`.
- HEAD validado: `9c938ed08cc771fb33d4ff49aba8e5fd2503074d`.
- Resultado: **success** (run concluído; job `validate` e todas as etapas aprovadas).
- Validador de catálogo, auditor baseline, compilação Python e upload: **success**.
- Testes: **25 aprovados, 0 falhas**.
- Artefato ID **13202777349**; nome `acervo-v2-baseline-9c938ed08cc771fb33d4ff49aba8e5fd2503074d`.
- Digest SHA-256 do ZIP: `cc351b109dbb050b02a095b224da5ba58718c420ffa8bbd42d1ce43c22bdde76`.
- Execução: https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41574703366
- Artefato: https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41574703366/artifacts/13202777349

### Relação entre baseline e validação final
- **Run 930** permanece como baseline original e origem do inventário/snapshot.
- **Run 931** permanece como validação intermediária da primeira reconciliação documental.
- **Run 933** valida o HEAD `9c938ed...` e é a validação final disponível antes deste alinhamento documental.
- O snapshot de 731 arquivos (314.216.337 bytes) e SHA-256 agregado `bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e` foi **preservado**, não recalculado nesta atualização. Sua origem é o baseline do run 930; o manifesto `catalog-snapshot.sha256` está no artefato **13202372616**. Os artefatos posteriores 931 e 933 carregam a evidência versionada, mas não representam um novo cálculo do snapshot original.

### Estado comparativo atual antes deste alinhamento
- `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- `develop/acervo-v2`: `9c938ed08cc771fb33d4ff49aba8e5fd2503074d`.
- **36 commits à frente, 0 atrás**; 15 arquivos alterados na comparação, **0** em `catalog/` ou `sources/`.
- Este commit é somente documental e não altera essa proteção.

A Fase A permanece tecnicamente encerrada. A Fase B permanece planejada e **não iniciada**.
