"""
DeepCritical utilities module.

This module provides various utilities including MCP server deployment,
code execution environments, and Jupyter integration.
"""

from .coding import (
    CodeBlock,
    CodeExecutor,
    CodeExtractor,
    CodeResult,
    CommandLineCodeResult,
    DockerCommandLineCodeExecutor,
    IPythonCodeResult,
    LocalCommandLineCodeExecutor,
    MarkdownCodeExtractor,
)
from .docker_compose_deployer import DockerComposeDeployer
from .environments import PythonEnvironment, SystemPythonEnvironment, WorkingDirectory
from .jupyter import (
    JupyterClient,
    JupyterCodeExecutor,
    JupyterConnectable,
    JupyterConnectionInfo,
    JupyterKernelClient,
)
from .python_code_execution import PythonCodeExecutionTool

__all__ = [
    "CodeBlock",
    "CodeExecutor",
    "CodeExtractor",
    "CodeResult",
    "CommandLineCodeResult",
    "DockerCommandLineCodeExecutor",
    "DockerComposeDeployer",
    "IPythonCodeResult",
    "JupyterClient",
    "JupyterCodeExecutor",
    "JupyterConnectable",
    "JupyterConnectionInfo",
    "JupyterKernelClient",
    "LocalCommandLineCodeExecutor",
    "MarkdownCodeExtractor",
    "PythonCodeExecutionTool",
    "PythonEnvironment",
    "SystemPythonEnvironment",
    "WorkingDirectory",
]


def __getattr__(name: str):
    # Avoid importing heavy testcontainers + vendored MCP servers at module import time.
    if name == "TestcontainersDeployer":
        from .testcontainers_deployer import TestcontainersDeployer

        return TestcontainersDeployer
    msg = f"module '{__name__}' has no attribute '{name}'"
    raise AttributeError(msg)
