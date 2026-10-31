package br.com.tcl.painel;

import java.util.*;

final class Snapshot {
    private static final java.util.regex.Pattern WS=java.util.regex.Pattern.compile("\\s+");
    static final String COMMAND = "echo PANEL_MEM; cat /proc/meminfo; echo PANEL_CPU; "
        + "head -n 1 /proc/stat; echo PANEL_PS; ps -A -o PID,UID,RSS,NAME; "
        + "echo PANEL_TICKS; for p in /proc/[0-9]*/stat; do "
        + "if read -r line < \"$p\" 2>/dev/null; then echo \"$line\"; fi; done";
    long totalKb, availableKb, swapKb, swapFreeKb, totalTicks, idleTicks;
    double cpu=-1;
    final Map<Integer,Proc> processes=new LinkedHashMap<>();
    static class Proc { int pid,uid; long rss,ticks,start; String name; double cpu=-1; }
    static Snapshot parse(String text,Snapshot previous) {
        Snapshot s=new Snapshot(); String section="";
        for(String raw:text.split("\n")) {
            String line=raw.trim();
            if(line.startsWith("PANEL_")) { section=line; continue; }
            try {
                String[] a=section.equals("PANEL_TICKS")?null:WS.split(line);
                if(section.equals("PANEL_MEM")&&a.length>=2) {
                    long kb=Long.parseLong(a[1]);
                    switch(a[0]) {
                        case "MemTotal:":s.totalKb=kb;break;
                        case "MemAvailable:":s.availableKb=kb;break;
                        case "SwapTotal:":s.swapKb=kb;break;
                        case "SwapFree:":s.swapFreeKb=kb;break;
                    }
                } else if(section.equals("PANEL_CPU")&&a[0].equals("cpu")) {
                    // guest/guest_nice are already counted in user/nice.
                    for(int i=1;i<=8&&i<a.length;i++) s.totalTicks+=Long.parseLong(a[i]);
                    s.idleTicks=Long.parseLong(a[4])+Long.parseLong(a[5]);
                } else if(section.equals("PANEL_PS")&&a.length>=4&&!a[0].equals("PID")) {
                    Proc p=new Proc(); p.pid=Integer.parseInt(a[0]); p.uid=Integer.parseInt(a[1]);
                    p.rss=Long.parseLong(a[2]); p.name=a[3]; s.processes.put(p.pid,p);
                } else if(section.equals("PANEL_TICKS")) {
                    int begin=line.indexOf('('), end=line.lastIndexOf(')');
                    if(begin<1||end<begin)continue;
                    int pid=Integer.parseInt(line.substring(0,begin).trim()); Proc p=s.processes.get(pid);
                    if(p!=null&&p.rss>0) {
                        String[] stat=WS.split(line.substring(end+1).trim());
                        p.ticks=Long.parseLong(stat[11])+Long.parseLong(stat[12]);
                        p.start=Long.parseLong(stat[19]);
                    }
                }
            } catch(NumberFormatException|IndexOutOfBoundsException ignored) { }
        }
        if(s.totalKb<=0||s.totalTicks<=0||s.processes.isEmpty())
            throw new IllegalArgumentException("A TV não retornou todas as medições");
        if(previous!=null) {
            long delta=s.totalTicks-previous.totalTicks;
            if(delta>0) {
                s.cpu=Math.max(0,Math.min(100,100.0*(delta-(s.idleTicks-previous.idleTicks))/delta));
                for(Proc p:s.processes.values()) {
                    Proc old=previous.processes.get(p.pid);
                    if(old!=null&&p.start>0&&p.start==old.start&&p.ticks>=old.ticks)
                        p.cpu=100.0*(p.ticks-old.ticks)/delta;
                }
            }
        }
        return s;
    }
}
