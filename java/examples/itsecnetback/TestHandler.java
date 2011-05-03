import java.io.IOException;
import java.security.cert.Certificate;
import org.jboss.netty.channel.Channel;
import org.jboss.netty.handler.ssl.SslHandler;
import org.msgpack.MessagePackObject;
import org.msgpack.MessagePackable;
import org.msgpack.Packer;

import itsecnetback.NetBack;
import itsecnetback.MessageHandler;

public class TestHandler implements MessageHandler {
	private final Channel chan;
	private Certificate cert;
	private String certdigest; 

	private class DebugMessage implements MessagePackable {
		private int opcode; private String arg1; private Object arg2;
		public DebugMessage(int opcode, String arg1, Object arg2) {
			this.opcode = opcode;
			this.arg1 = arg1;
			this.arg2 = arg2;
		}
		@Override
		public void messagePack(Packer pk) throws IOException {
			pk.packArray(3);
			pk.packInt(opcode);
			pk.packString(arg1);
			pk.pack(arg2);
		}
	}

	public TestHandler(Channel chan){
		this.chan = chan;
		this.chan.write(new DebugMessage(5, "foobarstr", (Object)null));
		this.chan.write(new DebugMessage(5, "foobarstr", (Object)null));
		try {
			this.cert = ((SslHandler)(chan.getPipeline().get("ssl"))).getEngine().getSession().getPeerCertificates()[0];
			this.certdigest = NetBack.calcDigest(this.cert.getEncoded());
		} catch (Exception e) {
			System.out.println("Could not get peer's certificate from channel. Closing link.");
			chan.close();
		}
	}

	public void handle(MessagePackObject msg) {
		System.out.println("handle called " + msg.toString());
		System.out.println("this client peer digest " + this.certdigest);
		if (msg.isArrayType()) {
			MessagePackObject[] ma = msg.asArray();
			for (int i=0; i<ma.length; i++)
				System.out.println("item " + ma[i].toString());
		} else
			System.out.println("item not arraytype :(");
	}

	public void closed(String cause) {
		System.out.println("closed, cause: " + cause);
	}
}
