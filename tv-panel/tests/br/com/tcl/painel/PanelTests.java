package br.com.tcl.painel;

public class PanelTests {
    static void check(boolean value,String why){if(!value)throw new AssertionError(why);}
    static String sample(int ticks,int idle,int processTicks,int start){
        // fields 3..22 of /proc/pid/stat, including a process name containing parentheses.
        return "PANEL_MEM\nMemTotal: 1024000 kB\nMemAvailable: 256000 kB\nSwapTotal: 1000 kB\nSwapFree: 700 kB\n"
            +"PANEL_CPU\ncpu "+ticks+" 0 0 "+idle+" 0 0 0 0 50 0\nPANEL_PS\nPID UID RSS NAME\n42 10042 10240 org.example.app\n"
            +"PANEL_TICKS\n42 (app (worker)) S 1 1 1 0 -1 0 0 0 0 0 "+processTicks+" 0 0 0 20 0 1 0 "+start+"\n";
    }
    public static void main(String[] args){
        Snapshot old=Snapshot.parse(sample(100,900,10,22),null);
        Snapshot now=Snapshot.parse(sample(120,980,15,22),old);
        check(now.totalTicks==1100,"guest time counted twice");
        check(Math.abs(now.cpu-20)<0.001,"CPU aggregate delta");
        check(Math.abs(now.processes.get(42).cpu-5)<0.001,"per-process CPU and parenthesized comm");
        check(now.availableKb==256000&&now.processes.get(42).rss==10240,"memory units");
        check(Snapshot.parse(sample(130,1070,2,23),now).processes.get(42).cpu<0,"PID reuse must reset CPU");
        check(old.cpu<0,"initial CPU is not an instant measurement");
        boolean failed=false;try{Snapshot.parse("permission denied",null);}catch(IllegalArgumentException e){failed=true;}
        check(failed,"unavailable snapshot must fail visibly");
        check(StopPolicy.canStop("org.example.app",10042,false,false,"org.home"),"user app");
        check(!StopPolicy.canStop("org.example.app",10042,false,true,"org.home"),"shared UID");
        check(!StopPolicy.canStop("org.home",10042,false,false,"org.home"),"launcher");
        check(!StopPolicy.canStop(StopPolicy.SELF,10042,false,false,"org.home"),"self");
        check(!StopPolicy.canStop("com.tcl.tvinput",10042,true,false,"org.home"),"HDMI");
        check(!StopPolicy.canStop("com.google.android.apps.mediashell",10042,true,false,"org.home"),"Cast");
        check(!StopPolicy.canStop("org.privileged.app",1000,false,false,"org.home"),"privileged UID");
        check(StopPolicy.canStop("com.netflix.ninja",10042,true,false,"org.home"),"known streaming app");
        check(!StopPolicy.canStop("org.example.app; reboot",10042,false,false,"org.home"),"shell injection in policy");
        failed=false;try{StopPolicy.command("org.app;reboot");}catch(IllegalArgumentException e){failed=true;}
        check(failed,"shell injection in command");
        System.out.println("PanelTests: all checks passed");
    }
}
