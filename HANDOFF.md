# Transferência de Contexto — CineHUB-ACERVO

## Repositório e estado
- Repositório: https://github.com/mooNXy7/CineHUB-ACERVO
- Branch: develop/acervo-v2
- HEAD validado pela execução final disponível 933: 9c938ed08cc771fb33d4ff49aba8e5fd2503074d.
- Commit temporário de integração do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- main preservada: c2176962dccc218cd17622f0acd786ff76b18a6d.
- Comparação atual antes deste alinhamento: 36 commits à frente, zero atrás; zero arquivos catalog/ ou sources/ alterados.
- TV, Mobile, WEB e PLAYER não foram modificados.

## Documentos normativos
Ler ACERVO_V2_SPEC.md, ACERVO_V2_BLUEPRINT.md, DECISIONS.md e ARCHITECTURE.md antes de mudar contratos. NEXT_TASK.md define a próxima tarefa; EXECUTION_LOG.md mantém evidências.

## Fase A — evidência canônica reconciliada
- GitHub Actions: Validate catalog, run 930, ID 41573383428 — success.
- Branch HEAD: 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3.
- SHA temporário do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Validador do catálogo: success.
- Auditor baseline: success.
- unittest: 25 testes aprovados, zero falhas.
- py_compile: success.
- Upload de artefato: success.
- Artefato ID 13202372616; nome acervo-v2-baseline-d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Digest SHA-256 do ZIP: f7474e0132200ff522e8c82e2b85a20494c3776f4bd0c88b66a835a3c27ae690.
- Snapshot: 731 arquivos, 314.216.337 bytes.
- SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- Manifesto por arquivo incluído no artefato 13202372616.

## Inventário e achados
- 2.431 canais.
- VOD: 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas; índices presentes e contagens conferem.
- Rádios: 1.026; 2 sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem em stream_url; 10 logos não HTTPS; zero IDs duplicados.
- EPG: 6 fontes; channel-map.json existe.
- Registry de fontes: uma fonte.
- Diretório de logos: três arquivos locais (README e dois .gitkeep), zero imagens.
- Quatro workflows; dois workflows VOD chamam quatro scripts ausentes (dois cada).
- update-catalog ainda clona a referência fki1976/SaimoPlayer.
- Workflows referenciam duas funções Supabase; nenhum segredo TMDB direto declarado. Valores de segredos Supabase não foram inspecionados.
- Nenhum manifesto convencional de dependências/configuração encontrado entre os nomes raiz verificados.

## Correção feita
Importador de rádios aceita o formato real nome|stream e o formato legado. URLs com extensão de imagem são rejeitadas como streams importados e ficam em revisão. Catálogos existentes não foram apagados ou reescritos.

## Próxima etapa
Fase B permanece planejada, mas **não foi iniciada**. Consultar NEXT_TASK.md quando o responsável autorizar a continuação.

## Limites
Não alterar main, TV, Mobile, Web ou repositórios de referência; não publicar OTA; não duplicar token TMDB; não inserir branding externo; não remover conteúdo em massa; não promover candidato sem quality gate e rollback. PR #2 permanece aberto como draft e não mesclado.


## Validação da reconciliação documental
- Run 931, ID 41574547389, evento push, conclusão success.
- HEAD validado: 4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f.
- 25 testes aprovados; validador, auditor, compilação e upload aprovados.
- Artefato ID 13202359615: acervo-v2-baseline-4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f.
- SHA-256 do snapshot: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.


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
