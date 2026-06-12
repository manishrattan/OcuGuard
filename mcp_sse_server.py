import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

# Official Model Context Protocol Engine Core Imports
from mcp.server import Server
import mcp.types as types

# Use the native, core SSE transport layer which is always available
from mcp.server.sse import SseServerTransport

# Configure logging parameters
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OcuGuard.MCPSSE")

# 1. Instantiate the official Model Context Protocol core wrapper object
mcp_server = Server("ocuguard-spatial-middleware")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Expose the OcuGuard multi-agent pipeline inputs to external LLMs."""
    return [
        types.Tool(
            name="evaluate_wearable_stream",
            description="Stateless edge middleware to optimize visual-to-acoustic layouts and monitor orientation ergonomics on smart eyewear.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Anonymized hardware node token."},
                    "input_string": {"type": "string", "description": "OCR structure string or audio transcription phrase."},
                    "agent_mode": {
                        "type": "string", 
                        "enum": ["EYE_SENTINEL", "OCUGUARD_CORE", "GAZE_COMPASS", "TABULAR_LAYOUT_SPEECH", "ERGONOMIC_SCHEDULE", "AMBIENT_LUMINANCE", "BE_MY_EYES"]
                    },
                    "pitch": {"type": "number", "description": "Horizontal X-axis tracking metric."},
                    "yaw": {"type": "number", "description": "Vertical Y-axis pan coordinate."}
                },
                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Route tool triggers straight down into the localized sub-agent evaluations."""
    if name != "evaluate_wearable_stream" or not arguments:
        raise ValueError("Invalid parameters passed to execution endpoint.")

    try:
        from app import process_single_frame
        response_payload = process_single_frame(arguments)
        return [
            types.TextContent(
                type="text",
                text=f"Status: {response_payload['status']}\nAction Required: {response_payload['action_required']}\nReasoning: {response_payload['reasoning']}"
            )
        ]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Pipeline exception: {str(e)}")]

# 2. Initialize the core transport layer with the relative messages endpoint path
mcp_transport = SseServerTransport("/messages")
app = FastAPI(title="OcuGuard Spatial Middleware")

# Shared mock router engine to bypass the lack of session_id during validation crawls
async def process_stateless_jsonrpc(request: Request):
    try:
        body = await request.json()
        rpc_id = body.get("id")
        method = body.get("method", "")
        
        # Intercept tool-discovery requests and mock them exactly to specifications
        if "tools/list" in method:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "tools": [
                        {
                            "name": "evaluate_wearable_stream",
                            "description": "Stateless edge middleware to optimize visual-to-acoustic layouts and monitor orientation ergonomics on smart eyewear.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "input_string": {"type": "string"},
                                    "agent_mode": {"type": "string"},
                                    "pitch": {"type": "number"},
                                    "yaw": {"type": "number"}
                                },
                                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
                            }
                        }
                    ]
                }
            })
            
        elif "resources/list" in method:
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"resources": []}})
        elif "prompts/list" in method:
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"prompts": []}})
        elif "triggers/list" in method:
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"triggers": []}})
        elif "initialize" in method:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "ocuguard-spatial-middleware", "version": "2.0.0"}
                }
            })
    except Exception:
        pass
        
    # If it's a valid post-handshake message with session tracking, send it to the core engine
    return await mcp_transport.handle_post_message(request.scope, request._receive, request._send)

@app.get("/")
async def handle_root_get():
    """Provide an explicit root index acknowledgement for scanning browsers."""
    return PlainTextResponse("OcuGuard MCP SSE Server Framework Active. Query /sse to establish channel links.")

@app.post("/")
async def handle_root_post(request: Request):
    """Proxy fallback endpoint: Gracefully intercept and respond to stateless scanner payloads."""
    if not request.query_params.get("session_id"):
        return await process_stateless_jsonrpc(request)
    return await mcp_transport.handle_post_message(request.scope, request._receive, request._send)

@app.get("/.well-known/mcp/server-card.json")
async def handle_server_card():
    """Advertise server card endpoints to allow automatic tool mapping discovery."""
    return JSONResponse({
        "mcp_version": "1.0.0",
        "name": "ocuguard-spatial-middleware",
        "version": "2.0.0",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages"
        }
    })

@app.get("/sse")
async def handle_sse(request: Request):
    """Expose the unified persistent real-time server-sent event route handler."""
    async with mcp_transport.connect_sse(
        request.scope, request._receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

@app.post("/sse")
async def handle_sse_post(request: Request):
    """Trap structural ping queries explicitly using the stateless proxy engine logic."""
    if not request.query_params.get("session_id"):
        return await process_stateless_jsonrpc(request)
    return await mcp_transport.handle_post_message(request.scope, request._receive, request._send)

@app.post("/messages")
async def handle_messages(request: Request):
    """Securely pass JSON-RPC tool listing requests straight down into the core transport engine."""
    if not request.query_params.get("session_id"):
        return await process_stateless_jsonrpc(request)
    return await mcp_transport.handle_post_message(request.scope, request._receive, request._send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)