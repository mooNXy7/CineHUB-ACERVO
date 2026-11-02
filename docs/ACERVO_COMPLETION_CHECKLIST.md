# CineHUB ACERVO — checklist de conclusão

Atualizado em 2026-11-02. Este checklist registra entregas verificadas e limitações reais. Não confundir associação estrutural com reprodução funcional.

## Escopo e segurança

- [x] Trabalho isolado em `audit/acervo-hardening-2026-10`.
- [x] PR #1 aberta; branch contém a `main` atual (zero commits atrás).
- [x] O ACERVO é compartilhado por CineHUB TV, Mobile e Web. Os aplicativos consumidores não são alterados nesta fase.
- [x] Nenhum merge, deploy de produção, deploy de Edge Function Supabase ou OTA executado.
- [x] Importação de referência executada em worktree temporária, com aprovação automática desabilitada.
- [x] Nenhuma fusão automática de títulos semelhantes.
- [ ] Revisão humana final e aprovação explícita do merge continuam necessárias.

## 1. Integridade e normalização

- [x] Validação de schemas, IDs, referências cruzadas, índices e shards.
- [x] Testes para normalização, preservação de dados, importação atômica e quarentena.
- [x] Auditorias de duplicidade sem excluir registros por coincidência de título.
- [x] Última validação integral executada no commit `be68382`: 163 testes aprovados.
- [x] Catálogo VOD de referência: 56.250 registros (40.939 filmes, 11.665 séries, 2.750 animes, 896 doramas).
- [ ] Reexecutar auditoria integral de qualidade após todos os checkpoints TMDB restantes.

## 2. VOD / TMDB

- [x] Enriquecimento limitado a registros com TMDB ID numérico já existente.
- [x] Confirmação de ID, título normalizado e ano quando presente.
- [x] Apenas campos vazios são preenchidos: pôster, ano, gêneros e sinopse.
- [x] Campos preenchidos e fontes de reprodução preservados.
- [x] Resposta de recurso inexistente classificada como `not_found` terminal pelo cliente, inclusive quando a Edge Function v4 envolve o 404 em HTTP 500.
- [x] Checkpoints confirmados: offset 0; offset 2.000; offset 3.000; offsets 4.000–8.000; offsets 9.000–13.000.
- [x] Offsets 9.000–13.000: 5.000 examinados, 4.562 registros atualizados, 11.363 campos preenchidos; workflow #41269624509 concluído com sucesso.
- [ ] Checkpoint 14.000–18.000: execução #41322827460 em andamento no último registro.
- [ ] Continuar em lotes de até 5.000 registros, avançando apenas após aplicação, validação, testes e commit confirmados.
- [ ] Gerar métricas finais de campos ausentes e identidade ambígua após o último checkpoint.
- [ ] A correção definitiva do status HTTP da Edge Function Supabase v4 exige autorização para deploy de produção; não executar nesta tarefa.

## 3. Canais e EPG

- [x] 2.431 canais no catálogo.
- [x] 2.110 canais com pelo menos uma referência de transmissão; 321 sem fonte ativa.
- [x] 2.081 canais com logo; 350 sem logo, conforme catálogo na branch em 2026-11-02.
- [x] 715 canais com `epg_id`; 713 IDs encontrados no índice XMLTV e dois não encontrados.
- [x] Seis fontes XMLTV saudáveis na última atualização registrada.
- [x] Parser HTML executado contra páginas reais: 87 programações saudáveis e duas páginas indisponíveis.
- [x] Nickelodeon classificado como falha de parsing no MeuGuia; Adult Swim classificado como HTTP 404 no Guia de TV.
- [x] Ambos preservam associações XMLTV alternativas; nenhum ID aproximado foi inventado.
- [x] Falha de parsing/fetch não substitui programação anterior válida.
- [ ] Encontrar fonte de programação confiável para Nickelodeon e Adult Swim, caso exista.
- [ ] Resolver os dois IDs XMLTV ausentes somente com correspondência explícita e verificada.
- [ ] A cobertura estrutural não comprova reprodução dos streams nem frescor de cada programa.

## 4. Logotipos de canais

- [x] Referência sanitizada de 526 entradas; 526 nomes normalizados únicos, sem duplicidade de chave no manifesto.
- [x] Auditoria do catálogo atual: 2.431 canais, 2.081 com logo e 350 sem logo.
- [x] Antes da correção, 1.410 dos 2.081 endereços preenchidos usavam HTTP e 671 HTTPS.
- [x] Comparação com referências autorizadas SaimoPlayer/Saimo-TV: 234 correspondências exatas; nenhuma das 350 lacunas tinha logo exata disponível.
- [x] Um candidato relaxado (`Loading HD` → `Loading`) foi rejeitado por ser placeholder genérico.
- [x] Nove logos HTTP substituídas por referências HTTPS do manifesto, com nome de canal exato após normalização: Canal Brasil, Lifetime, BIS, Modo Viagem, Curta, DOG TV, Eurochannel, Paramount + 4 e Prime Box Brazil.
- [ ] Permanecem 1.401 logos HTTP sem substituto HTTPS exato no manifesto; não converter esquema automaticamente nem inventar endpoints.
- [ ] Permanecem 350 canais sem logo; precisam de fontes com identidade de marca exata.
- [ ] A disponibilidade HTTP da imagem não foi testada nesta auditoria; HTTPS foi verificado estruturalmente, não por download.

## 5. Rádios

- [x] 753 rádios ativos.
- [x] 753/753 URLs de transmissão HTTPS.
- [x] 273 registros malformados preservados em quarentena; nenhum descarte.
- [x] Nenhum nome ativo contém URL.
- [x] 173 rádios com gênero e 272 com logo.
- [x] Três decisões manuais de gênero documentadas com evidências.
- [ ] 580 rádios continuam sem gênero confiável.
- [ ] 481 rádios continuam sem logo verificado.
- [ ] A referência SaimoPlayer `vod/radios.txt` contém nome e stream, mas não fornece gênero/logo confiáveis para preencher essas lacunas.
- [ ] Não inferir gênero pelo nome nem inventar logotipos ou endpoints.

## 6. Workflows e documentação

- [x] Workflows existentes revisados; nenhum workflow redundante criado.
- [x] Workflow de atualização do catálogo #41269881662 concluído com sucesso.
- [x] Workflow de validação #41323007565 concluído com sucesso: 163 testes aprovados.
- [x] Default do próximo checkpoint TMDB avançado para 14.000.
- [x] Marcadores temporários de checkpoint removidos e ignorados pelos workflows de enriquecimento.
- [x] Documentação TMDB atualizada para refletir o processo real.
- [ ] Aguardar conclusão do checkpoint atual e da revisão de IDs TMDB enfileirada.
- [ ] Revalidar o head final da branch e confirmar checks verdes antes de retirar o Draft.
- [ ] Atualizar este checklist e o worklog com os resultados finais.

## Critério de conclusão

O ACERVO estará tecnicamente pronto para revisão quando:
1. Todos os lotes TMDB planejados tiverem resultado terminal (aplicados ou classificados como revisão/not_found).
2. A validação integral e os testes passarem no head final.
3. Canais, EPG, rádios e quarentena tiverem métricas finais documentadas.
4. Pendências sem fonte confiável estiverem classificadas, sem dados inventados.
5. Workflows e documentação estiverem coerentes com a implementação.
6. A PR estiver revisada e pronta para aprovação.

**Estado atual:** em execução. PR #1 permanece aberta e em Draft. Nenhum merge, deploy de produção, deploy Supabase ou OTA autorizado.
