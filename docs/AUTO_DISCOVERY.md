# Descoberta e atualização automática do acervo

O CineHUB ACERVO sincroniza diariamente os catálogos de referência de canais, filmes, séries, animes, doramas e rádios.

## Como funciona

1. O GitHub Actions baixa somente os arquivos de catálogo necessários do repositório de referência autorizado; não clona o histórico completo.
2. O importador lê os índices de busca, fichas, listas de filmes e episódios, destaques, rádios e playlists de canais.
3. Os títulos são normalizados e deduplicados por identificador estável/nome normalizado; temporadas e episódios continuam hierarquizados.
4. Novas fontes e referências de provedores são anexadas sem apagar as anteriores. Assim, uma nova execução pode adicionar alternativas quando o catálogo de origem muda.
5. O índice VOD fica leve e aponta para arquivos de detalhes separados por categoria e letra.
6. A rotina valida JSON e testes, registra estatísticas em `reports/reference-import.json` e publica apenas alterações.

## Política de fontes

- URLs públicas sem credenciais explícitas são importadas como candidatas; o processo não faz teste de reprodução para cada título.
- URLs com usuário/senha, parâmetros de token evidentes, hosts privados ou caminhos que aparentam conter credenciais são omitidas e contabilizadas no relatório.
- Referências compactas de provedores são preservadas como `provider_refs` para que adaptadores possam resolvê-las sem perder títulos.
- O catálogo não remove um registro só porque ele desapareceu da rodada mais recente. Remoções exigem auditoria separada.
- Séries e episódios são mantidos separados de filmes. Anime e dorama são categorias derivadas quando a fonte traz sinais suficientes; títulos não classificados continuam em Séries.
- O conteúdo reservado/adulto não é importado.

## Consumo pelos aplicativos

- Índice geral: `catalog/vod/index.json`
- Detalhes de filmes: `catalog/vod/details/movies/{letra}.json`
- Detalhes de séries: `catalog/vod/details/series/{letra}.json`
- Animes: `catalog/vod/details/anime/{letra}.json`
- Doramas: `catalog/vod/details/doramas/{letra}.json`
- Canais: `catalog/channels/channels.json`
- Rádios: `catalog/radios/radios.json`

O aplicativo pode carregar primeiro o índice leve e baixar apenas o arquivo de detalhes da letra/categoria aberta. Para reprodução, tente as fontes na ordem de prioridade; em falha, avance para a próxima fonte e registre o resultado localmente. O próximo ciclo de sincronização acrescenta fontes novas sem apagar as que já existem.
