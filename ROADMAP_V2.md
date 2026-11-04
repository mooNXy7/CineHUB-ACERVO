# CINEHUB-ACERVO V2 — PLANO MESTRE INTEGRAL

> **ESTADO VIGENTE — 2026-11-04:** a branch `develop/acervo-v2` está no HEAD `5e2150f3c0f48075edacb56b70111304f797d25d`. Run 1002 (`41744148492`) passou 47 testes offline, 13 schemas, compilação, build integral, integridade e idempotência. A Fase B continua **EM ANDAMENTO**, não 100% nem concluída. A reconciliação autoritativa e as limitações atuais estão na seção 21 e em [reports/phase-b-quality-audit-2026-11-04.md](reports/phase-b-quality-audit-2026-11-04.md). Todos os SHAs/métricas anteriores são históricos quando não coincidem com esse adendo.

> **Documento mestre de continuidade, arquitetura, execução e aceite final.**  
> Branch de trabalho: `develop/acervo-v2`  
> Estado deste plano: consolidado a partir da especificação, do blueprint, do histórico disponível e do diagnóstico arquitetural fornecido pelo responsável do projeto.  
> **Regra de autoridade:** este documento organiza a jornada integral; `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md` e `DECISIONS.md` continuam normativos para requisitos e decisões. Em caso de divergência, não improvisar: registrar a divergência e reconciliar com o responsável.

## 0. Como usar este documento

Este arquivo é a memória operacional de longo prazo do CineHUB-ACERVO V2. Uma conversa ou executor novo deve lê-lo integralmente, junto com os documentos normativos e o estado real do repositório, antes de propor ou executar mudanças.

O plano contém o destino completo, mas **a execução é liberada uma etapa por vez**. O executor recebe somente a próxima etapa autorizada, implementa, testa, apresenta evidências e atualiza este documento. Não deve antecipar fases dependentes de aprovação.

### Estados permitidos

- `CONCLUÍDA`: implementação real, critérios de aceite atendidos e evidências registradas.
- `EM ANDAMENTO`: execução iniciada, ainda sem aceite completo.
- `NÃO INICIADA`: planejada, sem execução.
- `BLOQUEADA`: depende de acesso, infraestrutura, correção ou decisão.
- `AGUARDANDO APROVAÇÃO`: tecnicamente preparada, mas exige autorização explícita.

Nunca marcar uma fase como concluída apenas porque foi planejada, documentada, porque um workflow foi criado ou porque um workflow isolado ficou verde. A conclusão exige comportamento funcional, testes, evidências e atualização do histórico.

### Regra de retomada

Ao iniciar uma nova conversa:
1. Ler este documento por inteiro.
2. Ler `ACERVO_V2_SPEC.md`, `ACERVO_V2_BLUEPRINT.md`, `DECISIONS.md`, `ARCHITECTURE.md` (se existir), `PROJECT_STATUS.md`, `NEXT_TASK.md`, `EXECUTION_LOG.md` e `HANDOFF.md`.
3. Conferir o HEAD real de `develop/acervo-v2`, PRs, workflows e arquivos atuais. Não presumir que o HEAD registrado anteriormente continua atual.
4. Conferir o checklist e as evidências da última fase concluída.
5. Identificar a próxima tarefa liberada e executar somente ela.
6. Ao concluir, atualizar este documento e os documentos operacionais na mesma mudança lógica, sem criar estados contraditórios.
7. Nunca pedir ao usuário que reconte decisões já registradas aqui.

## 1. Missão e resultado final

O ACERVO V2 será o **núcleo central, próprio, independente e auditável de dados do ecossistema CineHUB**. Não será apenas uma coleção de JSONs ou playlists e não será um espelho passivo de um repositório de terceiros.

O sistema deverá descobrir fontes, coletar e preservar os arquivos recebidos, importar formatos distintos, interpretar, normalizar, resolver identidades, deduplicar sem perder variantes, enriquecer metadados, validar qualidade, gerar catálogos próprios, versionar, publicar, monitorar e recuperar falhas.

### 1.1 Princípio central de independência

O CineHUB-ACERVO mantém seus próprios:
- arquivos e registros coletados e autorizados;
- arquivo bruto e histórico de ingestão;
- contratos, identificadores e regras de negócio;
- catálogo canônico e índices derivados;
- metadados enriquecidos e associações;
- variantes de fontes de reprodução e sua procedência;
- relatórios, versões publicadas e mecanismos de recuperação.

Fontes externas e repositórios de referência podem ajudar a descobrir ou importar dados. **Não podem ser dependência operacional obrigatória** para processar, gerar, publicar ou servir os catálogos já internalizados. Desativar um adaptador de referência não pode impedir o ACERVO de operar sobre os dados que já possui.

Os aplicativos CineHUB consomem catálogos e contratos publicados pelo ACERVO. Não devem conhecer a estrutura interna dos provedores nem consultar repositórios externos para resolver índices, IDs, streams, metadados ou arquivos auxiliares.

O ACERVO administra metadados e referências de reprodução; não hospeda nem reivindica propriedade sobre obras audiovisuais. A internalização de playlists, URLs ou metadados não transfere direitos sobre o conteúdo. Somente fontes e assets cuja utilização/redistribuição seja permitida podem ser publicados.

### 1.2 Domínios cobertos

- On Demand: filmes, séries, temporadas, episódios, animes e doramas.
- Canais ao vivo: identidade, categorias, aliases, logos, EPG e variantes de transmissão.
- Rádios: estação, gênero, idioma/país quando conhecido, logo e variantes de áudio.
- Logos e assets visuais: coleta/referência, validação, associação e fallback.
- EPG: feeds XMLTV/API, mapeamento de canais, programação, timezone, cache e cobertura.
- Dados auxiliares: gêneros, fichas/detalhes, destaques, índices, listas alfabéticas, partições e demais artefatos necessários aos consumidores.

### 1.3 Critério de sucesso final

O projeto só estará 100% concluído quando os domínios previstos forem processados por pipelines reproduzíveis, os dados forem armazenados e administrados pelo próprio ACERVO, as fontes externas forem substituíveis, os catálogos e contratos estiverem validados, a publicação versionada e o rollback forem demonstrados, a operação automática for observável e os consumidores autorizados tiverem sido integrados e testados sem depender da estrutura interna de fontes externas.

## 2. Princípios arquiteturais permanentes

1. **Canonical-first:** contratos internos são a fonte de verdade; formatos externos são adaptadores.
2. **Independence-by-design:** fontes externas são substituíveis; nenhum repositório de referência é runtime obrigatório.
3. **Own-and-retain:** dados e arquivos de entrada autorizados são internalizados e preservados conforme política de retenção, com origem e hash.
4. **Raw-before-transform:** preservar o original antes de converter ou normalizar.
5. **Determinístico e idempotente:** a mesma entrada repetida não cria duplicatas nem muda IDs.
6. **Candidate-before-active:** gerar e testar candidato isolado antes de promover.
7. **Fail-safe:** falha de coleta não significa remoção de conteúdo.
8. **Observable:** cada execução informa o que leu, importou, alterou, rejeitou, enriqueceu e publicou.
9. **Consumer compatibility:** contratos e saídas são explícitos; consumidores não acessam fontes de terceiros diretamente.
10. **Preserve provenance:** cada registro/campo relevante deve permitir rastrear fonte, método, data, hash, confiança e transformação.
11. **Small-device aware:** índices e catálogos particionados devem evitar downloads enormes e consumo excessivo em TV Boxes.
12. **Provider-neutral:** GitHub, Cloudflare e Supabase têm responsabilidades condicionadas à auditoria real de recursos, limites, custos e permissões; regras de negócio não podem ficar presas a um fornecedor.
13. **No silent destructive changes:** fusões ambíguas, remoções em massa e mudanças incompatíveis exigem evidência, política e revisão.
14. **One authorized stage at a time:** o plano é integral, mas o executor só implementa a próxima etapa liberada.

## 3. Referências técnicas e auditoria de origem

A investigação arquitetural fornecida pelo responsável identificou cinco repositórios de referência associados ao ecossistema Fki/Gabriel:

| Repositório | Papel estudado |
|---|---|
| SaimoPlayer | Catálogos, fontes, processamento e geração |
| SaimoTV-Android | Consumo em Android TV |
| Saimo-TV | Aplicação Web |
| Saimo-Cell-V2 | Aplicação Mobile |
| SaimoWin | Aplicação Windows nativa |

Links autorizados conhecidos no histórico do projeto:
- `https://github.com/fki1976/SaimoPlayer`
- `https://github.com/fki1976/SaimoTV-Android`
- `https://github.com/fki1976/Saimo-TV`
- `https://github.com/fki1976/Saimo-Cell-V2`
- `https://github.com/fki1976/SaimoWin`

