package br.com.tcl.painel;

import java.io.*;
import java.net.*;
import java.nio.*;
import java.nio.file.*;
import java.security.*;
import java.security.spec.*;
import java.math.*;
import java.util.*;
import java.util.concurrent.*;
import javax.crypto.Cipher;

public class AdbTests {
    static final int CNXN=0x4e584e43, AUTH=0x48545541, OPEN=0x4e45504f,
        OKAY=0x59414b4f, WRTE=0x45545257, CLSE=0x45534c43;
    static class Packet {int cmd,a,b;byte[] data;}
    static Packet read(InputStream input)throws Exception{
        DataInputStream in=new DataInputStream(input);byte[] raw=new byte[24];in.readFully(raw);
        ByteBuffer h=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);Packet p=new Packet();
        p.cmd=h.getInt();p.a=h.getInt();p.b=h.getInt();int len=h.getInt(),sum=h.getInt(),magic=h.getInt();
        PanelTests.check(magic==(p.cmd^-1),"packet magic");p.data=new byte[len];in.readFully(p.data);
        int actual=0;for(byte b:p.data)actual+=b&255;PanelTests.check(actual==sum,"packet checksum");return p;
    }
    static void send(OutputStream out,int cmd,int a,int b,byte[] data)throws Exception{
        int sum=0;for(byte v:data)sum+=v&255;
        out.write(ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN).putInt(cmd).putInt(a).putInt(b).putInt(data.length).putInt(sum).putInt(cmd^-1).array());out.write(data);out.flush();
    }
    static byte[] bytes(String s)throws Exception{return s.getBytes("UTF-8");}
    static void verify(PublicKey pub,byte[] sig,byte[] token)throws Exception{
        Cipher c=Cipher.getInstance("RSA/ECB/PKCS1Padding");c.init(Cipher.DECRYPT_MODE,pub);byte[] result=c.doFinal(sig);
        PanelTests.check(result.length==35&&Arrays.equals(Arrays.copyOfRange(result,15,35),token),"ADB RSA token signature");
    }
    public static void main(String[] args)throws Exception{
        File dir=Files.createTempDirectory("panel-adb-test").toFile();
        ExecutorService executor=Executors.newSingleThreadExecutor();
        try(ServerSocket server=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"))){
            Future<?> result=executor.submit(()->{try{
                PublicKey pub=null;
                for(int connection=0;connection<2;connection++){
                    try(Socket socket=server.accept()){
                        socket.setSoTimeout(5000);InputStream in=socket.getInputStream();OutputStream out=socket.getOutputStream();
                        PanelTests.check(read(in).cmd==CNXN,"initial handshake");
                        byte[] token=new byte[20];Arrays.fill(token,(byte)42);send(out,AUTH,1,0,token);
                        Packet sig=read(in);PanelTests.check(sig.cmd==AUTH&&sig.a==2&&sig.data.length==256,"signed token");
                        if(pub==null){
                            send(out,AUTH,1,0,token);Packet publicPacket=read(in);
                            PanelTests.check(publicPacket.cmd==AUTH&&publicPacket.a==3,"first connection supplies public key");
                            String payload=new String(publicPacket.data,"UTF-8");byte[] binary=Base64.getDecoder().decode(payload.split(" ")[0]);
                            PanelTests.check(binary.length==524,"ADB public key structure");
                            byte[] modulus=new byte[256];for(int i=0;i<256;i++)modulus[255-i]=binary[i+8];
                            pub=KeyFactory.getInstance("RSA").generatePublic(new RSAPublicKeySpec(new BigInteger(1,modulus),BigInteger.valueOf(65537)));
                        }
                        verify(pub,sig.data,token);send(out,CNXN,0x01000000,4096,bytes("device::\0"));
                        int old=0;
                        for(int request=0;request<3;request++){
                            Packet p=read(in);PanelTests.check(p.cmd==OPEN,"CLOSE must not be acknowledged; next packet must be OPEN");
                            if(old!=0)send(out,CLSE,0,old,new byte[0]); // delayed frame for a completed stream
                            int id=7+request;send(out,OKAY,id,p.a,new byte[0]);
                            send(out,WRTE,id,p.a,bytes("part one\r\n"));PanelTests.check(read(in).cmd==OKAY,"write ack");
                            send(out,WRTE,id,p.a,bytes("part two\n"));PanelTests.check(read(in).cmd==OKAY,"second write ack");
                            send(out,CLSE,id,p.a,new byte[0]);old=p.a;
                        }
                    }
                }
            }catch(Exception e){throw new RuntimeException(e);}});
            for(int connection=0;connection<2;connection++){
                try(LocalAdb client=new LocalAdb(dir,server.getLocalPort())){
                    client.connect(()->{});
                    for(int request=0;request<3;request++)PanelTests.check(client.shell("echo test").equals("part one\npart two\n"),"multi-packet shell result");
                }
            }
            result.get(10,TimeUnit.SECONDS);
            System.out.println("AdbTests: authentication, saved key, streams and reconnect passed");
        }finally{executor.shutdownNow();Files.deleteIfExists(new File(dir,"local-adb.pk8").toPath());Files.deleteIfExists(dir.toPath());}
    }
}
