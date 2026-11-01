# Auditoria de compatibilidade das referências

Revisão em 2026-11-01.

O repositório fki1976/SaimoPlayer foi confirmado como a referência central para índices VOD, fichas, destaques, rádios, playlists e ferramentas de geração. O repositório fki1976/SaimoTV-Android foi examinado como referência complementar de consumo Android TV.

O formato de busca de referência é tabulado e contém título, tipo e letra, com ano opcional. O catálogo ACERVO organiza VOD em manifesto, índices por categoria e arquivos de detalhes. As amostras de séries mantêm temporadas e episódios hierárquicos em arrays JSON, compatíveis com a leitura atual do cliente TV.

A workflow da branch de trabalho foi corrigida para usar o endereço canônico fki1976/SaimoPlayer. O cliente atual da TV ainda contém uma URL antiga para resolver referências externas de provedor; essa alteração fica fora do escopo atual e deve ser tratada quando a integração TV for autorizada.

A inspeção foi documental e estrutural. Não foram executados testes de reprodução, sondagens em massa, build de APK ou testes em dispositivo. Nenhum catálogo de produção foi alterado.