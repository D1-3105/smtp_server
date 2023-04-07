import socket
import logging
import asyncio

logger = logging.getLogger('smtp_server')


class Server:

    _loop = None
    server: socket.socket

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((host, port))
        self.server.listen()
        self.server.setblocking(False)

    @property
    def loop(self):
        if self._loop:
            return self._loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop

    async def run(self):
        while True:
            client, _ = await self.loop.sock_accept(self.server)
            self.loop.create_task(self.echo(client))

    async def recv(self, client):
        request = None
        while request != 'quit':
            request = (await self.loop.sock_recv(client, 255)).decode('utf-8')
            yield request

    def kill(self):
        self.server.shutdown(1)
        self.loop.close()

    def terminate(self):
        self.server.shutdown(-1)
        self.loop.close()

    async def echo(self, client):
        async for request in self.recv(client):
            await self.loop.sock_sendall(client, request.encode())

