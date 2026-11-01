# Política de fontes

- Preferir APIs oficiais, catálogos abertos, fontes com licença explícita e listas mantidas por seus autores.
- Registrar origem, licença/termos, data de verificação e contato do mantenedor quando disponível.
- Não presumir que um stream público pode ser redistribuído.
- Não contornar DRM, login, paywall ou controles de acesso.
- Falha temporária não deve apagar o último catálogo válido.
- Testes de disponibilidade são limitados e respeitam o serviço de origem.
- Remover prontamente fontes mediante pedido fundamentado ou quando a licença não permitir uso.
- Metadados e imagens devem respeitar os termos de TMDB ou de outra API utilizada.

## Referência de rádios

- A referência autorizada `SaimoPlayer/vod/radios.txt` usa linhas `nome|stream`.
- O importador lê somente nome e URL HTTPS; não importa DRM, headers, tokens ou configurações de reprodução.
- Streams existentes nunca são substituídos automaticamente. URLs diferentes para a mesma rádio são registradas para revisão.
- Logos e gêneros existentes são preservados; a referência não é considerada fonte desses campos.

## Grades HTML de terceiros

- Fontes HTML de programação só podem ser ativadas quando houver autorização expressa para extração, armazenamento e redistribuição dos horários e títulos.
- `meuguia-br` e `guia-de-tv-br` permanecem desativadas até comprovação dessa autorização. A fonte Guia de TV publica termos que restringem cópia, armazenamento e compartilhamento do conteúdo.
- O pipeline remove grades HTML previamente armazenadas dessas fontes desativadas; falhas temporárias de fontes autorizadas continuam preservando o último dado válido.
- Os mapeamentos de canal são mantidos para possível reativação autorizada; as fontes XMLTV continuam independentes.

## Metadados de rádio em domínio público

- A fonte `radio-browser-br-metadata` utiliza os dados públicos de estações brasileiras do Radio Browser, cuja página oficial declara a base de dados em domínio público.
- A rotina só preenche gêneros a partir de tags reconhecidas e logos por URLs HTTPS de favicon cujo domínio corresponde ao homepage da estação.
- A correspondência exige nome normalizado exato e stream exato ou nome único; ambiguidades são ignoradas.
- Nenhum stream, ID, configuração de reprodução, DRM, header ou credencial é importado ou substituído por essa fonte.
