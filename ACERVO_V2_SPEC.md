# CineHUB-ACERVO V2 — Especificação Funcional
**Estado:** aprovada pelo responsável do projeto para orientar a construção  
**Branch:** `develop/acervo-v2`  
**Escopo:** núcleo de dados, processamento e distribuição do ecossistema CineHUB

## 1. Missão
O ACERVO V2 é o sistema central, independente e auditável que descobre, ingere, organiza, enriquece, valida, versiona e distribui dados de conteúdo para CineHUB TV, Mobile e Web. Ele administra metadados e referências de reprodução; não hospeda nem reivindica propriedade sobre obras audiovisuais.

A operação não pode depender de um repositório externo específico. Referências técnicas autorizadas podem auxiliar descoberta e importação, mas o ACERVO mantém seus próprios dados, regras, identificadores, processos e publicações.

## 2. Resultados que o sistema deve entregar
1. Catálogo canônico consistente de filmes, séries, temporadas, episódios, animes e doramas.
2. Catálogo de canais ao vivo com fontes alternativas, logos, categorias, aliases e metadados.
3. Catálogo de rádios com streams válidos, nome, gênero, país/idioma quando disponível, logo e alternativas.
4. Catálogo de logos e identidade de canais/estações com associação verificável.
5. EPG unificado com fontes, aliases, prioridade, janela temporal e cache.
6. Pesquisa, detalhes e índices preparados para os consumidores.
7. Atualizações automáticas controladas, com relatório, histórico, publicação versionada e rollback.
8. Diagnóstico de qualidade e saúde das fontes sem apagar conteúdo válido por falha temporária.

## 3. Domínios de dados
### 3.1 On Demand
Filmes, séries, temporadas, episódios, animes e doramas. Cada entidade possui ID interno estável, tipo, título canônico, aliases, metadados, identificadores externos opcionais (TMDB/IMDb), relações hierárquicas, fontes de reprodução e procedência. TMDB enriquece metadados; não é a identidade primária nem a fonte de streams. Correspondências incertas vão para revisão, nunca são aplicadas automaticamente como verdade.

### 3.2 Canais
Cada canal tem ID estável, nome canônico, aliases, categoria, país/idioma quando conhecido, logo, EPG ID e uma ou mais fontes de reprodução. Fontes são variantes independentes com protocolo, prioridade, origem, estado de validação e última verificação. A indisponibilidade de uma variante não invalida automaticamente o canal.

### 3.3 Rádios
Cada estação tem ID estável, nome, aliases, gênero/categoria, país/idioma quando conhecido, logo e uma ou mais URLs de stream. Imagens e logos nunca podem ocupar o campo de URL de áudio. A normalização precisa aceitar formatos de origem diferentes sem descartar informação útil.

### 3.4 Logos e identidade visual de canais
Logos são ativos referenciados por URL/caminho e associados a entidades por ID, com origem, formato, dimensões quando disponíveis, estado e fallback. A validação verifica acessibilidade, tipo real do arquivo e associação; não confia apenas na extensão.

### 3.5 EPG
EPG é um domínio próprio: fontes XMLTV/API, IDs de canal, aliases, regras de prioridade, timezone, horários de início/fim, janela de retenção e atualização. O vínculo canal-EPG é explícito e auditável. Falha de uma fonte não deve apagar a última grade válida.

## 4. Pipeline funcional
**Descoberta → Coleta → Arquivo bruto → Parse → Normalização → Identidade → Deduplicação → Enriquecimento → Validação → Catálogo candidato → Comparação → Publicação versionada → Monitoramento/rollback.**

- Coleta preserva a resposta original e registra origem, data, hash e resultado.
- Parser converte cada formato conhecido para contratos internos; formatos desconhecidos são isolados e reportados.
- Normalização padroniza campos sem destruir o valor original.
- Identidade resolve entidades por ID interno e identificadores externos; não depende de título isolado.
- Deduplicação agrupa possíveis duplicatas e preserva variantes/fontes; fusões ambíguas exigem revisão.
- Enriquecimento consulta TMDB e outras fontes permitidas, com cache, limites, procedência e confiança.
- Validação separa erros bloqueantes, avisos e itens em quarentena.
- Catálogo candidato é construído sem alterar a versão ativa.
- Publicação promove apenas versão aprovada pelos testes e políticas de qualidade.
- Rollback restaura manifesto/versão anterior sem reconstruir os dados manualmente.

