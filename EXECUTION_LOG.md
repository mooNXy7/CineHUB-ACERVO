# CineHUB-ACERVO — Registro de Execução

Cada entrada separa alterações, evidências, validação e pendências. Não registrar como concluído o que não foi executado.

## 2026-11-03 — Cérebro ACERVO V2 registrado no Git

### Autorização
O responsável aprovou a construção do ACERVO V2 e autorizou registrar a especificação e o blueprint na branch de desenvolvimento. Não houve autorização para alterar consumidores, `main` ou OTA.

### Alterações confirmadas
- Criado `ACERVO_V2_SPEC.md` — SHA do commit: `71d88198070344d53b5e0c119c9b7d1691682cd4`.
- Criado `ACERVO_V2_BLUEPRINT.md` — SHA do commit: `cc40a4ba4aea9ca89b1115a5fe8770641e11b7c3`.
- Atualizado `DECISIONS.md` para registrar a aprovação explícita e os limites de escopo.
- Atualizado `NEXT_TASK.md` para iniciar pela Fase A: baseline executável.
- Atualizado `HANDOFF.md` com ordem de leitura, protocolo de retomada e fatos técnicos que devem ser revalidados.
- Este log atualizado para registrar as alterações.

### Conteúdo técnico definido
- Arquitetura independente com registry de fontes, collectors, arquivo bruto, adaptadores, engines de processamento/enriquecimento/qualidade, builder, publisher e entrega.
- Domínios: VOD, canais, rádios, logos e EPG.
- IDs internos estáveis, aliases, variantes de streams, procedência e contratos versionados.
- TMDB com checkpoint, cache, rate limit, correspondência por confiança e revisão de ambiguidades.
- Publicação de snapshots imutáveis com manifesto promovido por último e rollback.
- Testes de regressão, falhas simuladas e teste de independência dos adaptadores de referência.

### Limites preservados
- Nenhuma alteração em `main`.
- Nenhuma alteração em TV, Mobile ou Web.
- Nenhuma OTA.
- Nenhum segredo foi copiado para o Git.
- Nenhum conteúdo de mídia audiovisual foi copiado/hospedado.

### Validação
- GitHub confirmou a criação dos dois documentos e retornou os SHAs acima.
- A validação de conteúdo, links internos e integridade do conjunto de documentos ainda será executada após atualizar o status e handoff.
- A implementação funcional ainda não começou; a próxima tarefa é a Fase A.

## 2026-11-02 — Preparação da continuidade e branch V2

### Objetivo
Criar uma linha de desenvolvimento isolada e documentos permanentes de continuidade.

### Verificações realizadas
- Repositório confirmado: `mooNXy7/CineHUB-ACERVO`.
- Branch padrão confirmada: `main`.
- HEAD de `main` consultado: `c2176962dccc218cd17622f0acd786ff76b18a6d`.
- Mensagem do commit-base: `revert: restore catalog after automatic sync`.

### Alterações realizadas
- Criada a branch `develop/acervo-v2`.
- Criados os seis documentos de continuidade: status, log, próxima tarefa, arquitetura, decisões e handoff.

### Limites
Nenhuma alteração funcional em catálogo/workflows, consumidores ou OTA. A branch V2 é isolada de `main`.


## 2026-11-03 — Fase A: baseline executável (em validação)

### Ambiente e proteção
- Repositório confirmado: mooNXy7/CineHUB-ACERVO.
- Branch: develop/acervo-v2; HEAD observado antes da execução: 2e430447866d9d3e3f042fda4cc0338efa1cfe68.
- main permaneceu em c2176962dccc218cd17622f0acd786ff76b18a6d. Comparação: V2 15 commits à frente, 0 atrás; diferença líquida limitada aos oito documentos V2.
- Nenhum catálogo foi alterado durante o inventário.

### Problema de rádios reproduzido
- Fonte autorizada fki1976/SaimoPlayer/vod/radios.txt usa nome|stream.
- Importador antigo exigia 3 colunas e interpretava campos 1/2 como nome/stream; formato atual era ignorado.
- Medição do catálogo: 1.026 rádios; 1.026 sem gênero; 754 sem logo; 2 sem stream; 253 URLs com extensão de imagem em stream; 0 IDs duplicados; 10 logos não HTTPS.
- Correção de código: parser aceita formato de 2 colunas e mantém compatibilidade com o layout legado. URL com extensão de imagem não entra como stream; fica em revisão. Nenhum registro existente foi removido.

### Implementação
- Adicionado tests/fixtures/radios_reference.txt com amostra curta da origem real.
- Adicionado tests/test_baseline.py com testes de formato atual, legado, imagem em stream, linhas malformadas e integridade básica da contagem/IDs.
- Adicionado scripts/audit_baseline.py, auditor somente de leitura para catálogo, workflows, scripts ausentes, dependências externas, logos e referências TMDB.
- Atualizado .github/workflows/validate.yml para executar também em develop/acervo-v2, rodar auditor e anexar relatório como artefato.