Há registro histórico de divergência de namespace/perfil (incluindo a menção a `fkuller`). Não presumir que perfis diferentes são equivalentes; confirmar repositório e autorização antes de acessar. Referências são somente leitura/estudo. Não modificar esses repositórios.

### 3.1 O que a investigação já identificou

A estrutura de referência não se limita a um arquivo único. Foram identificados conceitos de:
- catálogo de canais e rádios;
- catálogo VOD e índices;
- listas alfabéticas e arquivos particionados;
- divisões de séries e episódios;
- destaques, gêneros e fichas;
- fontes alternativas e listas auxiliares/reserva.

O SaimoWin documenta um catálogo de origem com cerca de 30 MB dividido por letras e blocos de séries, com índice para carregar apenas as partes necessárias. Isso sustenta a decisão proposta de catálogo particionado com índices e manifestos, mas os limites e a estratégia final devem ser dimensionados no ambiente CineHUB.

Foram identificados scripts/componentes de referência com responsabilidades distintas:
- `atualizar_tudo.sh`: orquestração;
- `atualizar_nexus.py`, `atualizar_frostview.py`, `atualizar_mgeb.py`, `atualizar_fenix.py`, `atualizar_pipocacine.py`: atualização por fonte/provedor;
- `gerar_vod.py`, `gerar_generos.py`, `gerar_imdb.py`, `gerar_destaques.py`;
- `limpar_duplicatas.py`, `remove_dead_links.py`;
- `parse_radios.py`, `organizar_canais_importados.py`, `testar_fontes_vod.py`;
- `gerar_embedplayer_filmes.py`, `gerar_embedplayer_series.py`.

Também foram identificados `Sources/generos.swift`, `Sources/ficha.swift` e `src/epg.rs` no estudo dos consumidores. O EPG observado inclui duas fontes XMLTV, uma fonte Pluto TV, prioridade, aliases de canais, cache local de seis horas, janela passada/futura e processamento fora da thread principal. Esses são achados de referência, não requisitos copiados automaticamente: validar aplicabilidade, licenças, formato e comportamento antes de adotar.

### 3.2 Auditoria complementar ainda necessária

A auditoria anterior identificou arquitetura e componentes, mas não comprovou leitura exaustiva de todos os arquivos dos cinco repositórios. Portanto, antes de fechar decisões dependentes dessas referências, executar uma matriz de leitura somente quando a etapa correspondente for liberada:
- scripts restantes, dependências, entradas, saídas, ordem e falhas;
- manifestos, índices, partições, fontes, logos, fichas, gêneros e EPG publicados;
- contratos reais consumidos por TV, Web, Mobile e Windows;
- diferenças de plataforma e compatibilidade;
- licença, permissão, procedência e viabilidade de cada dado/adaptador.

Não copiar aplicações nem código integralmente. Reaproveitar apenas estruturas e ideias tecnicamente úteis, com identidade própria CineHUB. Não inserir marca Saimo em interface, nomes de produto ou documentação pública. Proveniência técnica interna e conformidade legal devem ser registradas quando aplicável.

## 4. Diagnóstico inicial conhecido do ACERVO

A branch `develop/acervo-v2` contém uma estrutura inicial com diretórios/áreas como `catalog/channels`, `catalog/radios`, `catalog/vod`, `catalog/epg`, `catalog/logos`, `sources`, `normalizer`, `scripts`, `tests`, `reports` e workflows. A árvore proposta neste documento é destino conceitual, não afirmação de que todos os componentes já existam.

### 4.1 Métricas da baseline da Fase A

Valores históricos registrados no baseline:
- canais: 2.431;
- filmes: 40.938;
- séries: 11.665;
- animes: 2.749;
- doramas: 896;
- rádios: 1.026;
- EPG: 6 fontes;
- 252 URLs com extensão de imagem em campo de stream (contagem corrigida);
- rádios sem gênero: 1.026;
- rádios sem logo: 754;
- rádios sem stream: 2;
- IDs de rádio duplicados: 0;
- quatro índices VOD presentes e contagens compatíveis com o manifesto;
- três arquivos locais de logos na última execução reportada;
- quatro scripts VOD ausentes na branch auditada;
- updater principal ainda apresentava dependência de clone do SaimoPlayer.

Esses números são baseline histórico, não necessariamente contagens atuais. Recalcular apenas na etapa apropriada e registrar diferenças, sem sobrescrever a referência histórica.

### 4.2 Problemas concretos identificados

**A. Dependência externa:** um cliente de TV consultava `vod/indice.txt` no repositório de referência para resolver referências de provedores. Isso contradiz a independência. O ACERVO deverá internalizar os dados necessários e manter a referência externa somente como procedência/adaptador opcional. A correção do consumidor pertence à fase de integração, não às fases de núcleo.

**B. Rádios:** auditoria de 1.026 registros encontrou 1.026 sem gênero, 754 sem logo e 232 com URL de imagem no campo de transmissão. Outra contagem posterior da baseline reportou 252 URLs de imagem em campos de stream no conjunto auditado. A diferença deve ser explicada pela população/execução/critério antes de comparar. O parser de rádio já foi corrigido para aceitar formato de duas colunas mantendo compatibilidade legado e rejeitar URL de imagem como stream; os demais problemas de enriquecimento/associação continuam pendentes até comprovação.

**C. Workflows VOD:** foram encontrados dois workflows que chamavam quatro scripts ausentes:
- `scripts/enrich_vod_metadata.py`
- `scripts/apply_vod_metadata_patch.py`
- `scripts/suggest_vod_tmdb_matches.py`
- `scripts/apply_vod_tmdb_id_candidates.py`

Não considerar automação VOD funcional até implementar e testar os entrypoints e reconciliar os workflows.

**D. Volume e particionamento:** o V2 contém muitos detalhes VOD particionados. É necessário dimensionar armazenamento, quantidade de arquivos, tamanho de transferências, limites/custos e estratégia de cache antes de escolher distribuição. Não presumir GitHub como banco de dados de blobs grandes.

**E. EPG, logos, destaques e fontes:** há estruturas iniciais, mas pipeline completo, cobertura, associações e qualidade ainda precisam de evidência funcional.

## 5. Arquitetura funcional alvo — os oito blocos

1. **SOURCE HUB — Cadastro e política de fontes:** registro de fontes, domínio, formato, licença/permissão, prioridade, escopo, método de coleta, agendamento, credenciais referenciadas, limites, retry e estado.
2. **COLLECTOR — Coleta:** conectores HTTP/Git/M3U/JSON/XMLTV/APIs/arquivos; preserva payload original, timestamp, hash e procedência.
3. **PROCESSING ENGINE — Processamento:** parsers, normalização, identidade, deduplicação, associação de variantes e classificação.
4. **ENRICHMENT ENGINE — Enriquecimento:** TMDB, imagens, gêneros, elenco, sinopse, logos, aliases e dados complementares.
5. **QUALITY ENGINE — Qualidade:** disponibilidade, formato, integridade, duplicação, cobertura, anomalias, quarentena e políticas.
6. **CATALOG BUILDER — Geração:** catálogos canônicos, manifestos, índices, partições, detalhes, gêneros, destaques e exportações.
7. **PUBLISHER — Publicação:** snapshots versionados, verificação de integridade, promoção controlada e rollback.
8. **CONSUMERS — Distribuição:** TV, Mobile e Web consomem contratos estáveis e versões publicadas, sem conhecer fontes internas.

### 5.1 Motores especializados

| Motor | Responsabilidade |
|---|---|
| Source Engine | Descobrir, cadastrar e controlar fontes |
| Import Engine | Ler e importar formatos diferentes |
| Normalization Engine | Padronizar campos, nomes e categorias |
| Identity Engine | Resolver IDs internos e externos |
| Deduplication Engine | Detectar duplicatas sem perder variantes |
| Health Engine | Medir disponibilidade e qualidade |
| Metadata Engine | Buscar e atualizar metadados |
| Logo Engine | Descobrir, validar e associar logos |
| EPG Engine | Coletar e consolidar programação |
| Catalog Engine | Construir catálogos, índices e partições |
| Release Engine | Versionar, promover e publicar |
| Recovery Engine | Recuperar falhas e restaurar versões |

Uma falha em um motor/domínio não deve interromper os demais. Cada motor precisa ter entradas, saídas, contratos, logs, testes e execução isolável.

## 6. Pipeline ponta a ponta

`Descoberta → Registro de fonte → Coleta → Arquivo bruto → Parse → Normalização → Identidade → Deduplicação → Enriquecimento → Validação → Quarentena/revisão → Catálogo candidato → Comparação → Quality Gate → Snapshot → Publicação → Manifesto ativo → Monitoramento → Recuperação/rollback`

