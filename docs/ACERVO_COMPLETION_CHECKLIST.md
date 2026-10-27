# Checklist de conclusão — CineHUB ACERVO

Este documento é o quadro de controle para concluir a organização do ACERVO sem perder dados ou quebrar os consumidores existentes. Atualizar os estados somente com evidência de execução, diff ou teste.

## Regras que não podem ser quebradas

- [x] Manter TV, Mobile e PLAYER fora do escopo desta branch.
- [x] Não publicar OTA nem mesclar a PR sem autorização explícita.
- [x] Executar a importação de referência apenas em worktree temporária durante a revisão.
- [x] Não sobrescrever credenciais, URLs privadas, tokens, cookies ou parâmetros assinados.
- [x] Preservar os arquivos anteriores em falhas e publicar arquivos de catálogo atomicamente.
- [x] Manter compatibilidade dos schemas e formatos atuais.
- [ ] Fazer revisão humana do diff final e autorizar explicitamente eventual merge.
- [ ] Confirmar backup e rollback antes de qualquer atualização real de dados.

## 1. Integridade do catálogo

- [x] Auditoria somente leitura de canais, rádios, VOD, índices e referências.
- [x] Detectar IDs ausentes/duplicados dentro de cada namespace.
- [x] Falhar de forma segura quando shards ou índices VOD existentes estão corrompidos ou não podem ser interpretados.
- [x] Impedir que a deduplicação una registros só por título, ano ou ID externo ambíguo.
- [ ] Investigar e classificar todos os grupos de títulos repetidos; não apagar obras por coincidência de título.
- [ ] Validar cada delta da prévia de importação, especialmente colisões de identidade e metadados que pioram.
- [ ] Definir e testar limites aceitáveis de variação de volume antes de qualquer publicação.

**Última linha de base observada:** 2.431 canais, 1.026 rádios e 56.248 registros VOD (40.938 filmes, 11.665 séries, 2.749 animes, 896 doramas). Esses números são do artefato de auditoria, não uma declaração de que todos os itens funcionam.

## 2. Importação e reconciliação de referências

