# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** `develop/acervo-v2`  
**Branch estável preservada:** `main`  
**Base da branch V2:** `c2176962dccc218cd17622f0acd786ff76b18a6d`  
**Estado atual:** cérebro V2 documentado e aprovado; implementação funcional ainda não iniciada.

## Missão
Construir o núcleo independente de dados e distribuição do ecossistema CineHUB: On Demand, canais, rádios, logos e EPG, com ingestão, normalização, identidade, enriquecimento, validação, publicação versionada e recuperação.

## Documentos normativos
- `ACERVO_V2_SPEC.md` — o que o sistema deve fazer.
- `ACERVO_V2_BLUEPRINT.md` — arquitetura e como construir.
- `DECISIONS.md` — decisões aprovadas.
- `NEXT_TASK.md` — próxima tarefa executável.
- `EXECUTION_LOG.md` — evidências e histórico.
- `HANDOFF.md` — protocolo de retomada após expiração de conversa.

## Decisões aprovadas
- Fontes independentes são primárias; referências externas são adaptadores opcionais.
- ACERVO mantém IDs, catálogo, regras, índices, histórico e publicação próprios.
- A falha de uma fonte não apaga a última versão válida.
- TMDB usa a integração já configurada no Supabase; nenhum token deve ser duplicado no Git.
- `main` permanece preservada; todo desenvolvimento V2 ocorre em `develop/acervo-v2`.
- TV, Mobile e Web não serão modificados nesta fase.
- Nenhuma OTA ou publicação oficial sem autorização expressa.

## Evidências registradas nesta etapa
- Criado `ACERVO_V2_SPEC.md`: commit `71d88198070344d53b5e0c119c9b7d1691682cd4`.
- Criado `ACERVO_V2_BLUEPRINT.md`: commit `cc40a4ba4aea9ca89b1115a5fe8770641e11b7c3`.
- Atualizados decisões, próxima tarefa, handoff e log para refletir a aprovação e impedir reinício desordenado do trabalho.

## Progresso real
- [x] Branch isolada e documentos de continuidade criados.
- [x] Especificação funcional aprovada e registrada.
- [x] Blueprint técnico aprovado e registrado.
- [x] Ordem de retomada e próxima tarefa registradas.
- [ ] Fase A: baseline executável, inventário e testes de regressão.
- [ ] Fase B: schemas e importadores compatíveis com formatos reais.
- [ ] Fase C: catálogo canônico, identidade, deduplicação e procedência.
- [ ] Fase D: enriquecimento e qualidade por domínio.
- [ ] Fase E: build, snapshots, manifesto, entrega e rollback.
- [ ] Fase F: automação completa e prova de independência.
- [ ] Fase G: integração dos consumidores, somente com autorização posterior.

**Implementação funcional:** 0% concluída.  
**Preparação arquitetural/documental:** concluída nesta etapa. Não confundir documentação com sistema funcional.

## Regra de execução
Não reabrir o planejamento do zero. Executar `NEXT_TASK.md`, registrar evidências e atualizar este status. Uma fase só conta como concluída quando há código funcional, testes executados e critérios de aceite demonstrados.
