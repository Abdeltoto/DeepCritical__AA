"""Shared network binding policy for local DeepCritical services."""

from __future__ import annotations

from typing import Final

LOCAL_BIND_HOST: Final = "127.0.0.1"
LOCALHOST_ALIASES: Final = frozenset({LOCAL_BIND_HOST, "localhost", "::1"})

# Sentinel value used to detect wildcard binds and for Docker-internal service
# binds. Runtime service defaults must use LOCAL_BIND_HOST instead.
ALL_IPV4_INTERFACES: Final = "0.0.0.0"  # nosec B104
ALL_IPV6_INTERFACES: Final = "::"
WILDCARD_BIND_HOSTS: Final = frozenset({ALL_IPV4_INTERFACES, ALL_IPV6_INTERFACES})

# Docker containers often need to listen on all container interfaces so Docker
# port publishing can reach the service. Keep this out of host-process defaults.
DOCKER_CONTAINER_BIND_HOST: Final = ALL_IPV4_INTERFACES


def is_wildcard_host(host: str | None) -> bool:
    """Return true when a host value binds every available interface."""
    if host is None:
        return False
    return host.strip() in WILDCARD_BIND_HOSTS


def validate_bind_host(
    host: str | None,
    *,
    allow_external_bind: bool = False,
) -> str:
    """Normalize and validate a service bind host.

    Local services default to loopback. Wildcard binds are allowed only when
    the caller explicitly opts in because they expose the service beyond
    localhost on many systems.
    """
    normalized = (host or "").strip()
    if not normalized:
        return LOCAL_BIND_HOST
    if is_wildcard_host(normalized) and not allow_external_bind:
        msg = (
            "Wildcard bind hosts require allow_external_bind=True. "
            "Use 127.0.0.1 for localhost-only services."
        )
        raise ValueError(msg)
    return normalized


def client_host_for_bind_host(host: str | None) -> str:
    """Return a loopback client host for wildcard bind addresses."""
    normalized = validate_bind_host(host, allow_external_bind=True)
    return LOCAL_BIND_HOST if is_wildcard_host(normalized) else normalized
