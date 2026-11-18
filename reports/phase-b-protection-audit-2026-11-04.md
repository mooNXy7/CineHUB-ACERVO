# CINEHUB-ACERVO V2 — Auditoria de proteção, automações e aceite técnico

- Data: 2026-11-04
- Repositório: `mooNXy7/CineHUB-ACERVO`
- Branch de trabalho: `develop/acervo-v2`
- HEAD de entrada: `94ad349d455b336d63d4aab345c0d3409a26650c`
- HEAD da `main` verificado: `106dbb8aafa87cc14162c147732a7e185e185edb`
- PR #2: aberto, draft, não mesclado; cabeça `94ad349`, base `main`.
- Estado: **Fase B NÃO apresentada para aceite**. Os testes passam, mas há bloqueios de proteção e reconciliação de dados.

## 1. Resumo executivo

1. Runs 1004 e 1005 terminaram em sucesso, mas validaram árvores diferentes: Run 1004 validou o HEAD da branch; Run 1005 validou um merge virtual do PR #2 com a `main`.
2. A `main` possui um workflow legado que faz commits e push automáticos diretamente para `main`, sem aprovação humana. Ele já existia desde 2026-10-15 e foi mantido em commits do proprietário em 2026-11-03. Sua existência é histórica e deliberada, mas conflita com a decisão D-002, aprovada em 2026-11-03, de manter `main` estável e só integrar após aprovação explícita.
3. O Run 211 reimportou a referência Fki/SaimoPlayer e reduziu o índice de filmes de 40.938 para 32.637 itens, removendo 87 shards antigos de filmes após reconstrução. O código tenta preservar e mesclar dados antigos, mas a equivalência registro a registro ainda não foi comprovada.
4. O Run 212 atualizou o índice XMLTV; o candidato do merge PR identificou 148 IDs XMLTV duplicados da fonte `open-epg-br` e os colocou em quarentena.
5. A correção de identidade de My Name (2021) está aplicada no candidato: TMDB 110356, ID `series-my-name`, 8 episódios, 16 URLs únicas e 55 referências de provedor no artefato do Run 1005.
6. Dos 257 registros históricos de rádio em quarentena, 255 foram recuperados por correspondência exata com a referência, mas todos permanecem `unverified`; dois continuam sem stream recuperado.
7. EPG e logos não estão concluídos: 60 mapeamentos permanecem ambíguos, não há programação XMLTV local, e as 2.271 associações de logos não correspondem a assets locais com MIME/conteúdo/licença verificados.

## 2. Validação dos Runs 1004 e 1005

### Run 1004 — push da branch

- [Run 1004](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41892356556); evento `push`; workflow `Validate ACERVO V2` (ID 385789050).
- HEAD validado: `94ad349d455b336d63d4aab345c0d3409a26650c`; resultado `success`.
- 47 testes offline; 13/13 schemas; compilação; build integral; integridade; idempotência byte a byte de 11 arquivos.
- Artefato [13354583678](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41892356556/artifacts/13354583678), 73.111.234 bytes.
- SHA-256 do ZIP: `33cdb50b802ebfe887c2cb60ac6c8516170b821fc10c52d7d420e963208dde5c`.
- Métricas: 52.602 VOD; 2.437 canais; 1.026 rádios; 1.014 canais EPG; 18 resolvidos e 60 ambíguos; 0 programas XMLTV locais; 2.271 associações de logos; 257 itens em quarentena; 787.175 variantes de streams/episódios com IDs únicos.

### Run 1005 — validação do PR #2

- [Run 1005](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41892369131); evento `pull_request`; PR #2 ainda draft e não mesclado.
- HEAD do PR: `94ad349d455b336d63d4aab345c0d3409a26650c`.
- Árvore virtual: merge commit `69e7acd690f529de01f7e9bdeae53f71ea818cc8`, com pais `106dbb8aafa87cc14162c147732a7e185e185edb` (main) e `94ad349d455b336d63d4aab345c0d3409a26650c` (branch).
- Resultado `success`; 47 testes offline; 13/13 schemas; compilação; build integral; integridade; idempotência byte a byte de 11 arquivos.
- Artefato [13354648094](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41892369131/artifacts/13354648094), 82.494.793 bytes.
- SHA-256 do ZIP: `4ded5f4d5e7db8347f599f98706f9765c8733918f78d71056e419013ce8fd334`.
- Métricas do candidato de merge: 44.341 VOD; 2.437 canais; 1.026 rádios; 1.017 canais EPG; 18 resolvidos e 60 ambíguos; 0 programas XMLTV locais; 2.271 associações de logos; 405 itens em quarentena; 769.092 variantes únicas.
- Os 405 itens em quarentena são 257 rádios (255 recuperados e 2 pendentes) mais 148 canais XMLTV duplicados da fonte `open-epg-br`.

