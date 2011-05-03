package jpwrcall;

import java.math.BigInteger;
import java.security.SecureRandom;

public class Util {
	private static SecureRandom random = new SecureRandom();

	public static String conv_cert(String certpath) {
		return "foo";
	}

	public static String randstr() {
		return new BigInteger(130, random).toString(32);
	}

	public static interface Callback {
		void cb(Object result);
	}

	public static class NodeException extends Exception {
		public NodeException() {
		}

		public NodeException(String msg) {
			super(msg);
		}
	}
}
