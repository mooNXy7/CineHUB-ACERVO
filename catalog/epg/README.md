# EPG — fontes, prioridade e atualização

O ACERVO mantém o registro das fontes e o índice de canais XMLTV para que CineHUB TV e Mobile possam resolver a programação sem depender de um único provedor.

## Fontes registradas

| Prioridade | Fonte | Tipo | Uso |
|---:|---|---|---|
| 5 | [Pluto TV Brasil](https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/br.xml) | XMLTV | Exclusivamente canais Pluto reconhecidos por ID estável |
| 10 | [Meu Guia Brasil](https://meuguia.tv/programacao/canal/HBO) | Grade HTML | Fonte principal para canais mapeados por código |
| 20 | [Guia de TV Brasil](https://www.guiadetv.com/canal/sony-movies) | Grade HTML | Reserva para canais mapeados que não têm grade na fonte principal |
| 30 | [IPTV EPG Brasil](https://iptv-epg.org/files/epg-br.xml) | XMLTV | Cobertura geral, preenchimento de lacunas e metadados |
| 40 | [Open EPG Brasil](https://www.open-epg.com/files/brazil3.xml) | XMLTV | Segunda cobertura XMLTV e preenchimento de lacunas |

Prioridade menor significa maior precedência. A fonte Pluto é especial: seu ID não deve ser associado por aproximação de nome.

## Arquivos

- `sources.json`: URLs, formatos, prioridades, estratégia de associação e janela.
- `channel-map.json`: códigos de grade, slugs e aliases XMLTV.
- `xmltv-channels.json`: IDs e nomes de canais descobertos por cada feed; mantém a última versão válida quando uma fonte falha.
- `health.json`: status HTTP, tamanho, contagem de canais/programas, falhas consecutivas e quantidade de canais CineHUB associados.

## Atualização e segurança

`scripts/update_epg.py` é executado pelo workflow de atualização do ACERVO. Ele verifica os feeds XMLTV, valida a estrutura, limita respostas a 100 MiB, conta a programação da janela de 6 horas anteriores a 72 horas futuras e atualiza os IDs associados aos canais CineHUB.

Uma fonte indisponível não apaga seu último índice válido nem bloqueia as outras. A rotina registra a falha e preserva o último sucesso. O acervo publica o índice compacto de canais, não cópias integrais dos XMLTV externos.

O teste de saúde de uma página HTML confirma conectividade e presença de marcação de grade; não garante que cada canal mapeado esteja com a programação correta. O aplicativo usa a página por canal quando o acesso direto é permitido e continua com XMLTV quando o navegador bloqueia CORS.

## Contrato de associação

- Preferir ID XMLTV explícito quando existir.
- Depois, nome canônico normalizado sem acentos e marcadores de qualidade.
- Usar aliases explícitos para nomes que mudam entre feeds.
- Pluto TV: associar somente por ID Pluto encontrado no endereço do canal ou logo.
- Preservar `epg_id` para compatibilidade e `epg_sources[]` para manter IDs alternativos de diferentes feeds.
