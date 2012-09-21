package jpwrcall;

import java.lang.Math;
import java.lang.Class;
import java.lang.reflect.Type;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.AbstractMap;
import java.lang.ref.WeakReference;
import java.nio.ByteBuffer;
import java.nio.charset.Charset;

import java.io.IOException;
import java.security.cert.Certificate;
import org.jboss.netty.buffer.ChannelBuffer;
import org.jboss.netty.channel.Channel;
import org.jboss.netty.handler.ssl.SslHandler;
import org.msgpack.MessagePackObject;
import org.msgpack.MessagePackable;
import org.msgpack.Packer;
import org.msgpack.Unpacker;

import itsecnetback.NetBack;
import itsecnetback.MessageHandler;


public class RPCConnection implements MessageHandler {
	private final Channel chan;
	private Certificate cert;
	private String certdigest;
	private Node n;
	private AbstractMap<Integer, Promise> out_requests = new HashMap<Integer, Promise>();
	private int last_msgid = 0;
	private boolean negotiated = false;
	private String remote_info;
	private Unpacker pac = new Unpacker();

	public static Charset utf8charset = Charset.forName("UTF-8");
	public static final int RPC_REQUEST = 0;
	public static final int RPC_RESPONSE = 1;
	public static final int RPC_NOTIFY = 2;
	public static final int RPC_BOOTSTRAP = 3;

	private class BootstrapMessage implements MessagePackable {
		private String arg1;
		public BootstrapMessage(String arg1) {
			this.arg1 = arg1;
		}
		@Override
		public void messagePack(Packer pk) throws IOException {
			pk.packArray(2);
			pk.packInt(RPC_BOOTSTRAP);
			pk.packString(arg1);
		}
	}

	private class ResponseMessage implements MessagePackable {
		private Object arg1;
		private Object arg2;
		private Integer msgid;
		public ResponseMessage(Integer msgid, Object arg1, Object arg2) {
			this.msgid = msgid;
			this.arg1 = arg1;
			this.arg2 = arg2;
		}
		@Override
		public void messagePack(Packer pk) throws IOException {
			pk.packArray(4);
			pk.packInt(RPC_RESPONSE);
			pk.packInt(msgid);
			pk.pack(arg1);
			pk.pack(arg2);
		}
	}

	private class RequestMessage implements MessagePackable {
		private String arg1;
		private String arg2;
		private Integer msgid;
		private Object[] params;
		public RequestMessage(Integer msgid, String arg1, String arg2, Object[] params) {
			this.msgid = msgid;
			this.arg1 = arg1;
			this.arg2 = arg2;
			this.params = params;
		}
		@Override
		public void messagePack(Packer pk) throws IOException {
			pk.packArray(5);
			pk.packInt(RPC_REQUEST);
			pk.packInt(msgid);
			pk.packString(arg1);
			pk.packString(arg2);
			pk.packArray(params.length);
			for(Object p : params)
				pk.pack(p);
		}
	}

	public RPCConnection(Channel chan, Node n) {
		this.chan = chan;
		this.n = n;
		//System.out.println("sending msg");
		this.chan.write("pwrcall java - caps: msgpack\n");

		try {
			this.cert = ((SslHandler)(chan.getPipeline().get("ssl"))).getEngine().getSession().getPeerCertificates()[0];
			this.certdigest = NetBack.calcDigest(this.cert.getEncoded());
		} catch (Exception e) {
			System.out.println("Could not get peer's certificate from channel. Closing link.");
			chan.close();
		}
	}

	public void handle(ChannelBuffer msg) {
		if (!negotiated) {
			remote_info = msg.toString(utf8charset);
			System.out.println("remote banner: " + remote_info);
			negotiated = true;
			return;
		}

		ByteBuffer buffer = msg.toByteBuffer();
		pac.feed(buffer);

		for(MessagePackObject obj : pac) {
			System.out.println("found msgpack object " + obj.toString());
			if (!obj.isArrayType()) { logclose("message not array"); return; }
			MessagePackObject[] array = obj.asArray();
			if (array.length < 1 || !array[0].isIntegerType()) { logclose("message opcode not int"); return; }

			int opcode = array[0].asInt();
			System.out.println("handle called " + array.length + " opcode " + opcode);

			switch (opcode) {
				case RPC_REQUEST: {
					int msgid = array[1].asInt();
					String ref = array[2].asString();
					String method = array[3].asString();
					MessagePackObject[] params = array[4].asArray();
					handle_request(msgid, ref, method, params);
					break;
				}
				case RPC_RESPONSE: {
					int msgid = array[1].asInt();
					MessagePackObject error = array[2];
					MessagePackObject result = array[3];
					handle_response(msgid, error, result);
					break;
				}
				case RPC_NOTIFY: {
					String ref = array[1].asString();
					String method = array[2].asString();
					MessagePackObject[] params = array[3].asArray();
					handle_notify(ref, method, params);
					break;
				}
				case RPC_BOOTSTRAP: {
					MessagePackObject obj2 = array[1];
					handle_bootstrap(obj2);
					break;
				}
				default: {
					logclose("unknown opcode: " + opcode);
				}
			}
		}
	}

