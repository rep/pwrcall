package jpwrcall;

import java.security.cert.X509Certificate;
import org.jboss.netty.channel.Channel;

import itsecnetback.NetFront;
import itsecnetback.MessageHandler;


public class Frontend implements NetFront {
	private Node n;

	public Frontend(Node n) {
		this.n = n;
	}

	public boolean verify(X509Certificate cert, String digest) {
		try {
			cert.checkValidity();
		} catch (Exception e) {
			System.err.println("checkValidity fails");
			return false;
		}
		System.out.println("verify called with digest " + digest);
		return true;
	}

	public MessageHandler genHandler(Channel chan) {
		RPCConnection rc = new RPCConnection(chan, this.n);
		this.n.conn_cb(rc, chan);
		return rc;
	}
}

