# Enriquecimento seguro de metadados VOD

## Fluxo atual

O ACERVO usa a API oficial do TMDB por meio da Edge Function `cinehub-catalog` do Supabase. O segredo `TMDB_TOKEN` permanece exclusivamente no Supabase. O repositório recebe apenas o segredo de acesso público `SUPABASE_ANON_KEY` via GitHub Actions.

O script `scripts/enrich_vod_metadata.py`:
- percorre as quatro categorias declaradas no manifesto (`movies`, `series`, `anime`, `doramas`);
- usa a sequência estável dos registros com TMDB ID numérico existente;
- consulta o ID exato, sem busca por título e sem atribuir novos IDs;
- confirma o ID retornado, o título normalizado e eventual ano explícito;
- considera apenas campos vazios: pôster, ano, gêneros e sinopse;
- produz patches de revisão, sem modificar diretamente o catálogo;
- usa cache SQLite por execução, timeout, intervalo e retries limitados.

O workflow `.github/workflows/enrich-vod-metadata.yml` aplica os patches que passam pelas verificações de identidade, executa `validate_catalog.py` e a suíte de testes e só então publica os arquivos modificados na branch de auditoria. Campos preenchidos anteriormente e fontes de reprodução são preservados.

## Checkpoints

O offset é contado sobre a sequência estável de registros com TMDB ID numérico existente, atravessando as quatro categorias. Cada execução pode processar até cinco lotes consecutivos de 1.000 registros.

Checkpoints concluídos e confirmados:
- Offset 0: 913 registros atualizados; 1.533 campos preenchidos.
- Offset 2.000: 38 registros atualizados.
- Offset 3.000: 890 registros atualizados; 2.324 campos preenchidos nos dois lotes 2.000/3.000.
- Offsets 4.000–8.000: 4.593 registros atualizados; 11.621 campos preenchidos.
- Offsets 9.000–13.000: 4.562 registros atualizados; 11.363 campos preenchidos; 5.000 registros examinados e 5.000 requisições; zero conflito de campos e zero rejeição de identidade.

A execução 9.000–13.000 foi concluída com sucesso no workflow [41269624509](https://github.com/mooNXy7/CineHUB-ACERVO/actions/runs/41269624509).

O próximo checkpoint foi avançado para offset 14.000. Não repetir offsets já concluídos. Cada lote só deve ser contabilizado após sucesso da aplicação, validação, testes e commit.

## Tratamento de respostas TMDB

O cliente trata HTTP 404 como `not_found` terminal. A Edge Function Supabase v4 atualmente converte alguns 404 do TMDB em HTTP 500; o cliente reconhece somente a resposta explícita de recurso inexistente (`status_code=34` ou mensagem correspondente) como `not_found`, sem retry transitório. Outros HTTP 500/502/503/504 continuam sujeitos a retries limitados.

Uma correção definitiva no contrato HTTP da Edge Function exige atualização e deploy no Supabase. Isso permanece fora desta branch e não deve ser executado sem autorização explícita para alterar produção.

## Segurança e critérios de aceite

- Nunca incluir `TMDB_TOKEN`, chaves ou URLs de reprodução em commits, relatórios ou logs.
- Não preencher IDs TMDB novos automaticamente.
- Não aceitar correspondência apenas por título quando a identidade for ambígua.
- Não sobrescrever metadados existentes.
- Não alterar fontes de reprodução.
- Não publicar lotes se validação ou testes falharem.
- Manter patches e resumos de execução como artefatos temporários do GitHub Actions.
- Não fazer merge, deploy de produção, deploy Supabase ou OTA como parte deste fluxo.