1. Descobrir fontes permitidas e registrar procedência, formato e política.
2. Verificar quais fontes precisam de atualização.
3. Coletar com timeout, limite de tamanho, rate limit e retry.
4. Preservar o payload original em armazenamento próprio adequado, com hash e metadados.
5. Executar parser específico; formatos desconhecidos ficam isolados e reportados.
6. Normalizar sem perder valor original.
7. Resolver IDs internos e externos com evidência e confiança.
8. Deduplicar entidades reais, preservando variantes, streams, logos e procedências.
9. Enriquecer metadados e relações, registrando origem/confiança.
10. Validar schemas, integridade, links, formatos, cobertura e anomalias.
11. Colocar registros suspeitos/ambíguos em quarentena, sem descarte silencioso.
12. Construir candidato isolado, índices, partições e manifestos.
13. Comparar com a última versão válida e aplicar thresholds/regressões.
14. Publicar snapshot imutável; atualizar o ponteiro/manifesto ativo por último.
15. Monitorar saúde e preservar fallback.
16. Em falha, retomar checkpoint ou apontar manifesto para a versão anterior.

### 6.1 Proteção de dados e falhas

- Falha de rede, timeout ou fonte vazia inesperada não equivale a exclusão.
- Uma única falha pontual não remove stream nem entidade.
- Desativação de variante exige política com falhas em janelas separadas e evidência.
- Fonte removida, conteúdo expirado e indisponibilidade temporária devem ser estados distintos.
- Catálogo ativo nunca é substituído por candidato inválido.
- Quarentena preserva payload, motivo e possibilidade de revisão/recuperação.
- Toda operação destrutiva deve ter diff, justificativa, backup e rollback.

## 7. Contratos e identidade dos dados

Os contratos serão JSON Schema versionados e validados em CI. Os campos abaixo são requisitos conceituais; nomes e tipos finais devem ser definidos após examinar os dados reais e contratos dos consumidores.

### 7.1 Entidade canônica

- ID interno estável, tipo, título canônico e aliases;
- idioma, país, categorias/gêneros e metadados;
- IDs externos tipados (TMDB/IMDb etc.), opcionais;
- relações hierárquicas (série/temporada/episódio);
- procedência por fonte/campo, método, data, hash/versão e confiança;
- created/updated timestamps e schema_version.

### 7.2 Variantes de reprodução

- ID próprio, entity_id, tipo/protocolo, URL ou referência protegida;
- prioridade, source_id, status, última verificação;
- contagem de falhas, último erro e evidência de validação.

Não armazenar URL de imagem no campo de stream. Não imprimir credenciais em URL/log.

### 7.3 Asset/logo

- ID, entidade associada, URL/caminho, MIME real, dimensões quando disponíveis;
- source_id, status, is_primary, data de validação;
- fallback e aliases de associação.

Validar conteúdo real do arquivo, não confiar apenas em extensão.

### 7.4 EPG

- fontes XMLTV/API e política de prioridade;
- canal EPG, aliases e mapeamento explícito para channel_id;
- programa, título, descrição, início/fim com timezone;
- janela temporal, cache, retenção, atualização e cobertura.

Rejeitar intervalos inválidos e preservar timezone/original quando necessário.

### 7.5 IDs e deduplicação

IDs internos não dependem da ordem de arquivos, posição em listas, URL do provedor ou título mutável. Usar IDs externos confiáveis quando tipo/idioma/ano forem coerentes; caso contrário matching composto com título normalizado, ano, tipo, idioma, temporada/episódio e duração quando disponível.

Matcher deve produzir score, evidências e decisão:
- alta confiança: auto-match somente conforme threshold conservador aprovado;
- faixa intermediária: revisão/candidato;
- baixa confiança: manter entidade distinta/candidato.

Não fundir variantes de streams, logos e procedências. Registrar aliases e histórico quando identidade mudar. Mudanças de IDs precisam ser compatíveis com favoritos, histórico e referências persistentes dos consumidores.

## 8. Enriquecimento e metadados

### 8.1 TMDB

- Reutilizar integração/token já existente no Supabase; não duplicar segredo.
- Resolver por ID confirmado primeiro; busca textual gera sugestão, não verdade automática.
- Cache, rate limit, retry/backoff, checkpoint e execução incremental.
- Atualizar apenas campos permitidos, ausentes ou desatualizados conforme política.
- Preservar valores manuais e sua procedência.
- Salvar candidatos, score e diferenças antes de aplicar correspondências ambíguas.
- Relatórios separam enriquecidos, já atualizados, não encontrados, ambíguos, falhas e ignorados.
- Não bloquear outros domínios quando TMDB estiver indisponível.

### 8.2 Dados auxiliares VOD

Gerar, quando aplicável e validado:
- índices gerais e por tipo;
- índices alfabéticos/letras;
- partições/shards por tamanho/quantidade;
- detalhes/fichas por ID estável;
- gêneros;
- destaques calculados a partir de dados confiáveis;
- relações de temporadas e episódios;
- variantes de fontes de reprodução;
- manifestos que permitam carregar somente partes necessárias.

A estratégia deve reduzir transferência e memória em TV Box. Não replicar cegamente a estrutura de referência: medir tamanhos, número de arquivos, latência e compatibilidade.

### 8.3 Logos e imagens

Descobrir/coletar fontes permitidas, validar MIME e conteúdo, associar por identidade e confiança, manter aliases/fallback e relatório de cobertura. Não associar por semelhança de nome sem evidência suficiente. Preservar logos já válidos se uma fonte falhar.

### 8.4 Destaques

Destaques devem ser derivados de metadados confiáveis e regras explícitas (popularidade/curadoria/recência, conforme fontes permitidas). Não inventar ranking nem publicar cards sem identidade/dados suficientes. Separar pipeline de geração de sua apresentação no app.

## 9. Domínios: entregas específicas

### 9.1 On Demand — filmes, séries, temporadas, episódios, animes e doramas
- Importar todos os formatos atuais e mapear campos.
- Consolidar identidade interna e IDs externos.
- Resolver hierarquia série/temporada/episódio.
- Preservar múltiplas fontes/variantes por conteúdo.
- Corrigir quatro scripts VOD ausentes identificados na baseline.
- Corrigir workflows que chamam scripts inexistentes ou usam branch fixa antiga.
- Enriquecer metadados TMDB com matching seguro e checkpoints.
- Gerar índices, partições, gêneros, fichas e destaques.
- Validar contagens, integridade referencial e compatibilidade.
- Testar busca, paginação/partições e consumo de detalhes.

### 9.2 Canais ao vivo
- Importar M3U/M3U8, JSON e demais formatos identificados.
- Canonicalizar nome, aliases, categoria, país/idioma quando disponível.
- Manter várias variantes de transmissão com prioridade e procedência.
- Associar logos e EPG IDs de forma explícita.
- Validar protocolo, conteúdo e saúde sem apagar por falha pontual.
- Gerar grupos/categorias e índices compatíveis.
- Medir cobertura de logos, EPG e fontes alternativas.

### 9.3 Rádios
- Suportar formatos de origem identificados, incluindo formato duas colunas `Nome|URL` e legado.
- Rejeitar imagens no campo de stream e validar protocolos de áudio.
- Manter IDs estáveis, nomes, aliases, gêneros, país/idioma quando conhecidos, logos e variantes.
- Não inventar gênero ou logo; ausência deve ser reportada.
- Tratar streams ausentes/inválidos por quarentena e política, sem apagar outras variantes.
- Melhorar cobertura por fontes autorizadas e fallback.
- Validar contagem, duplicação, URL, MIME/conteúdo e regressão.
- Preservar os resultados já concluídos na etapa de rádios, verificando evidências antes de repetir trabalho.

### 9.4 Logos
- Catálogo próprio de assets e associações.
- Ingestão e validação de arquivos/URLs.
- Detecção de duplicatas por hash/conteúdo.
- Associação por IDs e aliases confiáveis.
- Fallback e relatório de cobertura por domínio.
- Política de retenção e direitos de uso.

### 9.5 EPG
- Cadastro de feeds XMLTV/API e políticas.
- Coletores isolados, cache e janela temporal.
- Parser robusto, timezone e validação de horários.
- Mapeamento channel_id ↔ epg_channel_id com aliases e confiança.
- Prioridade/fusão entre fontes e relatório de cobertura.
- Preservação da última grade válida durante falhas.
- Teste de atualização, cache, conflito e recuperação.

## 10. Motores operacionais e workflows

- Workflows devem chamar somente entrypoints existentes.
- Falhar cedo e claramente se dependência/script estiver ausente.
- Jobs por domínio/rotina pesada com dependências explícitas.
- Lock/concurrency para evitar publicação simultânea.
- Timeout, retry/backoff, checkpoint e cancelamento seguro.
- Execução agendada e manual reproduzível.
- Segredos referenciados por nome, nunca escritos em arquivos/logs.
- Relatório JSON e resumo humano por execução.
- Artefatos: logs resumidos, métricas, diff, candidato, manifesto e evidências.
- Falha de um domínio não bloqueia domínios independentes.
- Não usar clone de SaimoPlayer como caminho operacional obrigatório; adaptadores de referência são opcionais.

