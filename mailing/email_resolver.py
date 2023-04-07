# python
import dataclasses
import smtplib
import typing
import dns.asyncresolver
from collections.abc import Iterable
import asyncio
# pydantic

@dataclasses.dataclass
class BaseResolver:
    on_resolve: typing.Any

    @staticmethod
    def retrieve_domain_from_email(email: str):
        return email.split('@')[1]

    @classmethod
    def from_email(cls, email: typing.Any):
        raise NotImplemented

    @staticmethod
    async def resolve_domain(domain: str):
        """
        Get metric and domain,
        sort by metric
        :return: ['30', 'alt3.gmail-smtp-in.l.google.com.'], ['20', 'alt2.gmail-smtp-in.l.google.com.']
        """
        mxs = await dns.asyncresolver.resolve(domain, 15)
        mxs = mxs.rrset
        metrics_fdqns = []
        for mx in mxs:
            metrics_fdqns.append(mx.to_text().split(' '))
        return list(sorted(metrics_fdqns, key=lambda mfdqn: int(mfdqn[0])))

    @staticmethod
    async def resolve_to_ip(domain) -> dict[tuple[str]]:
        ip_resolved = await dns.asyncresolver.resolve(domain)
        return {domain: (i.address for i in ip_resolved.rrset)}

    async def fetch_ips(self, dom_list: list[str]):
        """
        Gets any domain-dict and async reviles ip address
        :return: {'mxs.mail.ru.': ['217.69.139.150', '94.100.180.31']}
        """
        tasks = []
        for metric, domain in dom_list:
            tasks.append(self.resolve_to_ip(domain))
        ips = await asyncio.gather(*tasks)
        ip_dict = {}
        for separated_domain in ips:
            ip_dict.update(separated_domain)
        return ip_dict

    async def resolve(self):
        raise NotImplemented


class EmailResolver(BaseResolver):
    on_resolve: str

    @classmethod
    def from_email(cls, email: str):
        on_resolve = cls.retrieve_domain_from_email(email)
        return cls(on_resolve=on_resolve)

    async def resolve(self):
        return {self.on_resolve: await self.resolve_domain(self.on_resolve)}


class MultiResolver(BaseResolver):
    on_resolve: set

    @classmethod
    def from_email(cls, email_input: str | Iterable):
        if isinstance(email_input, str):
            return cls(on_resolve={cls.retrieve_domain_from_email(email_input)})
        elif isinstance(email_input, Iterable):
            return cls(on_resolve=set(cls.retrieve_domain_from_email(i) for i in email_input))

    async def resolve(self):
        tasks: list[typing.Coroutine] = []
        for dom in self.on_resolve:
            tasks.append(self.resolve_domain(dom))
        mxs = dict(zip(self.on_resolve, await asyncio.gather(*tasks)))
        return mxs
