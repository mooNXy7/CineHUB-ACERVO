# Revisão de pipelines de referência autorizados

Esta revisão orienta melhorias no CineHUB ACERVO. É um mapa de capacidades e padrões de engenharia, não uma importação automática de listas. Os repositórios de referência pertencem ao Gabriel e foram autorizados pelo usuário para análise/reutilização pertinente.

## VOD: descoberta, fontes e metadados

- **SaimoPlayer** (`gerar_vod.py`) combina listas M3U de origens distintas, agrupa fontes do mesmo título/ano/versão e mantém refilmagens separadas quando o ano é conhecido.
- O pipeline lê atributos M3U sem quebrar títulos com vírgulas entre aspas; normaliza marcadores de qualidade/idioma e ordena fontes por prioridade.
- O catálogo é fatiado por letra e as séries em partes menores, reduzindo o tamanho baixado por tela/dispositivo.
- O gerador de metadados (`gerar_generos.py`) usa cache persistente e busca correspondência de título com ano/tipo; isso é preferível a escolher a primeira imagem encontrada.
- **Saimo-TV** (`src/services/vodService.ts`) usa arquivos menores e cacheia leituras durante a visita; falha de rede não deve ser cacheada permanentemente como se o arquivo estivesse vazio/ausente.
- **Aplicação ao ACERVO:** manter múltiplas fontes com proveniência, deduplicar conservadoramente por identidade estável e metadados confirmados, manter os índices atuais compatíveis e nunca apagar uma fonte válida só porque uma atualização não a trouxe. A importação automática agora mantém registros existentes elegíveis para receber novas fontes após reconciliação de identidade, mas retém novos títulos sem pôster/ano/gêneros ou com colisão de título até enriquecimento/revisão. A prévia deve mostrar a diferença líquida do índice separadamente dos contadores internos de parsing.

## EPG: combinar cobertura sem confundir horários e metadados

- **Saimo-TV** (`src/workers/epgWorker.ts`) prioriza a grade HTML do Meu Guia para horários onde a fonte é conhecida por ser mais confiável; feeds XMLTV ampliam cobertura e podem enriquecer descrições, pôsteres, elenco, ano e episódio.
- O worker usa aliases explícitos para nomes diferentes entre catálogo e feed, limita a janela temporal, descarta marcadores sem programação e faz parsing fora da linha principal.
- **Saimo-Cell-V2** mantém mapeamentos explícitos para códigos Meu Guia e slugs Guia de TV, incluindo correções documentadas de códigos. O documento da referência registra que páginas sem grade devem ser removidas do mapa.
- **SaimoPlayer** e implementações móveis interpretam campos XMLTV de episódio com validação de plausibilidade; campos ausentes são opcionais, não erros que invalidem todo o programa.
- **Aplicação ao ACERVO:** manter o sidecar HTML separado até validar HTML real e consumidor; guardar fonte e horário de atualização por canal; aliases e códigos precisam ser confirmados por resposta não vazia, e fallback não pode sobrescrever cache primário válido.

## Canais, normalização e cache

- **Saimo-TV** combina catálogo principal com lista extra de reserva, casa por nome normalizado, preserva cache anterior enquanto a rede falha e ordena HTTPS antes de fontes não HTTPS sem reescrever URLs.
- **Saimo-Cell-V2** possui regras determinísticas de categoria pelo nome para canais sem categoria explícita e identifica canais Pluto por ID presente no stream/logo, em vez de casar apenas pelo nome.
- **Aplicação ao ACERVO:** normalização pode sugerir correspondências, mas não deve trocar IDs estáveis ou consolidar canais automaticamente quando há variantes regionais. O relatório de qualidade é só leitura até existir política de reconciliação aprovada.

## Rádio

- O arquivo `vod/radios.txt` do SaimoPlayer contém nome e stream, mas não uma taxonomia consistente de gênero. Portanto, não é evidência suficiente para preencher o campo `genre` dos 1.026 registros do ACERVO.
- **Aplicação ao ACERVO:** pesquisar gêneros em fontes explícitas de metadados e guardar origem/confiança de cada enriquecimento. Não inferir gênero apenas por nome de estação e não substituir streams existentes em massa.

## Segurança e limites

