import itsecnetback.Server;
import itsecnetback.Client;

/**
 * 
 * @author Mark Schloesser
 */
public class Srvtest {
	public static void main(String[] gs) {
		Frontend front = new Frontend();
		Frontend front2 = new Frontend();
		Server foo = new Server(20001, front, "cert_t1.jks", "secret", "secret");
		Client foo2 = new Client("127.0.0.1", 20001, front2, "cert_t2.jks", "secret", "secret");
	}
}