## 11. Armazenamento, infraestrutura e distribuição

A decisão final depende de auditoria real de recursos ativos, permissões, limites, custos e volume. Não presumir que serviço está configurado.

| Plataforma | Papel candidato | Condição |
|---|---|---|
| GitHub | código, schemas, configs versionadas, testes, workflows, docs e artefatos pequenos | não virar banco de blobs/catálogo gigante |
| Cloudflare R2 | arquivo bruto, imagens e arquivos grandes | confirmar conta, bucket, permissões, custo e política |
| Cloudflare Pages | distribuição de catálogos estáticos/manifestos | confirmar limites, build e volume |
| Cloudflare Workers | API, resolução de versões e cache | confirmar recursos e necessidade real |
| Supabase | estado operacional, filas/checkpoints e integração segura existente | inventariar schema, Edge Functions, storage, secrets e limites; não duplicar catálogo sem necessidade |
| TMDB | fonte externa de metadados | usar integração/token já existente de forma segura |

### 11.1 Auditoria obrigatória de infraestrutura

- Inventariar recursos ativos Cloudflare e Supabase.
- Confirmar buckets, Workers, Pages, Functions, tabelas, secrets, limites e permissões.
- Medir tamanho de raw, catálogo, shards, logos e taxa de atualização.
- Comparar custo/latência/limites de milhares de arquivos pequenos versus objetos agregados.
- Definir política de retenção, lifecycle, cache, versionamento e backup.
- Registrar decisão e alternativa de migração.
- Não criar infraestrutura paga nem alterar recursos de produção sem autorização.

### 11.2 Contrato de distribuição

Consumidores consultam manifesto estável que identifica versão, schema, URLs/paths, hashes, tamanhos, índices e partições. Devem conseguir baixar somente dados necessários, validar hash e usar cache/fallback. A lógica de domínio permanece independente do provedor de hosting.

## 12. Testes, qualidade e segurança

Testes obrigatórios, ampliados por domínio:
1. Unitários: parsers, normalização, matching, dedupe, prioridade e validação.
2. Fixtures: amostras reais sanitizadas de cada formato, incluindo rádio duas colunas e legado.
3. Contrato: JSON Schema, tipos, relações e compatibilidade.
4. Integração: ingestão até candidato com dependências simuladas.
5. Regressão: nenhum registro válido perdido sem justificativa e evidência.
6. Falhas: timeout, fonte vazia, JSON/XML truncado, rate limit, URL de imagem em stream, IDs conflitantes e mídia inválida.
7. Idempotência: duas execuções iguais não duplicam nem alteram IDs.
8. Proveniência: todo dado importado/enriquecido rastreável.
9. Independência: desativar adaptador de referência não impede build, validação, publicação nem consumo de dados internalizados.
10. Publicação: candidato inválido não promove; falha parcial não altera manifesto; rollback restaura versão.
11. Segurança: sem tokens em logs, URLs ou arquivos; limites e políticas de fonte respeitados.
12. Desempenho: build, transferência, memória, cache e navegação por partições em dispositivos de baixo recurso.

Quality Gate mínimo:
- schemas válidos;
- integridade referencial;
- nenhum catálogo vazio inesperado;
- variações de contagem dentro de thresholds ou justificadas;
- sem perda massiva de streams;
- sem IDs conflitantes não resolvidos;
- sem URLs de imagem em campos de stream;
- hashes/tamanhos/manifestos coerentes;
- regressões aprovadas;
- diff e relatório revisados;
- aprovação explícita para mudanças massivas ou publicação oficial.

## 13. Plano integral por fases

A sequência abaixo cobre a jornada do estado atual até a operação e integração final. A divisão poderá ser refinada com descobertas técnicas, mas nenhuma obrigação do cérebro pode ser descartada. Alterar ordem ou escopo exige registrar motivo e impacto.

### Fase A — Baseline executável
**Estado: CONCLUÍDA**

Objetivo: congelar e compreender o estado inicial sem alterar catálogos ativos.

Entregas/evidências registradas:
- snapshot/manifesto e inventário;
- auditoria de scripts/workflows;
- parser de rádio corrigido para formato duas colunas com compatibilidade legado;
- rejeição de URL de imagem em campo de stream;
- fixtures e testes específicos;
- validador, auditoria read-only e relatórios;
- 25 testes aprovados no run 935;
- documentação histórica reconciliada.

Referências históricas:
- commit base validado: `1908b9adf242129fe85b20731f60ff203e8e7cf4`;
- correção documental posterior: `8967eb303de13b3c69c69bc453d425eb11dede92`;
- run 935: `41576192907`, success;
- artefato: `13203323544`;
- snapshot original run 930: 731 arquivos, 314.216.337 bytes, SHA-256 `bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e`;
- quatro scripts VOD ausentes e dependência do clone de referência permaneceram como pendências, não como itens resolvidos.

Aceite: encerrada conforme documentação histórica. Não reabrir sem evidência concreta de regressão.

### Fase B — Auditoria complementar, contratos canônicos e importadores
**Estado: EM ANDAMENTO — implementação e validação técnica em execução na branch develop/acervo-v2**

Objetivo: transformar formatos reais em contratos canônicos executáveis e fechar a matriz de entradas/saídas.

Tarefas:
- conferir estado/HEAD e ler documentos normativos;
- inventariar formatos e arquivos atuais de cada domínio;
- completar auditoria de scripts/workflows do ACERVO e identificar todos os entrypoints ausentes;
- completar investigação de referências autorizadas apenas nos pontos necessários, em modo somente leitura;
- criar schemas versionados para common/provenance, VOD, channels, radios, logos e EPG;
- definir contratos de source, stream variant, asset, EPG mapping/program e report;
- implementar parsers/importadores por formato e domínio;
- suportar rádio duas colunas e formatos legados;
- criar fixtures sanitizadas e testes unitários/contrato;
- produzir relatórios de incompatibilidade e campos não mapeados;
- garantir IDs/proveniência preservados na conversão;
- manter saídas candidatas isoladas, sem substituir catálogos ativos.

Aceite:
- schemas validados por CI;
- fixtures cobrem formatos reais conhecidos;
- parsers determinísticos/idempotentes;
- entradas inválidas isoladas com motivo;
- provenance preservada;
- nenhum catálogo ativo alterado;
- testes e relatório de cobertura aprovados.

### Fase C — Source Hub e independência de ingestão
**Estado: NÃO INICIADA**

Objetivo: ACERVO possuir cadastro e conectores próprios de fontes, sem clone/repositório externo obrigatório.

Tarefas:
- criar registro declarativo de fontes por domínio;
- registrar licença/permissão, formato, escopo, prioridade, método, credenciais referenciadas, limites, retry e saúde;
- implementar descoberta/ativação/desativação controlada;
- implementar coletores HTTP/Git/M3U/JSON/XMLTV/API/arquivos conforme fontes reais;
- preservar payload bruto, timestamp, hash e metadados de coleta;
- armazenamento próprio para raw, staging e quarentena;
- checkpoint e retomada;
- adaptadores de referência opcionais, isolados e desligáveis;
- testar operação com todos os adaptadores de referência desativados;
- garantir que dados internalizados continuem processáveis sem a origem estar disponível.

Aceite:
- ingestão reproduzível a partir de fontes registradas;
- raw archive recuperável e auditável;
- fonte externa substituível;
- desligar referências não interrompe build/publicação dos dados existentes;
- segredos protegidos;
- política de origem/licença documentada.

### Fase D — Núcleo canônico: identidade, normalização e deduplicação
**Estado: NÃO INICIADA**

Objetivo: construir a camada que converte importações em entidades próprias consistentes.

Tarefas:
- normalização global de títulos, nomes, categorias, idiomas, países, aliases e campos;
- preservação de valores originais;
- IDs internos estáveis por entidade;
- resolução de IDs externos tipados;
- matcher composto com score/evidência;
- deduplicação conservadora e revisão de ambiguidades;
- associação de variantes de streams, logos e procedências;
- relações de série/temporada/episódio;
- aliases/histórico de IDs;
- migração candidata dos catálogos existentes;
- relatórios de duplicação, conflito e perda potencial.

Aceite:
- execução idempotente;
- IDs não dependem de posição/título/URL de provedor;
- nenhuma fusão ambígua silenciosa;
- variantes e procedência preservadas;
- comparação demonstra ausência de perda injustificada.

### Fase E — Catálogo On Demand e enriquecimento TMDB
**Estado: NÃO INICIADA**

Objetivo: completar VOD com identidade, metadados, detalhes, índices e fontes próprias.

