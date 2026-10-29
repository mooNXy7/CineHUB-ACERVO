# EPG — fontes, prioridade e atualização

O ACERVO mantém o registro das fontes e o índice de canais XMLTV para que CineHUB TV e Mobile possam resolver a programação sem depender de um único provedor.

## Fontes registradas

| Prioridade | Fonte | Tipo | Uso |
|---:|---|---|---|
| 5 | [Pluto TV Brasil](https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/br.xml) | XMLTV | Exclusivamente canais Pluto reconhecidos por ID estável |
| 10 | [Meu Guia Brasil](https://meuguia.tv/programacao/canal/HBO) | Grade HTML | Fonte principal para canais mapeados por código |
| 20 | [Guia de TV Brasil](https://www.guiadetv.com/canal/sony-movies) | Grade HTML | Reserva para canais mapeados que não têm grade na fonte principal |
| 25 | [EPG Brasil — catálogo combinado](https://raw.githubusercontent.com/marcoshimselfxd/EPG-Scrapper-BR/main/epg.xml) | XMLTV | Cobertura combinada e fallback geral |
| 30 | [IPTV EPG Brasil](https://iptv-epg.org/files/epg-br.xml) | XMLTV | Cobertura geral, preenchimento de lacunas e metadados |
| 40 | [Open EPG Brasil](https://www.open-epg.com/files/brazil3.xml) | XMLTV | Segunda cobertura XMLTV e preenchimento de lacunas |

Prioridade menor significa maior precedência. A fonte Pluto é especial: seu ID não deve ser associado por aproximação de nome.

## Arquivos

- `sources.json`: URLs, formatos, prioridades, estratégia de associação e janela.
- `channel-map.json`: códigos de grade, slugs e aliases XMLTV.
- `xmltv-channels.json`: IDs e nomes de canais descobertos por cada feed; mantém a última versão válida quando uma fonte falha.
- `html-programmes.json`: programação extraída das páginas HTML explicitamente mapeadas; mantém o último horário válido por canal e registra a saúde por canal.
- `health.json`: status HTTP, tamanho, contagem de canais/programas, falhas consecutivas e quantidade de canais CineHUB associados.

## Atualização e segurança

`scripts/update_epg.py` verifica os feeds XMLTV, valida a estrutura, limita respostas a 100 MiB, conta a programação da janela de 6 horas anteriores a 72 horas futuras e atualiza os IDs associados aos canais CineHUB. `scripts/update_html_epg.py` consulta apenas os códigos/slugs explícitos do mapa, com concorrência máxima de quatro requisições, timeout de 20 s e limite de 5 MiB por resposta; publica a programação num arquivo lateral separado, sem alterar `channels.json` nem o índice XMLTV.

Uma fonte indisponível não apaga seu último índice válido nem bloqueia as outras. A rotina registra a falha e preserva o último sucesso. O acervo publica o índice compacto de canais, não cópias integrais dos XMLTV externos.

A extração HTML usa parsers testáveis sem rede e fuso `America/Sao_Paulo`. Uma resposta vazia, bloqueada ou com marcação inesperada não substitui uma programação válida anterior. A ordem definida para o sidecar é Meu Guia e, para canais mapeados sem grade anterior, Guia de TV. A publicação desse sidecar não muda automaticamente os apps: a integração do consumidor ainda precisa ser validada separadamente. O teste de saúde de uma página HTML confirma conectividade e presença de marcação de grade; não garante que cada canal mapeado esteja com a programação correta. A auditoria de cobertura também lista códigos/slugs compartilhados e entradas de mapa sem correspondência após normalização de acentos, caixa e marcadores de qualidade com o nome atual do catálogo como candidatos de revisão; isso não altera nem remove mapeamentos automaticamente.

## Contrato de associação

- Preferir ID XMLTV explícito quando existir.
- Depois, nome canônico normalizado sem acentos e marcadores de qualidade.
- Usar aliases explícitos para nomes que mudam entre feeds.
- Pluto TV: associar somente por ID Pluto encontrado no endereço do canal ou logo.
- Preservar `epg_id` para compatibilidade e `epg_sources[]` para manter IDs alternativos de diferentes feeds.