### Outros achados confirmados
- Manifesto VOD declara 40.938 filmes, 11.665 séries, 2.749 animes e 896 doramas (56.248). A contagem real será confirmada pelo auditor em CI.
- EPG registry tem seis fontes; health versionado de 2026-10-26 não foi tratado como verificação atual.
- Registry de fontes independentes declara uma fonte de canais.
- Workflows VOD referenciam quatro scripts ausentes e branch fixa antiga audit/acervo-hardening-2026-10.
- Atualizador principal ainda clona a referência externa para importar.
- Workflows TMDB usam função Supabase e SUPABASE_ANON_KEY; nenhum valor de segredo foi consultado ou copiado.

### Validação pendente
- Testes e auditor precisam executar no GitHub Actions após o commit.
- Snapshot/hash completo dos catálogos e inventário final de canais/logos/VOD dependem do relatório executado.
- A Fase A permanece aberta até essas evidências serem verificadas.


## 2026-11-03 — Fase A concluída

### Execução
- GitHub Actions: Validate catalog, run 930, run ID 41573383428.
- Resultado final: success.
- validate_catalog.py: success.
- audit_baseline.py: success.
- unittest: 25 testes, 0 falhas.
- py_compile scripts/*.py: success.
- Artefato ID 13202372616, com baseline.json, baseline.md e catalog-snapshot.sha256.

### Inventário executado
- catalog/: 728 arquivos, 314.213.984 bytes.
- sources/: 3 arquivos, 2.353 bytes.
- normalizer/: 1 arquivo, 311 bytes.
- scripts/: 6 arquivos, 79.560 bytes.
- tests/: 3 arquivos, 12.713 bytes.
- reports/: 1 arquivo antes dos relatórios desta baseline.
- .github/workflows/: 4 arquivos, 16.460 bytes.
- Nenhum manifesto padrão de dependências/configuração encontrado na raiz entre os nomes verificados.
- Canais: 2.431.
- VOD: filmes 40.938, séries 11.665, animes 2.749, doramas 896; arquivos presentes e contagens reais conferem.
- EPG: seis fontes; channel-map presente.
- Sources registry: uma fonte.
- Logos locais: zero imagens; apenas README e dois .gitkeep.

### Qualidade e problemas confirmados
- Rádios: 1.026; dois sem stream; 754 sem logo; 1.026 sem gênero; 252 URLs com extensão de imagem no campo stream_url; dez logos não HTTPS; zero IDs duplicados.
- Importador incompatível com referência nome|stream foi corrigido, mantendo o layout legado e rejeitando imagens como streams novos.
- Dois workflows VOD apontam para quatro scripts ausentes.
- update-catalog ainda clona a referência externa.
- Dois workflows referenciam funções Supabase; nenhum segredo TMDB declarado diretamente.
- Health EPG versionado em 2026-10-26 não foi tratado como sondagem ao vivo.

### Snapshot de proteção
- 731 arquivos em catalog/ e sources/.
- Total: 314.216.337 bytes.
- SHA-256 agregado: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- Manifesto individual disponível no artefato 13202372616.
- Nenhum catálogo ativo foi modificado durante a Fase A.

### Encerramento
Critérios da Fase A atendidos: inventário real; workflows/scripts verificados; testes implementados e executados; problemas confirmados separados de hipóteses; proteção documentada; histórico e próxima tarefa atualizados. Próxima etapa: Fase B, conforme NEXT_TASK.md.


## 2026-11-03 — Reconciliação técnica/documental da Fase A

### Identificadores reconciliados
- Branch auditada: develop/acervo-v2.
- HEAD real da branch: 3c4d2f7b2c4177e09745f6979860c95ffc8f39a3.
- Commit temporário de integração do runner: d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Comparação com main c2176962dccc218cd17622f0acd786ff76b18a6d: 34 commits à frente, zero atrás.
- Arquivos catalog/ ou sources/ na diferença: zero.

### Execução e artefato canônicos
- Workflow Validate catalog, run 930, ID 41573383428: success.
- Job validate: success.
- Validador do catálogo, auditor baseline, suíte unittest (25/25), py_compile e upload do artefato: success.
- Artefato ID 13202372616.
- Nome: acervo-v2-baseline-d6266bbe5679546e39a63e2724b1460c5465ed4f.
- Digest SHA-256 do ZIP: f7474e0132200ff522e8c82e2b85a20494c3776f4bd0c88b66a835a3c27ae690.
- SHA-256 agregado do snapshot de 731 arquivos: bf761a87164ba3a36f003f27a784d9f68cc3d60d48b113529db95d9e45eee67e.
- O baseline.json dentro do artefato registra git_head=d6266bbe..., que é o merge commit temporário do runner. Não confundir com o HEAD da branch 3c4d2f7....

### Fechamento
Relatórios, status, handoff e próxima tarefa reconciliados para os identificadores corretos da execução 930. PR #2 permanece aberto como draft, não mesclado. Nenhum catálogo, consumidor, segredo, configuração TMDB ou repositório de referência foi alterado. Fase B não iniciada.