Tarefas:
- implementar os quatro entrypoints VOD ausentes identificados na Fase A;
- corrigir workflows VOD e eliminar branch fixa antiga;
- garantir que todo script chamado exista e seja testado;
- integrar com TMDB por credencial já existente no Supabase, sem duplicar token;
- resolver por IDs confirmados; busca textual gera candidatos;
- implementar cache, rate limit, backoff, checkpoints e lotes retomáveis;
- preservar dados manuais/proveniência;
- fila de revisão para correspondências ambíguas;
- enriquecer filmes, séries, animes, doramas, temporadas e episódios;
- gerar gêneros, fichas, imagens e dados auxiliares;
- construir índices gerais, alfabéticos e por tipo;
- definir partições/shards e manifestos para carregamento parcial;
- gerar destaques com regras verificáveis;
- preservar múltiplas variantes de reprodução;
- medir qualidade/cobertura por tipo e relatório de não encontrados/ambíguos.

Aceite:
- pipelines VOD completos e executáveis;
- TMDB idempotente, seguro e rastreável;
- nenhum match ambíguo aplicado automaticamente;
- relações hierárquicas válidas;
- índices/partições reproduzíveis;
- compatibilidade e desempenho medidos;
- falha TMDB não impede outros domínios.

### Fase F — Canais ao vivo
**Estado: NÃO INICIADA**

Objetivo: catálogo de canais independente, com fontes alternativas, grupos, logos e EPG IDs.

Tarefas:
- inventariar e importar fontes permitidas;
- normalizar nomes, aliases, grupos, categorias, idioma/país;
- gerar IDs estáveis;
- consolidar duplicatas mantendo variantes;
- validar streams por protocolo/conteúdo e saúde;
- definir prioridade/fallback;
- associar logos com confiança;
- associar EPG IDs e aliases;
- relatório de cobertura e canais sem mapeamento;
- testar atualização e falha de cada fonte.

Aceite:
- catálogo canônico consistente;
- variantes e procedência preservadas;
- nenhuma remoção por falha pontual;
- cobertura de categorias, logos e EPG reportada;
- exportações compatíveis testadas.

### Fase G — Rádios
**Estado: NÃO INICIADA / histórico parcial a reconciliar**

Objetivo: completar o domínio rádio, aproveitando correções já realizadas sem refazer trabalho validado.

Tarefas:
- conferir commits/relatórios da etapa anterior de rádios;
- reconciliar 1.026 registros históricos e métricas atuais;
- preservar parser duas colunas e compatibilidade legado;
- validar URL de áudio e rejeitar imagem;
- normalizar nome, aliases, gênero, idioma/país;
- buscar gêneros/logos somente em fontes confiáveis;
- associar logo e fallback;
- manter múltiplas variantes e prioridade;
- quarentena para stream inválido/ausente;
- monitorar saúde sem remoção automática;
- criar relatório de cobertura, falhas e duplicatas.

Aceite:
- importação determinística;
- nenhuma imagem em campo de áudio;
- IDs estáveis e sem duplicatas não justificadas;
- gênero/logo ausente explicitamente reportado, sem invenção;
- streams e variantes preservados;
- testes de falha e regressão aprovados.

### Fase H — Logos e assets
**Estado: NÃO INICIADA — parcialmente relacionada às etapas anteriores**

Objetivo: catálogo próprio de logos/assets com associação confiável e qualidade.

Tarefas:
- inventariar arquivos locais e URLs;
- definir política de origem/licença;
- coletar/importar assets permitidos;
- validar MIME, assinatura/conteúdo, tamanho e dimensões;
- deduplicar por hash;
- associar por ID/alias com score e evidência;
- distinguir logo de canal, estação e imagens VOD;
- criar fallback e política de ausência;
- gerar relatórios de cobertura e assets órfãos;
- preservar versão anterior quando fonte falhar.

Aceite:
- associação auditável;
- nenhum asset ambíguo aplicado silenciosamente;
- MIME/conteúdo validados;
- duplicatas tratadas;
- fallback testado;
- cobertura por domínio mensurada.

### Fase I — EPG completo
**Estado: NÃO INICIADA**

Objetivo: EPG como subsistema próprio e independente.

Tarefas:
- inventariar fontes XMLTV/API e permissões;
- cadastrar prioridade, formato, janela e agendamento;
- implementar coletores/parsers;
- normalizar timezone e intervalos;
- mapear channel_id ↔ epg_channel_id por aliases/evidências;
- consolidar múltiplas fontes sem apagar última grade válida;
- cache, retenção e janela passada/futura configuráveis;
- relatório de cobertura, conflitos e canais sem programação;
- executar processamento fora de rotinas sensíveis de interface (responsabilidade do backend);
- testar falha, cache, conflito e recuperação.

Aceite:
- feeds processados e validados;
- mapeamento auditável;
- programação temporal consistente;
- cache e prioridade demonstrados;
- falha de feed preserva última grade válida.

### Fase J — Quality Engine, observabilidade e recuperação operacional
**Estado: NÃO INICIADA**

Objetivo: tornar o sistema mensurável, recuperável e seguro em operação contínua.

Tarefas:
- health checks para fontes, streams, logos e feeds;
- classificar reachable, timeout, HTTP error, invalid content, unsupported protocol e unknown;
- políticas de falhas em janelas separadas;
- thresholds por domínio e fonte;
- quarentena com motivo, origem e caminho de recuperação;
- métricas de cobertura, frescor, duplicatas, erros e volume;
- logs estruturados sem segredos;
- relatórios por run/domínio;
- alertas e runbooks;
- retries, checkpoints, locks e cancelamento seguro;
- recuperação após falha parcial;
- provar que falha de um domínio não corrompe os outros.

Aceite:
- falhas classificadas corretamente;
- sem remoção indevida por falha temporária;
- retomada testada;
- relatórios/alertas acionáveis;
- regressão entre domínios aprovada.

### Fase K — Infraestrutura definitiva e armazenamento
**Estado: NÃO INICIADA — depende de auditoria de recursos e aprovação quando houver custo/produção**

Objetivo: escolher e configurar o armazenamento e a distribuição próprios do ACERVO com base em dados reais.

Tarefas:
- concluir inventário Cloudflare/Supabase;
- medir raw, staging, quarantine, catálogos, shards, logos e crescimento;
- decidir o que fica em GitHub, R2, Pages, Workers e Supabase;
- implementar abstração de storage/provider;
- definir versionamento, retenção, backup, cache, lifecycle e acesso;
- implementar upload/download e verificação de hashes;
- testar limites, custo, latência e escala;
- registrar plano de migração/rollback;
- não criar serviço pago ou alterar produção sem autorização.

Aceite:
- decisão técnica baseada em inventário/medição;
- dados brutos e arquivos grandes em camada apropriada;
- GitHub não usado como banco de blobs;
- lógica independente do provedor;
- backup/retention e permissões testados.

### Fase L — Catalog Builder, snapshots, publicação e rollback
**Estado: NÃO INICIADA**

Objetivo: transformar dados canônicos em releases imutáveis e servir uma versão ativa segura.

Tarefas:
- gerar catálogos e índices por domínio;
- gerar partições/shards e manifestos;
- validar schema, relações, hashes, tamanhos e contagens;
- comparar candidato com versão ativa;
- quality gate com thresholds e bloqueios;
- snapshots imutáveis;
- promoção atômica, manifesto ativo atualizado por último;
- cache e fallback;
- rollback para versão anterior;
- retenção e limpeza separadas da publicação;
- testar falhas antes/durante/depois do upload e promoção.

Aceite:
- candidato inválido nunca promove;
- promoção atômica demonstrada;
- rollback demonstrado;
- consumidores podem validar hash e selecionar partes;
- última versão válida preservada.

### Fase M — Operação autônoma e orquestração de ponta a ponta
**Estado: NÃO INICIADA**

Objetivo: executar atualização do ACERVO de forma automatizada, reproduzível e independente.

Tarefas:
- orquestrador de pipeline com dependências explícitas;
- rotinas isoladas por domínio;
- agendamento e execução manual;
- locks/concurrency;
- timeouts, retries, checkpoints e limites;
- workflows completos e sem scripts inexistentes;
- logs, métricas, relatórios e artefatos;
- execução idempotente;
- testes de atualização completa e parcial;
- teste de indisponibilidade das fontes externas;
- runbooks de operação e manutenção.

Aceite:
- execução ponta a ponta reproduzível;
- atualização incremental e retomável;
- um domínio pode falhar sem derrubar os demais;
- dados publicados permanecem íntegros;
- operação não depende de repositório de referência.

### Fase N — Contratos e compatibilidade dos consumidores
**Estado: NÃO INICIADA — não modificar consumidores antes desta fase e da autorização**

Objetivo: definir e validar como TV, Mobile e Web recebem o catálogo próprio do ACERVO.

