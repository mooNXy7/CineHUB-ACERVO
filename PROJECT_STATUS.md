# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** \`develop/acervo-v2\`  
**HEAD auditado da branch:** \`3c4d2f7b2c4177e09745f6979860c95ffc8f39a3\`  
**Commit temporário do runner na validação 930:** \`d6266bbe5679546e39a63e2724b1460c5465ed4f\`  
**main preservada:** \`c2176962dccc218cd17622f0acd786ff76b18a6d\`  
**Comparação atual antes deste alinhamento:** 36 commits à frente, 0 atrás; 15 arquivos alterados no total, nenhum em `catalog/` ou `sources/`.  
**Estado:** Fase A concluída; reconciliação documental baseada na execução 930.

## Missão e decisões aprovadas
ACERVO V2 é o núcleo independente de ingestão, normalização, identidade, enriquecimento, validação, publicação e recuperação de dados CineHUB. Fontes independentes são primárias; referências externas são adaptadores auxiliares. Falha de fonte não apaga a última versão válida. Reutilizar a integração TMDB existente no Supabase; não duplicar tokens. Não alterar main, TV, Mobile ou Web; não publicar OTA.

## Evidência canônica da Fase A
GitHub Actions **Validate catalog**, run **930**, ID **41573383428**:
- Branch: develop/acervo-v2.
- HEAD real da branch: 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3.
- Commit temporário do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Conclusão: success.
- Validador de catálogo: success.
- Auditor baseline: success.
- unittest: 25 testes aprovados, 0 falhas.
- py_compile: success.
- Upload de artefato: success.
- Artefato ID 13202372616; nome acervo-v2-baseline-d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Digest SHA-256 do ZIP: f7474e0132200ff522e8c82e2b85a20494c3776f4bd0c88b66a835a3c27ae690.
- Snapshot SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.

## Inventário executado no run 930
- catalog/: 728 arquivos, 314.213.984 bytes.
- sources/: 3 arquivos, 2.353 bytes.
- normalizer/: 1 arquivo, 311 bytes.
- scripts/: 6 arquivos, 79.560 bytes.
- tests/: 3 arquivos, 12.713 bytes.
- reports/: 3 arquivos, 7.600 bytes no checkout auditado pelo runner.
- .github/workflows/: 4 arquivos, 16.460 bytes.
- Nenhum manifesto de dependências/configuração padrão foi encontrado na raiz entre os nomes verificados.
- Canais: 2.431.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas; índices presentes e contagens conferem.
- Rádios: 1.026; 2 streams ausentes; 754 logos ausentes; 1.026 gêneros ausentes; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json presente.
- Registry de fontes: 1 entrada.
- Diretório de logos: 3 arquivos locais, mas zero imagens.
- Quatro scripts VOD ausentes em dois workflows.
- update-catalog ainda clona fki1976/SaimoPlayer.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB declarado diretamente. Valores de segredos Supabase não foram inspecionados.

## Correção técnica incluída
Importador de rádios aceita o formato real nome|stream e mantém compatibilidade com o formato legado. URLs com extensão de imagem não são aceitas como streams novos. Catálogos existentes não foram reescritos.

## Proteção dos catálogos
Snapshot de 731 arquivos em catalog/ e sources/, total de 314.216.337 bytes.
SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
Manifesto individual incluído no artefato 13202372616. Nenhum catálogo foi alterado na diferença de 34 commits com main.

## Próxima etapa
A Fase B continua apenas como próxima tarefa planejada, conforme NEXT_TASK.md. Não foi iniciada nesta reconciliação documental.

## Limites permanentes
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar TMDB token; não remover conteúdo por falha pontual; não aplicar correspondências TMDB ambíguas; não promover catálogo candidato sem quality gate, snapshot e rollback.


## Validação da reconciliação documental
- GitHub Actions run 931, ID 41574547389, evento push na branch develop/acervo-v2.
- HEAD validado: 4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f.
- Conclusão success; validador, auditor, 25 testes, py_compile e upload aprovados.
- Artefato ID 13202359615, nome acervo-v2-baseline-4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f.
- Digest ZIP SHA-256: 9909dc289a4782a4a6eddf852578143afe27415efa20f53f104a0aade9f44000.
- O baseline.json desse artefato confirma o HEAD 4e64a79... e o snapshot SHA-256 agregado bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.


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
