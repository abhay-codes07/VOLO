"""volo-mcp — record, replay, and (future) fuzz Model Context Protocol servers (newplan P1/M10)."""

from volo_mcp.conformance import ConformanceReport, StepVerdict, check_conformance
from volo_mcp.framing import FramingError, MessageBuffer, encode_message
from volo_mcp.fuzz import (
    MCP_FUZZ_OPS,
    default_mcp_fuzz_library,
    fuzz_change_summary,
    fuzz_recording,
    mcp_fuzz_scenarios,
)
from volo_mcp.messages import SIM_MISS_CODE, tool_key
from volo_mcp.recorder import MCPRecorder, MCPRecorderStats
from volo_mcp.replay import MCPReplayServer
from volo_mcp.stdio import StdioRecordProxy, serve_stdio

__all__ = [
    "MCP_FUZZ_OPS",
    "SIM_MISS_CODE",
    "ConformanceReport",
    "FramingError",
    "MCPRecorder",
    "MCPRecorderStats",
    "MCPReplayServer",
    "MessageBuffer",
    "StdioRecordProxy",
    "StepVerdict",
    "check_conformance",
    "default_mcp_fuzz_library",
    "encode_message",
    "fuzz_change_summary",
    "fuzz_recording",
    "mcp_fuzz_scenarios",
    "serve_stdio",
    "tool_key",
]
