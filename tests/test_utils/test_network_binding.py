from __future__ import annotations

import pytest

from DeepResearch.src.utils.network_binding import (
    DOCKER_CONTAINER_BIND_HOST,
    LOCAL_BIND_HOST,
    client_host_for_bind_host,
    is_wildcard_host,
    validate_bind_host,
)


def test_validate_bind_host_defaults_blank_values_to_loopback() -> None:
    assert validate_bind_host(None) == LOCAL_BIND_HOST
    assert validate_bind_host("") == LOCAL_BIND_HOST
    assert validate_bind_host("   ") == LOCAL_BIND_HOST


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1", "vllm.local"])
def test_validate_bind_host_allows_loopback_and_named_hosts(host: str) -> None:
    assert validate_bind_host(host) == host


@pytest.mark.parametrize("host", ["0.0.0.0", "::"])
def test_validate_bind_host_rejects_wildcards_without_opt_in(host: str) -> None:
    with pytest.raises(ValueError, match="allow_external_bind=True"):
        validate_bind_host(host)


@pytest.mark.parametrize("host", ["0.0.0.0", "::"])
def test_validate_bind_host_allows_explicit_external_bind(host: str) -> None:
    assert validate_bind_host(host, allow_external_bind=True) == host


def test_client_host_for_bind_host_maps_wildcards_to_loopback() -> None:
    assert client_host_for_bind_host("0.0.0.0") == LOCAL_BIND_HOST
    assert client_host_for_bind_host("::") == LOCAL_BIND_HOST
    assert client_host_for_bind_host("localhost") == "localhost"


def test_docker_container_bind_host_is_explicit_wildcard() -> None:
    assert DOCKER_CONTAINER_BIND_HOST == "0.0.0.0"
    assert is_wildcard_host(DOCKER_CONTAINER_BIND_HOST)
