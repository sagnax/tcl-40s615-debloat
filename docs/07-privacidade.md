# 7. Publicar sem expor a sua TV

## Este repositório contém

Código, testes com dados fictícios, perfis de pacotes, especificações de
modelo/firmware, resultados resumidos e links para fontes originais.

Não contém dumps reais, registros de reversão da TV original, screenshots da
sessão, APKs, imagens de boot, ferramentas binárias, identificadores individuais,
credenciais ou dados da rede usada no diagnóstico.

## Arquivos gerados na sua máquina

`inventory` pode registrar número de série, IPs, propriedades, contas/nomes em
saídas de sistema e outros dados privados. Os registros de reversão guardam
identidade do aparelho para impedir aplicação em uma TV diferente. Tudo fica
em `reports/`, ignorado pelo Git. Backups e downloads também são ignorados.

Não use `git add -f` nessas pastas. Não envie logs completos em issues mesmo
que estejam fora do Git. Para relatar um problema, descreva o sintoma e informe
modelo, plataforma, versão de firmware e pacote envolvido; revise o texto.

No painel Android, a pasta `tv-panel/build/` contém o APK gerado e a chave de
assinatura de desenvolvimento. Ela fica fora do Git. Também são excluídos
keystores (`.jks`, `.keystore`) e chaves ADB (`.pk8`). Preserve sua chave de
assinatura local para atualizar o app instalado, sem publicá-la.

Também devem permanecer privados: ESN Netflix, MACs, serial do bootloader,
prefixos de lote associados à sua unidade, SSIDs, senhas, tokens, e-mails,
hostname e caminhos pessoais de arquivos.

## Verificar antes de publicar

```bash
python3 scripts/check_public_tree.py
git add README.md LICENSE .gitignore .gitattributes tvtool.py profiles docs scripts tests .githooks
python3 scripts/check_public_tree.py --staged
git diff --cached
```

O verificador rejeita caminhos privados, binários, padrões comuns de tokens,
chaves privadas, endereços de rede e e-mails no conteúdo selecionado. Ele não é
um detector perfeito de informação pessoal; uma revisão humana continua necessária.

Opcionalmente habilite o hook local para repetir a checagem em cada commit:

```bash
git config core.hooksPath .githooks
```

O hook verifica o conteúdo **do índice Git**, não só o arquivo atual. Assim uma
edição local posterior não mascara algo que já foi colocado no próximo commit.
Use um e-mail de commit `noreply` do GitHub se não quiser tornar seu e-mail pessoal
público. As credenciais de publicação não precisam estar em arquivos deste projeto.
