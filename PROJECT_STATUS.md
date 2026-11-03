# CineHUB-ACERVO — Estado do Projeto

**Branch de trabalho:** `develop/acervo-v2`  
**Branch de produção preservada:** `main`  
**Base da branch:** `main` no commit `c2176962dccc218cd17622f0acd786ff76b18a6d`  
**Status desta inicialização:** estrutura de continuidade criada; reconstrução V2 ainda não iniciada.

## Objetivo

Transformar o CineHUB-ACERVO na plataforma central, independente e confiável de dados e distribuição de conteúdo do ecossistema CineHUB.

## Decisões já aprovadas

- Estratégia B: fontes independentes como base principal; repositórios de referência de Gabriel podem ser usados como fonte auxiliar de descoberta/importação, nunca como dependência operacional exclusiva.
- `main` permanece como linha estável até validação e aprovação explícita.
- O desenvolvimento V2 acontece em `develop/acervo-v2`.
- Nesta etapa, não modificar os repositórios consumidores (TV, Mobile e Web).
- Não publicar OTA nem alterar aplicações consumidoras sem autorização explícita.
- Não introduzir marca, identidade visual ou créditos Saimo na experiência CineHUB.

## Estado conhecido e ressalvas

- Esta branch foi criada a partir do HEAD de `main` informado acima.
- O commit-base tem a mensagem `revert: restore catalog after automatic sync`. Antes de qualquer alteração funcional, verificar o estado atual dos catálogos, workflows e resultados recentes.
- As etapas recentes de Logos e Rádios precisam ser revalidadas nesta base. Não presumir que estão concluídas ou pendentes sem conferir arquivos, commits e execuções.
- O levantamento anterior identificou dependência de importação do repositório de referência no workflow de atualização. Confirmar se isso permanece no HEAD atual antes de alterar.
- A especificação completa do funcionamento do ACERVO V2 ainda será discutida e aprovada pelo responsável pelo projeto. Este arquivo não substitui essa especificação.

## Progresso

- [x] Confirmar repositório e branch principal.
- [x] Criar branch isolada `develop/acervo-v2` a partir de `main`.
- [x] Criar documentos permanentes de continuidade e verificar sua leitura no GitHub.
- [x] Registrar o HEAD confirmado da branch: `ccdbe570e082f633b2b7207fe1fa208e83ae3bfe`.
- [ ] Discutir e aprovar a especificação funcional/arquitetural do ACERVO V2.
- [ ] Auditar novamente o estado real da branch de trabalho.
- [ ] Definir etapas de implementação, testes e critérios de aceite.
- [ ] Implementar, validar e documentar cada etapa.
- [ ] Solicitar aprovação antes de integrar à `main`.

**Percentual de implementação V2:** ainda não iniciado. A criação da estrutura de controle não representa conclusão funcional do V2.

## Regra de atualização

Atualizar este documento sempre que houver mudança relevante de etapa, branch, estado de validação, bloqueio ou decisão. Nunca declarar concluído algo que não tenha evidência verificável.
