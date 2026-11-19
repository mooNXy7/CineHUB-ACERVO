# CineHUB ACERVO

Repositório central de dados do CineHUB TV, Mobile, Web e futuras plataformas. O catálogo é construído e validado de forma independente dos aplicativos.

> **Linha de desenvolvimento:** `develop/acervo-v3`. A branch `main` permanece preservada durante toda a construção e homologação da V3. A V2 e suas branches de trabalho também são mantidas.

## Objetivos

- Catálogo compartilhado de filmes, séries, animes, doramas, canais e rádios.
- Temporadas, episódios, EPG, fontes, alternativas de reprodução e assets.
- Identidade canônica independente dos provedores, com proveniência rastreável.
- Importação, normalização, enriquecimento, validação e publicação controlada.
- Índices leves e detalhes sob demanda, com compatibilidade para TV Boxes e conexões limitadas.
- Atualizações que preservam a última versão válida em caso de falha.

## Estrutura existente

A árvore abaixo resume os domínios e módulos presentes; ela não é uma ordem para recriar diretórios nem substitui o inventário do código:

```text
catalog/             dados atuais por domínio (VOD, canais, rádios, EPG, logos)
sources/             registro e referências de fontes
normalizer/          regras de normalização
acervo_v2/           importadores e parsers canônicos já existentes
schemas/             contratos JSON Schema versionados
scripts/             validação, importação, auditoria e build de candidatos
tests/               testes offline e fixtures
reports/             evidências e relatórios técnicos
staging/             área de trabalho para candidatos; não é catálogo publicado
docs/                documentação operacional e técnica
.github/workflows/   validação e rotinas controladas
```

Preservar estruturas úteis existentes. Dados brutos, staging, registros canônicos, referências de reprodução, metadados e saídas publicáveis devem permanecer conceitualmente separados.

## Desenvolvimento V3

Trabalhe somente na branch `develop/acervo-v3`. Não faça push, merge, rebase ou reset em `main`, nem altere consumidores TV/Mobile/Web durante a construção.

Consulte [docs/DEVELOPMENT_V3.md](docs/DEVELOPMENT_V3.md) para checkout, dependências, validação offline, build de candidato e limites de publicação.

## Segurança e fontes

- Não armazenar tokens, senhas, cookies, credenciais ou URLs privadas no repositório.
- Não presumir que uma URL esteja funcional ou que exista autorização para redistribuir conteúdo.
- Não importar fontes sem autorização documentada.
- Não permitir que uma candidata incompleta substitua o último catálogo válido.
- Não executar publicação automática sem validar o fluxo e respeitar a configuração do responsável.

## Status

A V3 parte do estado técnico herdado da V2. A existência de scripts, schemas ou workflows não significa, por si só, que todos os domínios estejam completos ou que publicação esteja homologada. Cada capacidade será declarada concluída somente após execução de testes e evidência verificável.
