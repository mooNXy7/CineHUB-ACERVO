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
