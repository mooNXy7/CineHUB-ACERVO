# CineHUB-ACERVO — Princípios de Arquitetura

> Documento-base de princípios. A arquitetura detalhada do ACERVO V2 será definida em uma especificação própria após discussão e aprovação. Não tratar este documento como autorização para implementar todos os componentes abaixo.

## Responsabilidade central

O ACERVO deve ser o proprietário lógico dos registros canônicos de conteúdo, da normalização, dos metadados que armazenar, dos descritores de fontes, dos processos de validação e dos artefatos publicados para os consumidores CineHUB.

## Princípios obrigatórios

1. **Independência:** o funcionamento do ACERVO não pode depender exclusivamente de um repositório externo ou de um único fornecedor de dados.
2. **Fontes múltiplas:** manter registro de fontes independentes e permitir fontes auxiliares opcionais, com prioridade, estado e histórico.
3. **Identidade estável:** IDs internos não devem depender de URL, título exibido ou posição em playlist.
4. **Separação de camadas:** distinguir dados brutos importados, registros normalizados/canônicos, metadados enriquecidos, descritores de streams e arquivos/assets.
5. **Rastreabilidade:** registrar origem, horário de coleta, hash quando aplicável, parser, resultado da validação e histórico de alterações.
6. **Resiliência:** falhas de uma fonte não devem apagar automaticamente dados válidos; preservar último estado válido e alternativas quando aplicável.
7. **Validação antes de publicação:** publicar somente após validações obrigatórias e geração bem-sucedida dos artefatos.
8. **Distribuição estável:** consumidores devem depender de contratos e endpoints versionados, não de caminhos internos de fontes externas.
9. **Compatibilidade:** alterações nos formatos consumidos por TV, Mobile e Web exigem análise de impacto e aprovação antes da migração.
10. **Segurança e direitos:** registrar permissões/licenças e não presumir autorização para copiar ou redistribuir mídia protegida. Metadados, imagens, playlists, EPG e conteúdo audiovisual têm requisitos distintos.

## Estratégia de fontes aprovada

- Fontes independentes são a base principal.
- Repositórios de referência autorizados por Gabriel podem atuar como fonte auxiliar de descoberta/importação.
- Essa fonte auxiliar não pode ser exclusiva nem se tornar dependência de runtime.
- Falha, mudança de URL ou indisponibilidade da fonte auxiliar não pode interromper o catálogo independente.

## Separação conceitual

- **Descoberta/ingestão:** localizar e coletar dados de fontes autorizadas.
- **Staging bruto:** preservar a entrada original e sua proveniência para auditoria/reprocessamento.
- **Normalização:** converter formatos distintos em um modelo canônico.
- **Enriquecimento:** associar metadados externos, mantendo identificadores e confiança da correspondência.
- **Resolução/saúde de fontes:** verificar disponibilidade e administrar candidatos/alternativas sem confundir resposta HTTP com garantia de reprodução ou autorização.
- **Catálogo:** gerar dados consistentes e próprios para consumo.
- **Distribuição:** publicar manifestos e arquivos versionados, com validação e possibilidade de rollback.

## Serviços e tecnologias

GitHub, GitHub Actions, Cloudflare, Supabase e TMDB foram discutidos como opções/serviços do ecossistema. Seus papéis exatos, limites, custos, segredos e dependências devem ser confirmados na especificação V2. Não assumir que todos serão necessários nem que endpoints exemplificativos já estejam configurados.

## Fora do escopo desta preparação

- Implementar novos conectores.
- Alterar o formato dos catálogos consumidos.
- Migrar TV, Mobile ou Web.
- Modificar dados de produção ou publicar OTA.
- Definir detalhes ainda não aprovados do V2.
