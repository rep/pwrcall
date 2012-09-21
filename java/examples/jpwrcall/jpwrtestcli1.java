import jpwrcall.Node;
import jpwrcall.Util;
import jpwrcall.Promise;
import jpwrcall.RPCConnection;

import org.msgpack.MessagePackObject;

/**
 * 
 * @author Mark Schloesser
 */
public class jpwrtestcli1 {
	public static char[] hexStringToByteArray(String s) {
	    int len = s.length();
	    char[] data = new char[len / 2];
	    for (int i = 0; i < len; i += 2) {
		data[i / 2] = (char) (Integer.parseInt(s.substring(i, i+2), 16) & 0xff);
	    }
	    return data;
	}

	private static class OnResult implements Util.Callback {
		public void cb(Object r) {
			System.out.println("on_result " + r.toString());
			MessagePackObject rm = (MessagePackObject)r;
			if (rm.isIntegerType())
				System.out.println("received result: " + rm.asInt());
			System.exit(0);
		}
	}

	private static class OnConnected implements Util.Callback {
		private String ref;

		public OnConnected(String ref) {
			this.ref = ref;
			//this.ref = new String(hexStringToByteArray(ref));
		}

		public void cb(Object r) {
			System.out.println("on_connected " + r.toString());

			RPCConnection rc = (RPCConnection) r;
			Promise p = rc.call(this.ref, "add", 25, 75);
			p.when(new OnResult());
			p.except(new OnError());
		}
	}

	private static class OnError implements Util.Callback {
		public void cb(Object r) {
			System.out.println("on_error " + r.toString());
		}
	}

	public static void main(String[] args) {
		Node n = new Node("client_keystore.jks");
		Promise p = n.connect("127.0.0.1", 10003);
		p.when(new OnConnected(args[0]));
		p.except(new OnError());
	}

}
