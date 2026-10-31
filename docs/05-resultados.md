# 5. Resultados e histórico do caso

## O que foi feito, na ordem

1. Identificação da plataforma, firmware, memória, armazenamento e ABI.
2. Instalação local do ADB oficial; diagnóstico das tentativas USB e de rede.
3. Conexão estável usando celular por USB e hotspot do notebook, depois de
   retirar o Ethernet da TV. Autorização ADB aceita na tela.
4. Inventário de pacotes, estados, processos, serviços, HOME e recursos.
5. Instalação e teste do FLauncher; desativação de busca/voz e feedback Google.
6. Troca de HOME, desativação do launcher Google e retirada da interceptação
   Projectivy da lista de acessibilidade, com registro do valor anterior.
7. Desativação de recomendações. Projectivy primeiro desativado e depois removido,
   após copiar APK base e splits, por escolha do proprietário.
8. Testes de Alexa: desativação e remoção por usuário revertidas pelo firmware;
   bloqueio individual de componentes recusado. Adotadas restrições AppOps.
9. Netflix com vídeo, Home e HDMI 1 com dispositivo físico testados.
10. Investigação de boot/root solicitada: consultas somente de leitura,
    retorno ao Android e confirmação dos estados anteriores.
11. Revisão de background identificou o custo da animação dos ícones FLauncher;
    opção desligada e nova medição de CPU.
12. Guard desativado e testado após reboot; depois TTvs, em lote separado e com
    outro reboot. Ambos permaneceram sem processos/serviços.
13. Netflix, HDMI 1, áudio e Home testados novamente com esse último lote.
14. Dois banners TCL Channel investigados pelo pacote e pelo destino de abertura;
    apenas o atalho redundante foi ocultado. TCL Channel e TCL Home mantidos.
15. Reinício final, amostras inicial e após mais 45 segundos, conferência de CPU,
    memória, serviços, pacotes, AppOps, HOME e registro de falhas.

## Estado final

| Categoria | Resultado |
|---|---|
| Desativados | Katniss, feedback, recomendações, launcher Google, Guard e TTvs |
| Removido para o usuário | Projectivy, com backup dos APKs e pedido de preservação de dados |
| Alexa | App reinstalado/reativado pelo firmware; background restringido via AppOps |
| Interface | FLauncher; animação de destaque desligada; um único atalho Channel visível |
| Preservados | Netflix, Prime Video, YouTube, Play Store, Play Services, Cast, Bluetooth, teclados, componentes TCL de HDMI/controle |
| Já desativados antes | Stan, Wuaki/Rakuten, Google Videos e Play Games; não foram mudanças desta sessão |

O estado do microfone Alexa já era `ignore` por UID antes do ajuste de AppOps
de background. Não atribuímos essa configuração a uma mudança feita aqui.

## Medições e seus limites

- Antes de desligar a animação, FLauncher apareceu em **49–53,5% de um núcleo**.
- Depois do ajuste, a medição específica foi **3,2%, 0,5%, 0,5%**, em repouso.
- Após o último reboot, FLauncher ficou em **1,5–3% de um núcleo** nas duas
  amostras finais; havia serviços terminando tarefas de inicialização.
- CPU total nessa última sequência: **15,5%, 6,25%, 8,5%**. O aparelho tem quatro
  núcleos; o `top` mostra capacidade agregada de 400%. Para uso total, dividimos
  a porcentagem agregada usada por quatro.
- RAM disponível: **~324 MiB** na amostra inicial e **~374,5 MiB** na posterior.
- Nenhum dos seis pacotes desativados reapareceu como processo nessas amostras.
- TCL Channel e TCL Home não iniciaram processos na última revisão pós-boot.
- Não apareceram erros fatais no buffer de falhas consultado.

Não há benchmark controlado de ganho global em RAM/CPU: os snapshots anteriores
tinham telas, apps e tempos de boot diferentes. **Não se somam RSS dos processos
como memória exclusiva**, pois incluem páginas compartilhadas. As estimativas
individuais do Guard e TTvs citadas no guia são PSS de momentos específicos.

### Como conferir no seu aparelho

Os comandos abaixo são consultas. Salve resultados apenas localmente:

```bash
adb -s "$TV_SERIAL" shell ps -A
adb -s "$TV_SERIAL" shell dumpsys activity services
adb -s "$TV_SERIAL" shell cat /proc/meminfo
adb -s "$TV_SERIAL" shell top -b -n 3 -d 2 -m 12
adb -s "$TV_SERIAL" shell dumpsys meminfo com.tcl.guard
adb -s "$TV_SERIAL" shell dumpsys meminfo com.tcl.ttvs
adb -s "$TV_SERIAL" shell logcat -b crash -d -t 100
```

Na leitura de memória use `MemAvailable`, além de contexto e PSS; `MemFree`
sozinho ignora memória recuperável pelo sistema. Um processo carregado sem
serviço/CPU relevante pode ser cache de um app usado recentemente. Não force
paradas em massa apenas para deixar uma captura “vazia”.

`dumpsys cpuinfo` pode apresentar uma janela histórica; confira o período no
próprio cabeçalho. Para uma observação mais atual, usamos vários ciclos do `top`.

Durante o teste isolado Guard/TTvs, MemAvailable chegou a ser menor logo após
reiniciar do que na amostra anterior. Isso reforça que a ausência dos processos
é comprovada, mas um ganho fixo em MB não foi estabelecido.

## O que ainda não foi validado

Cast físico, CEC, portas HDMI além da 1, standby/retorno, instalação de um app
pela Play Store após o último lote e uso prolongado. Manter o pacote habilitado
não prova que toda a função funciona. Uma atualização futura de firmware pode
alterar pacotes, políticas e comportamento.

Os helpers públicos `home` e `alexa` empacotam as operações descritas; foram
testados com ADB simulado, inclusive reversão e falhas. Não houve teste em uma
segunda unidade. Registros reais foram mantidos privados, e os resultados aqui
foram transcritos sem identificadores do aparelho.
