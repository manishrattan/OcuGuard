import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import httpx
import mcp.types as mcp_types
import pytest

import mcp_agent_server
import mcp_sse_server


async def _request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    content: bytes | None = None,
) -> httpx.Response:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mcp_sse_server.app),
        base_url="http://testserver",
    ) as client:
        if payload is None:
            return await client.request(method, path, content=content)
        return await client.request(method, path, json=payload)


async def _list_stdio_tools() -> list[mcp_types.Tool]:
    handler = getattr(mcp_agent_server, "handle_list_tools")
    return await handler()


async def _call_stdio_tool(
    name: str,
    arguments: dict[str, object],
) -> list[mcp_types.TextContent | mcp_types.ImageContent]:
    handler = getattr(mcp_agent_server, "handle_call_tool")
    return await handler(name, arguments)


def test_stateless_messages_tools_list_returns_jsonrpc_response():
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {"jsonrpc": "2.0", "id": "tools-1", "method": "tools/list"},
        )
    )

    assert response.status_code == 200
    result = response.json()
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == "tools-1"
    assert {
        tool["name"] for tool in result["result"]["tools"]
    } == {
        "evaluate_wearable_stream",
        "ocuguard_calibrate_vision",
        "ocuguard_remap_text_grid",
        "ocuguard_triage_anxiety",
    }


def test_stateless_messages_empty_body_returns_parse_error():
    response = asyncio.run(_request("POST", "/messages"))

    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32700


def test_stateless_messages_invalid_json_returns_parse_error():
    response = asyncio.run(_request("POST", "/messages", content=b"{"))

    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32700


def test_stateless_messages_invalid_request_returns_jsonrpc_error():
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {"jsonrpc": "1.0", "id": "invalid-1", "method": "tools/list"},
        )
    )

    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32600
    assert response.json()["id"] == "invalid-1"


def test_stateless_messages_unknown_method_returns_method_not_found():
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {"jsonrpc": "2.0", "id": "unknown-1", "method": "unsupported/method"},
        )
    )

    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32601
    assert response.json()["id"] == "unknown-1"


def test_stateless_notification_has_no_jsonrpc_response_body():
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
    )

    assert response.status_code == 202
    assert response.content == b""


def test_stateless_tools_call_dispatches_and_returns_structured_status():
    arguments = {
        "user_id": "synthetic-test",
        "input_string": "synthetic OCR payload",
        "agent_mode": "OCUGUARD_CORE",
        "pitch": -20.0,
        "yaw": 5.0,
        "history": {"cataract_surgery": True, "retinal_disease": False},
    }
    data = {
        "status": "SAFE",
        "action_required": "Synthetic response.",
        "reasoning": "Synthetic test.",
    }
    with patch("app.process_single_frame", return_value=data) as process_frame:
        response = asyncio.run(
            _request(
                "POST",
                "/messages",
                {
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "method": "tools/call",
                    "params": {
                        "name": "evaluate_wearable_stream",
                        "arguments": arguments,
                    },
                },
            )
        )

    process_frame.assert_called_once_with(arguments)
    body = response.json()
    assert response.status_code == 200
    assert body["id"] == "call-1"
    assert body["result"]["structuredContent"]["data"] == data
    assert body["result"]["isError"] is False


def test_stateless_tools_call_rejects_unknown_tool():
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {
                "jsonrpc": "2.0",
                "id": "call-unknown",
                "method": "tools/call",
                "params": {"name": "not-a-tool", "arguments": {}},
            },
        )
    )

    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32602


def test_sse_get_establishes_transport_and_runs_mcp_server(monkeypatch):
    @asynccontextmanager
    async def fake_connect_sse(scope, receive, send):
        assert scope["type"] == "http"
        assert callable(receive)
        assert callable(send)
        yield object(), object()

    server_run = AsyncMock()
    monkeypatch.setattr(mcp_sse_server.mcp_transport, "connect_sse", fake_connect_sse)
    monkeypatch.setattr(mcp_sse_server.mcp_server, "run", server_run)

    response = asyncio.run(_request("GET", "/sse"))

    assert response.status_code == 200
    server_run.assert_awaited_once()