	Object lookup(String reference) throws Util.NodeException {
		WeakReference wr = this.n.exports.get(reference);
		if (wr == null) throw new Util.NodeException("Invalid object reference used.");
		Object obj = wr.get();
		if (obj == null) throw new Util.NodeException("Object has gone away.");
		return obj;
	}

	Object invoke(Object obj, String method, MessagePackObject[] params) throws Util.NodeException {
		Class cls = obj.getClass();
		Method m = null; Object result;
		try {
			//do it in an ugly loop cause getDeclaredMethod somehow screws up
			Method[] ms = cls.getDeclaredMethods();
			for(Method cm : ms) {
				//System.out.println("object has method: " + cm.getName() + ". we want " + method + "." + cm.getName().getClass() + method.getClass());
				if (cm.getName().equals(method)) {
					m = cm; break;
				}
			}
			if (m == null) throw new NoSuchMethodException();
			//m = cls.getDeclaredMethod(method, (Class[])null);
		} catch (NoSuchMethodException e) {
			throw new Util.NodeException("Object has no such method: " + method);
		}

		Type[] types = m.getGenericParameterTypes();
		Object[] converted = new Object[types.length];

		for (int i=0; i<Math.min(types.length, params.length); i++) {
			MessagePackObject tmp = params[i];
			Type type = types[i];

			if (type.equals(boolean.class)) {
				converted[i] = tmp.asBoolean();
			} else if(type.equals(byte.class)) {
				converted[i] = tmp.asByte();
			} else if(type.equals(short.class)) {
				converted[i] = tmp.asShort();
			} else if(type.equals(int.class)) {
				converted[i] = tmp.asInt();
			} else if(type.equals(long.class)) {
				converted[i] = tmp.asLong();
			} else if(type.equals(float.class)) {
				converted[i] = tmp.asFloat();
			} else if(type.equals(double.class)) {
				converted[i] = tmp.asDouble();
			} else {
				// TODO
				//Template tmpl = TemplateRegistry.lookup(e.getGenericType(), true);
				//res[i] = new ObjectArgumentEntry(e, tmpl);
				converted[i] = null;
			}
		}

		//System.out.println("params " + params.toString() + ((Object[])params).toString());
		//if (params.length > 0)
		//	System.out.println("params " + params[0].toString() + ((Object)params[0]).toString());


		try {
			result = m.invoke(obj, converted);
		} catch (Exception e) {
			throw new Util.NodeException("Exception: " + e.toString());
		}

		return result;
	}

	private void handle_request(int msgid, String ref, String method, MessagePackObject[] params) {
		//System.out.println("handle_request " + msgid + " " + ref + " " + method);
		Object obj; Object result;

		try {
			obj = lookup(ref);
		} catch (Util.NodeException e) {
			send_response(msgid, e.toString(), null);
			return;
		}

		try {
			result = invoke(obj, method, params);
		} catch (Util.NodeException e) {
			send_response(msgid, e.toString(), null);
			return;
		}

		send_response(msgid, null, result);
	}

	private void handle_notify(String ref, String method, MessagePackObject[] params) {
		//System.out.println("handle_notify " + ref + " " + method);
	}

	private void handle_response(int msgid, MessagePackObject error, MessagePackObject result) {
		//System.out.println("handle_response " + error + " " + result.toString());
		Promise p = out_requests.get(msgid);
		if (p == null)
			System.out.println("could not find promise for this response... :(");
		else {
			if (error.isNil())
				p.resolve(result);
			else
				p.smash(error.asString());
		}
	}

	private void handle_bootstrap(MessagePackObject obj) {
		//System.out.println("handle_bootstrap " + obj.asString());
	}

	private void send_response(int msgid, String error, Object obj) {
		//System.out.println("send_response " + msgid + " " + error + " " + obj);
		this.chan.write(new ResponseMessage(msgid, error, obj));
	}

	public void closed(String cause) {
		System.out.println("rpc conn closed, cause: " + cause);
	}

	public void logclose(String cause) {
		System.out.println("rpc conn will be closed, cause: " + cause);
		this.chan.close();
	}

	String gen_cap(Object obj) {
		return Util.randstr();
	}

	public Promise call(String ref, String method, Object ... params) {
		//System.out.println("call " + ref + " " + method + " " + params[0] +" , " +  params[1]);
		this.last_msgid += 1;
		int callid = this.last_msgid;
		Promise p = new Promise();
		out_requests.put(callid, p);
		this.chan.write(new RequestMessage(callid, ref, method, params));
		return p;
	}
}