- Não importar chaves de API, tokens, cabeçalhos de autenticação, cookies, parâmetros assinados ou lógica de resolução privada dos projetos de referência. O gerador de metadados de referência contém uma credencial de API hardcoded no código; esse valor não foi copiado para o ACERVO. Para qualquer novo enriquecimento, usar credencial própria em secret de CI e confirmar condições de uso da API.
- Não importar automaticamente URLs com markup malformado nem publicar novos endpoints antes de revisão e testes.
- O pipeline de atualização executa a importação de referência em worktree isolado; se a barreira de qualidade bloquear os novos títulos, esses dados não são copiados para a área de trabalho, mas as atualizações independentes de M3U e EPG continuam. O marcador de sincronização só avança quando a importação passa pela barreira e recebe aprovação manual explícita por `workflow_dispatch`.
- Presença de URL não prova reprodução. O conteúdo pode expirar, exigir cabeçalhos ou ter restrições que precisam ser respeitadas.
- Esta revisão não alterou dados dos apps, não testou reprodução de todos os streams e não considera o EPG HTML pronto para consumo pelos aplicativos.

## Próximos passos seguros

1. Usar o relatório por registro para priorizar faltas de logo, grupo, EPG e metadados.
2. Fazer inventário de fontes por proveniência antes de qualquer consolidação.
3. Validar amostras de EPG real em fluxo manual, medindo página não vazia, fuso horário, ordenação e janela de horários.
4. Planejar enriquecimento VOD por lotes pequenos, com correspondência por título/ano/tipo, cache, limite de taxa e relatório de candidatos ambíguos.
5. Só promover correções de dados com diff revisável, backup e testes de compatibilidade dos schemas.


## Verificação adicional — 25/10/2026

### Referências inspecionadas nesta rodada

- **SaimoPlayer**: gerador VOD principal, gerador de gêneros/metadados com cache persistente, e gerador de fontes extras por IDs exatos.
- **Saimo-TV**: parser do catálogo de canais, serviço VOD por fragmentos, pontuação de resultados TMDB, cache/worker EPG e resolvedor de fontes VOD.
- **SaimoTV-Android**: definições de catálogo, regras EPG/aliases e gerador M3U para catálogo Kotlin.
- **Saimo-Cell-V2**: serviço EPG, mapa explícito de códigos/slugs e cache de fontes.

### Decisão de implementação

A revisão confirmou um risco de identidade no importador do ACERVO: fontes extras de séries podiam ser anexadas ao primeiro título-base compatível mesmo quando havia remakes com anos diferentes; o caminho equivalente de filmes também podia selecionar o primeiro candidato pelo nome-base. O importador foi endurecido para:

1. preferir ID de provedor exato;
2. depois usar título/ano exatos;
3. aceitar correspondência por título-base somente se houver um único candidato possível;
4. quando o ano estiver presente, exigir o mesmo ano;
5. se permanecer ambíguo, criar candidato separado em vez de fundir fontes no registro errado.

Testes de regressão foram adicionados para filmes e séries com o mesmo título-base em anos diferentes. A validação do workflow passou após corrigir o formato do fixture de temporadas: **70 testes automatizados e compilação dos scripts concluídos com sucesso** no run [40243650983](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/40243650983).

### O que ainda não significa conclusão de dados

- A validação estrutural não prova que cada stream reproduz nem que cada programação EPG está atualizada.
- O sidecar HTML de EPG continua separado do formato consumido pelos apps.
- Não foi executado enriquecimento de dezenas de milhares de registros por API externa. Isso depende de escolher provedor/termos, usar credencial própria em segredo e gerar/revisar um diff antes de alterar dados.
- Os metadados e fontes existentes não foram apagados nem substituídos por ausência em uma referência.


### Correção adicional — preservação de metadados VOD

A inspeção do importador revelou que o caminho de filmes atribuía diretamente os metadados da referência, inclusive quando a referência não possuía ID TMDB, pôster ou gêneros. Isso poderia substituir dados já existentes por valores vazios. A correção agora trata a referência como enriquecimento: mantém ID e pôster existentes, preenche ano quando ausente e reconhecível no título, e combina gêneros sem duplicação. O caminho de séries também combina gêneros e preenche o ano ausente sem apagar os dados já existentes.

Testes de regressão cobrem filmes e séries, preservação de ID/pôster/fontes e combinação de gêneros. A execução [#160](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/40245113697) passou com **72 testes automatizados**, auditorias e compilação dos scripts.


### Alinhamento da origem de referência

A conferência da automação encontrou que o workflow .github/workflows/update-catalog.yml ainda clonava gabrielsaimo/SaimoPlayer, enquanto a referência explicitamente autorizada para esta etapa é fkuller/SaimoPlayer. Os dois repositórios têm conteúdo e SHAs diferentes, embora o repositório autorizado mantenha os caminhos de dados esperados (vod/filmes-*.txt, vod/series-*-*.txt, vod/fichas.txt, vod/destaques.txt, rádios e fontes extras). A URL do clone foi alinhada para fkuller/SaimoPlayer; os caminhos sparse e a importação incremental foram mantidos. Essa alteração está somente nesta branch e ainda precisa de revisão antes de ser mesclada; nenhuma importação automática foi executada por essa mudança.
