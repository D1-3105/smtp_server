import logging
from mailing.smtp_server import Server
from socket import gethostbyname, gethostname
logging.Logger(name='smtp_server')

my_fqdn = gethostbyname(gethostname())

app = Server('localhost', 10025)



