# 6. Bootloader e root: investigação, não requisito

**O debloat deste guia não exige root, desbloqueio ou firmware modificado.**
A investigação abaixo ocorreu por solicitação do proprietário e está registrada
para evitar que outra pessoa repita tentativas sem saber seus limites.

## O que foi confirmado

- `adb root` recusado por ser build de produção; não foi localizado `su`.
- Bootloader bloqueado, `secure=yes`, Verified Boot `green` e SELinux enforcing.
- O USB A–A enumerou Fastboot no modo bootloader, apesar de não enumerar ADB
  durante o Android normal. Produto reportado: `C06_eu`.
- As consultas de tamanho indicaram boot `0x01f00000` e recovery `0x02900000`.
  São metadados; não são backups.
- `flashing get_unlock_ability` respondeu apenas `lock`; não comprovou que o
  desbloqueio fosse permitido. Nenhum comando de desbloqueio foi executado.
- `fetch` não foi suportado: o dispositivo não forneceu `max-fetch-size`.
  **Não foi obtida uma cópia do boot original.** Um arquivo local vazio criado
  pela tentativa foi descartado e não tratado como backup.
- Algumas consultas Fastboot reportaram `FAILED` no texto mesmo com código de
  saída zero. A saída inteira foi considerada; não se inferiu sucesso pelo exit code.
- Nenhuma partição foi gravada, apagada ou modificada.
- O retorno com `fastboot reboot` foi aceito. A TV ficou em espera e precisou
  ser ligada pelo controle; depois Android, ADB e FLauncher voltaram.

Os comandos de desbloqueio, flash e apagamento deliberadamente não fazem parte
do procedimento de reprodução deste repositório.

## Por que não trocamos o sistema

A busca no [portal oficial TCL SEMP](https://www.tclsemp.com.br/suporte/tcl/downloads?tipo=driver)
não retornou um pacote na sessão. Isso não prova que o firmware não exista.
Não foi encontrada/validada uma imagem completa de recuperação correspondente
à unidade antes de considerar modificação do boot.

A TCL publica [fontes do kernel MT9221](https://github.com/TCLOpenSource/mt9221).
Isso não fornece, por si só, uma ROM completa com os componentes necessários
de painel, entradas e serviços proprietários desta TV.

Existe um [projeto de boot modificado para G06/32S5400](https://github.com/Long0823-1/TCL-G06-Magisk-Boot).
Nossa unidade é **C06**, e a documentação daquele projeto limita a compatibilidade.
O uso do mesmo nome de chip não confirmou equivalência; a imagem não foi usada.

Pelo modelo de [Verified Boot do Android](https://source.android.com/docs/security/features/verifiedboot/device-state),
mudanças do estado de bloqueio apagam dados. Também seria preciso revalidar
streaming/DRM, HDMI e recuperação depois de qualquer alteração de sistema.

## O que seria necessário para continuar essa investigação

Obter firmware original de recuperação para a placa/projeto/firmware corretos,
procedimento de reinstalação por USB e verificação de integridade/compatibilidade.
Não foi comprovado um caminho de root para esta unidade nesta sessão.

Mensagem genérica para o suporte, a ser preenchida e enviada pelo próprio dono:

> Tenho uma TCL 40S615, plataforma C06/MT9221/T221T01, firmware
> V8-T221T01-LF1V622.000807. Preciso da imagem original completa de recuperação,
> checksum e procedimento USB correspondente à revisão do meu aparelho.
> O portal de downloads não retornou pacote na consulta. Posso fornecer os
> identificadores solicitados pelo canal privado de atendimento.

Não coloque número de série, ESN ou comprovantes pessoais em issue pública.
Se o TTvs estiver desativado, restaure-o antes de usar o atualizador pelo menu.
