# Referências estáticas de recuperação e identidade

Este diretório contém snapshots locais, versionados e somente de build, usados para resolver problemas de qualidade identificados no candidato V2.

## Rádio

`radio-recovery.json` contém 255 correspondências únicas por URL normalizada entre registros brutos de `catalog/radios/radios.json` e a lista `vod/radios.txt` do repositório fki1976/SaimoPlayer, commit `41b2c62769fdf049165b2fedb19cc70473fe2c2d`.

- A URL original no campo `name` é preservada.
- Nome da estação e URL de áudio são recuperados da referência.
- Uma URL de imagem original em `stream_url` pode virar candidata de logo, sempre não verificada.
- Os itens de quarentena permanecem registrados e recebem anotação de resolução.
- Não há sondagem de rede nem declaração de disponibilidade dos streams.

## Identidade VOD

`vod-identity-overrides.json` registra uma correção explícita e limitada para duas entradas de 2021 com TMDB 2317. A referência distingue TMDB 2317 (Meu Nome é Earl, 2005) de TMDB 110356 (My Name, 2021, 8 episódios). A regra falha o build se o número esperado de correspondências deixar de ser exatamente dois.

Os IDs legados e o TMDB original permanecem preservados no raw, na procedência e no relatório de identidade.

## Segurança e atualização

- Estes arquivos não são catálogos ativos nem feeds habilitados.
- O build os consome localmente; não faz chamadas à referência externa.
- Commits, caminhos e Git blob SHAs ficam registrados nos próprios arquivos.
- Nenhum arquivo de imagem ou conteúdo audiovisual é copiado.
- O snapshot de referência não contém arquivo `LICENSE`; os metadados não inventam uma licença formal.
- Qualquer atualização exige revisão explícita dos matches e da procedência.
