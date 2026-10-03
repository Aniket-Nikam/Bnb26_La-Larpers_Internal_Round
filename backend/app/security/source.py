from __future__ import annotations

import ipaddress
from collections.abc import Iterable


def resolve_source_address(
    *,
    peer_address: str,
    forwarded_for: str | None,
    trusted_proxy_cidrs: Iterable[str],
) -> str:
    peer = _address(peer_address)
    trusted = tuple(ipaddress.ip_network(value, strict=False) for value in trusted_proxy_cidrs)
    if not _trusted(peer, trusted) or not forwarded_for:
        return peer.compressed

    chain = []
    for raw in forwarded_for.split(","):
        raw = raw.strip()
        if not raw or len(raw) > 64:
            return peer.compressed
        try:
            chain.append(_address(raw))
        except ValueError:
            return peer.compressed
    chain.append(peer)
    for address in reversed(chain):
        if not _trusted(address, trusted):
            return address.compressed
    return chain[0].compressed


def _address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    # ASGI peer addresses do not contain a port. Bracketed/host:port input is rejected.
    return ipaddress.ip_address(value)


def _trusted(
    address: ipaddress.IPv4Address | ipaddress.IPv6Address,
    networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...],
) -> bool:
    return any(address.version == network.version and address in network for network in networks)
