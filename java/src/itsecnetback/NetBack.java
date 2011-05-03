package itsecnetback;

import java.io.FileInputStream;
import java.util.logging.Logger;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.cert.CertificateException;
import java.security.cert.CertificateEncodingException;
import java.security.cert.X509Certificate;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLEngine;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import org.jboss.netty.handler.ssl.SslHandler;
import org.jboss.netty.channel.ChannelPipeline;
import org.jboss.netty.channel.ChannelPipelineFactory;
import org.jboss.netty.channel.Channel;
import org.jboss.netty.channel.Channels;
import org.jboss.netty.channel.ChannelFuture;
import org.jboss.netty.channel.ChannelFutureListener;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.channel.ChannelEvent;
import org.jboss.netty.channel.ChannelStateEvent;
import org.jboss.netty.channel.ExceptionEvent;
import org.jboss.netty.channel.MessageEvent;
import org.jboss.netty.channel.SimpleChannelUpstreamHandler;

import org.msgpack.MessagePackObject;

public abstract class NetBack {

	protected final Logger logger = Logger.getLogger("itsecnetback");
	protected SSLContext sslctx = null;
	protected String certpath;
	protected String kspw;
	protected String ksipw;
	protected NetFront frontend;

	public static String getHex( final byte [] raw ) {
		if ( raw == null ) return null; 
		final StringBuilder hex = new StringBuilder( 2 * raw.length );

		for ( final byte b : raw ) {
			int v = b & 0xff;
			if (v<16) hex.append('0');
			hex.append(Integer.toHexString(v));
		}
		return hex.toString();
	}

	public static String calcDigest(byte[] data) throws NoSuchAlgorithmException {
		MessageDigest md = MessageDigest.getInstance("SHA-1");
		md.update(data);
		return getHex(md.digest());
	}

	private final TrustManager NetBackTrustMan = new X509TrustManager() {
		public X509Certificate[] getAcceptedIssuers() {
			return new X509Certificate[0];
		}

		public void checkClientTrusted(X509Certificate[] chain, String authType) throws CertificateException {
			checkTrusted(chain, authType);
		}

		public void checkServerTrusted(X509Certificate[] chain, String authType) throws CertificateException {
			checkTrusted(chain, authType);
		}

		private void checkTrusted(X509Certificate[] chain, String authType) throws CertificateException {
			try {
				if (!frontend.verify(chain[0], calcDigest(chain[0].getEncoded())))
					throw new CertificateException("Frontend verify() = false");
			} catch (Exception e) {
				throw new CertificateException("exception " + e.toString());
			}
		}
	};

	private SSLContext getContext() {
		if (sslctx == null) {
			try {
				KeyStore ks = KeyStore.getInstance("JKS");
				ks.load(new FileInputStream(certpath), ksipw.toCharArray());
				KeyManagerFactory kmf = KeyManagerFactory.getInstance("SunX509");
				kmf.init(ks, kspw.toCharArray());
				sslctx = SSLContext.getInstance("TLSv1");
				sslctx.init(kmf.getKeyManagers(), new TrustManager[]{NetBackTrustMan}, null);
			} catch (Exception e) {
				throw new Error("Failed to initialize the SSLContext", e);
			}
		}
		return sslctx;
	}

	private class NetBackHandler extends SimpleChannelUpstreamHandler {
		private MessageHandler handler = null;

		@Override
		public void channelConnected(ChannelHandlerContext ctx, ChannelStateEvent e) throws Exception {
			final SslHandler sslHandler = ctx.getPipeline().get(SslHandler.class);
			ChannelFuture handshakeFuture = sslHandler.handshake();
			handshakeFuture.addListener(new ReadyWaiter());
		}

		@Override
		public void channelClosed(ChannelHandlerContext ctx, ChannelStateEvent e) throws Exception {
			handler.closed("channelClosed");
		}

		@Override
		public void messageReceived(ChannelHandlerContext ctx, MessageEvent e) {
			System.out.println("messageReveiced " + e.toString());
			Object m = e.getMessage();
			if(!(m instanceof MessagePackObject)) {
				ctx.sendUpstream(e);
				return;
			}

			MessagePackObject msg = (MessagePackObject)m;
			System.out.println(" -> is MessagePackObject " + msg.toString());
			if (handler == null)
				e.getChannel().close();
			else
				handler.handle(msg);
		}

		@Override
		public void exceptionCaught(ChannelHandlerContext ctx, ExceptionEvent e) {
			logger.warning("Unexpected exception from downstream. " + e.getCause());
			e.getChannel().close();
			if (handler != null) {
				handler.closed(e.getCause().toString());
				e.getCause().printStackTrace();
			}
		}

		private final class ReadyWaiter implements ChannelFutureListener {
			public void operationComplete(ChannelFuture future) throws Exception {
				if (future.isSuccess()) {
					handler = frontend.genHandler(future.getChannel());
				} else {
					future.getChannel().close();
				}
			}
		}
	}

	protected class PipeLineFactory implements ChannelPipelineFactory {
		public ChannelPipeline getPipeline() throws Exception {
			ChannelPipeline pipeline = Channels.pipeline();
			
			SSLEngine engine = getContext().createSSLEngine();
			configureEngine(engine);

			pipeline.addLast("ssl", new SslHandler(engine));
			pipeline.addLast("msgpack-decode-stream", new MessagePackStreamDecoder());
			pipeline.addLast("msgpack-encode", new MessagePackEncoder());
			pipeline.addLast("message", new NetBackHandler());
			return pipeline;
		}
	}

	protected abstract void configureEngine(SSLEngine engine);

	public NetBack(NetFront frontend, String keystorepath, String keystorepassword, String keystoreintegrity) {
		this.frontend = frontend;
		this.certpath = keystorepath;
		this.kspw = keystorepassword;
		this.ksipw = keystoreintegrity;
	}
}
