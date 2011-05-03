package itsecnetback;

import javax.net.ssl.SSLEngine;
import java.net.InetSocketAddress;
import java.util.concurrent.Executors;
import org.jboss.netty.bootstrap.ClientBootstrap;
import org.jboss.netty.channel.socket.nio.NioClientSocketChannelFactory;

public class Client extends NetBack {
	protected void configureEngine(SSLEngine engine) {
		engine.setUseClientMode(true);
	}

	public Client(String hostname, int port, NetFront frontend, String keystorepath, String keystorepassword, String keystoreintegrity) {
		super(frontend, keystorepath, keystorepassword, keystoreintegrity);

		ClientBootstrap bootstrap = new ClientBootstrap(
			new NioClientSocketChannelFactory(
				Executors.newCachedThreadPool(),
				Executors.newCachedThreadPool()
			)
		);
		bootstrap.setPipelineFactory(new PipeLineFactory());
		bootstrap.connect(new InetSocketAddress(hostname, port));
	}
}