Tarefas:
- mapear contratos reais de cada consumidor (TV, Mobile, Web e Player quando aplicável);
- comparar formatos atuais e formatos V2;
- definir contrato público/versionado e período de compatibilidade;
- resolver manifestos, índices, detalhes, logos, EPG e streams via ACERVO;
- substituir dependências externas diretas, incluindo referência a `vod/indice.txt`, somente nesta fase;
- criar adaptadores/exportações legadas se necessários;
- testar cache, fallback, paginação/partições e comportamento offline;
- garantir IDs estáveis para favoritos, histórico e relações;
- elaborar plano de rollout e rollback por consumidor.

Aceite:
- contrato documentado por consumidor;
- nenhum app precisa consultar repositório externo para resolver catálogo;
- compatibilidade validada em builds de teste;
- fallback para versão válida;
- nenhuma OTA/publicação oficial sem aprovação expressa.

### Fase O — Integração gradual com TV, Mobile, Web e Player
**Estado: AGUARDANDO APROVAÇÃO**

Objetivo: conectar consumidores ao ACERVO publicado sem quebrar versões existentes.

Tarefas:
- integração em branches de trabalho apropriadas, com PRs separados;
- começar por ambiente de teste e catálogo não oficial;
- testar TV, Mobile e Web separadamente;
- validar pesquisa, detalhes, categorias, favoritos, histórico, reprodução, logos, rádios e EPG;
- testar dispositivos de baixo recurso e redes lentas;
- validar compatibilidade e observabilidade;
- manter consumidores antigos funcionando durante transição;
- preparar rollback por aplicativo;
- somente após aprovação explícita planejar release/OTA.

Aceite:
- testes reais por consumidor;
- nenhuma dependência antiga obrigatória;
- fallback/rollback testados;
- aprovação do responsável antes de merge/release/OTA.

### Fase P — Auditoria final, estabilização e declaração de 100%
**Estado: NÃO INICIADA**

Objetivo: comprovar o ACERVO completo, independente, sustentável e pronto para operação.

Tarefas:
- auditoria de arquitetura e dependências;
- desligar todos os adaptadores de referência e provar operação com dados internalizados;
- simular fontes indisponíveis, dados malformados e falhas de storage/publicação;
- testar recuperação e rollback;
- validar todos os domínios e contratos;
- validar segurança de secrets, licenças, logs e permissões;
- medir desempenho, custos, frescor e cobertura;
- revisar documentação, runbooks e continuidade;
- corrigir pendências críticas;
- gerar relatório final com evidências e limitações conhecidas.

Aceite final:
- núcleo próprio e independente;
- ingestão e armazenamento próprios de dados autorizados;
- schemas e importadores de todos os domínios;
- identidade/dedupe/proveniência;
- enriquecimento e metadados;
- canais, rádios, logos e EPG funcionais;
- índices/partições e catálogos próprios;
- health/quality/quarentena/monitoramento;
- publicação versionada, manifesto, cache e rollback;
- automação ponta a ponta;
- integração consumidora autorizada e validada;
- nenhum bloqueio crítico aberto;
- evidências reproduzíveis e documentação atualizada.

## 14. Estrutura de diretórios alvo

A árvore abaixo é proposta de organização, não ordem de criação nem inventário do que já existe. Criar somente diretórios/arquivos que tenham responsabilidade e implementação reais.

```text
config/
  sources/
  policies/
schemas/
  common/
  vod/
  channels/
  radios/
  logos/
  epg/
adapters/
  <source_or_format>/
engine/
  collect/
  parse/
  normalize/
  identity/
  deduplicate/
  enrich/
  validate/
  build/
  publish/
  recover/
catalog/
  canonical/
  indexes/
  exports/
storage/
  raw/
  staging/
  quarantine/
reports/
  runs/
  quality/
  changes/
  source-health/
  enrichment/
  releases/
scripts/
tests/
  fixtures/
  unit/
  contract/
  integration/
  regression/
.github/workflows/
```

Separação lógica:
- `sources/`: registro/configuração de fontes e, se aplicável, referências/manifestos de entrada; não confundir com dependência operacional de terceiros.
- `storage/raw/`: configuração/manifestos e ponteiro para blobs no storage escolhido.
- `catalog/canonical/`: entidades canônicas; `indexes/` e `exports/` são derivados.
- `reports/`: evidência por execução, sem segredos.
- GitHub guarda código, schemas, configurações pequenas, testes e histórico; blobs grandes ficam na camada escolhida após dimensionamento.

## 15. Matriz de responsabilidade e rastreabilidade

Para cada artefato importante, manter uma matriz com:
- artefato/arquivo;
- domínio;
- produtor (motor/script/workflow);
- entradas/fontes;
- armazenamento;
- contrato/schema;
- consumidor;
- teste que o valida;
- política de atualização/retention;
- comportamento de falha;
- evidência da última execução.

A matriz Fki × ACERVO atual × CineHUB V2 deverá identificar:
- conceito/componente observado na referência;
- evidência concreta e repositório/arquivo;
- estado atual no ACERVO;
- decisão CineHUB (adotar/adaptar/descartar/pendente);
- componente responsável no V2;
- risco/licença/compatibilidade;
- teste de aceite.

Nenhuma decisão importante deve ficar escondida em conversa ou em memória pessoal.

## 16. Restrições e aprovações permanentes

- Trabalhar na branch `develop/acervo-v2` durante construção V2.
- Preservar `main`; não mesclar PR sem autorização expressa.
- Não alterar CineHUB TV, Mobile, Web ou Player antes das fases N/O e autorização específica.
- Não publicar catálogo oficial nem OTA sem autorização expressa.
- Não duplicar token TMDB já integrado no Supabase.
- Não apagar dados válidos por ausência temporária de fonte.
- Não substituir catálogo ativo sem candidato, backup, quality gate e rollback.
- Não depender exclusivamente de SaimoPlayer ou qualquer repositório externo.
- Não criar infraestrutura paga nem alterar serviços de produção sem aprovação.
- Não inventar metadados, gêneros, logos, IDs ou direitos.
- Não copiar aplicativos ou identidade visual de terceiros.
- Manter identidade própria CineHUB.
- Não tratar planejamento, workflow verde ou relatório vazio como conclusão funcional.
- Não reabrir Fase A sem evidência de regressão.
- Se houver bloqueio, registrar causa e continuar tarefas seguras que não dependam dele.
- O executor não muda arquitetura, prioridade ou escopo sem registrar justificativa e obter aprovação quando necessário.

## 17. Checklist mestre resumido

| Fase | Escopo | Estado |
|---|---|---|
| A | Baseline executável e snapshot | **CONCLUÍDA** |
| B | Auditoria complementar, schemas e importadores | **EM ANDAMENTO** |
| C | Source Hub, coletores e independência de ingestão | NÃO INICIADA |
| D | Identidade, normalização e deduplicação | NÃO INICIADA |
| E | VOD, TMDB, fichas, gêneros, índices e partições | NÃO INICIADA |
| F | Canais ao vivo | NÃO INICIADA |
| G | Rádios | NÃO INICIADA / histórico parcial a reconciliar |
| H | Logos e assets | NÃO INICIADA |
| I | EPG | NÃO INICIADA |
| J | Qualidade, monitoramento e recuperação | NÃO INICIADA |
| K | Infraestrutura e armazenamento definitivo | NÃO INICIADA |
| L | Catalog Builder, publicação e rollback | NÃO INICIADA |
| M | Operação autônoma e orquestração | NÃO INICIADA |
| N | Contratos e compatibilidade dos consumidores | NÃO INICIADA |
| O | Integração gradual com consumidores | AGUARDANDO APROVAÇÃO |
| P | Auditoria final e aceite 100% | NÃO INICIADA |

A sequência e os limites entre fases podem ser ajustados após descobertas reais, mas nenhum requisito pode desaparecer. Tarefas concluídas parcialmente devem ser marcadas por subitem, não como fase completa.

## 18. Continuidade e retomada — estado no momento da consolidação

- Repositório: `mooNXy7/CineHUB-ACERVO`.
- Branch: `develop/acervo-v2`.
- HEAD conhecido antes da gravação deste documento: `8967eb303de13b3c69c69bc453d425eb11dede92`.
- Fase A: CONCLUÍDA, conforme evidências históricas acima.
- Próxima fase: B — auditoria complementar, contratos e importadores.
- Fase B: EM ANDAMENTO; esta fotografia histórica foi superada pelo adendo operacional da seção 20.
- Não iniciar Fase B automaticamente como parte da criação deste documento.
- PR #2 foi registrado no histórico como draft e não mesclado; verificar estado atual antes de qualquer ação.
- Quatro scripts VOD ausentes continuam pendências até implementação/teste.
- Desacoplamento do clone de SaimoPlayer continua pendência até comprovação.
- Infraestrutura Cloudflare/Supabase ainda precisa de inventário real antes de decisões definitivas.
- Consumidores não devem ser modificados nesta etapa.
- Nenhuma publicação oficial/OTA está autorizada.

### Próxima ação liberada

