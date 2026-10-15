# Relatório de importação inicial

Data da importação: 2026-10-15

## Resultado

- **332** registros de canais importados com nome, categoria e logo quando disponíveis.
- **3.243** referências a streams identificadas no catálogo de origem. Elas **não foram publicadas como fontes de reprodução** nesta etapa; cada canal guarda apenas a contagem de candidatos para revisão.
- **753** estações de rádio importadas com nome, URL de stream e logo quando disponível.
- IDs de rádio duplicados por variações de nomes foram consolidados quando a chave normalizada coincidia.
- O projeto usa nomenclatura e identidade CineHUB; a marca do aplicativo de referência não foi incorporada aos arquivos do CineHUB.

## Por que os streams de canais ficaram pendentes?

A lista de origem contém grande volume de URLs HTTP sem TLS, endereços IP diretos, URLs com segmentos que aparentam credenciais de acesso e proxies/relays. Não é seguro tratá-las como fontes públicas estáveis apenas porque aparecem em um repositório. Antes de ativá-las, precisamos verificar autorização de redistribuição, ausência de credenciais privadas, estabilidade e compatibilidade.

## Próximas ações

1. Revisar fontes de canais e selecionar streams públicos e autorizados.
2. Testar disponibilidade com limites e timeouts.
3. Acrescentar identificadores estáveis e fontes alternativas validadas.
4. Auditar rádios (duplicatas, resposta HTTP, tipo de áudio e logos).
5. Expandir o importador para EPG/XMLTV e índices de VOD.

Nenhuma chave DRM, senha ou cabeçalho de autenticação foi migrado para o catálogo CineHUB.
