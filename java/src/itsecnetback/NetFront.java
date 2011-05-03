package itsecnetback;

import java.security.cert.X509Certificate;
import org.jboss.netty.channel.Channel;

public interface NetFront {
	boolean verify(X509Certificate cert, String digest);
	MessageHandler genHandler(Channel chan);
}

