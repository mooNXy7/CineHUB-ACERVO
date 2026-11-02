# Auditoria da automação de referência — plataforma TV

Data da auditoria: 2026-11-02

## Repositórios e limites

- Referência central autorizada: `fki1976/SaimoPlayer`.
- Referência complementar Android TV: `fki1976/SaimoTV-Android`.
- Destino desta fase: somente `mooNXy7/CineHUB-ACERVO` para CineHUB TV.
- Esta auditoria não autoriza alterações nos aplicativos nem publicação OTA.

## O que foi confirmado no SaimoPlayer

1. O catálogo central reúne listas de canais e rádios, fontes alternativas e índices VOD.
2. O fluxo de manutenção local `atualizar_tudo.sh` encadeia descoberta/atualização RedeFlix, montagem VOD, gêneros/metadados, IDs IMDb e destaques.
3. O script `scripts/agendar_atualizacao.sh` agenda essa rotina via macOS launchd às 05:00 na máquina configurada. É um agendamento local, não um GitHub Actions.
4. O único workflow GitHub Actions presente em `.github/workflows/` nesta revisão é `atualizar-ids-redeflix.yml`. Ele roda diariamente às 14:17 UTC (11:17 em Brasília), atualiza IDs/episódios RedeFlix e, em seguida, gera os destaques.
5. Portanto, não é correto afirmar que todo o conjunto de tarefas de `atualizar_tudo.sh` roda diariamente no GitHub Actions. O workflow diário e a rotina local têm escopos diferentes.

## Consequência para o CineHUB ACERVO

- O agendamento de atualização do ACERVO foi movido para 14:37 UTC (11:37 BRT), depois do workflow de referência das 14:17 UTC, para que a sincronização diária possa consumir o catálogo de referência já atualizado no mesmo dia.
- A URL de clonagem da referência foi corrigida de `fkuller/SaimoPlayer` para o proprietário canônico `fki1976/SaimoPlayer`.
- A importação continua isolada na branch de auditoria e sujeita ao quality gate. Não se deve remover esse gate nem sobrescrever dados existentes só para igualar a estrutura da referência.

## O que deve ser adaptado — não copiado cegamente

- Atualização de fontes: incorporar somente URLs públicas, tecnicamente válidas e permitidas; preservar a ordem/prioridade e as fontes existentes.
- Verificação de streams: separar disponibilidade HTTP de teste real de reprodução; registrar timeout, status, última verificação e resultado por fonte.
- Fallback: manter várias fontes por canal/título e nunca apagar a última fonte conhecida apenas por uma falha transitória.
- Limpeza: quarentena para links inválidos e duplicatas suspeitas; nenhuma exclusão automática baseada apenas em nome semelhante.
- VOD: atualizar índices e detalhes em etapas; completar apenas campos ausentes; validar identidade por tipo/ano/ID antes de atribuir TMDB; não sobrescrever IDs ou fontes existentes.
- EPG: armazenar associações e estado das fontes; buscar feeds autorizados em execução/cache do consumidor. Não presumir que um XMLTV permanente existe no repositório central.
- Logos e metadados: priorizar IDs públicos e URLs estáveis; não inventar imagens nem copiar tokens/credenciais.

## Proteções obrigatórias

- Nunca importar tokens, cookies, credenciais, cabeçalhos privados ou material DRM.
- Nunca transformar um resultado de teste de fixture em evidência de saúde de catálogo real.
- Nunca promover alterações para `main`, alterar o app TV ou publicar OTA sem aprovação explícita.
- Cada rotina automática deve produzir relatório, preservar a última versão válida e falhar de forma segura.\n## Complemento: catálogo estruturado de canais (catalogo.txt)\n\nA auditoria do arquivo `catalogo.txt` encontrou 472 blocos de canal. O importador existente lia `1.m3u` e `3.m3u`, mas não consumia diretamente os campos `fonte`, `qualidade`, `referer` e `agente` do catálogo estruturado.\n\nFoi adicionado um relatório somente leitura para mapear fontes por nome exato, preservando a ordem de fallback. Ele rejeita HTTP, credenciais explícitas, chaves sensíveis em query, caminhos IPTV com credenciais, relays base64 que ocultam caminhos de credenciais e segmentos hexadecimais opacos.\n\nOs candidatos restantes são classificados como `eligible_unverified`: isso **não** significa que o stream esteja online ou reproduza. Antes de qualquer inclusão no catálogo ativo, cada URL precisa passar por uma sondagem de rede e revisão. Nenhum stream, EPG, logo ou metadado existente é sobrescrito.\n\nA rotina agora também faz uma sondagem HTTP limitada a 8 KiB, com redirecionamentos revalidados e sem Authorization/Cookie. No branch isolado de auditoria, somente URLs que retornam uma playlist HLS válida (`#EXTM3U`) podem ser anexadas a canais ainda sem fontes. URLs DASH e formatos indiretos ficam apenas no relatório. O status do canal não é marcado como reprodução saudável: o teste não substitui validação em aparelho Android TV. Em `main/master`, a etapa de aplicação não executa.\n