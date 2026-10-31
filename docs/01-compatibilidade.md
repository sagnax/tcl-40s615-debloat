# 1. Compatibilidade e preparação

## Unidade em que o procedimento foi validado

| Item | Valor não identificável |
|---|---|
| Modelo comercial | TCL 40S615 |
| Produto / dispositivo | C06_2K_GB / C06 |
| Identificação Fastboot | C06_eu |
| Plataforma reportada | MT9221; `ro.board.platform=mt5867` |
| Firmware | V8-T221T01-LF1V622.000807 |
| Android / kernel | Android TV 11 / Linux 4.19.116+ |
| ABI | armeabi-v7a / armeabi, 32 bits |
| Hardware anunciado | 1 GB RAM, 8 GB armazenamento, painel Full HD |
| RAM visível ao sistema | Aproximadamente 918 MiB |
| Launcher usado | FLauncher 0.18.0 |

Esses códigos descrevem um modelo/firmware, não uma unidade individual.
Não foram publicados número de série, MAC, ESN Netflix, IP, conta ou nome de rede.

O nome comercial sozinho não comprova equivalência de placa, painel ou firmware.
Em outra plataforma, use apenas a parte de inventário e analise as dependências.
O comando `home` recusa um launcher original diferente do caso testado.

## Preparação

- Tenha acesso ao controle remoto e aos botões físicos da TV.
- Ative as opções do desenvolvedor pelo número da compilação e habilite a
  depuração USB; a localização do menu pode mudar por firmware.
- Instale Python 3.10+ e os Android SDK Platform Tools oficiais no notebook.
- Confirme o aparelho em `adb devices -l` e aceite a autorização na TV.
- Anote os apps e recursos que você realmente usa. Os perfis publicados não
  removem Netflix, Prime Video, YouTube ou o receptor Cast.

Você pode colocar `adb` no PATH ou usar `--adb CAMINHO_DO_ADB`. Também é aceito
`.tools/platform-tools/adb` dentro desta pasta; no Windows, `adb.exe`.

## Antes de alterar

```bash
adb devices -l
export TV_SERIAL='SUBSTITUA_PELO_SERIAL_DO_ADB'
python3 tvtool.py --serial "$TV_SERIAL" inventory
```

O inventário grava em `reports/`, incluindo firmware, pacotes, processos,
memória, armazenamento e HOME. Essa pasta é privada e ignorada pelo Git.

**Inventário não é backup de firmware nem dos dados privados dos apps.** Com
ADB comum não obtivemos acesso a esses dados nem uma cópia da partição de boot.

## Limites de uso e validação

Aplicar desativação a pacotes do sistema exige avaliar o aparelho real. Faça um
lote por vez e teste controle, configurações, rede, vídeo e HDMI após reiniciar.
Se uma função necessária falhar, restaure o último lote antes de continuar.

Na unidade testada não se usava TV aberta. Mesmo assim, `com.tcl.tvinput` e
`com.tcl.tv` foram preservados porque também fornecem as entradas/funcionalidades
usadas por HDMI. CEC, Cast real, outras portas e standby não foram validados.

## Componentes que preservamos

| Componentes | Por que permaneceram |
|---|---|
| `com.tcl.tv`, `com.tcl.tvinput`, `sitatvservice` | Entradas, painel e funções usadas por HDMI; não tratar como “só TV digital” |
| `com.tcl.system.server`, `com.tcl.tcl_bt_rcu_service`, `com.tcl.autopair` | Controle, teclas e integração TCL |
| `com.tcl.inputmethod.international`, `com.google.android.inputmethod.latin` | Teclados; não remover sem alternativa validada |
| `com.google.android.apps.mediashell`, `com.google.android.tv.remote.service` | Cast e controle remoto do ecossistema Google |
| `com.google.android.gms`, `com.google.android.gsf`, `com.android.vending` | Serviços Google e loja |
| SystemUI, provedores, rede, Bluetooth, DRM, permissões, instalador e WebView | Infraestrutura do Android e dos apps |
| `com.tcl.partnercustomizer` | Preservado; apenas sua entrada duplicada do Channel foi ocultada |

`ginga_service` permaneceu como serviço nativo do firmware, iniciado como root.
Apesar de o usuário dispensar TV digital, não houve um mecanismo validado para
removê-lo isoladamente. O pico de CPU inicial dele não se manteve nas amostras
posteriores. Não foram mortos processos nativos de painel/áudio/entradas.

A verificação de identidade da restauração exige o mesmo firmware e usuário.
Quando ambos os registros têm serial físico válido e igual, um novo IP/serial
de transporte ADB é aceito. Sem esse identificador, o transporte também deve
coincidir. Não edite registros de outro aparelho para contornar essa verificação.
