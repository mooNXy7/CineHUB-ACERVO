# Política de fontes

- Preferir APIs oficiais, catálogos abertos, fontes com licença explícita e listas mantidas por seus autores.
- Registrar origem, licença/termos, data de verificação e contato do mantenedor quando disponível.
- Não presumir que um stream público pode ser redistribuído.
- Não contornar DRM, login, paywall ou controles de acesso.
- Falha temporária não deve apagar o último catálogo válido.
- Testes de disponibilidade são limitados e respeitam o serviço de origem.
- Remover prontamente fontes mediante pedido fundamentado ou quando a licença não permitir uso.
- Metadados e imagens devem respeitar os termos de TMDB ou de outra API utilizada.


## Registro central V3

O arquivo `sources/sources.json` é o registro operacional central. Cada entrada deve manter:
- ID estável, provedor responsável/curador, domínio (`vod`, `channels`, `radios`, `epg` ou `logos`) e formato;
- origem como URL pública HTTPS/HTTP ou caminho relativo dentro do repositório;
- prioridade, idioma, região e estratégia/adaptador;
- autorização/termos, status, frequência e última execução;
- último erro e histórico de erros;
- referência a credencial somente pelo nome lógico de um Secret/proxy, nunca pelo valor.

Formatos com adaptadores: `m3u`, `json`, `txt`, `xmltv` e `vod_catalog`. TXT exige adaptador explícito para evitar interpretar o mesmo texto com semânticas incompatíveis. O catálogo VOD local usa o parser hierárquico já existente.

## Estados e quarentena

- `active`: elegível para importação quando também estiver `enabled: true`.
- `disabled`: cadastrado, mas não importável.
- `pending_review`: termos/autorização ainda precisam de revisão; permanece desabilitado.
- `degraded`: fonte conhecida com falha operacional; preservar dados válidos anteriores.
- `quarantined`: entrada rejeitada até correção.

O validador rejeita URLs com esquemas não HTTP(S), hosts locais, IPs privados/reservados, credenciais embutidas, portas inválidas e parâmetros de query sensíveis comuns. O registro também detecta origens duplicadas dentro do mesmo domínio/formato, normalizando host e portas HTTP(S) padrão. Antes de qualquer requisição real, o cliente HTTP ainda deve validar os endereços IP resolvidos e cada redirecionamento; a validação estática do registro não substitui essa defesa contra DNS rebinding/SSRF. Nenhum adaptador desta etapa faz requisições de rede. Origens locais são resolvidas dentro da raiz do repositório, exigem arquivo existente e rejeitam escapes por caminho ou symlink. O adaptador só lê arquivos locais; fontes remotas exigem payload fornecido por um cliente de rede controlado, que deverá validar DNS e cada redirecionamento antes de conectar. Saídas de quarentena e campos brutos redigem valores de credenciais conhecidos.

Fontes EPG legadas sem comprovação explícita de termos foram centralizadas como `pending_review` e `enabled: false`. Fixtures TXT são registradas somente como teste e permanecem desabilitadas. Não cadastrar novas fontes externas sem autorização e procedência verificáveis.
