import os
import queue
import asyncio
import websockets
import ssl
from spoke.conn import abc

DEFAULT_WEBPORT = 7182


class Connection(abc.AbstractConnection):
    def __init__(self, websocket, close_event=None):
        self.__close_event = close_event
        self.__websocket = websocket
        self.__connected = True

    async def send(self, msg):
        if not self.__connected:
            raise ConnectionError("Not connected")
        try:
            await self.__websocket.send(msg)
        except websockets.exceptions.ConnectionClosed as e:
            raise ConnectionError() from e

    async def recv(self):
        if not self.__connected:
            raise ConnectionError("Not connected")
        try:
            return await self.__websocket.recv()
        except websockets.exceptions.ConnectionClosed as e:
            raise ConnectionError("Disconnected from server") from e

    async def close(self):
        if self.__connected:
            self.__connected = False
            await self.__websocket.close()
            if self.__close_event is not None:
                self.__close_event.set()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.recv()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class Client(abc.AbstractClient):
    def __init__(self, host=None, port=None, cert=None):
        host = host or os.getenv("SPOKEWEBHOST", os.getenv("SPOKEHOST", "localhost"))
        port = port or int(
            os.getenv("SPOKEWEBPORT", os.getenv("SPOKEPORT", DEFAULT_WEBPORT))
        )
        protocol = "wss" if cert else "ws"
        self._uri = f"{protocol}://{host}:{port}"
        self._connection = None
        self._cert = cert

    async def connect(self) -> Connection:
        "Create a new connection, closing any existing one"
        await self.reset()
        loop = asyncio.get_running_loop()
        while True:
            try:
                if self._cert:
                    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                    ssl_context.load_verify_locations(self._cert)
                    websocket = await websockets.connect(self._uri, ssl=ssl_context)
                else:
                    websocket = await websockets.connect(self._uri)
                conn = Connection(websocket)
                self._connection.set_result(conn)
                return conn
            except ConnectionError:
                await asyncio.sleep(0.1)
            except Exception as err:
                self._connection.set_exception(err)
                raise

    async def connection(self) -> Connection:
        loop = asyncio.get_running_loop()
        if self._connection is None:
            self._connection = loop.create_future()
        return await self._connection

    async def reset(self):
        "Close and forget the existing connection if one exists"
        loop = asyncio.get_running_loop()
        if self._connection is None:
            self._connection = loop.create_future()
        elif self._connection.done():
            try:
                await self._connection.result().close()
                self._connection = loop.create_future()
            except ConnectionError:
                pass

    def __aiter__(self):
        return self

    async def __anext__(self) -> Connection:
        return await self.connect()


class Server(abc.AbstractServer):
    def __init__(self, host=None, port=None, cert=None):
        self.__host = host or os.getenv(
            "SPOKEWEBHOST", os.getenv("SPOKEHOST", "0.0.0.0")
        )
        self.__port = port or int(
            os.getenv("SPOKEWEBPORT", os.getenv("SPOKEPORT", DEFAULT_WEBPORT))
        )
        self.__cert = cert
        self.__client_queue = None
        self.__server = None
        self.__open = True

    async def accept(self) -> Connection:
        if not self.__open:
            raise ValueError

        if not self.__server:
            self.__client_queue = asyncio.Queue()

            async def _listen(websocket, path):
                close_event = asyncio.Event()
                connection = Connection(websocket, close_event)
                await self.__client_queue.put(connection)
                await close_event.wait()

            if self.__cert:
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self.__cert)
                self.__server = await websockets.serve(
                    _listen, self.__host, self.__port, ssl=ssl_context
                )
            else:
                self.__server = await websockets.serve(
                    _listen, self.__host, self.__port
                )

        return await self.__client_queue.get()

    async def close(self):
        if self.__open:
            self.__client_queue = None
            self.__open = False
            self.__server.close()
            self.__server = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    def __aiter__(self):
        return self

    async def __anext__(self) -> Connection:
        return await self.accept()
