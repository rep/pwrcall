import jpwrcall.Node;
import jpwrcall.Util;
import jpwrcall.Promise;
import jpwrcall.RPCConnection;

import org.msgpack.MessagePackObject;

import java.util.Date;
import java.util.Random;

public class Testclient1 {
	private static int c = 0;
	private static long stime = new Date().getTime();
	private static Random randm = new Random(stime);
	private static RPCConnection rc;
	private static String ref;

	private static void startcall() {
		int a = randm.nextInt();
		int b = randm.nextInt();

		Promise p = rc.call(ref, "add", a, b);
		p.when(new OnResult(a, b));
		p.except(new OnError());
	}

	private static class OnResult implements Util.Callback {
		private int a; private int b;
		public OnResult(int a, int b) {
			this.a = a; this.b = b;
		}
		public void cb(Object r) {
			//System.out.println("on_result " + r.toString());
			int res = ((MessagePackObject)r).asInt();
			long now = new Date().getTime();
			if (res != this.a+this.b) {
				System.out.println("error, res!= a+b");
				System.exit(0);
			}
			c += 1;
			if (c % 1000 == 0) {
				System.out.println(now + " " + c);
			}

			if (now - stime < 60000) startcall();
			else {
				System.out.println(now + " " + c);
				System.exit(0);
			}
			//if (rm.isIntegerType())
				//System.out.println("received result: " + rm.asInt());
		}
	}

	private static class OnConnected implements Util.Callback {
		public void cb(Object r) {
			long now = new Date().getTime();
			//System.out.println("on_connected " + r.toString());
			System.out.println(now + " " + c);
			rc = (RPCConnection) r;
			startcall();
		}
	}

	private static class OnError implements Util.Callback {
		public void cb(Object r) {
			System.out.println("on_error " + r.toString());
		}
	}

	public static void main(String[] args) {
		Node n = new Node("cert_t1.jks");
		Promise p = n.connect(args[0], 10000);
		ref = "mathobj";
		p.when(new OnConnected());
		p.except(new OnError());
	}

}
