package itsecnetback;

import javax.net.ssl.SSLEngine;
import java.net.InetSocketAddress;
import java.util.concurrent.Executors;
import org.jboss.netty.bootstrap.ServerBootstrap;
import org.jboss.netty.channel.socket.nio.NioServerSocketChannelFactory;

public class Server extends NetBack {
	@Override
	protected void configureEngine(SSLEngine engine) {
		engine.setUseClientMode(false);
		engine.setNeedClientAuth(true);
	}

	public Server(int port, NetFront frontend, String keystorepath, String keystorepassword, String keystoreintegrity) {
		super(frontend, keystorepath, keystorepassword, keystoreintegrity);

		ServerBootstrap bootstrap = new ServerBootstrap(
			new NioServerSocketChannelFactory(
				Executors.newCachedThreadPool(),
				Executors.newCachedThreadPool()
			)
		);
		bootstrap.setPipelineFactory(new PipeLineFactory());
		bootstrap.bind(new InetSocketAddress(port));
	}
}
