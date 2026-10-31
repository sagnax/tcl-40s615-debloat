package br.com.tcl.painel;

import android.app.*;
import android.os.*;
import android.content.*;
import android.content.pm.*;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.provider.Settings;
import android.view.*;
import android.widget.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

public class MainActivity extends Activity {
    private static final int BG=0xff101722, CARD=0xff1c2939, TEXT=0xfff0f4fa,
        MUTED=0xffa1b2c7, ACCENT=0xff78e5c3;
    private final Handler ui=new Handler(Looper.getMainLooper());
    private final ExecutorService worker=Executors.newSingleThreadExecutor();
    private final AtomicBoolean busy=new AtomicBoolean();
    private LocalAdb adb;
    private volatile boolean active;
    private Snapshot previous;
    private TextView status,cpuValue,ramValue,swapValue,footer;
    private ProgressBar cpuBar,ramBar;
    private Button filter,sort;
    private ListView list;
    private Rows adapter;
    private boolean all=false, byCpu=false, dialogOpen=false;
    private String home, keyboard;
    private Map<String,ApplicationInfo> apps=new HashMap<>();
    private Map<String,String> labels=new HashMap<>();
    private Map<Integer,List<String>> packagesByUid=new HashMap<>();
    private final ArrayList<Row> rows=new ArrayList<>();
    private final Runnable tick=new Runnable(){ public void run(){if(active){refresh();ui.postDelayed(this,5000);}}};

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            |View.SYSTEM_UI_FLAG_HIDE_NAVIGATION|View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
        adb=new LocalAdb(getFilesDir());
        buildUi();
    }
    private void loadApps() {
        apps.clear();packagesByUid.clear();
        String input=Settings.Secure.getString(getContentResolver(),Settings.Secure.DEFAULT_INPUT_METHOD);
        keyboard=input==null?null:input.split("/",2)[0];
        PackageManager pm=getPackageManager();
        Intent homeIntent=new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME);
        ResolveInfo resolved=pm.resolveActivity(homeIntent,PackageManager.MATCH_DEFAULT_ONLY);
        home=resolved!=null&&resolved.activityInfo!=null?resolved.activityInfo.packageName:null;
        for(ApplicationInfo a:pm.getInstalledApplications(0)) {
            apps.put(a.packageName,a);
            if(!labels.containsKey(a.packageName))labels.put(a.packageName,pm.getApplicationLabel(a).toString());
            List<String> group=packagesByUid.get(a.uid);
            if(group==null){group=new ArrayList<>();packagesByUid.put(a.uid,group);} group.add(a.packageName);
        }
    }
    @Override protected void onStart(){super.onStart();loadApps();active=true;ui.post(tick);}
    @Override protected void onStop(){active=false;ui.removeCallbacks(tick);adb.close();super.onStop();}
    @Override protected void onDestroy(){adb.close();worker.shutdownNow();super.onDestroy();}
    private int dp(float n){return (int)(n*getResources().getDisplayMetrics().density+0.5f);}
    private TextView text(String s,int size,int color){
        TextView t=new TextView(this);t.setText(s);t.setTextSize(size);t.setTextColor(color);return t;
    }
    private GradientDrawable shape(int color){GradientDrawable g=new GradientDrawable();g.setColor(color);g.setCornerRadius(dp(9));return g;}
    private LinearLayout horizontal(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);l.setGravity(Gravity.CENTER_VERTICAL);return l;}
    private Button button(String label,Runnable action){
        Button b=new Button(this); b.setText(label);b.setTextSize(13);b.setAllCaps(false);
        b.setTextColor(TEXT);b.setPadding(dp(13),0,dp(13),0);b.setMinWidth(0);b.setMinimumWidth(0);
        b.setBackground(shape(CARD));
        b.setOnFocusChangeListener((v,focused)->{b.setBackground(shape(focused?ACCENT:CARD));b.setTextColor(focused?BG:TEXT);});
        b.setOnClickListener(v->action.run());return b;
    }
    private void toolbarButton(LinearLayout parent,Button b){
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-2,dp(38));p.rightMargin=dp(10);parent.addView(b,p);
    }
    private void buildUi(){
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(32),dp(22),dp(32),dp(18));root.setBackgroundColor(BG);setContentView(root);
        LinearLayout header=horizontal();
        TextView title=text("Painel da TV",26,TEXT);title.setTypeface(null,Typeface.BOLD);
        header.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        status=text("Conectando…",12,ACCENT);header.addView(status);root.addView(header);
        TextView subtitle=text("O que está acontecendo na sua TV, em uma tela.",13,MUTED);
        LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,-2);sp.topMargin=dp(3);sp.bottomMargin=dp(14);root.addView(subtitle,sp);
        LinearLayout metrics=horizontal();
        cpuValue=metric(metrics,"CPU · capacidade total");ramValue=metric(metrics,"RAM disponível");swapValue=metric(metrics,"zRAM / swap em uso");
        root.addView(metrics,new LinearLayout.LayoutParams(-1,dp(82)));
        LinearLayout controls=horizontal();LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,dp(58));root.addView(controls,cp);
        toolbarButton(controls,button("Atualizar",()->refresh()));
        filter=button("Exibir: apps",()->{all=!all;filter.setText(all?"Exibir: todos":"Exibir: apps");renderRows();});toolbarButton(controls,filter);
        sort=button("Ordenar: RAM",()->{byCpu=!byCpu;sort.setText(byCpu?"Ordenar: CPU":"Ordenar: RAM");renderRows();});toolbarButton(controls,sort);
        toolbarButton(controls,button("Conexão",()->showConnection()));
        toolbarButton(controls,button("Ajuda",()->showHelp()));
        LinearLayout headings=horizontal(); headings.setPadding(dp(12),0,dp(12),dp(4));
        headings.addView(text("APLICATIVO / PROCESSO",11,MUTED),new LinearLayout.LayoutParams(0,-2,1));
        column(headings,"CPU¹",80,11,MUTED);column(headings,"RAM²",94,11,MUTED);column(headings,"AÇÃO",110,11,MUTED);
        root.addView(headings);
        list=new ListView(this);list.setDividerHeight(dp(4));list.setDivider(new android.graphics.drawable.ColorDrawable(BG));
        list.setCacheColorHint(BG);list.setSelector(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
        adapter=new Rows();list.setAdapter(adapter);list.setItemsCanFocus(false);
        list.setOnItemClickListener((parent,view,position,id)->showActions(rows.get(position)));
        root.addView(list,new LinearLayout.LayoutParams(-1,0,1));
        footer=text("Aguardando acesso local. Autorize a conexão na TV se aparecer uma solicitação.",11,MUTED);
        footer.setPadding(0,dp(8),0,0);footer.setMinHeight(dp(34));root.addView(footer);
    }
    private TextView metric(LinearLayout parent,String label){
        LinearLayout card=new LinearLayout(this);card.setOrientation(LinearLayout.VERTICAL);card.setPadding(dp(16),dp(10),dp(16),dp(8));card.setBackground(shape(CARD));
        LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(0,-1,1);lp.rightMargin=dp(8);parent.addView(card,lp);
        card.addView(text(label,12,MUTED));TextView value=text("—",23,TEXT);value.setTypeface(null,Typeface.BOLD);card.addView(value);
        if(parent.getChildCount()<3){
            ProgressBar bar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);bar.setMax(100);
            bar.setProgressTintList(android.content.res.ColorStateList.valueOf(ACCENT));
            card.addView(bar,new LinearLayout.LayoutParams(-1,dp(4)));
            if(parent.getChildCount()==1)cpuBar=bar;else ramBar=bar;
        }
        return value;
    }
    private void column(LinearLayout row,String value,int width,int size,int color){
        TextView t=text(value,size,color);t.setGravity(Gravity.RIGHT|Gravity.CENTER_VERTICAL);
        row.addView(t,new LinearLayout.LayoutParams(dp(width),-1));
    }
    private void refresh(){
        if(!active||dialogOpen||!busy.compareAndSet(false,true))return;
        worker.execute(()->{
            try{
                if(!adb.connected()){
                    previous=null;
                    ui.post(()->{status.setText("Conectando ao ADB local…");status.setTextColor(ACCENT);});
                    adb.connect(()->ui.post(()->{status.setText("Autorize na TV");footer.setText("Na solicitação do Android, permita a depuração para painel@tv.");}));
                }
                Snapshot snap=Snapshot.parse(adb.shell(Snapshot.COMMAND),previous);previous=snap;
                ui.post(()->{if(active)showSnapshot(snap);});
            }catch(Exception e){adb.close();previous=null;ui.post(()->{if(active){
                status.setText("Sem conexão ADB");status.setTextColor(0xffffbd83);
                cpuValue.setText("—");ramValue.setText("—");swapValue.setText("—");cpuBar.setProgress(0);ramBar.setProgress(0);
                rows.clear();adapter.notifyDataSetChanged();
                footer.setText("Sem dados atuais. Abra Conexão para tentar novamente. "+friendly(e));
            }});}finally{busy.set(false);}
        });
    }
    private String friendly(Exception e){
        if(e instanceof java.net.ConnectException)return "ADB local indisponível.";
        if(e instanceof java.net.SocketTimeoutException)return "Tempo de conexão esgotado; confira a autorização.";
        return e.getMessage()==null?e.getClass().getSimpleName():e.getMessage();
    }
    private Snapshot shown;
    private void showSnapshot(Snapshot s){
        shown=s;status.setText("● ADB local · "+new java.text.SimpleDateFormat("HH:mm:ss",Locale.getDefault()).format(new Date()));status.setTextColor(ACCENT);
        cpuValue.setText(s.cpu<0?"Medindo…":String.format(Locale.US,"%.1f %%",s.cpu));cpuBar.setProgress((int)Math.max(0,s.cpu));
        ramValue.setText(mib(s.availableKb)+" / "+mib(s.totalKb));ramBar.setProgress((int)(100*s.availableKb/s.totalKb));
        swapValue.setText(mib(s.swapKb-s.swapFreeKb)+" / "+mib(s.swapKb));
        renderRows();
    }
    private String mib(long kb){return String.format(Locale.US,"%.0f MiB",kb/1024.0);}
    private static class Row {String key,pkg,label,detail;long ram;double cpu;int count;boolean measured,stoppable;}
    private void renderRows(){
        if(shown==null||!adb.connected())return;
        String selected=null;int oldIndex=list.getSelectedItemPosition();
        if(oldIndex>=0&&oldIndex<rows.size())selected=rows.get(oldIndex).key;
        Map<String,Row> grouped=new LinkedHashMap<>();
        for(Snapshot.Proc p:shown.processes.values()){
            if(p.rss<=0)continue;
            String base=p.name.split(":",2)[0];String pkg=apps.containsKey(base)?base:null;
            // Ambiguous shared UIDs and native services are never assigned to an arbitrary app.
            List<String> candidates=packagesByUid.get(p.uid);
            if(pkg==null&&candidates!=null&&candidates.size()==1)pkg=candidates.get(0);
            if(!all&&pkg==null)continue;
            String key=pkg!=null?pkg:"pid:"+p.pid;
            Row r=grouped.get(key);
            if(r==null){
                r=new Row();r.key=key;r.pkg=pkg;r.label=pkg!=null?labels.get(pkg):p.name;r.detail=pkg!=null?pkg:"PID "+p.pid+" · serviço do sistema";
                if(pkg!=null){
                    ApplicationInfo a=apps.get(pkg);
                    r.stoppable=!pkg.equals(keyboard)&&StopPolicy.canStop(pkg,a.uid,(a.flags&(ApplicationInfo.FLAG_SYSTEM|ApplicationInfo.FLAG_UPDATED_SYSTEM_APP))!=0,
                        candidates!=null&&candidates.size()>1,home);
                }
                grouped.put(key,r);
            }
            r.ram+=p.rss;r.count++;if(p.cpu>=0){r.cpu+=p.cpu;r.measured=true;}
        }
        rows.clear();rows.addAll(grouped.values());
        Collections.sort(rows,(a,b)->{int c=byCpu?Double.compare(b.cpu,a.cpu):Long.compare(b.ram,a.ram);return c!=0?c:a.key.compareTo(b.key);});
        adapter.notifyDataSetChanged();
        if(selected!=null){for(int i=0;i<rows.size();i++)if(rows.get(i).key.equals(selected)){list.setSelection(i);break;}}
        footer.setText(rows.size()+" itens · OK: ações · Atualiza a cada 5 s\n¹ CPU: fração da TV (0–100%).  ² RAM residente (RSS), inclui memória compartilhada.");
    }
    private void dialog(AlertDialog d){
        dialogOpen=true;d.setOnDismissListener(x->{dialogOpen=false;});d.show();
    }
    private void showActions(Row r){
        if(r.pkg==null){dialog(new AlertDialog.Builder(this).setTitle(r.label).setMessage(r.detail+"\nRAM residente: "+mib(r.ram)+"\nServiço protegido; disponível apenas para consulta.").setPositiveButton("Voltar",null).create());return;}
        ArrayList<String> choices=new ArrayList<>();if(r.stoppable)choices.add("Encerrar aplicativo");choices.add("Configurações do aplicativo");
        dialog(new AlertDialog.Builder(this).setTitle(r.label).setItems(choices.toArray(new String[0]),(d,n)->{
            if(r.stoppable&&n==0){ui.post(()->confirmStop(r));}
            else startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+r.pkg)));
        }).setNegativeButton("Voltar",null).create());
    }
    private void confirmStop(Row r){
        dialog(new AlertDialog.Builder(this).setTitle("Encerrar "+r.label+"?")
            .setMessage("A reprodução e as atividades deste app serão interrompidas. Seus dados e login serão preservados. A RAM liberada pode ser reutilizada pelo Android.")
            .setNegativeButton("Cancelar",null).setPositiveButton("Encerrar",(d,n)->ui.post(()->stop(r))).create());
    }
    private void stop(Row row){
        // Re-evaluate the policy at action time, rather than trusting a stale list item.
        ApplicationInfo a=apps.get(row.pkg);List<String> peers=a==null?null:packagesByUid.get(a.uid);
        if(a==null||row.pkg.equals(keyboard)||!StopPolicy.canStop(row.pkg,a.uid,(a.flags&(ApplicationInfo.FLAG_SYSTEM|ApplicationInfo.FLAG_UPDATED_SYSTEM_APP))!=0,
            peers!=null&&peers.size()>1,home)){Toast.makeText(this,"Aplicativo protegido",Toast.LENGTH_LONG).show();return;}
        if(!busy.compareAndSet(false,true)){Toast.makeText(this,"Aguarde a atualização e tente novamente",Toast.LENGTH_SHORT).show();return;}
        long before=shown==null?0:shown.availableKb;
        worker.execute(()->{try{
            if(!adb.connected())throw new IllegalStateException("ADB desconectado; reconecte antes de encerrar");
            String result=adb.shell(StopPolicy.command(row.pkg));
            if(!result.trim().equals("PANEL_EXIT:0"))throw new IllegalStateException("A TV não confirmou o encerramento: "+result);
            Snapshot snap=Snapshot.parse(adb.shell(Snapshot.COMMAND),previous);previous=snap;
            boolean running=false;for(Snapshot.Proc p:snap.processes.values())if(p.name.equals(row.pkg)||p.name.startsWith(row.pkg+":"))running=true;
            final boolean stillRunning=running;
            ui.post(()->{if(active){showSnapshot(snap);dialog(new AlertDialog.Builder(this).setTitle(stillRunning?"O app voltou a executar":"Aplicativo encerrado")
                .setMessage(row.label+"\nRAM disponível antes: "+mib(before)+"\nRAM disponível agora: "+mib(snap.availableKb)
                    +"\nA variação inclui outras atividades da TV."+(stillRunning?"\nO sistema pode ter reiniciado o processo.":""))
                .setPositiveButton("OK",null).create());}});
        }catch(Exception e){adb.close();ui.post(()->{if(active)dialog(new AlertDialog.Builder(this).setTitle("Não foi possível encerrar").setMessage(friendly(e)).setPositiveButton("OK",null).create());});}
        finally{busy.set(false);}});
    }
    private void showConnection(){
        dialog(new AlertDialog.Builder(this).setTitle("Conexão com a própria TV")
            .setMessage("O painel usa o ADB em 127.0.0.1:5555. Não precisa do notebook depois de autorizado.\n\nNa primeira conexão, permita a depuração do painel@tv e marque “Sempre permitir” para guardar a autorização.\n\nSe não conectar após reiniciar a TV, o ADB de rede pode precisar ser reativado pelo computador. O painel não altera essa configuração.")
            .setNegativeButton("Voltar",null).setPositiveButton("Reconectar",(d,n)->{adb.close();ui.post(()->refresh());}).create());
    }
    private void showHelp(){
        dialog(new AlertDialog.Builder(this).setTitle("Como usar")
            .setMessage("Use as setas e OK do controle. Selecione um app para encerrá-lo ou abrir suas configurações.\n\nCPU é a parcela da capacidade total da TV, medida entre atualizações. RAM é a memória residente (RSS); páginas compartilhadas podem aparecer em vários processos. A soma dos apps não representa a RAM total ocupada.\n\nO Android usa RAM como cache e a libera quando precisa. Encerrar um app pode ajudar se estiver travado; limpar tudo continuamente pode deixar a TV mais lenta.\n\nServiços de sistema, Cast, HDMI, teclado, launcher e este painel são protegidos. O painel só coleta enquanto está aberto. Nenhum dado é enviado para a internet.")
            .setPositiveButton("Entendi",null).create());
    }
    private class Rows extends BaseAdapter {
        public int getCount(){return rows.size();}public Object getItem(int p){return rows.get(p);}public long getItemId(int p){return rows.get(p).key.hashCode();}
        public boolean hasStableIds(){return true;}
        public View getView(int position,View convert,android.view.ViewGroup parent){
            Row r=rows.get(position);LinearLayout row;TextView name,detail,cpu,ram,action;
            if(convert==null){
                row=horizontal();row.setPadding(dp(12),dp(7),dp(12),dp(7));row.setMinimumHeight(dp(52));
                android.graphics.drawable.StateListDrawable states=new android.graphics.drawable.StateListDrawable();
                states.addState(new int[]{android.R.attr.state_selected},shape(0xff305d62));
                states.addState(new int[]{android.R.attr.state_pressed},shape(0xff305d62));states.addState(new int[]{},shape(CARD));row.setBackground(states);
                LinearLayout names=new LinearLayout(MainActivity.this);names.setOrientation(LinearLayout.VERTICAL);
                name=text("",15,TEXT);name.setSingleLine(true);name.setEllipsize(android.text.TextUtils.TruncateAt.END);name.setTypeface(null,Typeface.BOLD);
                detail=text("",10,MUTED);detail.setSingleLine(true);detail.setEllipsize(android.text.TextUtils.TruncateAt.END);
                names.addView(name);names.addView(detail);row.addView(names,new LinearLayout.LayoutParams(0,-2,1));
                column(row,"",80,15,TEXT);column(row,"",94,15,TEXT);column(row,"",110,11,ACCENT);
                cpu=(TextView)row.getChildAt(1);ram=(TextView)row.getChildAt(2);action=(TextView)row.getChildAt(3);
                row.setTag(new TextView[]{name,detail,cpu,ram,action});
            }else row=(LinearLayout)convert;
            TextView[] views=(TextView[])row.getTag();views[0].setText(r.label);views[1].setText(r.detail+(r.count>1?" · "+r.count+" processos":""));
            views[2].setText(r.measured?String.format(Locale.US,"%.1f %%",r.cpu):"—");views[3].setText(mib(r.ram));views[4].setText(r.stoppable?"Gerenciar":"Protegido");
            return row;
        }
    }
}
