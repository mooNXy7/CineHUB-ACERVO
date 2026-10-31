# MegaEmbed no CineHUB ACERVO

O registro central fica em `catalog/vod/providers/megaembed.json`. Ele documenta as rotas de incorporação que os clientes CineHUB já utilizam como fallback quando as fontes diretas falham.

## Comportamento

- Priorizar fontes diretas válidas do item.
- Tentar as rotas MegaEmbed somente como fallback.
- Usar TMDB ID ou IMDb ID quando disponível; busca por título fica por último.
- Para séries, exigir temporada e episódio.
- Tratar as rotas como páginas de incorporação, nunca como URLs diretas de mídia.
- Respeitar bloqueios de iframe/CSP do provedor; oferecer abertura externa quando necessário.
- Não atribuir IDs TMDB por semelhança de título nem misturar filmes, séries, remakes ou temporadas.

## Integração existente

O adaptador CineHUB Web/TV já gera candidatos de filmes e episódios a partir de `tmdb_id`, `imdb_id`, título e ano. Este registro transforma essas rotas em contrato versionado do ACERVO, para que os clientes não dependam de listas privadas ou de URLs de reprodução inventadas.

A presença de uma rota não garante que o provedor tenha mídia disponível, que a incorporação seja permitida em todos os dispositivos ou que a reprodução funcione. O player deve manter timeout, fallback e opção de abertura externa.

## Formato nos registros

Fontes de incorporação já importadas devem permanecer identificadas com `source_type: "embed"` e `source_id: "reference-mgeb"`. Não as converter em fontes diretas e não remover fontes existentes durante atualizações.