**Interpretação:** os dois sucessos não são métricas intercambiáveis. Run 1004 valida o snapshot de `develop/acervo-v2`; Run 1005 valida a árvore virtual do PR com a `main` atual. O PR #2 não foi mesclado e o merge commit virtual não moveu nenhuma branch.

## 3. Investigação da movimentação da main

### Workflow e gatilho

- Workflow responsável: [`.github/workflows/update-catalog.yml` na main](https://github.com/mooNXy7/CineHUB-ACERVO/blob/main/.github/workflows/update-catalog.yml).
- Workflow ID: `385789067`, nome `Update catalog`.
- Permissão: `contents: write`.
- Gatilhos: agendamento diário (`23 8 * * *` UTC), `push` em caminhos de fontes/scripts e `workflow_dispatch`.
- No final, executa commit e `git push origin HEAD:${GITHUB_REF_NAME}`. Em execução agendada na branch padrão, o destino é `main`. Não abre PR nem aguarda aprovação humana.

### Histórico e autorização anterior

O workflow foi introduzido na fundação do ACERVO em 2026-10-15 e recebeu commits do proprietário:
- `c9220a0` — fundação do ACERVO e automação.
- `5bb5eea` — atualização por mudanças nas fontes.
- `e13236d` — descoberta completa agendada da referência.
- `15225d2` — ignorar importação pesada quando a referência não muda.
- `6181dde` — correção do proprietário do repositório SaimoPlayer.
- `2102733` — prevenção de auto-disparo em 2026-11-03; removeu `catalog/epg/**` e o próprio YAML do filtro de push, mas manteve o agendamento e o push automático.

Portanto, a automação de ingestão/atualização já fazia parte do fluxo legado intencional do ACERVO. A estratégia de fontes independentes e referência auxiliar também consta da decisão D-001. Entretanto, a decisão D-002, aprovada em 2026-11-03, determina que `main` permaneça estável e que integração à `main` ocorra somente após validação e aprovação explícita. Não foi encontrada aprovação posterior que excepcione D-002 para permitir promoção automática direta. **Há uma contradição de governança a resolver.** Esta auditoria não desativou nem alterou o workflow.

### Run 211 — importação da referência

- [Run 211](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41673175722), evento `schedule`, 2026-11-03.
- Base: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- SHA da referência Fki/SaimoPlayer atualizado: `41b2c62769fdf049165b2fedb19cc70473fe2c2d`; SHA anterior: `0549ec355b8572df5d2b921d842195c4be941922`.
- Importação registrada: 769.326 fontes adicionadas; 1.129.890 referências de provedor adicionadas; 316.560 URLs ignoradas pelo filtro de segurança; 32.637 filmes; 11.705 séries; 2.749 animes; 896 doramas; 1.026 rádios; 2.431 canais.
- Commit criado: [`d3cd659`](https://github.com/mooNXy7/CineHUB-ACERVO/commit/d3cd6592da8620f4ef672539df2c9c3e6325cb15), pai `c2176962`.
- Comparação de árvores: 87 shards antigos de filmes removidos; 626 shards VOD restantes modificados; nenhum novo caminho de shard criado. Os 87 removidos pertenciam somente a `catalog/vod/details/movies/`.
- Manifesto: filmes 40.938 → 32.637 (-8.301); séries 11.665 → 11.705 (+40); animes 2.749 (sem mudança); doramas 896 (sem mudança).

O importador carrega detalhes e índices existentes, mescla fontes, referências de provedor e episódios, deduplica registros por TMDB/título-ano e só depois remove shards que não fazem mais parte da distribuição nova. Isso é compatível com reconstrução/deduplicação e não prova, por si só, perda de conteúdo. Porém, a validação executada é estrutural; não foi encontrada comparação completa de cada identidade/episódio/provedor antes e depois. A redução de 8.301 entradas de filmes precisa de reconciliação registro a registro antes de declarar integridade histórica integral.

### Run 212 — atualização diária

- [Run 212](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41866946989), evento `schedule`, 2026-11-04.
- Importação pesada Fki ignorada porque o SHA da referência não havia mudado desde Run 211.
- Fonte M3U `public-brazil-broadcasters`: 6 canais verificados; sem alterações no catálogo.
- Atualizador EPG: seis fontes saudáveis; 713 registros de canais mapeados.
- Normalizador: 2.431 canais; nenhum registro removido.
- Commit criado: [`106dbb8`](https://github.com/mooNXy7/CineHUB-ACERVO/commit/106dbb8aafa87cc14162c147732a7e185e185edb), pai `d3cd659`; três arquivos alterados: catálogo de canais, saúde EPG e índice XMLTV compacto.
- A fonte `open-epg-br` passou a reportar 307 canais e 20.666 programas no health snapshot. Na validação do merge PR, 148 IDs dessa fonte foram classificados como `duplicate_xmltv_channel_id` e colocados em quarentena.

### Publicação, histórico e rollback

O workflow não executou deploy, publicação em Cloudflare/R2/Supabase, release ou OTA. A ação observada foi commit/push no próprio repositório GitHub. Isso ainda altera o conteúdo disponível na `main` e pode afetar consumidores que leiam diretamente essa branch, embora nenhum repositório consumidor tenha sido modificado nesta auditoria.

A sequência de commits é linear e preservada: `c2176962 → d3cd659 → 106dbb8`. Não houve force-push. A árvore anterior continua acessível no histórico; rollback por revert seria tecnicamente possível, mas **não foi executado** e depende de autorização separada.

## 4. Integridade dos rádios

Auditoria do artefato do Run 1002 e confirmação no Run 1005:
- 1.026 registros de rádio.
- 257 itens na quarentena histórica: 255 com motivo `image_url_in_audio_stream` e 2 sem resolução.
- 255 registros em `sources/reference/radio-recovery.json`, com IDs únicos, linhas de referência únicas, URLs recuperadas únicas e `match_count = 1`.
- Método: `casefold_and_trim_trailing_slash`.
- Cada item recuperado mantém identidade, referência/commit/blob, linha, URL original, URL recuperada e resultado da correspondência.
- O candidato contém 255 streams recuperados com `stream_added=true`, mas status `unverified`. Correspondência de referência não equivale a teste de reprodução.
- Dois pendentes:
  - `radio-https-hts02-brascast-com-9758-live`
  - `radio-https-radiomec-stream-ebc-com-br-ebc-radiomec-playlist-m3u8`

A quarentena não deve ser interpretada como 257 falhas atuais: 255 registros foram recuperados como dados, mas continuam historicamente rastreados e sem validação de reprodução. Dois permanecem sem stream. Nenhum stream recuperado foi promovido a catálogo ativo por esta auditoria.

A referência Fki usada no recovery não possui licença encontrada no snapshot. Isso não invalida a evidência técnica de correspondência, mas permanece dependência de autorização para eventual redistribuição.

## 5. Auditoria VOD — My Name (2021)

No candidato do Run 1004 e novamente no candidato do merge do Run 1005:
- ID canônico: `series-my-name`.
- TMDB: `110356`; tipo `dorama`; ano `2021`.
- Título de exibição preservado: `Meu Nome é`; alias: `My Name`.
- Seções de origem: `series` e `doramas`.
- IDs legados preservados: `series-meu-nome-e` e `series-my-name`.
- `legacy_id_conflict=false`; duas referências de índice corrigidas pelo override.
- 8 episódios, cada um com variante dublada e legendada: 16 variantes/URLs únicas.
- 33 referências de provedor únicas no candidato do Run 1004; 55 no candidato do Run 1005, após incorporar referências presentes na árvore atualizada da main.
- Valores brutos legados (TMDB 2317) permanecem no raw/proveniência; o candidato usa TMDB 110356.

A identidade canônica está correta. O título localizado `Meu Nome é` não representa um segundo registro; `My Name` permanece como alias e título canônico da evidência de referência. As variantes, episódios e referências de provedor foram consolidados em um único registro canônico no candidato.

## 6. EPG

- 60 mapeamentos continuam ambíguos; 18 estão resolvidos. Nenhuma associação forçada foi feita.
- Run 1004: 1.014 canais EPG, sem quarentena EPG adicional.
- Run 1005: 1.017 canais EPG e 148 registros em quarentena, todos de `open-epg-br` por `duplicate_xmltv_channel_id`.
- Quatro feeds XMLTV e dois serviços HTML permanecem registrados; a fonte `EPG-Scrapper-BR` está atualizada, mas não foi localizada licença explícita para internalização/redistribuição.
- Programas XMLTV locais: 0. Não declarar EPG concluído; o catálogo depende de feeds externos e não há programação local válida internalizada.

## 7. Logos e assets

- 2.271 associações lógicas no candidato.
- Associação não equivale a URL de imagem válida, arquivo armazenado, MIME identificado, conteúdo validado ou licença.
- Não foram baixadas imagens nesta auditoria.
- Não há evidência de assets locais com MIME/conteúdo/hash/licença verificados. URLs candidatos permanecem não verificados.
- A estratégia de armazenamento e as permissões de uso/redistribuição precisam ser confirmadas antes de internalizar assets.

## 8. Entry points e workflows V2

Os quatro entrypoints foram revisados:
- `enrich_vod_metadata.py`: consulta IDs TMDB já existentes e gera propostas apenas para metadados ausentes; declara `catalog_mutated=false`.
- `apply_vod_metadata_patch.py`: aplica propostas somente em overlay/staging, preservando campos preenchidos e streams.
- `suggest_vod_tmdb_matches.py`: gera sugestões de ID em modo somente leitura; não atribui IDs.
- `apply_vod_tmdb_id_candidates.py`: aceita apenas candidato único com título, tipo e ano exatos; escreve em overlay/staging, não na árvore ativa.

Workflows da branch V2:
- `enrich-vod-metadata.yml` e `suggest-vod-tmdb-ids.yml`: somente `workflow_dispatch`, permissão `contents: read`, artefatos de revisão; token TMDB permanece no Supabase.
- `update-catalog.yml` em `develop/acervo-v2`: somente `workflow_dispatch`, permissão `contents: read`, gera snapshot candidato e artefato.
- `validate.yml`: push/PR/manual, permissão `contents: read`, valida e gera artefato; não faz commit/push de catálogo.

Nenhum desses workflows V2 promove automaticamente o candidato para catálogo ativo. O único escritor automático identificado é o workflow legado da `main` descrito na seção 3.

## 9. Bloqueios para aceite da Fase B

1. **Governança da main:** resolver a contradição entre o workflow legado de push automático e D-002. Não modificar/desativar sem autorização explícita.
2. **Preservação VOD da atualização main:** reconciliar as 8.301 entradas de filmes a menos entre manifesto anterior e posterior, demonstrando que cada identidade, episódio, variante e provider ref foi preservado ou deduplicado justificadamente.
3. **EPG:** tratar os 148 IDs duplicados de `open-epg-br`; resolver os 60 mapeamentos ambíguos; internalizar programação XMLTV válida somente após licença/permissão.
4. **Logos:** esclarecer licença/proveniência e validar MIME/conteúdo antes de armazenar ou distribuir imagens.
5. **Rádios:** validar reprodução dos 255 streams recuperados sem promovê-los antes do teste; classificar os dois pendentes.
6. **Independência:** comprovar que o catálogo V2 pode ser construído/servido sem depender de referência externa operacional.

## 10. Proteções mantidas nesta auditoria

- Nenhuma alteração feita na `main`.
- Nenhum consumidor TV/Mobile/Web/PLAYER modificado.
- Nenhum PR mesclado; PR #1 e PR #2 continuam draft.
- Nenhum catálogo ativo publicado; nenhum OTA; nenhum deploy externo.
- Nenhum segredo alterado.
- Nenhum dado apagado manualmente.
- Nenhum candidato promovido.
- Fase C não iniciada.

**Parecer:** validação técnica estrutural aprovada nos Runs 1004/1005; integridade histórica completa e governança de promoção ainda não comprovadas. A Fase B permanece **EM ANDAMENTO** e não está pronta para aceite. Esta auditoria aguarda decisão explícita do responsável sobre a automação legada da `main` e as reconciliações pendentes.
