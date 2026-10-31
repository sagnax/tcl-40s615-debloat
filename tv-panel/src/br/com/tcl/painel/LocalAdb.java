package br.com.tcl.painel;

import java.io.*;
import java.math.BigInteger;
import java.net.*;
import java.nio.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.*;
import java.security.interfaces.*;
import java.security.spec.*;
import java.util.Base64;
import javax.crypto.Cipher;

/** Small ADB client: only loopback, one shell stream at a time, no listener/server. */
final class LocalAdb implements Closeable {
    private static final int CNXN=0x4e584e43, AUTH=0x48545541, OPEN=0x4e45504f,
            OKAY=0x59414b4f, WRTE=0x45545257, CLSE=0x45534c43;
    private final File keyFile;
    private final int port;
    private volatile Socket socket;
    private InputStream in;
    private OutputStream out;
    private int nextId=1;

    LocalAdb(File directory) { this(directory,5555); }
    LocalAdb(File directory,int port) { keyFile = new File(directory, "local-adb.pk8"); this.port=port; }

    private RSAPrivateKey key() throws Exception {
        if (keyFile.exists()) return (RSAPrivateKey) KeyFactory.getInstance("RSA")
                .generatePrivate(new PKCS8EncodedKeySpec(Files.readAllBytes(keyFile.toPath())));
        KeyPairGenerator gen=KeyPairGenerator.getInstance("RSA"); gen.initialize(new RSAKeyGenParameterSpec(2048, RSAKeyGenParameterSpec.F4));
        RSAPrivateKey key=(RSAPrivateKey)gen.generateKeyPair().getPrivate();
        try(FileOutputStream f=new FileOutputStream(keyFile)) { f.write(key.getEncoded()); }
        return key;
    }
    private byte[] publicKey(RSAPrivateKey key) {
        BigInteger n=key.getModulus(), word=BigInteger.ONE.shiftLeft(32);
        ByteBuffer b=ByteBuffer.allocate(524).order(ByteOrder.LITTLE_ENDIAN);
        b.putInt(64); b.putInt(n.modInverse(word).negate().mod(word).intValue());
        putInteger(b,n); putInteger(b,BigInteger.ONE.shiftLeft(4096).mod(n));
        b.putInt(65537);
        return (Base64.getEncoder().encodeToString(b.array())+" painel@tv\0").getBytes(StandardCharsets.UTF_8);
    }
    private void putInteger(ByteBuffer out, BigInteger value) {
        for(int i=0;i<64;i++) { out.putInt(value.intValue()); value=value.shiftRight(32); }
    }
    private byte[] sign(RSAPrivateKey key,byte[] token) throws Exception {
        byte[] prefix={0x30,0x21,0x30,0x09,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x05,0x00,0x04,0x14};
        ByteArrayOutputStream data=new ByteArrayOutputStream(); data.write(prefix); data.write(token);
        Cipher c=Cipher.getInstance("RSA/ECB/PKCS1Padding"); c.init(Cipher.ENCRYPT_MODE,key);
        return c.doFinal(data.toByteArray());
    }
    void connect(Runnable authorizationNeeded) throws Exception {
        close(); Socket s=new Socket(); socket=s;
        s.connect(new InetSocketAddress("127.0.0.1",port),3000);
        s.setSoTimeout(60000); s.setTcpNoDelay(true); in=s.getInputStream(); out=s.getOutputStream();
        send(CNXN,0x01000000,4096,"host::\0".getBytes(StandardCharsets.UTF_8));
        RSAPrivateKey key=null; int attempts=0;
        while(true) {
            Packet p=read();
            if(p.cmd==CNXN) { s.setSoTimeout(12000); return; }
            if(p.cmd!=AUTH || p.a!=1) throw new IOException("Resposta ADB inesperada");
            if(key==null) key=key();
            if(attempts++==0) send(AUTH,2,0,sign(key,p.data));
            else if(attempts==2) { authorizationNeeded.run(); send(AUTH,3,0,publicKey(key)); }
            else throw new IOException("A autorização ADB foi recusada");
        }
    }
    boolean connected() { Socket s=socket; return s!=null && !s.isClosed(); }
    String shell(String command) throws Exception {
        int id=nextId++;
        send(OPEN,id,0,("shell:"+command+"\0").getBytes(StandardCharsets.UTF_8));
        ByteArrayOutputStream data=new ByteArrayOutputStream();
        while(true) {
            Packet p=read();
            if(p.b!=id) {
                if(p.cmd==CLSE||p.cmd==OKAY)continue;
                throw new IOException("Stream ADB inesperado");
            }
            if(p.cmd==OKAY) { /* Stream is ready. */ }
            else if(p.cmd==WRTE) {
                if(data.size()+p.data.length>2*1024*1024) throw new IOException("Resposta ADB grande demais");
                data.write(p.data); send(OKAY,id,p.a,new byte[0]);
            } else if(p.cmd==CLSE) {
                // CLOSE is terminal and must not be acknowledged (ADB protocol).
                return data.toString("UTF-8").replace("\r", "");
            } else throw new IOException("Pacote ADB inesperado");
        }
    }
    private void send(int cmd,int a,int b,byte[] data) throws IOException {
        int sum=0; for(byte v:data) sum+=v&255;
        byte[] h=ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(cmd).putInt(a).putInt(b).putInt(data.length).putInt(sum).putInt(cmd^-1).array();
        out.write(h); out.write(data); out.flush();
    }
    private Packet read() throws IOException {
        ByteBuffer h=ByteBuffer.wrap(exact(24)).order(ByteOrder.LITTLE_ENDIAN);
        Packet p=new Packet(); p.cmd=h.getInt(); p.a=h.getInt(); p.b=h.getInt();
        int length=h.getInt(), checksum=h.getInt(), magic=h.getInt();
        if(magic!=(p.cmd^-1)||length<0||length>1024*1024) throw new IOException("Cabeçalho ADB inválido");
        p.data=exact(length); int sum=0; for(byte v:p.data) sum+=v&255;
        if(sum!=checksum) throw new IOException("Checksum ADB inválido");
        return p;
    }
    private byte[] exact(int n) throws IOException {
        byte[] b=new byte[n]; int pos=0;
        while(pos<n) { int count=in.read(b,pos,n-pos); if(count<0)throw new EOFException("ADB desconectado"); pos+=count; }
        return b;
    }
    public void close() { Socket s=socket; socket=null; if(s!=null) try{s.close();}catch(IOException ignored){} }
    private static class Packet { int cmd,a,b; byte[] data; }
}
