# Painel da TV

Aplicativo Android TV nativo em Java, sem dependências externas de runtime,
para a TCL com Android 11. Nome no launcher: **Painel da TV**.

- CPU total e por app/processo, normalizada pela capacidade total da TV (0–100%).
- RAM disponível via `MemAvailable`, total e zRAM/swap em uso.
- Lista de apps em execução, agrupando seus processos; opção de mostrar serviços
  nativos e ordenar por CPU ou RAM.
- RAM dos processos em **RSS**, em MiB. Inclui páginas compartilhadas; somar as
  linhas não representa a RAM usada pela TV, nem quanto um encerramento liberará.
- Ações pelo controle: encerrar app com confirmação ou abrir suas configurações.
- Encerramento bloqueado para launcher atual, teclado ativo, o próprio painel,
  UIDs privilegiados/compartilhados e apps de sistema. Exceções explícitas para
  Netflix, Prime Video, YouTube e YouTube Music, identificados nesta TV.
- Não apaga dados/cache, não desativa pacotes e não faz limpeza automática.

## Conexão

Usa o ADB da própria TV em **127.0.0.1:5555**. O notebook só é necessário para
instalar o APK ou reativar ADB TCP caso o firmware o desligue. O app não depende
nem do endereço Wi-Fi da TV nem de um servidor no notebook. Não oferece um
terminal/comandos arbitrários, não abre portas e não envia dados para a internet.

Na primeira conexão o Android pede autorização de depuração. Marcar “Sempre
permitir” salva a chave pública no sistema. Cada instalação gera sua própria
chave RSA em armazenamento privado; a chave do notebook não é copiada.
Backup do app está desativado. Desinstalar/limpar os dados gera outra chave na
próxima instalação, que precisará de nova autorização.

A coleta ocorre a cada 5 segundos enquanto a Activity está visível. Ao sair,
o socket fecha; não há serviço nem coleta em segundo plano. A CPU precisa de
duas amostras e aparece inicialmente como “Medindo…”. Conexões recusadas ou
medições incompletas deixam os valores indisponíveis, em vez de exibir dados
antigos como atuais. As ações dependem do ADB autorizado.

Não é necessário root. A persistência do ADB TCP após reiniciar a TV depende do
firmware e ainda não foi testada especificamente com este app. Para diagnóstico,
o botão **Conexão** explica como reconectar.

## Compilar e instalar

Requer JDK 17+, Python 3 e Android SDK Platform 30 / Build Tools 35.0.0. Os
binários do SDK usados localmente foram obtidos do repositório oficial Google:

- `https://dl.google.com/android/repository/platform-30_r03.zip`
  SHA-1 `e7c6280901dcfa511af098d67dd88c4dfcbc6ea2`
- `https://dl.google.com/android/repository/build-tools_r35_linux.zip`
  SHA-1 `2cfaa0bbb2336e9ec18ed3ecea84fa2e2af607bc`

Com Android SDK instalado, defina `ANDROID_SDK_ROOT` e instale os componentes:

```bash
sdkmanager "platforms;android-30" "build-tools;35.0.0"
```

Na raiz deste repositório:

```bash
./tv-panel/test.sh
./tv-panel/build.sh

# Escolha o serial exibido por adb devices -l.
export TV_SERIAL='SUBSTITUA_PELO_SERIAL_DO_ADB'
adb -s "$TV_SERIAL" install --no-incremental -r tv-panel/build/painel-tv.apk
adb -s "$TV_SERIAL" shell am start -n br.com.tcl.painel/.MainActivity
```

O build reconhece o layout padrão do SDK e também os arquivos ZIP oficiais
extraídos em `.tools/android-sdk/` na raiz do repositório. Para outros layouts,
defina `PANEL_BUILD_TOOLS` (pasta dos executáveis) e `PANEL_ANDROID_JAR`
(caminho do `android.jar`).

O APK está em `build/painel-tv.apk` (aproximadamente 33 KiB). A chave local de
assinatura está em `build/panel-dev.jks`, ignorada pelo Git, com senha de
desenvolvimento `android`. Preserve esse arquivo para atualizar o APK instalado
sem desinstalar. Não é uma chave para publicação em loja. O APK pequeno não
representa o uso de memória em execução: na amostra da TV, PSS ~31 MiB.

Para remover somente o painel:

```bash
adb -s "$TV_SERIAL" uninstall br.com.tcl.painel
```

## Validação em 2026-10-31

- Testes JVM: deltas de CPU, nomes de processos com parênteses, reutilização de
  PID, memória/unidades, dados inválidos, bloqueios de encerramento e rejeição
  de nomes de pacote que poderiam injetar comandos.
- ADB com servidor simulado: assinatura RSA de tokens, formato da chave pública,
  chave persistida, múltiplos streams, dados fragmentados e pacotes atrasados.
- APK compilado, assinatura verificada, instalado e aberto na TCL real.
- Conexão loopback autorizada e reconexão com a chave salva verificadas.
- Leituras de RAM e CPU e atualizações sucessivas verificadas pela interface.
- App temporário `br.com.tcl.painel.teste` instalado para validar o fluxo real:
  seleção → confirmação → force-stop → ausência de PID → mensagem de resultado.
  O app de teste foi removido ao terminar.
- No teste, RAM disponível foi de 324 para 321 MiB apesar do app ter encerrado:
  outras atividades do sistema influenciam a medição; não se promete ganho fixo.
- Navegação com D-pad/OK, filtro apps/todos e menu protegido verificados.
- Transporte ADB do notebook desconectado: painel continuou atualizando usando
  loopback. Ao pressionar Home, conexão local fechou; ao reabrir, reconectou
  usando a autorização salva.
- Nenhum app de streaming foi encerrado para realizar o teste.
- Evidências brutas da sessão permanecem locais; não fazem parte do repositório público.

Referência do protocolo: [ADB no AOSP](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/android14-release/protocol.txt).
