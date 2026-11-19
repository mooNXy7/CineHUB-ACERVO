# Etapa 1 — Fundação da Branch V3

Data: 18/11/2026

## Estado confirmado

- Repositório: `mooNXy7/CineHUB-ACERVO`.
- Branch de trabalho: `develop/acervo-v3` (existe no GitHub).
- Commit-base da V3: `29cd1c635f4fb5ea3cd29a31e6e20d94d09a1d86`.
- Esse commit é idêntico ao HEAD de `develop/acervo-v2` no momento da criação.
- HEAD atual da V3: `a470661e2f702bcc8e2f20e10a8c6ca53839176b`.
- Comparação viva: V3 está 5 commits à frente e 0 atrás de `develop/acervo-v2`.
- `main` permanece separada e intocada; HEAD observado durante a inspeção: `430dc8908f209eb26611a67bcc888adf198635a5`. A comparação main → V3 mostra 83 commits à frente e 19 atrás; não houve integração ou alteração da main nesta etapa.

## Inventário técnico inicial

A V3 herdou a implementação V2, sem recriação do zero. Foram identificados:

- Importadores/parsers canônicos em `acervo_v2/importers.py` e `acervo_v2/xmltv.py`.
- Schemas JSON Schema versionados em `schemas/` para VOD, canais, rádios, logos, EPG e estruturas comuns.
- Scripts de validação, auditoria, importação, enriquecimento e build de candidata em `scripts/`.
- Testes offline e fixtures em `tests/`.
- Catálogos e fontes existentes em `catalog/` e `sources/`.
- Workflows de validação e rotinas manuais controladas em `.github/workflows/`.
- Dependências de desenvolvimento em `requirements-dev.txt`.

Não foram recriados diretórios ou catálogos apenas para imitar a árvore ilustrativa do Plano Mestre.

## Alterações desta etapa

1. Atualizado `README.md` para identificar V3 como linha de desenvolvimento e explicitar preservação da V2/main, limites de segurança e organização atual.
2. Criado `docs/DEVELOPMENT_V3.md` com checkout seguro, Python 3.12, instalação, comandos offline, build isolado, reprodutibilidade e limites operacionais.
3. Atualizado `.github/workflows/validate.yml`: workflow agora identifica V3, inclui `develop/acervo-v3` no gatilho de push, usa grupo de concorrência V3 e nomes de artefato/candidata V3. Os passos de validação herdados foram mantidos.
4. Nenhum catálogo, fonte, segredo, aplicativo, workflow de importação/enriquecimento ou branch de produção foi alterado nesta etapa.

## Validação

Inspeção remota dos arquivos e comparação de refs concluídas. A execução integral dos comandos locais/CI ainda precisa de evidência de execução na V3; não declarar os testes como aprovados apenas pela leitura dos workflows.

Comandos cobertos pelo guia:
- `python scripts/validate_catalog.py`
- `python scripts/validate_schemas.py`
- `python -m unittest discover -s tests -v`
- `python -m py_compile scripts/*.py acervo_v2/*.py`
- Build de candidata em `staging/` e validação dos schemas.

**Pendência de aceite:** executar o workflow `Validate ACERVO V3` na branch `develop/acervo-v3` e confirmar sucesso do job completo, incluindo build idempotente. Até essa evidência, a fundação documental e de CI está preparada, mas a Etapa 1 permanece aguardando validação executada.

## Próxima etapa

Após CI verde e confirmação dos comandos básicos, encerrar Etapa 1 e iniciar Etapa 2 — Sistema Central de Fontes e Provedores.
