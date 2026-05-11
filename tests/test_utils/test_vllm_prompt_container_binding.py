from __future__ import annotations

from typing import Any

from omegaconf import OmegaConf

from DeepResearch.src.utils.network_binding import DOCKER_CONTAINER_BIND_HOST
from scripts.prompt_testing import testcontainers_vllm


class FakeVLLMContainer:
    """Minimal fake for asserting VLLM container construction."""

    instances: list[FakeVLLMContainer] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        FakeVLLMContainer.instances.append(self)

    def with_cpu_limit(self, _cpu_limit: str | float) -> FakeVLLMContainer:
        return self

    def with_memory_limit(self, _memory_limit: str) -> FakeVLLMContainer:
        return self

    def start(self) -> None:
        return None

    def stop(self) -> None:
        return None

    def get_connection_url(self) -> str:
        return "http://127.0.0.1:8000"


def test_prompt_tester_uses_container_bind_host_for_vllm_host(
    monkeypatch,
    tmp_path,
) -> None:
    FakeVLLMContainer.instances.clear()
    monkeypatch.setattr(testcontainers_vllm, "VLLM_AVAILABLE", True)
    monkeypatch.setattr(testcontainers_vllm, "VLLMContainer", FakeVLLMContainer)
    monkeypatch.setattr(
        testcontainers_vllm.VLLMPromptTester,
        "_check_docker_availability",
        lambda _self: True,
    )
    monkeypatch.setattr(
        testcontainers_vllm.VLLMPromptTester,
        "_wait_for_ready",
        lambda _self, _timeout: None,
    )

    config = OmegaConf.create(
        {
            "vllm_tests": {
                "artifacts": {"base_directory": str(tmp_path)},
                "monitoring": {"enabled": False},
            },
            "model": {
                "name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                "container": {
                    "image": "vllm/vllm-openai:latest",
                    "environment": {
                        "VLLM_HOST": "bad-override",
                        "EXTRA_FLAG": "1",
                    },
                },
                "server": {
                    "host": "127.0.0.1",
                    "container_bind_host": DOCKER_CONTAINER_BIND_HOST,
                    "port": 8123,
                },
                "generation": {
                    "max_tokens": 32,
                    "temperature": 0.2,
                },
            },
            "performance": {"max_container_startup_time": 1},
        }
    )

    tester = testcontainers_vllm.VLLMPromptTester(config=config)
    tester.start_container()

    assert len(FakeVLLMContainer.instances) == 1
    container = FakeVLLMContainer.instances[0]
    assert container.kwargs["container_bind_host"] == DOCKER_CONTAINER_BIND_HOST
    assert container.kwargs["environment"]["VLLM_HOST"] == DOCKER_CONTAINER_BIND_HOST
    assert container.kwargs["environment"]["EXTRA_FLAG"] == "1"
