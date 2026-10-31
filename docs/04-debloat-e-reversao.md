# 4. Aplicar em etapas e conseguir voltar

## Perfis de desativação

Todos usam `pm disable-user --user 0`. Mantêm APK e dados. O script primeiro
consulta **todos os estados do lote**, salva o estado anterior antes de cada
escrita e verifica a resposta. Não assume sucesso apenas pela mensagem do ADB.

Depois de validar o FLauncher, execute **um lote por vez**, começando pela
simulação. Exemplo para voz/feedback:

```bash
python3 tvtool.py --serial "$TV_SERIAL" apply profiles/01-voice-feedback.json
python3 tvtool.py --serial "$TV_SERIAL" apply profiles/01-voice-feedback.json --execute
```

Repita, se corresponder ao seu uso, com:

1. `profiles/02-recommendations.json` — depois da troca de launcher.
2. `profiles/03-tcl-guard.json` — teste isolado do Guard.
3. `profiles/04-tcl-services-optional.json` — somente após ler o efeito abaixo.

Guarde o registro `reports/...-journal.json` gerado por cada execução. Se um
pacote não existir, o script interrompe; revise o manifesto local em vez de
aplicar nomes de outra revisão sem investigar.

### Guard

`com.tcl.guard` mantinha serviços de gerência de memória, uso do aparelho,
limites de I/O, saúde e limpeza. Foi desativado, seguido de reinício, e confirmado
sem processo nem serviço. Na medição anterior, tinha ~14,5 MiB PSS.

### TCL TV Services — opcional

`com.tcl.ttvs` mantinha serviços de estatísticas de uso/BI, conta, mensagens e
integração Alexa. **Também fornece o atualizador de firmware TCL.**

Desativá-lo deixou o atualizador pelo menu indisponível. Restaure esse pacote
antes de uma atualização local ou de rede por esse menu. Se você quer manter
o atualizador disponível o tempo inteiro, **não aplique esse perfil**.

Foram observados dois processos, principal e `.persistent`, somando ~34,6 MiB
PSS naquela medição. Após desativar e reiniciar, ambos desapareceram; Netflix,
HDMI 1, áudio e Home foram novamente testados pelo proprietário.

Guard e TTvs compartilham UID de sistema. Não aplique bloqueios por UID nem
revogue suas permissões em massa: outros componentes compartilham essa identidade.
Neste caso foi alterado somente o estado de cada pacote.

## Reiniciar e validar cada etapa

```bash
adb -s "$TV_SERIAL" reboot
# Aguarde a TV voltar, confirme seu IP e reconecte se necessário.
adb connect "$TV_SERIAL"
adb -s "$TV_SERIAL" shell getprop sys.boot_completed

adb -s "$TV_SERIAL" shell pm list packages -d --user 0
adb -s "$TV_SERIAL" shell ps -A
adb -s "$TV_SERIAL" shell dumpsys activity services com.tcl.guard
adb -s "$TV_SERIAL" shell dumpsys activity services com.tcl.ttvs
```

Estado desativado e ausência de processos são verificações diferentes. Observe
também depois que a inicialização assentar: o firmware reativou outro pacote
durante nossos testes. Uma amostra imediatamente após executar `pm` não basta.

Teste Home/Voltar, configurações, Netflix com vídeo, HDMI com imagem e áudio,
volume e reinicialização. Teste Cast com celular/TV na mesma rede. CEC, outras
portas e standby precisam de seus próprios testes se você usa esses recursos.

Para restaurar um lote, primeiro simule e depois execute:

```bash
python3 tvtool.py --serial "$TV_SERIAL" restore reports/SEU_REGISTRO-journal.json
python3 tvtool.py --serial "$TV_SERIAL" restore reports/SEU_REGISTRO-journal.json --execute
```

O script restaura o estado **original**, inclusive a diferença entre padrão e
habilitado explicitamente. Reverte também operações pendentes no registro caso
a conexão tenha caído depois de uma escrita. Uma alteração externa de estado
pode fazê-lo recusar a reversão; revise em vez de sobrescrever o registro.