- [x] Corrigir parsing de rádios para aceitar \`nome|stream\` e \`nome|stream|logo\`.
- [x] Preservar rádios existentes em vez de substituí-las por entradas de referência.
- [x] Preservar fontes múltiplas para o mesmo ID estável.
- [x] Isolar a prévia em diretório temporário e gerar relatório sem URLs de stream/logo.
- [x] Contabilizar fontes, referências de provedores, URLs rejeitadas e colisões de identidade.
- [ ] Revisar a prévia atual: ela adiciona 808 VOD, mas também aumenta campos ausentes (pôster +776, ano +630, gêneros +777) e grupos de títulos repetidos em séries/animes/doramas; por isso a publicação segue bloqueada.
- [ ] Inspecionar os exemplos detalhados de títulos repetidos e metadados faltantes gerados pela nova versão do relatório.
- [ ] Decidir por lote quais candidatos podem ser incorporados com identidade confirmada e quais devem permanecer em revisão/quarentena.
- [ ] Confirmar proveniência, licença e compatibilidade de cada fonte antes de promovê-la ao catálogo publicado.
- [ ] Não importar resolvedores de fontes que contornem DRM, autenticação, paywall ou controles de acesso.

## 3. Metadados VOD

- [x] Gerar relatório read-only de pôster, ano, gêneros e IDs externos.
- [x] Validar sintaxe de \`tmdb_id\`, \`imdb_id\`, \`tvdb_id\`, \`mal_id\` e \`anilist_id\`.
- [x] Não chamar APIs externas nem alterar o catálogo no dry-run.
- [ ] Resolver os registros existentes sem ano: linha de base 30.526.
- [ ] Resolver os registros existentes sem pôster: linha de base 7.620.
- [ ] Resolver os registros existentes sem gêneros: linha de base 7.976.
- [ ] Criar fluxo de enriquecimento por lotes com cache persistente, limites de taxa, confiança de correspondência e revisão de candidatos ambíguos.
- [ ] Usar credenciais próprias em secrets de CI se um provedor de metadados exigir chave; nunca copiar chaves dos repositórios de referência.
- [ ] Confirmar tipo, título original/localizado, ano e identidade antes de atualizar campos existentes.
- [ ] Testar que o enriquecimento não substitui metadados válidos por valores vazios ou de baixa confiança.

## 4. Canais e fontes ao vivo

- [x] Medir cobertura estrutural de fontes sem fazer requisições de rede.
- [x] Registrar candidatos a URL malformada e URLs inválidas sem expor endpoints no relatório.
- [ ] Revisar os 3 casos de referência URL suspeita e corrigi-los apenas após identificar a representação correta.
- [ ] Investigar os canais sem lista de fontes; linha de base: 321.
- [ ] Investigar canais sem logo; linha de base: 683.
- [ ] Validar disponibilidade das fontes com probes limitados, timeout, limite de resposta e política que não contorne autenticação/DRM.
- [ ] Manter fontes alternativas distintas e proveniência por fonte; não substituir URLs existentes apenas por prioridade nominal.
- [ ] Documentar fonte/licença e data da última verificação para cada origem publicada.

## 5. Rádio

- [x] Corrigir o formato de importação e preservar streams já existentes.
- [x] Medir cobertura estrutural e detectar campos vazios.
- [ ] Investigar as 2 rádios sem stream.
- [ ] Investigar as 754 rádios sem logo.
- [ ] Preencher gênero somente quando houver metadado explícito com proveniência; não inferir apenas pelo nome da estação.
- [ ] Validar streams de rádio em lote com timeout e registrar status/data, sem remover fontes por falha transitória.

## 6. EPG

- [x] Manter a configuração XMLTV atual e aliases existentes.
- [x] Criar parser isolado para grades HTML de Meu Guia e Guia de TV.
- [x] Criar sidecar \`catalog/epg/html-programmes.json\` sem alterar os schemas consumidos pelos apps.
- [x] Aplicar limites de timeout/tamanho/concorrência e preservar cache válido em falhas.
- [x] Distinguir códigos compartilhados de EPG documentados de duplicatas não explicadas no relatório.
- [ ] Executar e registrar o probe manual contra páginas HTML reais; os testes sintéticos não comprovam que o site atual continua compatível.
- [ ] Confirmar códigos/slugs com grade não vazia e horários coerentes no fuso \`America/Sao_Paulo\`.
- [ ] Resolver associações ausentes com mapeamentos explícitos verificados; não adivinhar IDs de EPG.
- [ ] Investigar os 2 IDs EPG não encontrados no índice XMLTV.
- [ ] Validar frescor, cobertura de horários e fallback com dados reais antes de marcar o sidecar pronto para consumidores.
- [ ] Não sobrescrever uma grade primária válida com fallback vazio, antigo ou de baixa qualidade.

**Última auditoria estrutural:** 2.110/2.431 canais com referência de stream (86,8%); 718/2.431 com associação EPG estrutural (29,54%); 1.024/1.026 rádios com stream (99,81%). Referência estrutural não comprova reprodução nem programação atual.

## 7. Normalizador, automação e segurança

- [x] Publicação atômica nos caminhos de atualização cobertos por testes.
- [x] Validação de URL e redirecionamentos para os fluxos de atualização cobertos.
- [x] Testes automatizados para parser, normalizador, importador, auditorias e preservação de dados.
- [x] Workflow de validação executa schemas, auditorias, testes e compilação Python.
- [ ] Confirmar a última execução verde após todas as alterações desta branch.
- [ ] Confirmar que o workflow agendado falha fechado se a origem estiver indisponível, vazia ou reduzir o catálogo de forma suspeita.
- [ ] Verificar logs/artefatos para garantir que URLs privadas, tokens, chaves e corpos completos de respostas não são publicados.
- [ ] Testar idempotência: duas execuções com a mesma entrada não devem criar duplicatas nem novos diffs.
- [ ] Documentar rollback e procedimento de recuperação de backup.

## 8. Critérios de pronto

O ACERVO só deve ser considerado pronto para merge quando:

1. A última execução de CI estiver verde após as últimas alterações.
2. A prévia de importação não tiver regressões sem explicação; toda colisão relevante estiver classificada.
3. Nenhum registro existente for apagado ou substituído sem decisão documentada.
4. Os problemas de metadados estiverem tratados por lotes seguros ou explicitamente contabilizados como pendências, sem alegar cobertura completa.
5. O probe EPG real tiver resultado documentado e as limitações do consumidor estiverem claras.
6. A proveniência/licença das fontes promovidas estiver revisada.
7. Houver backup, rollback, diff revisado e autorização explícita antes do merge.

**Estado atual:** em revisão; importação de referência bloqueada; nenhuma publicação de catálogo ou OTA autorizada por este documento.
