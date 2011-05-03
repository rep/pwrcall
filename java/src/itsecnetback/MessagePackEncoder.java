package itsecnetback;

import org.jboss.netty.buffer.ChannelBuffer;
import org.jboss.netty.buffer.ChannelBuffers;
import org.jboss.netty.buffer.ChannelBufferOutputStream;
import org.jboss.netty.channel.Channel;
import org.jboss.netty.channel.ChannelHandlerContext;
import org.jboss.netty.handler.codec.oneone.OneToOneEncoder;

import org.msgpack.MessagePack;

public class MessagePackEncoder extends OneToOneEncoder {
	private final int estimatedLength;

	public MessagePackEncoder() {
		this(1024);
	}

	public MessagePackEncoder(int estimatedLength) {
		this.estimatedLength = estimatedLength;
	}

	@Override
	protected Object encode(ChannelHandlerContext ctx, Channel channel, Object msg) throws Exception {
		if(msg instanceof ChannelBuffer)
			return msg;

		ChannelBufferOutputStream out = new ChannelBufferOutputStream(
			ChannelBuffers.dynamicBuffer(
				estimatedLength,
				ctx.getChannel().getConfig().getBufferFactory()
		));

		MessagePack.pack(out, msg);

		ChannelBuffer result = out.buffer();
		return result;
	}
}