## 5. Independência e fontes
Fontes independentes são a base de operação. Cada fonte possui registro próprio: ID, domínio, tipo, formato, escopo, método de coleta, agendamento, credenciais referenciadas (nunca armazenadas em texto), prioridade, estado, política de retry, limites e histórico de saúde.

Repositórios de referência autorizados podem ser adaptadores de importação opcionais. Desativá-los ou removê-los não pode interromper atualização, geração, publicação nem consumo dos catálogos já importados. Nenhum consumidor deve precisar consultar diretamente tais repositórios para resolver IDs, streams, índices ou metadados.

## 6. Contratos e compatibilidade
- Contrato canônico versionado por domínio.
- IDs internos estáveis e não derivados de posição em listas ou título mutável.
- Aliases e identificadores externos são campos auxiliares.
- Fontes/streams são registros filhos ou variantes, não sobrescrevem a entidade.
- Cada registro mantém procedência e timestamps de coleta, alteração e validação.
- Índices e arquivos legados podem ser gerados como artefatos de compatibilidade, não como fonte de verdade.
- Mudanças incompatíveis exigem nova versão do contrato e período de compatibilidade.

## 7. Qualidade, segurança e política de publicação
Erros de parsing, catálogo vazio inesperado, queda abrupta de contagem, perda massiva de streams, IDs conflitantes, links de imagem em campos de stream e regressões de schema bloqueiam publicação. Falha transitória de uma fonte gera alerta e preserva a última versão válida. Itens inválidos são isolados; não se apaga em massa por ausência momentânea.

Segredos ficam em secret manager/ambiente protegido. Logs não imprimem tokens. Toda execução gera relatório legível e dados estruturados. Operações destrutivas, merges ambíguos e mudanças de contrato exigem revisão explícita.

## 8. Distribuição
O ACERVO publica snapshots imutáveis e um manifesto que aponta a versão ativa. Consumidores leem apenas versões publicadas, com cache e fallback para a última versão conhecida. A camada de distribuição pode usar arquivos estáticos e/ou API; a escolha concreta depende da auditoria dos recursos ativos de Cloudflare e Supabase. A lógica do catálogo não pode ficar presa a um único provedor.

## 9. Operação automática
Cada rotina tem gatilho, lock contra concorrência, timeout, retry com backoff, idempotência, limites de chamadas externas, logs, métricas e relatório. Rotinas são separadas por domínio para que falha em logos, rádios ou TMDB não interrompa os demais domínios. Um orquestrador pode coordenar etapas, mas cada etapa deve ser executável e testável isoladamente.

## 10. Critérios de aceite do V2
- Nenhuma dependência operacional obrigatória dos repositórios de referência.
- Catálogos canônicos e schemas validados para VOD, canais, rádios, logos e EPG.
- Importadores testados com fixtures reais dos formatos identificados.
- Identidade/deduplicação preserva variantes e não faz fusões incertas silenciosas.
- Enriquecimento TMDB idempotente, rastreável, com confiança e fila de revisão.
- Testes de saúde não confundem falha temporária com remoção definitiva.
- Publicação atômica, versionada, com comparação, manifesto e rollback demonstrado.
- Workflows sem referências a scripts ausentes; execução reproduzível e relatórios.
- Testes de regressão provam que falha de um domínio não corrompe os outros.
- TV, Mobile e Web continuam fora do escopo de alteração até uma etapa de integração autorizada.

## 11. Fora do escopo desta especificação
Reescrever aplicativos consumidores, alterar player, mudar UX, publicar OTA, copiar repositórios de terceiros, hospedar mídia audiovisual ou prometer disponibilidade de streams externos. Integrações consumidoras só começam depois do núcleo V2 validado e de autorização própria.

## 12. Regra de conclusão
Uma etapa só é concluída com alteração concreta no repositório, testes executados, evidência registrada e critérios de aceite atendidos. “Planejado”, “workflow criado” ou “enriquecimento iniciado” não equivalem a concluído.