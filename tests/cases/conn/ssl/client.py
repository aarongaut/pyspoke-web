import sys
import os
import asyncio
import spoke_web

name = os.getenv("name", "unnamed")
count = int(os.getenv("count", 10))
delay = float(os.getenv("delay", 1))
cert = "../../../common/localhost.pem"


async def main():
    client = spoke_web.conn.Client(cert=cert)
    async with await client.connect() as conn:
        print("Connected")

        async def echo(conn):
            try:
                async for data in conn:
                    print(f"recv: {data.decode('utf8')}")
            except ConnectionError:
                pass
            print("Disconnected")

        asyncio.create_task(echo(conn))

        try:
            for i in range(count):
                msg = "{} {}".format(name, i)
                print(f"sending: {msg}")
                await conn.send(msg.encode("utf8"))
                await asyncio.sleep(delay)
        except ConnectionError:
            pass


asyncio.run(main())
