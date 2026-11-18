# Contratos canônicos CineHUB ACERVO

Schemas JSON Schema Draft 2020-12 versionados. Os contratos preservam extensões e campos de origem em `raw` e aceitam propriedades adicionais para evitar perda de informação durante a migração.

- `common/`: provenance, fontes, variantes de transmissão e assets.
- `vod/v1.schema.json`: filmes, séries, animes, doramas, temporadas e episódios.
- `channels/v1.schema.json`: canais, aliases, streams e relações EPG.
- `radios/v1.schema.json`: estações e variantes de áudio.
- `logos/v1.schema.json`: assets referenciados e associações.
- `epg/`: fontes, mapeamentos e programas.

Mudanças incompatíveis devem criar nova versão; não editar silenciosamente o contrato publicado. Os schemas descrevem candidatos canônicos, não autorizam promoção de catálogo.


## Execução local e offline

Na raiz do checkout, instale as dependências de validação uma vez:

```bash
python -m pip install -r requirements-dev.txt
```

Valide os 13 schemas, rode os testes e compile os scripts:

```bash
python scripts/validate_schemas.py
python -m unittest discover -s tests -v
python -m py_compile scripts/*.py acervo_v2/*.py
```

Construa e valide um candidato isolado, sem rede e sem segredos:

```bash
python scripts/build_candidate_catalog.py --root . --output ./staging/acervo-v2-candidate
python scripts/validate_schemas.py --candidate-dir ./staging/acervo-v2-candidate
```

Os scripts adicionam a raiz do checkout ao caminho de importação, portanto também podem ser executados por caminho absoluto a partir de outro diretório. O diretório de saída é staging/candidato; esses comandos não substituem arquivos ativos. As rotinas TMDB são separadas e exigem a integração Supabase/segredo já configurado somente quando executadas como workflows online.
