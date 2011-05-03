package jpwrcall;

public class Promise {
	private Util.Callback resultcb;
	private Util.Callback errorcb;
	private Object result;

	public void when(Util.Callback cb) {
		this.resultcb = cb;
	}
	public void except(Util.Callback cb) {
		this.errorcb = cb;
	}
	public void resolve(Object result) {
		if (this.resultcb != null)
		this.resultcb.cb(result);
	}
	public void smash(String error) {
		if (this.errorcb != null)
		this.errorcb.cb(error);
	}
}