def test_stdio_mcp_server_lists_wearable_evaluation_tool():
    tools = asyncio.run(_list_stdio_tools())

    evaluation_tool = next(
        tool for tool in tools if tool.name == "evaluate_wearable_stream"
    )
    assert "agent_mode" in evaluation_tool.inputSchema["properties"]
    assert "pitch" in evaluation_tool.inputSchema["required"]
    assert {
        "gaze_x",
        "confidence",
        "posture_hold_duration",
        "ambient_light_intensity",
        "perceived_size_delta",
        "text_wavy_index",
        "vocal_stress_score",
    }.issubset(evaluation_tool.inputSchema["properties"])
    assert set(evaluation_tool.inputSchema["properties"]["agent_mode"]["enum"]) == {
        "EYE_SENTINEL",
        "OCUGUARD_CORE",
        "GAZE_COMPASS",
        "TABULAR_LAYOUT_SPEECH",
        "ERGONOMIC_SCHEDULE",
        "AMBIENT_LUMINANCE",
        "BE_MY_EYES",
        "ANISEIKONIA_SCALING",
        "METAMORPHOPSIA_GRID_REMAPPER",
        "BIOFEEDBACK_ANXIETY_SENTINEL",
    }


@pytest.mark.parametrize(
    ("name", "arguments", "expected_status", "expected_result_field"),
    [
        (
            "ocuguard_calibrate_vision",
            {"perceived_size_delta": 0.25},
            "WARN",
            '"scale_factor": 0.8',
        ),
        (
            "ocuguard_remap_text_grid",
            {"text_wavy_index": 0.5},
            "WARN",
            '"css_warp_matrix"',
        ),
        (
            "ocuguard_triage_anxiety",
            {"input_string": "synthetic anxious phrase", "vocal_stress_score": 0.2},
            "WARN",
            '"panic_phrase_detected": true',
        ),
    ],
)
def test_stdio_mcp_server_dispatches_direct_agent_tools(
    name: str,
    arguments: dict[str, object],
    expected_status: str,
    expected_result_field: str,
):
    content = asyncio.run(_call_stdio_tool(name, arguments))

    assert len(content) == 1
    result = content[0]
    assert isinstance(result, mcp_types.TextContent)
    assert f"Status: {expected_status}" in result.text
    assert expected_result_field in result.text


@pytest.mark.parametrize(
    ("name", "arguments", "expected_status"),
    [
        ("ocuguard_calibrate_vision", {"perceived_size_delta": 0.25}, "WARN"),
        ("ocuguard_remap_text_grid", {"text_wavy_index": 0.5}, "WARN"),
        (
            "ocuguard_triage_anxiety",
            {"input_string": "synthetic anxious phrase", "vocal_stress_score": 0.2},
            "WARN",
        ),
    ],
)
def test_stateless_messages_dispatches_direct_agent_tools(
    name: str, arguments: dict[str, object], expected_status: str
):
    response = asyncio.run(
        _request(
            "POST",
            "/messages",
            {
                "jsonrpc": "2.0",
                "id": f"direct-{name}",
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
    )

    assert response.status_code == 200
    data = response.json()["result"]["structuredContent"]["data"]
    assert data["status"] == expected_status
    assert response.json()["result"]["isError"] is False


def test_stdio_mcp_server_dispatches_evaluation_to_pipeline():
    arguments = {
        "user_id": "synthetic-test",
        "input_string": "synthetic frame",
        "agent_mode": "OCUGUARD_CORE",
        "pitch": 0.0,
        "yaw": 0.0,
    }
    response_payload = {
        "status": "SAFE",
        "action_required": "Synthetic demo output.",
        "reasoning": "Synthetic test response.",
    }

    with patch(
        "mcp_agent_server.process_single_frame", return_value=response_payload
    ) as process_frame:
        content = asyncio.run(
            _call_stdio_tool("evaluate_wearable_stream", arguments)
        )

    process_frame.assert_called_once_with(arguments)
    assert len(content) == 1
    result = content[0]
    assert isinstance(result, mcp_types.TextContent)
    assert "Status: SAFE" in result.text
    assert "Synthetic demo output." in result.text


def test_stdio_mcp_server_rejects_unknown_tool():
    with pytest.raises(ValueError, match="Unknown tool"):
        asyncio.run(_call_stdio_tool("unknown", {"value": 1}))
