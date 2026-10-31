# 3. FLauncher, Home e ícones

## Instalar e testar antes de trocar HOME

A versão usada foi **FLauncher 0.18.0**, com suporte à ABI armeabi-v7a da TV.
Obtenha pela loja ou pelo [release do próprio projeto](https://gitlab.com/flauncher/flauncher/-/releases/0.18.0).
Não use um APK de origem desconhecida ou uma versão para outra ABI.

Exemplo Bash, com ADB já disponível e `TV_SERIAL` definido:

```bash
mkdir -p .tools
curl --fail --location \
  'https://gitlab.com/api/v4/projects/26632151/packages/generic/flauncher/0.18.0/flauncher-0.18.0.apk' \
  -o .tools/flauncher-0.18.0.apk

sha256sum .tools/flauncher-0.18.0.apk
adb -s "$TV_SERIAL" install .tools/flauncher-0.18.0.apk
adb -s "$TV_SERIAL" shell am start -W -n me.efesser.flauncher/.MainActivity
```

SHA-256 do APK oficial usado na sessão:

```text
376fc528c880cdf7c7c04b2d3708c69f911144498218babb6300808b772af32e
```

O checksum identifica esse artefato específico; não valida sozinho a procedência
de um download obtido em outro lugar. Se já tiver outra versão, registre-a e
teste; não force downgrade para seguir o guia.

**Antes do próximo passo, navegue pela grade com o controle e abra um app.**
Mantenha o launcher original habilitado até confirmar que isso funciona.

## Selecionar como tela inicial

Na unidade testada, `set-home-activity` sozinho não resolveu: o Home ainda abria
o Google. Havia também um Projectivy previamente instalado com serviço de
acessibilidade interceptando o botão.

O helper abaixo registra HOME, estado do Google Launcher e lista de serviços
de acessibilidade. Na execução, abre FLauncher, retira **somente** o serviço do
Projectivy dessa lista, desativa o launcher Google, seleciona FLauncher e verifica
HOME. Outros serviços de acessibilidade são preservados.

```bash
python3 tvtool.py --serial "$TV_SERIAL" home
python3 tvtool.py --serial "$TV_SERIAL" home --execute
```

Ele só suporta a troca de `com.google.android.tvlauncher/.MainActivity` para
`me.efesser.flauncher/.MainActivity`. Outro HOME interrompe o comando. Se houver
falha durante a troca, tenta restaurar o estado anterior; se ADB cair, use o
registro salvo para restaurar após reconectar.

Guarde o caminho `reports/...-home.json` mostrado no terminal. Para simular ou
executar a reversão:

```bash
python3 tvtool.py --serial "$TV_SERIAL" restore-home reports/SEU_REGISTRO-home.json
python3 tvtool.py --serial "$TV_SERIAL" restore-home reports/SEU_REGISTRO-home.json --execute
```

Alternativas: manter o launcher original e reduzir suas recomendações, ou usar
um launcher alternativo que você já tenha testado, como Projectivy. Não aplique
o helper específico acima a outro launcher; siga o procedimento do projeto
escolhido e preserve um caminho de volta. Não foi necessário escrever um
launcher novo para alcançar o resultado deste caso.

## Ajuste que reduziu trabalho contínuo de CPU

No FLauncher, abra a engrenagem → **Settings** e desligue
**App card highlight animation**.

Nesta versão a animação vinha ligada por padrão. Com a tela inicial em repouso,
o processo apareceu em ~49–53,5% de um núcleo; após desligar, caiu para ~0,5%
nas amostras seguintes. Não confunda porcentagem de um processo em um núcleo
com porcentagem da CPU total de quatro núcleos.

Para reverter, basta religar a mesma opção. Wallpaper e demais preferências
podem ser ajustados pela interface; não foram alteradas escalas globais de
animação do Android para obter essa medição.

## Por que havia dois TCL Channel?

| Entrada na grade | Pacote | Resultado ao abrir |
|---|---|---|
| TCL Channel, versão 9.47 | `com.tcl.partnercustomizer` | Redireciona para o Channel real |
| TCL Channel, versão 7.2.1.6 | `com.tcl.waterfall.overseas` | Abre o app de conteúdo |
| TCL Home, versão 1.682 | `com.tcl.dashboard` | App separado, mantido |

O primeiro expõe `.tkey.WithIcon`; o segundo expõe `.main.MainActivity`.
Os dois testes terminaram em `com.tcl.waterfall.overseas/.main.MainActivity`.
Eram **dois pacotes com a mesma marca/destino**, não duas instalações do app de
conteúdo. A atualização em `/data` e a cópia de fábrica do mesmo pacote também
não significam dois apps separados para o usuário.

Para identificar com segurança, segure OK no ícone e leia o pacote no painel
do FLauncher. Use **Hide** apenas em `com.tcl.partnercustomizer`. Isso oculta
o atalho da grade, mantendo o pacote, o Channel real e o TCL Home.

Reversão: Settings → Applications → TCL Channel versão 9.47 / pacote
`com.tcl.partnercustomizer` → **Unhide**. Se as versões diferirem, use o pacote,
não apenas o desenho do ícone.

Ícones de pacotes desativados também podem continuar no banco do launcher.
O ícone visível sozinho não prova que o app esteja rodando; confira processos
e serviços antes de tomar outra decisão.
