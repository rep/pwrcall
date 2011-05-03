
import java.security.cert.X509Certificate;
import org.jboss.netty.channel.Channel;

import itsecnetback.NetFront;
import itsecnetback.MessageHandler;

public class Frontend implements NetFront {

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
		return new TestHandler(chan);
	}
}

