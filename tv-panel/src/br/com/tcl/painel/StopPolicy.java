package br.com.tcl.painel;

import java.util.*;

final class StopPolicy {
    static final String SELF="br.com.tcl.painel";
    private static final Set<String> STREAMING=new HashSet<>(Arrays.asList(
        "com.netflix.ninja", "com.amazon.amazonvideo.livingroom",
        "com.google.android.youtube.tv", "com.google.android.youtube.tvmusic"));
    static boolean canStop(String pkg,int uid,boolean system,boolean sharedUid,String home) {
        if(pkg==null||!pkg.matches("[a-zA-Z][a-zA-Z0-9_]*(\\.[a-zA-Z0-9_]+)+"))return false;
        if(pkg.equals(SELF)||pkg.equals(home)||uid<10000||sharedUid)return false;
        // All manufacturer/system services are read-only, except these known video players.
        return !system||STREAMING.contains(pkg);
    }
    static String command(String pkg) {
        if(pkg==null||!pkg.matches("[a-zA-Z][a-zA-Z0-9_]*(\\.[a-zA-Z0-9_]+)+"))
            throw new IllegalArgumentException("Pacote inválido");
        return "am force-stop --user 0 "+pkg+"; echo PANEL_EXIT:$?";
    }
}
