# pytest
import asyncio

import pytest
# mailing
from mailing.email_resolver import EmailResolver, MultiResolver
from mailing.smtp_server import Server
from mailing.smtp_client import SMTPClient
from mailing.config.conf import my_fqdn
# python
import socket


@pytest.fixture
def default_email_addr():
    return 'lyerhd@gmail.com'


@pytest.fixture
def list_of_emails():
    return ['lyerhd@gmail.com', 'lyerhd@mail.ru', 'lyerhd@yandex.ru']

@pytest.fixture
def app_test():
    from mailing.config.conf import app
    return app


@pytest.mark.asyncio
async def test_email_resolver(default_email_addr):
    addr = default_email_addr
    resolver = EmailResolver.from_email(email=addr)
    mxs = await resolver.resolve()
    assert mxs is not None


@pytest.mark.asyncio
async def test_multi_resolver(list_of_emails):
    addrs: list[str] = list_of_emails
    resolver = MultiResolver.from_email(addrs)
    mxs = await resolver.resolve()
    print(mxs)
    assert [] not in mxs.values()


@pytest.mark.asyncio
async def test_resolve_to_ips(list_of_emails):
    addrs: list[str] = list_of_emails
    results = await SMTPClient.get_smtp_addresses(addrs)
    print(results)
    assert sorted(list(results.keys())) == sorted(list(map(lambda e: e.split('@')[1], addrs)))


@pytest.mark.asyncio
async def test_create_smtp_client(list_of_emails):
    async with SMTPClient() as smtp:
        await smtp.create_clients(list_of_emails)
        assert smtp.clients is not []
        await asyncio.sleep(1)


@pytest.mark.asyncio
async def test_send_mail(list_of_emails):
    async with SMTPClient() as smtp:
        await smtp.create_clients(list_of_emails)
        assert smtp.clients is not []
        await asyncio.sleep(1)
        await smtp.mail(recipients='lyerhd@gmail.com', from_email=f'lyerhd@{my_fqdn}', data='HELLO!')
        await asyncio.sleep(10)


def test_echo_smtp_server():
    # app_test.run()
    client = socket.socket()
    client.connect(('localhost', 10025))
    client.setblocking(True)
    for i in range(5):
        send_line = f'Request number {i+1}: Sending:\n'
        print(send_line, end='')
        client.send(send_line.encode())
        print('Done')
        response = client.recv(255)
        print(response)
    client.send(b'quit')