## Alexa: o que não persistiu e a alternativa aplicada

`com.tcl.smartalexa` voltou ao estado padrão após reboot. Removê-lo com
`pm uninstall -k --user 0` também não persistiu: o firmware o reinstalou.
Tentativas de bloquear seus componentes individuais foram recusadas pelo sistema.

A solução aplicada foi restringir **somente as duas operações de background**
do pacote Alexa, depois de guardar os modos anteriores:

```bash
python3 tvtool.py --serial "$TV_SERIAL" alexa
python3 tvtool.py --serial "$TV_SERIAL" alexa --execute

adb -s "$TV_SERIAL" shell cmd appops get com.tcl.smartalexa RUN_IN_BACKGROUND
adb -s "$TV_SERIAL" shell cmd appops get com.tcl.smartalexa RUN_ANY_IN_BACKGROUND
adb -s "$TV_SERIAL" shell dumpsys activity services com.tcl.smartalexa
```

Os dois modos ficaram `ignore` e persistiram nos reinícios observados. Isso
**não é remoção definitiva do app nem garantia de bloquear todo tipo de execução**.
Serviços vinculados por outros apps precisam ser verificados no aparelho real.

O microfone já estava em `ignore` por UID nesta unidade; não foi alterado.
O helper também não altera microfone. Confira as permissões pela interface se
isso for uma preferência sua. Não copie uma política de UID para outra unidade.

O registro `reports/...-alexa.json` permite restaurar os modos que existiam,
em vez de presumir que o original era `allow`:

```bash
python3 tvtool.py --serial "$TV_SERIAL" restore-alexa reports/SEU_REGISTRO-alexa.json
python3 tvtool.py --serial "$TV_SERIAL" restore-alexa reports/SEU_REGISTRO-alexa.json --execute
```

## Projectivy — remoção opcional com backup dos splits

Havia um Projectivy instalado antes do procedimento. Após validar FLauncher,
ele foi desativado e depois removido a pedido do proprietário. **Se não tiver
Projectivy ou quiser mantê-lo como alternativa, pule esta parte.**

Copie todos os APKs do pacote, inclusive os splits, antes de removê-lo:

```bash
python3 scripts/backup_projectivy.py --serial "$TV_SERIAL"
# Só avance quando o script confirmar backup completo e informar a pasta.
adb -s "$TV_SERIAL" shell pm uninstall -k --user 0 com.spocky.projengmenu
```

`-k` solicita preservação dos dados; isso não substitui backup privado dos dados
do aplicativo. O backup de APKs contém código, não suas credenciais/configurações.
Os APKs ficam privados em `reports/` e não são redistribuídos aqui.

Para restaurar, use a pasta que o helper gerou, confira os hashes e instale
todos os splits juntos:

```bash
export PROJECTIVY_BACKUP='SUBSTITUA_PELA_PASTA_DO_BACKUP'
(cd "$PROJECTIVY_BACKUP" && sha256sum -c SHA256SUMS)
adb -s "$TV_SERIAL" install-multiple -r "$PROJECTIVY_BACKUP"/*.apk
```

Não instale apenas o `base.apk` de um pacote dividido em splits.

## Ordem para desfazer o procedimento inteiro

Use **os registros produzidos na sua TV**, nunca os de outra pessoa:

1. Restaure TTvs e Guard, se os tiver desativado.
2. Reinstale Projectivy pelo backup, se o tiver removido e quiser voltar ao estado anterior.
3. Restaure as políticas Alexa com `restore-alexa`.
4. Restaure o lote de recomendações.
5. Restaure HOME/acessibilidade com `restore-home`.
6. Restaure voz/feedback.
7. Pela interface, reverta a animação e o atalho oculto se desejar.

O FLauncher instalado permanece disponível após `restore-home`; só o remova
depois de confirmar que o launcher original abre. Os dados reais e registros
da sessão original não estão no Git por conterem identificadores privados.
