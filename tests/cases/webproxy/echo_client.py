import asyncio
import spoke
import spoke_web

cert = "../../common/localhost.pem"

async def echo(msg):
    print("{}: {}".format(msg.channel, msg.body))

async def main():
    client = spoke.pubsub.client.Client(
        conn_client_class=spoke_web.conn.Client, conn_opts={"cert": cert}
    )
    await client.run()
    await client.subscribe("**", echo)
    await spoke.wait()

asyncio.run(main())