Após validar este documento e alinhar `PROJECT_STATUS.md`, `NEXT_TASK.md` e `HANDOFF.md`, continuar **somente a Fase B**, com leitura dos documentos normativos, inventário dos formatos reais e implementação dos contratos/importadores mínimos funcionais. Preservar catálogos ativos e gerar candidatos isolados. Não avançar automaticamente para a Fase C.

### Atualização obrigatória a cada etapa

Ao concluir uma tarefa:
1. marcar apenas o subitem realmente concluído;
2. anexar commit, run, testes, artefatos e métricas;
3. registrar pendências e diferenças;
4. atualizar estado da fase;
5. atualizar próxima tarefa;
6. registrar qualquer mudança de decisão com motivo e aprovação;
7. nunca apagar histórico anterior — adicionar nova evidência e manter trilha auditável.

---

**Declaração de integridade do plano:** este documento consolida os requisitos e a arquitetura descritos no cérebro arquitetural fornecido pelo responsável, junto às decisões e evidências já registradas na branch. Ele não afirma que as fases futuras foram implementadas, que a auditoria de todos os repositórios de referência foi concluída, nem que recursos Cloudflare/Supabase estejam configurados. O plano será refinado por evidências, sem reduzir o objetivo de independência do ACERVO.


---

## 19. Retomada operacional — 2026-11-03 (histórico, superado pela seção 21)

Este adendo atualiza a fotografia de continuidade da seção 18; não apaga o histórico nem altera o plano técnico das fases.

- Branch: `develop/acervo-v2`.
- HEAD confirmado no GitHub nesta retomada: `3d8d143ae387f3340c1efb285fb3199393c25a99`.
- `main`: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- Comparação atual: 45 commits à frente, 0 atrás; 15 arquivos no diff reportado, sem alterações em `catalog/` ou `sources/` nesta comparação.
- PR #1 (“Hardening, normalização e enriquecimento seguro do CineHUB ACERVO”): aberto, draft, não mesclado.
- PR #2 (“[DRAFT] ACERVO V2 — Fase A: baseline executável”): aberto, draft, não mesclado.
- Fase A: CONCLUÍDA. Fase B: EM ANDAMENTO, com implementação publicada e validação integral ainda pendente.
- Esta atualização é documental; não conta como implementação ou aceite da Fase B.
- O executor deve conferir os PRs, workflows, diffs e SHAs reais antes de agir; PRs não são substitutos da branch `develop/acervo-v2`.
- A próxima tarefa é exclusivamente a Fase B. O roteiro executável e critérios mínimos estão em `NEXT_TASK.md`.
- Permanecem proibidos: merge em `main`, alterações nos consumidores TV/Mobile/Web/Player, alterações em repositórios de referência, mudanças em segredos/produção Supabase/Cloudflare, OTA e publicação oficial.
- Não alterar catálogo ativo nem promover candidato. Não iniciar Fase C automaticamente.
- SHAs e comparações acima são uma fotografia desta retomada; revalidar no começo da execução.


## 20. Execução técnica da Fase B — atualização 2026-11-03 (histórico, superado pela seção 21)

Este adendo é a fotografia operacional vigente e prevalece sobre estados históricos das seções 18–19. A Fase B está efetivamente em implementação; não está concluída.

### Commits publicados em develop/acervo-v2
- `b7ff0b15b8713d944b8d857a7b822028ff18c9af` — contratos versionados, parsers/importadores, staging e entrypoints VOD.
- `6da90d372ce1c332317a7b429cfd1ff2745ef2d7` — correção da expectativa de teste para variantes de áudio em episódios.
- `bb2dc858dedcec368e6311244c16888fd38a279c` — bootstrap da raiz do checkout para imports diretos de scripts.
- `0b37cd73f8a0f52b3f4240ebdb31e92128bc03b8` — correção da contagem da fixture M3U (três registros).
- `af4ee37ca4f538022b819b834226514a18028e4b` — importação do índice local de canais XMLTV.
- `667a4529692de3807f3f544658de9f6c8e43dec8` — uso explícito do normalizador no mapeamento EPG.
- `093921241ef57d8ae9f25dacf56a6fa88afb619a` — integridade referencial do candidato.
- `638722caf78ffa5709bdf61d7fc2ebad661552c1` — import de regex no validador de integridade.
- `98d77f89f6468c688fcd104473ecb9f78726677c` — construção incremental de VOD por shard, com escrita atômica.
- `02b695f035de64ab68119915b88b22cbd7c8740a` — validação incremental de documentos grandes com ijson.
- `9b869cd1705cd70550b87e7db95a8024496327af` — preservação do resolver/base URI de schemas em validação incremental.

### Evidências de CI
- Runs 960–965 registraram falhas reais de teste/importação; as causas foram identificadas e corrigidas nos commits acima.
- Runs 976 e 977 executaram a construção integral do candidato com sucesso; a validação seguinte foi cancelada por atualização posterior da branch.
- Runs 978 e 979 identificaram uma falha no resolver de referências relativas ao validar sub-schemas; correção publicada em `cf2148d`.
- Run 980 (ID `41590601634`, SHA `cf2148d`) confirmou 40 testes offline aprovados, compilação Python aprovada e construção integral do candidato aprovada; a validação integral do candidato estava em andamento na última consulta. Não registrar como CI verde até conclusão do job.
- Run 976 produziu artefato `13209354445`, SHA-256 `19d59e0b5a5ec3404b4d7182d156b9c50ded0525640d6ca5a34ec9772b26cdf9`; esse artefato continha baseline, manifesto e relatório, não o conjunto completo dos documentos candidatos. O workflow foi ajustado para incluir o diretório candidato completo em execuções subsequentes.

### Cobertura confirmada e limites atuais
- 13 schemas JSON Schema versionados e validados.
- 40 testes aprovados na última execução observada antes desta atualização; cobrem canais, rádios, VOD, EPG/XMLTV, variantes, proveniência, quarentena, staging e segurança TMDB simulada.
- O construtor lê catálogos locais, produz saída isolada e processa VOD por shard para limitar memória.
- O índice local `catalog/epg/xmltv-channels.json` contém 1.014 canais em quatro feeds; esses canais agora são normalizados com ID de provedor, ID interno e proveniência.
- O catálogo atual não contém payload XMLTV local completo de programação; `epg-programmes.json` permanece vazio. O parser XMLTV possui fixture/teste, mas a programação integral não foi importada.
- Os diretórios locais de logos não contêm imagens; referências externas são marcadas como não verificadas. MIME/conteúdo, licença e disponibilidade dos assets não foram validados por download, deliberadamente, para manter o build offline.
- Os quatro entrypoints VOD existem e os workflows foram reconciliados; execução online TMDB não foi disparada nem exigiu alteração de segredos. Os scripts de aplicação escrevem somente overlays/candidatos.
- Candidato não é publicação: nenhum catálogo ativo foi substituído.

### Pendências para aceite da Fase B
1. Concluir CI com construção integral, validação incremental de todos os documentos e artefato completo.
2. Confirmar idempotência do build integral e execução local documentada.
3. Executar smoke tests offline dos quatro entrypoints VOD e confirmar todos os workflows que os chamam.
4. Revisar associações de assets e EPG, incluindo limites de MIME/licença e ausência de payload de programas.
5. Atualizar relatórios/artefatos com contagens reais do candidato e quarentena.
6. Corrigir qualquer erro encontrado e registrar novo run/commit.
7. Parar na Fase B e aguardar autorização antes da Fase C.

**Estado:** EM ANDAMENTO. Estimativa de progresso técnico: aproximadamente 65%; não é declaração de aceite nem de 100%.


### Atualização de evidência após os testes de idempotência — 2026-11-03
- Commit de documentação/testes/workflow: `9b869cd1705cd70550b87e7db95a8024496327af`.
- A suíte passou a 40 testes: repetição do build com SOURCE_DATE_EPOCH fixo e comparação byte a byte dos documentos; smoke test offline `--help` dos quatro entrypoints VOD a partir de diretório externo.
- O workflow de validação agora envia o diretório completo do candidato como artefato, junto do baseline.
- Run 983 (`41591165169`) já confirmou testes, compilação e build integral; a validação de todos os documentos candidatos e o upload estavam em execução na última consulta.


## Histórico — validação integral Run 991 (2026-11-03; superada pelo Run 1002)

Branch: `develop/acervo-v2`. HEAD de código validado: `0ff93e98ca3a1f167e9d3e53f1882d962ff2384b`.

