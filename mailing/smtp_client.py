import typing
from dataclasses import dataclass
from mailing.config.conf import my_fqdn
import socket
import asyncio
import threading
from typing import Iterable, Any
from .email_resolver import EmailResolver, MultiResolver, BaseResolver


@dataclass
class ResolverFabric:
    email_data: str | Iterable

    def make_resolver(self) -> BaseResolver:
        if isinstance(self.email_data, str):
            return EmailResolver.from_email(self.email_data)
        elif isinstance(self.email_data, Iterable):
            return MultiResolver.from_email(self.email_data)
        else:
            raise ValueError


class BaseSMTPClientException(Exception):
    ...


class ClientTimeout(Exception):
    ...


@dataclass
class SyncExecutor:
    transactions: dict

    @staticmethod
    def run_transaction(client: socket.socket, msgs):
        client.setblocking(True)
        for msg in msgs:
            SMTPClient.send_anything(msg, client)
            client.recv(255)

    def execute(self):
        for client, msgs in self.transactions.items():
            exec_thread = threading.Thread(
                target=self.run_transaction,
                kwargs={'msgs': msgs, 'client': client}
            )
            exec_thread.start()
            exec_thread.join()


def run_in_daemon(coro):
    async def wrapper(*args, **kwargs):
        transactions = await coro(*args, **kwargs)
        SyncExecutor(transactions).execute()
        return 1

    return wrapper


class SMTPClient:
    host: str
    clients: dict[str: socket.socket] = {}
    _loop = None

    def __init__(self, host='localhost'):
        self.host = host

    @property
    def loop(self):
        if self._loop:
            return self._loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
        return loop

    @staticmethod
    async def get_smtp_addresses(emails):
        resolver = ResolverFabric(emails).make_resolver()
        mxs: dict[str] = await resolver.resolve()
        tasks = []
        for mx_list in mxs.values():
            tasks.append(resolver.fetch_ips(mx_list))
        results = await asyncio.gather(*tasks)
        return dict(zip(mxs.keys(), results))

    async def _make_client(self, address: str):
        sock = socket.socket()
        sock.setblocking(False)
        await self.loop.sock_connect(sock, (address, 25))
        ehlo = f'EHLO {my_fqdn} \r\n'
        await self.loop.sock_sendall(sock, ehlo.encode())
        return sock

    async def make_client(self, domain_smtps: list[str]) -> socket.socket:
        """
        Recursively calls self to create any connection with any of smtp-servers
        :param domain_smtps: [[12.2.2.2, 212.22.23.2], ...]
        :return:
        """
        for smtp_addresses in domain_smtps:
            for ip_addr in smtp_addresses:
                try:
                    client = await self._make_client(ip_addr)
                    return client
                except socket.error as e:
                    continue
            else:
                raise ClientTimeout(f'Timeout occurred on set: {domain_smtps}')

    async def create_clients(self, email_receiver_inp: list[str] | str):
        domains_to_mx_ips = await self.get_smtp_addresses(email_receiver_inp)
        client_tasks = []
        for domain_addresses in domains_to_mx_ips.values():
            client_tasks.append(self.make_client(domain_addresses.values()))
        sockets = await asyncio.gather(*client_tasks, return_exceptions=True)
        self.clients: dict[str: socket.socket] = dict(zip(domains_to_mx_ips.keys(), sockets))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for client in self.clients.values():
            client: socket.socket
            client.close()

    @staticmethod
    def send_anything(data: str | bytes, client: socket.socket):
        anchor_symb = '\r\n'
        if isinstance(data, str):
            data += anchor_symb
            data = data.encode()
            client.send(data)
        elif isinstance(data, bytes):
            client.send(data)
            client.send(anchor_symb.encode())
        else:
            raise BaseSMTPClientException(f'Unsupported content! Required string or bytes, got: {type(data)}')

    @run_in_daemon
    async def mail(self, recipients: list[str] | str, from_email: str, data: str | bytes):
        if isinstance(recipients, str):
            recipients = [recipients]
        transactions = dict(zip(self.clients.values(), [[] for _ in self.clients.values()]))
        for recipient in recipients:
            email_domain = recipient.split('@')[1]
            client: socket.socket = self.clients.get(email_domain)
            assert client is not None
            transactions[client].extend(
                [
                    f'MAIL FROM:<{from_email}>',
                    f'RCPT TO:<{recipient}>',
                    f'DATA',
                    data+'\r\n.',
                ]
            )
        return transactions
