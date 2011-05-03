package itsecnetback;

import org.msgpack.MessagePackObject;

public interface MessageHandler {
	void handle(MessagePackObject msg);
	void closed(String cause);
}

