from __future__ import annotations

import pytest

from DeepResearch.src.datatypes.vllm_dataclass import VLLMServer, create_vllm_config
from DeepResearch.src.datatypes.vllm_integration import (
    VLLMDeployment,
    VLLMEmbeddingServerConfig,
    VLLMServerConfig,
)


def test_vllm_server_defaults_to_loopback() -> None:
    server = VLLMServer(create_vllm_config(model="gpt2"))

    assert server.host == "127.0.0.1"


def test_vllm_server_rejects_wildcard_bind_without_opt_in() -> None:
    config = create_vllm_config(model="gpt2")

    with pytest.raises(ValueError, match="allow_external_bind=True"):
        VLLMServer(config, host="0.0.0.0")


def test_vllm_server_allows_explicit_external_bind() -> None:
    server = VLLMServer(
        create_vllm_config(model="gpt2"),
        host="0.0.0.0",
        allow_external_bind=True,
    )

    assert server.host == "0.0.0.0"


def test_vllm_deployment_configs_default_to_loopback() -> None:
    llm_config = VLLMServerConfig(model_name="TinyLlama")
    embedding_config = VLLMEmbeddingServerConfig(model_name="all-MiniLM")

    assert llm_config.host == "127.0.0.1"
    assert embedding_config.host == "127.0.0.1"


@pytest.mark.parametrize("config_cls", [VLLMServerConfig, VLLMEmbeddingServerConfig])
def test_vllm_deployment_configs_reject_wildcard_without_opt_in(
    config_cls: type[VLLMServerConfig | VLLMEmbeddingServerConfig],
) -> None:
    with pytest.raises(ValueError, match="allow_external_bind=True"):
        config_cls(model_name="model", host="0.0.0.0")


@pytest.mark.parametrize("config_cls", [VLLMServerConfig, VLLMEmbeddingServerConfig])
def test_vllm_deployment_configs_allow_explicit_external_bind(
    config_cls: type[VLLMServerConfig | VLLMEmbeddingServerConfig],
) -> None:
    config = config_cls(
        model_name="model",
        host="0.0.0.0",
        allow_external_bind=True,
    )

    assert config.host == "0.0.0.0"


@pytest.mark.asyncio
async def test_deployment_health_checks_use_loopback_for_wildcard_binds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    urls: list[str] = []

    async def fake_health_check(_self: VLLMDeployment, url: str) -> bool:
        urls.append(url)
        return True

    monkeypatch.setattr(VLLMDeployment, "_check_server_health", fake_health_check)

    deployment = VLLMDeployment(
        llm_config=VLLMServerConfig(
            model_name="llm",
            host="0.0.0.0",
            allow_external_bind=True,
        ),
        embedding_config=VLLMEmbeddingServerConfig(
            model_name="embedding",
            host="0.0.0.0",
            allow_external_bind=True,
        ),
    )

    assert await deployment.start_llm_server()
    assert await deployment.start_embedding_server()

    assert urls == [
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8001/health",
    ]
