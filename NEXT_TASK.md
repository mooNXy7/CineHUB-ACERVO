# Próxima Tarefa — CineHUB-ACERVO

## Tarefa atual
**Fase A — estabelecer baseline executável do ACERVO V2.**

A autorização para construir o cérebro foi concedida. A especificação e o blueprint estão registrados em:
- `ACERVO_V2_SPEC.md`
- `ACERVO_V2_BLUEPRINT.md`

## Execução imediata
1. Confirmar HEAD e estado da branch `develop/acervo-v2`.
2. Inventariar catálogo, scripts, workflows, formatos e dependências existentes.
3. Executar validações disponíveis e registrar falhas reais, sem mascarar scripts ausentes.
4. Criar fixtures representativas dos formatos existentes (começando por rádios e VOD) e testes de regressão.
5. Definir baseline reproduzível e lista fechada de bloqueios antes de refatorar o pipeline.

## Ordem de construção
Baseline → contratos/importadores → núcleo canônico → enriquecimento/qualidade → build/publicação/rollback → automação autônoma → integração dos consumidores autorizada separadamente.

## Regras de segurança
- Não alterar `main`.
- Não alterar TV, Mobile ou Web nesta fase.
- Não publicar OTA.
- Não apagar ou substituir dados em massa sem backup, diff e validação.
- Não aplicar automaticamente correspondências TMDB ambíguas.
- Não declarar tarefa concluída sem alteração, teste e evidência.
- A falha de uma fonte não pode apagar a última versão válida do catálogo.

## Definição de concluído
Cada fase precisa produzir uma saída executável e verificável. A fase A termina com baseline reproduzível, testes iniciais e inventário fechado de falhas. Não criar apenas documentação ou diretórios vazios.
