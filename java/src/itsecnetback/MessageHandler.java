package itsecnetback;

import org.jboss.netty.buffer.ChannelBuffer;

public interface MessageHandler {
	void handle(ChannelBuffer msg);
	void closed(String cause);
}

