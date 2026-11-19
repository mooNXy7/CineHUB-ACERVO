# Desenvolvimento — CineHUB ACERVO V3

## Branch e isolamento

- Repositório: `mooNXy7/CineHUB-ACERVO`
- Branch de desenvolvimento: `develop/acervo-v3`
- Produção preservada: `main`
- V2 preservada: `develop/acervo-v2` e demais branches existentes.

Comandos iniciais:

```bash
git fetch origin --prune
git switch develop/acervo-v3
git pull --ff-only origin develop/acervo-v3
git status --short --branch
git rev-parse HEAD
```

Antes de editar, confirme que o branch atual é `develop/acervo-v3` e registre o HEAD. Não use reset, force-push, merge ou rebase destrutivo. Nunca faça checkout/push de alterações de trabalho na `main`.

## Requisitos

- Python 3.12 (mesma versão usada pelo workflow de validação).
- Dependências de validação listadas em `requirements-dev.txt`.

Instalação:

```bash
python -m pip install -r requirements-dev.txt
```

## Validação offline

Executar na raiz do repositório:

```bash
python scripts/validate_catalog.py
python scripts/validate_schemas.py
python -m unittest discover -s tests -v
python -m py_compile scripts/*.py acervo_v2/*.py
```

Esses comandos não precisam de rede, tokens ou credenciais. A validação do catálogo deve ser somente leitura.

## Build isolado de candidata

```bash
python scripts/build_candidate_catalog.py --root . --output ./staging/acervo-v3-candidate
python scripts/validate_schemas.py --candidate-dir ./staging/acervo-v3-candidate
```

A saída é uma candidata separada. Não copie automaticamente essa saída para `catalog/`, não altere manifesto ativo e não publique a candidata. A publicação só poderá ser implementada/ativada após validação integral do pipeline e aprovação conforme o plano mestre.

Para verificar reprodutibilidade local, execute o build duas vezes em diretórios diferentes e compare os arquivos:

```bash
python scripts/build_candidate_catalog.py --root . --output ./staging/candidate-a
python scripts/build_candidate_catalog.py --root . --output ./staging/candidate-b
diff -qr ./staging/candidate-a ./staging/candidate-b
```

## Limites operacionais

- Não executar workflows online de TMDB/fontes como parte da validação offline.
- Workflows de enriquecimento e sugestão dependem de integração/proxy e secrets existentes; não colocar credenciais em arquivos ou logs.
- Não ativar agendamentos, gatilhos automáticos de importação ou publicação durante a construção.
- Não alterar TV, Mobile, Web, Player, Supabase/Cloudflare de produção ou repositórios de referência nesta etapa.
- Não remover dados ou arquivos herdados sem provar obsolescência e impacto.
- Dados de fixtures/teste devem permanecer identificados como tais.

## Fluxo de contribuição

1. Confirmar branch e HEAD.
2. Alterar somente o necessário para a etapa em andamento.
3. Executar os testes relevantes e a validação completa quando aplicável.
4. Revisar `git diff --check` e `git status`.
5. Criar commit pequeno e descritivo na V3.
6. Registrar evidências, resultado e próxima etapa na documentação de estado.
