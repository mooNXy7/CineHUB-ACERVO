# EXECUTION LOG — CineHUB-ACERVO

## Estado atual e validação mais recente
**HEAD-base validado:** 1908b9adf242129fe85b20731f60ff203e8e7cf4  
**main:** c2176962dccc218cd17622f0acd786ff76b18a6d  
**Comparação no HEAD-base:** 37 commits à frente, 0 atrás; 15 arquivos alterados; 0 em catalog/ ou sources/.  
**Validação desse HEAD-base:** Validate catalog, run 935, ID 41576192907, push, success; 25 testes aprovados, 0 falhas; validador, auditor, py_compile e upload success.  
**Artefato:** 13203323544; acervo-v2-baseline-1908b9adf242129fe85b20731f60ff203e8e7cf4; ZIP SHA-256 1abf5cb68741f5985f0a92a8748ee22fe6d249aa7b8d0e4ce7a0063b81ff53eb.  
Este alinhamento gera um único commit documental filho do HEAD-base acima; após ele, a comparação da branch passa a 38 commits à frente e 0 atrás, mantendo 15 arquivos alterados e zero em catalog/ ou sources/.  
Snapshot original do run 930: 731 arquivos, 314.216.337 bytes, SHA-256 bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e; manifesto catalog-snapshot.sha256 no artefato 13202372616. O run 935 não recalculou o snapshot.  
Histórico: run 930 = baseline e origem do snapshot; run 931 = validação intermediária; run 933 = validação do HEAD anterior 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; run 935 = validação do HEAD-base documental atual.  
Fase A encerrada. Fase B está em implementação; os registros abaixo documentam a execução real.

## Registro consolidado das validações
- **Run 930 / 41573383428:** baseline original, inventário e snapshot; artifact 13202372616; success.
- **Run 931 / 41574547389:** validação intermediária da reconciliação; artifact 13202359615; success.
- **Run 933 / 41574703366:** validação do HEAD anterior 9c938ed...; artifact 13202777349; success.
- **Run 935 / 41576192907:** validação do HEAD-base 1908b9adf242129fe85b20731f60ff203e8e7cf4; artifact 13203323544; success; 25 testes aprovados, 0 falhas.
- O run 935 não recalculou o snapshot original.

## Snapshot original preservado
- Origem: run 930, artifact 13202372616.
- Manifesto: catalog-snapshot.sha256.
- 731 arquivos; 314.216.337 bytes.
- SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.

## Histórico cronológico anterior
Os registros abaixo descrevem o estado observado em cada data/execução; SHAs e comparações antigas são históricos, não representam o HEAD atual.

- Run 930: branch HEAD 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3; runner integration commit d6266bbe5679546e39a63e2724b1460c5465ed4f; baseline original.
- Run 931: HEAD 4e64a79adfcc1b5d88f0b1eeb153b41f0d6ed59f; validação intermediária.
- Run 933: HEAD 9c938ed08cc771fb33d4ff49aba8e5fd2503074d; validação do commit anterior ao alinhamento documental.
- Commit documental previamente validado pelo run 935: 1908b9adf242129fe85b20731f60ff203e8e7cf4. Esta entrada registra o HEAD-base; o commit atual desta correção é filho direto dele.

## Restrições mantidas
Nenhum catálogo ou fonte ativa foi alterado; nenhum consumidor, segredo, configuração de produção ou repositório de referência foi modificado; PRs permanecem draft/não mesclados; Fase B está em andamento.


---