### CI e evidências
- Run 990 / ID `41597574427`: sucesso no workflow `validate`.
- Run 991 / ID `41597580123`: sucesso no workflow `validate`; validação de referência para esta atualização.
- Run 991 aprovou: validação do catálogo ativo sem mutação; 13 JSON Schemas; 42 testes offline; compilação Python; construção integral do candidato; comparação byte a byte de duas construções; validação dos documentos candidatos e integridade entre domínios; upload do artefato.
- Testes: `Ran 42 tests`, todos aprovados. Não dependem de rede ou segredos.
- Idempotência integral: 11 arquivos comparados; `diff -qr` e hashes SHA-256 iguais entre duas construções com `SOURCE_DATE_EPOCH=1760000000`.
- Artefato completo do Run 991: `13213490340`; ZIP SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`.

### Métricas do candidato integral (Run 991)
- VOD: 56.248 entradas de índice -> 52.603 identidades canônicas; 3.645 entradas consolidadas; 3.598 grupos com IDs legados repetidos; 47 grupos unidos por identidade de provedor entre IDs legados diferentes; 1 ID legado reutilizado entre identidades distintas (2 grupos afetados). Nenhum registro foi removido em massa.
- Streams/variantes de episódio: 786.939; IDs únicos: 786.939.
- Canais: 2.437; rádios: 1.026; logos associados: 2.018.
- EPG: 1.014 canais, 78 mapeamentos (18 resolvidos, 60 ambíguos, 0 sem correspondência), 0 programas XMLTV locais.
- Quarentena: 252 rádios. Permanecem pendentes de classificação/correção; não foram descartados silenciosamente.
- Integridade final: 0 erros de IDs/variantes duplicados indevidos; todos os documentos gerados passaram pelos 13 schemas.
- Build report confirmou `active_catalogs_modified=false` e `reference_network_used=false`.

### SHA-256 por documento candidato
- `vod.json`: `3ca39d09bcc1c6d9ae0c1dc7fd2773c306a3e173d9adac58ca674c23b352438c`
- `channels.json`: `4704295fee3311621cc3abe57f6fb38080ce395ac01b33038658c0e9b0f2c57e`
- `radios.json`: `7476a340eb515cda6364e2f3863cf605c8727eb41668f63bc6eabf6c26db0792`
- `logos.json`: `384480406378613f2a01556b18c1b81063f4b51ac7b8866576a746a9f1c91784`
- `sources.json`: `d200887ea28752edd898da149f2c5f2b4886c2f5c0f2e19e629f794ca30043c4`
- `epg-sources.json`: `73fc11ff9f01c2d3f4357a0ab712f14943d821974a0ff08d1c4826b09959bb11`
- `epg-mappings.json`: `594a523e4e624ebb3dafd0ca74ac17ca91e9f10cb067c8fbcdf806b89d71fe05`
- `epg-channels.json`: `9a045d8a7a9501af85197b27bc28f5e1b6259359f96df9d268d362cbca2f2974`
- `epg-programmes.json`: `056e69cd15a3683cfd7517b63742a851deaef37673e2703935a0e872afebda2d`

### Pendências para aceite da Fase B
1. Investigar e classificar os 252 registros de rádio em quarentena, preservando os dados originais.
2. Resolver ou documentar as 60 associações EPG ambíguas; programação continua ausente do snapshot local e não deve ser inventada nem buscada durante validação offline.
3. Diferenciar referências de logos de arquivos de imagem locais efetivamente armazenados/verificados; não há imagens locais para validação de conteúdo/MIME/licença.
4. Fechar revisão de cobertura dos cinco domínios e comprovar em evidência os quatro entrypoints/workflows VOD, incluindo limites de execução online TMDB sem disparar integração externa nesta validação.
5. Revisar a identidade conservadora dos 2 grupos afetados por reutilização de ID legado e registrar decisões sem colapsar entidades distintas.
6. Revalidar PRs/diff e escopo protegido antes do encerramento; manter Fase B aberta até os critérios de aceite do roadmap estarem cobertos.

**Estado da Fase B: EM ANDAMENTO.** A integridade técnica e reprodutibilidade do candidato integral passaram no CI, mas as pendências de rádio, EPG, assets e revisão dos entrypoints impedem declarar 100% ou concluir a fase. Nenhum catálogo foi publicado/promovido; Fase C não iniciada.


## Auditoria complementar da Fase B — 2026-11-03 (Run 991; superada pelo relatório Run 1002)

Relatório detalhado persistido em `reports/phase-b-quality-audit-2026-11-03.md`, baseado no artefato integral do Run 991 (`13213490340`, SHA-256 `ad985335333c8bf0ef860c6b24283316d8de3fef4501c69aedbfe0f291d7d860`).

- VOD: o ID legado `series-my-name` afeta as identidades canônicas `series-meu-nome-e` (TMDB 2317) e `series-my-name` (TMDB 110356). A separação canônica foi preservada, mas os dois grupos compartilham as mesmas 16 URLs de episódio com `/2317/` e provider refs com `110356`; associação das fontes permanece pendente de confirmação. O `report.json` atual tem contadores, não inventário detalhado de conflitos/consolidações.
- Rádios: os 252 itens em quarentena são URLs de imagem em `stream_url`; em todos, `name` contém uma URL com aparência de stream. Há mais 2 registros com `stream_url` vazio/ausente e URL em `name`. Nenhum endpoint foi testado em rede.
- EPG: quatro feeds XMLTV indexam 1.014 canais (179/494/182/159; prioridades 5/25/30/40), além de duas fontes HTML. Os 60 mapeamentos ambíguos correspondem a múltiplos IDs CineHUB por canal/qualidade e permanecem sem associação forçada. Não há programação XMLTV local.
- Logos: 2.018 referências externas (1.748 canais, 270 rádios); 2.018 não verificadas, MIME desconhecido, zero arquivos locais de imagem e nenhuma licença registrada.
- Workflows: os quatro entrypoints e quatro workflows foram revisados. Os fluxos online de enriquecimento TMDB não foram executados. Nenhum workflow publica ou promove automaticamente.

O Run 991 permanece a evidência de validação integral de referência: 42 testes, 13 schemas, build integral, idempotência de 11 arquivos e integridade referencial aprovados. A Fase B continua aberta; não publicar, não mesclar e não iniciar a Fase C.


## 21. Reconciliação autoritativa Run 1002 — 2026-11-04

- Branch: `develop/acervo-v2`; HEAD analisado: `5e2150f3c0f48075edacb56b70111304f797d25d`.
- Run 1002 / ID `41744148492`: job `validate` concluído com sucesso; 47 testes, 13 schemas, compilação, build integral, integridade e idempotência de 11 arquivos aprovados.
- Artefato `13283645574`, ZIP SHA-256 `3d7b347cdb5bb5f309f263f0fca1f0fa1c8c353e700c7f6808ba032da4632fca`, 73.111.225 bytes, 15 arquivos.
- VOD: 56.248 entradas -> 52.602 identidades; 3.645 grupos consolidados; 3.646 entradas de índice consolidadas; zero IDs legados reutilizados entre identidades distintas. A regra My Name (2021) corrige duas referências para TMDB 110356. As três referências de detalhe observadas preservam oito episódios, 16 linhas episódio/áudio cada, 16 URLs únicas no conjunto e 33 provider refs distintos; as URLs e provider refs foram agregados pelo merge, sem perda silenciosa. A antiga pendência de conflito VOD está resolvida no candidato.
- Rádios: 1.026 registros; 257 itens históricos na quarentena, todos com procedência; 255 resolvidos por correspondência exata no snapshot fixado (253 itens `image_url_in_audio_stream` e dois `missing_stream_url`), dois `image_url_in_audio_stream` ainda sem resolução e sem stream válido. Foram adicionados 255 streams e promovidos 253 candidatos de logo. O artefato contém a trilha por item; quarentena total não equivale a falhas abertas.
- EPG: seis fontes (quatro XMLTV e duas HTML), 1.014 registros de canais, 78 mapeamentos (18 correspondências únicas e 60 ambíguos: 46 códigos Meu Guia, 12 aliases XMLTV e dois slugs Guia de TV). Zero programas XMLTV locais. A saúde local dos feeds data de 2026-10-26; feeds públicos foram identificados, mas permissão de redistribuição não foi comprovada para todos. A Pluto TV exige consentimento escrito para redistribuição de conteúdo. Não forçar mapeamentos nem internalizar payload sem autorização.
- Logos: 2.271 associações (1.748 canais e 523 rádios), 1.429 URLs HTTP e 842 HTTPS; zero imagens locais, MIME, hash de conteúdo ou licenças documentadas. Associação lógica não é asset completo. O backend de armazenamento permanece condicionado ao inventário real de Cloudflare/Supabase.
- Entry points/workflows: quatro scripts e quatro workflows revisados; testes offline de CLI/help passaram. Os fluxos TMDB online não foram executados e continuam dependendo do segredo já existente no Supabase; não houve alteração de segredo.
- O Run 1002 foi offline: `active_catalogs_modified=false`, `reference_network_used=false`. Nenhuma publicação, OTA, promoção de catálogo, alteração de consumidor ou merge de PR.
- Fase B: **EM ANDAMENTO**. As limitações remanescentes estão formalmente classificadas no relatório Run 1002. Aguardar aceite explícito antes de encerrar a fase ou iniciar a Fase C.
