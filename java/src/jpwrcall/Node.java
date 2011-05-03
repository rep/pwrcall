package jpwrcall;

import java.lang.ref.WeakReference;
import java.util.HashMap;
import java.util.AbstractMap;
import org.jboss.netty.channel.Channel;
import java.net.InetSocketAddress;

import itsecnetback.Server;
import itsecnetback.Client;

import itsecnetback.NetFront;

/**
 * 
 * @author Mark Schloesser
 */
public class Node {
	private Frontend f;
	private String certpath;
	public AbstractMap<String, WeakReference> exports = new HashMap<String, WeakReference>();
	public AbstractMap<String, Promise> connection_promises = new HashMap<String, Promise>();

	public Node(String cert) {
		this.certpath = cert;
		this.f = new Frontend(this);
	}

	public void conn_cb(RPCConnection rc, Channel chan) {
		InetSocketAddress addr = (InetSocketAddress) chan.getRemoteAddress();
		String addrstr = addr.getAddress().getHostAddress() + ":" + addr.getPort();
		Promise p = connection_promises.get(addrstr);
		if (p == null)
			System.out.println("conn_cb, but can't find promise to fulfill... :(");
		else
			p.resolve(rc);
	}
	
	public Promise connect(String host, int port) {
		Promise p = new Promise();
		Client foo2 = new Client(host, port, this.f, this.certpath, "secret", "secret");
		connection_promises.put(host + ":" + port, p);
		return p;
	}

	public void listen(String host, int port) {
		Server foo = new Server(port, this.f, this.certpath, "secret", "secret");
	}

	public String register_object(Object o) {
		String ref = Util.randstr();
		return register_object(o, ref);
	}

	public String register_object(Object o, String ref) {
		exports.put(ref, new WeakReference(o));
		return ref;
	}


	public String refurl(String ref) {
		return "pwrcall://certhash@host:port/" + ref;
	}
}