## Retomada documental — 2026-11-03
- HEAD remoto confirmado de `develop/acervo-v2`: `3d8d143ae387f3340c1efb285fb3199393c25a99`.
- `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- Comparação: 45 commits à frente, 0 atrás; 15 arquivos reportados; zero alterações em `catalog/` e `sources/` nesta comparação.
- PR #1 e PR #2: ambos abertos, draft e não mesclados.
- Fase A continua encerrada. Fase B continua sem implementação iniciada; recebeu autorização explícita do responsável para o executor começar.
- Esta atualização apenas corrige a passagem operacional; não representa implementação, validação de código nem execução de workflow da Fase B.
- Não reutilizar os SHAs acima sem revalidar. Ver `NEXT_TASK.md` para o roteiro e os limites da execução.


## Execução da Fase B — 2026-11-03
### Commits
- `b7ff0b15b8713d944b8d857a7b822028ff18c9af`: contratos, parsers, staging e quatro entrypoints VOD.
- `6da90d372ce1c332317a7b429cfd1ff2745ef2d7`: expectativa correta para variante de áudio de episódio.
- `bb2dc858dedcec368e6311244c16888fd38a279c`: import path para scripts executados diretamente.
- `0b37cd73f8a0f52b3f4240ebdb31e92128bc03b8`: contagem correta da fixture M3U.
- `af4ee37ca4f538022b819b834226514a18028e4b`: parser do índice XMLTV local.
- `667a4529692de3807f3f544658de9f6c8e43dec8`: normalizador EPG explícito.
- `093921241ef57d8ae9f25dacf56a6fa88afb619a`: validação de integridade entre domínios.
- `638722caf78ffa5709bdf61d7fc2ebad661552c1`: import regex no validador.
- `98d77f89f6468c688fcd104473ecb9f78726677c`: construção VOD incremental por shard.
- `02b695f035de64ab68119915b88b22cbd7c8740a`: validação incremental via ijson.
- `9b869cd1705cd70550b87e7db95a8024496327af`: resolver de schemas relativo preservado.

### Runs e evidências
- Runs 960–965 falharam por expectativas de teste e importação de pacote; correções registradas nos commits correspondentes.
- Runs 976/977: construção integral do candidato passou; validação subsequente foi cancelada por atualização da branch.
- Runs 978/979: falha na resolução de referências relativas dos sub-schemas durante validação incremental; corrigida em `cf2148d`.
- Run 980 / `41590601634`: 40 testes offline aprovados, compilação Python aprovada, build integral do candidato aprovado; validação integral em andamento na última consulta.
- Artifact 13209354445 (run 976), ZIP SHA-256 `19d59e0b5a5ec3404b4d7182d156b9c50ded0525640d6ca5a34ec9772b26cdf9`, 69.908 bytes; incluía baseline, manifest e report, ainda sem os documentos candidatos completos. O workflow foi alterado para incluir a pasta integral do candidato em runs seguintes.

### Cobertura e limitações
- 13 schemas versionados.
- 40 testes aprovados; cinco domínios cobertos por fixtures/parsers e validação de integridade.
- Índice EPG local: 1.014 canais em quatro feeds normalizados. Sem payload XMLTV local de programas; programmes permanece vazio.
- Logos/assets: associações de canais e rádios; sem arquivos de imagem locais para validar MIME, conteúdo ou licença. Referências externas ficam não verificadas.
- Quatro entrypoints VOD existem; aplicação TMDB permanece em overlays/candidatos. Workflows online não foram executados, nem segredos foram alterados.
- Candidato é staging; nenhum arquivo de catálogo ativo foi substituído.

### Próximas ações
Concluir validação integral, comprovar idempotência, executar smoke tests CLI dos quatro scripts VOD, guardar o conjunto completo de artefatos e atualizar métricas reais/quarentena. Fase B continua EM ANDAMENTO; Fase C não iniciada.


## Atualização — commit `9b869cd1705cd70550b87e7db95a8024496327af`
- 40 testes na suíte: idempotência byte a byte do build com timestamp fixo e smoke test offline dos quatro entrypoints VOD.
- `.github/workflows/validate.yml` agora inclui a pasta completa do candidato no artefato.
- Run 983 / 41591165169: offline tests success; py_compile success; full candidate build success; candidate schema/integrity validation em andamento na última consulta.
