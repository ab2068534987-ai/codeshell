from __future__ import annotations

import asyncio
import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from codeshell.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from codeshell.sandbox import Sandbox, SandboxConfig

MAX_TIMEOUT = 600

_COMMAND_ERROR_THRESHOLDS: dict[str, int] = {
    "grep": 2,
    "egrep": 2,
    "fgrep": 2,
    "rg": 2,
    "diff": 2,
    "find": 2,
    "test": 2,
    "[": 2,
}


def _extract_last_command_name(command: str) -> str | None:
    last_segment = command.rsplit("|", maxsplit=1)[-1].strip()
    if not last_segment:
        return None
    try:
        tokens = shlex.split(last_segment)
    except ValueError:
        tokens = last_segment.split()
    for token in tokens:
        if re.match(r"^[A-Za-z_]\w*=", token):
            continue
        return token.rsplit("/", maxsplit=1)[-1]
    return None


def _interpret_exit_code(command: str, exit_code: int) -> bool:
    if exit_code == 0:
        return False
    cmd_name = _extract_last_command_name(command)
    if cmd_name and cmd_name in _COMMAND_ERROR_THRESHOLDS:
        return exit_code >= _COMMAND_ERROR_THRESHOLDS[cmd_name]
    return True


_EXIT_CODE_HINTS: dict[str, str] = {
    "grep": "no matches found",
    "egrep": "no matches found",
    "fgrep": "no matches found",
    "rg": "no matches found",
    "diff": "files differ",
    "find": "some directories were inaccessible",
    "test": "condition is false",
    "[": "condition is false",
}


def _exit_code_hint(command: str, exit_code: int) -> str:
    cmd_name = _extract_last_command_name(command)
    hint = _EXIT_CODE_HINTS.get(cmd_name, "") if cmd_name else ""
    if hint:
        return f"Exit code {exit_code} ({hint})"
    return f"Exit code {exit_code}"


@dataclass
class ShellCommandResult:
    output: str
    exit_code: int = 0
    is_error: bool = False


def _format_shell_output(command: str, output: str, exit_code: int) -> str:
    if exit_code != 0:
        hint = _exit_code_hint(command, exit_code)
        if output:
            output = f"{output.rstrip()}\n\n{hint}"
        else:
            output = hint
    if not output:
        output = "(no output)"
    return output


async def run_shell_command(
    command: str,
    timeout: int = 120,
    cwd: str | None = None,
    sandbox: "Sandbox | None" = None,
    sandbox_config: "SandboxConfig | None" = None,
) -> ShellCommandResult:
    timeout = min(timeout, MAX_TIMEOUT)
    actual_command = command
    if sandbox and sandbox_config and sandbox.available():
        actual_command = sandbox.wrap(command, sandbox_config)
    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            actual_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=cwd,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        if proc is not None:
            proc.kill()
            await proc.wait()
        return ShellCommandResult(
            output=f"Error: command timed out after {timeout}s",
            exit_code=-1,
            is_error=True,
        )
    except Exception as e:
        return ShellCommandResult(
            output=f"Error executing command: {e}",
            exit_code=-1,
            is_error=True,
        )

    raw_output = stdout.decode(errors="replace") if stdout else ""
    exit_code = proc.returncode or 0
    return ShellCommandResult(
        output=_format_shell_output(command, raw_output, exit_code),
        exit_code=exit_code,
        is_error=False,
    )


class Params(BaseModel):
    command: str = Field(description="Shell command to execute")
    timeout: int = Field(default=120, description="Timeout in seconds (max 600)")


class Bash(Tool):
    name = "Bash"
    description = "Execute a shell command and return stdout and stderr."
    params_model = Params
    category = "command"

    work_dir: str | None = None
    sandbox: "Sandbox | None" = None
    sandbox_config: "SandboxConfig | None" = None

    async def execute(self, params: Params) -> ToolResult:
        result = await run_shell_command(
            params.command,
            timeout=params.timeout,
            cwd=self.work_dir,
            sandbox=self.sandbox,
            sandbox_config=self.sandbox_config,
        )
        return ToolResult(output=result.output, is_error=result.is_error)