# TCL 40S615 · menos serviços, uma tela inicial simples

[![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](tvtool.py)
[![Android TV 11](https://img.shields.io/badge/Android_TV-11-3DDC84.svg)](docs/01-compatibilidade.md)

Um caso real de debloat **sem root** em uma TCL 40S615 com **1 GB de RAM**:
FLauncher como tela inicial, menos serviços proprietários em segundo plano e
reversão documentada para cada mudança.

O objetivo foi manter **streaming, HDMI, áudio e controle remoto**, dispensando
busca/comando de voz. O receptor Cast foi preservado; o teste físico de transmissão
do celular ainda não foi realizado.

> **Confirme a plataforma, não apenas o nome da TV.** A unidade testada usa
> **C06 / MT9221 / MT5867 / T221T01**, Android 11 e firmware
> **V8-T221T01-LF1V622.000807**. Uma TV com o mesmo nome comercial pode ter outra
> revisão. O perfil opcional `ttvs` também desativa o atualizador TCL.

## O que foi validado

| Função | Resultado nesta unidade |
|---|---|
| FLauncher após reiniciar / botão Home | Funcionando |
| Reprodução de vídeo no Netflix | Confirmada pelo proprietário |
| HDMI 1 e áudio | Confirmados pelo proprietário |
| Guard e `ttvs` após reiniciar | Desativados, sem processos/serviços ativos |
| Projectivy | Removido para o usuário, com backup dos APKs |
| TCL Channel e TCL Home | Mantidos; atalho redundante do Channel ocultado |
| Cast, CEC, outras portas HDMI, standby | Validação física pendente |
| Atualização de firmware pelo menu TCL | Requer reativar `ttvs` |

Na última observação após reiniciar e aguardar a inicialização assentar, havia
**~375 MiB de RAM disponível** e **~6–9% de CPU total em uso** nas duas amostras
finais. Isso é uma observação deste aparelho, não uma promessa de ganho.

O ajuste mais claro de CPU foi desligar a animação dos ícones do FLauncher:
nas amostras em repouso, o processo saiu de **~49–53,5% de um núcleo** para
**~0,5%**. Medições posteriores ao boot variaram; veja os [resultados](docs/05-resultados.md).

## Comece por aqui

```text
Conferir hardware → Conectar ADB → Inventário → Instalar e testar FLauncher
       → Trocar HOME → Aplicar um perfil por vez → Reiniciar → Validar
```

1. [Compatibilidade, requisitos e limites](docs/01-compatibilidade.md)
2. [ADB, Ethernet, hotspot e alternativas de conexão](docs/02-conexao.md)
3. [Instalação do launcher, animação e ícones duplicados](docs/03-launcher.md)
4. [Debloat, Alexa, Projectivy e restauração](docs/04-debloat-e-reversao.md)
5. [Resultados e histórico das decisões](docs/05-resultados.md)
6. [O que descobrimos sobre bootloader/root](docs/06-boot-e-firmware.md)
7. [Privacidade antes de compartilhar arquivos](docs/07-privacidade.md)

## Painel de tarefas para a TV

O app **[Painel da TV](tv-panel/README.md)** mostra CPU total e por processo,
RAM disponível, memória residente dos apps e zRAM/swap. É navegável pelo controle
remoto e permite encerrar apps individualmente, com confirmação e proteção de
serviços essenciais, launcher e teclado.

Funciona sem root usando ADB local autorizado na própria TV. Código Java,
recursos, testes e scripts de compilação estão em [`tv-panel/`](tv-panel/).
A instalação é independente dos perfis de debloat. A persistência da conexão
após reiniciar a TV ainda depende de validação neste firmware.

## Uso dos scripts

Requisitos: Python 3.10+ e [ADB oficial](https://developer.android.com/tools/releases/platform-tools).
O procedimento completo foi executado em Linux. Os scripts não precisam de
pacotes Python adicionais; instruções Bash/NetworkManager são específicas de Linux.

```bash
git clone https://github.com/sagnax/tcl-40s615-debloat.git
cd tcl-40s615-debloat

# Escolha o dispositivo exibido por adb devices -l.
# Este texto é um placeholder, não um endereço para usar literalmente.
export TV_SERIAL='SUBSTITUA_PELO_SERIAL_DO_ADB'

python3 tvtool.py --serial "$TV_SERIAL" inventory

# Primeiro simula. A execução exige acrescentar --execute.
python3 tvtool.py --serial "$TV_SERIAL" apply profiles/01-voice-feedback.json
python3 tvtool.py --serial "$TV_SERIAL" apply profiles/01-voice-feedback.json --execute

# Use o arquivo de reversão gerado na SUA máquina.
python3 tvtool.py --serial "$TV_SERIAL" restore reports/SEU_REGISTRO-journal.json
python3 tvtool.py --serial "$TV_SERIAL" restore reports/SEU_REGISTRO-journal.json --execute
```

Leia o guia antes de executar. `inventory` só consulta a TV. `apply`, `home`,
`alexa` e os comandos de restauração **simulam por padrão**. Uma falha interrompe
o lote; o registro é salvo antes de cada alteração e pode incluir uma operação
pendente caso a conexão caia. Confira o resultado antes de avançar.

Os comandos ADB escritos diretamente na documentação **executam imediatamente**;
eles não usam a proteção `--execute` do script.

## Perfis separados por decisão

| Perfil | O que altera | Quando usar |
|---|---|---|
| `01-voice-feedback.json` | Busca/Assistant Google e feedback | Se você dispensa voz/busca |
| `02-recommendations.json` | Recomendações do Google | Depois de validar o novo launcher |
| `03-tcl-guard.json` | Limpeza/monitoramento TCL Guard | Teste isolado, seguido de reboot |
| `04-tcl-services-optional.json` | Estatísticas, conta, integrações e atualizador TCL | Opcional; leia a consequência para atualizações |

Não há comando de “remover tudo”. O script também bloqueia nomes de vários
componentes essenciais; essa barreira não substitui análise de dependências.
Pacotes ausentes ou estados desconhecidos interrompem o procedimento.

## O que permanece fora do Git

Inventários, registros de reversão, backups, APKs e ferramentas baixadas ficam
somente na máquina de quem executa. **Os registros deste aparelho não estão
neste repositório.** Eles contêm identificadores e não serviriam para restaurar
uma TV diferente.

Não são distribuídos firmware, imagens de boot, binários ADB ou APKs de terceiros.
Links apontam para os projetos originais. A licença MIT cobre o código e a
documentação deste repositório, não o software desses terceiros.

## Verificação local

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_public_tree.py

# Requer JDK 17+; não precisa de Android SDK nem de TV conectada.
./tv-panel/test.sh
```

Os testes simulam ADB e verificam reversão, interrupções, troca de HOME, AppOps e
proteções. Eles **não substituem testes físicos de HDMI, streaming ou Cast**.

Contribuições são bem-vindas com modelo, plataforma, versão do firmware e um
resumo do resultado. Não anexe dumps brutos, credenciais ou identificadores do
aparelho em issues e pull requests.
