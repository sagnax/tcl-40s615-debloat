# 2. Conectar pelo ADB

## Caminho simples: mesma rede local

Leia o IP atual em Configurações → Rede da TV. No Bash:

```bash
read -r -p 'IP atual da TV: ' TV_IP
export TV_SERIAL="${TV_IP}:5555"
adb connect "$TV_SERIAL"
adb devices -l
```

Aceite “Permitir depuração USB?” na TV. Em alguns firmwares, a opção chamada
“depuração USB” também disponibiliza ADB na rede; isso precisa ser testado,
não presumido. `unauthorized` significa que o aparelho respondeu e aguarda
autorização. Um timeout ou `No route to host` não é a mesma coisa.

Se houver uma opção de depuração por rede com porta/código próprios, use os
dados mostrados pelo aparelho e a [documentação oficial ADB](https://developer.android.com/tools/adb).
O pareamento Wi-Fi moderno não foi o caminho usado nesta TV Android 11.

## O obstáculo encontrado nesta sessão

A TV não aparecia no USB durante o Android normal. As tentativas pela rede
doméstica também falhavam na resolução de vizinhança, inclusive com a TV por
Ethernet. A causa dessas primeiras falhas **não foi comprovada**; não afirmamos
que o roteador tivesse isolamento de clientes.

Depois de criar um hotspot, a TV via a rede, recebia a senha e dizia não conseguir
encontrá-la. **Retirar fisicamente o cabo Ethernet permitiu conectar ao Wi-Fi.**
Esse foi o detalhe decisivo na unidade testada.

Para testar Wi-Fi nesta situação, retire o Ethernet da TV antes de insistir
em senha, banda ou restauração de rede. O IP pode mudar ao trocar de interface.

## Caminho que funcionou: celular por USB + hotspot do notebook

```text
Internet móvel → celular → ancoragem USB → notebook → Wi-Fi de teste → TV
```

1. Conecte um celular Android ao notebook com cabo de dados.
2. No celular, procure **Ancoragem USB / Compartilhamento de internet por USB**
   nas configurações de hotspot/rede. Não é a seleção PTP/MTP/Android Auto.
3. Confirme no notebook uma interface USB de rede e acesso à internet por ela.
4. Crie um ponto de acesso no notebook em **2,4 GHz, WPA2, canal 6**.
5. Retire o Ethernet da TV e conecte-a a essa rede.
6. Leia o novo IP da TV e execute `adb connect` novamente.

### Exemplo Linux com NetworkManager

Verifique suporte AP antes de mudar a conexão:

```bash
nmcli -f GENERAL.DEVICE,WIFI-PROPERTIES device show
ip -brief address
ip route
```

O hotspot usa a interface Wi-Fi; pode substituir a conexão Wi-Fi atual. Confirme
primeiro que a internet pelo USB funciona. Defina os placeholders abaixo e
guarde a senha localmente, sem colocá-la em issue ou commit.

```bash
export WIFI_IFACE='SUBSTITUA_PELA_INTERFACE_WIFI'
export TEST_SSID='SUBSTITUA_PELO_NOME_DA_REDE_DE_TESTE'
read -r -s -p 'Senha temporária WPA2 (8+ caracteres): ' TEST_PSK
printf '\n'

nmcli connection add type wifi ifname "$WIFI_IFACE" \
  con-name tv-diagnostico autoconnect no ssid "$TEST_SSID" \
  802-11-wireless.mode ap 802-11-wireless.band bg \
  802-11-wireless.channel 6 \
  802-11-wireless-security.key-mgmt wpa-psk \
  802-11-wireless-security.proto rsn \
  802-11-wireless-security.pairwise ccmp \
  802-11-wireless-security.group ccmp \
  802-11-wireless-security.pmf disable \
  802-11-wireless-security.psk "$TEST_PSK" \
  ipv4.method shared ipv6.method disabled

unset TEST_PSK
nmcli connection up tv-diagnostico
```

Use WPA2 apenas para esse teste de compatibilidade; não altere a segurança da
rede doméstica inteira. A criação do perfil pode depender das permissões locais.
No Distrobox, as consultas e comandos de rede foram executados no host com
`distrobox-host-exec nmcli ...`; não foi necessário instalar ADB globalmente.

Após terminar, desconecte a TV da rede de teste e restaure a conexão habitual:

```bash
nmcli connection down tv-diagnostico
nmcli connection delete tv-diagnostico
# Reconecte o notebook à sua rede habitual pelo gerenciador de rede.
```

Não desligue essa rede enquanto depender dela para uma reversão por ADB.

## Outras alternativas

- TV e notebook por Ethernet no mesmo roteador, se ambos tiverem interface.
- Hotspot do celular em 2,4 GHz/WPA2, com Ethernet retirado da TV.
- USB direto, se a porta, o cabo e o firmware expuserem ADB.

O cabo USB A–A **não enumerou ADB no Android normal**, mas funcionou em Fastboot
nesta unidade. Isso não significa que todo cabo/porta tenha essa função.
Não entre no bootloader apenas para resolver conectividade: o debloat foi por
ADB na rede.

Cast precisa de descoberta entre os dispositivos. A topologia de diagnóstico
acima coloca celular e TV em sub-redes diferentes; teste transmissão real depois
de colocar ambos na mesma rede doméstica.

## Captura de tela: particularidade observada

Nesta unidade, `exec-out screencap -p` acrescentou mensagens do wrapper nativo
antes dos bytes PNG, corrompendo o arquivo redirecionado. Funcionou gravar o
PNG no aparelho e depois usar `adb pull`:

```bash
mkdir -p private
adb -s "$TV_SERIAL" shell screencap -p /sdcard/tv-diagnostico.png
adb -s "$TV_SERIAL" pull /sdcard/tv-diagnostico.png private/tv-diagnostico.png
adb -s "$TV_SERIAL" shell rm /sdcard/tv-diagnostico.png
```

Revise a imagem antes de compartilhá-la: telas de rede/Sobre podem expor
identificadores. Nenhuma imagem da sessão original foi incluída no repositório.
