import asyncio
import logging
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, PlainTextResponse

# Official Model Context Protocol Engine Core Imports
from mcp.server import Server
import mcp.types as types

# Import the native SSE transport layer directly from the official core location
from mcp.server.sse import SseServerTransport

logger = logging.getLogger("OcuGuard.MCPSSE")

# Instantiate the official Model Context Protocol core wrapper object
mcp_server = Server("ocuguard-spatial-middleware")

@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Expose the OcuGuard multi-agent pipeline inputs to external LLMs."""
    return [
        types.Tool(
            name="evaluate_wearable_stream",
            description="Stateless edge middleware to optimize visual-to-acoustic metadata layouts and monitor orientation ergonomics on smart eyewear.",
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

# Bind transport relative routing parameters for client messaging hooks using your active tunnel link
# Change this line from the full localtunnel URL back to a pure relative path string
mcp_transport = SseServerTransport("/messages")

async def handle_sse_message_stream(request):
    """Establish persistent SSE connection, accepting GET handshakes or POST pings."""
    # If a bot sends a POST ping to negotiate/test headers, respond with a clean validation handshake
    if request.method == "POST":
        return JSONResponse({"status": "ready", "transport": "sse"})
        
    scope = request.scope
    receive = request.receive
    send = request.send
    
    async with mcp_transport.connect_sse(scope, receive, send) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

# DISCOVERY ROUTE ENDPOINTS TO SWEEP AWAY THE SMITHERY 405/404 ERRORS
async def handle_root_index(request):
    """Provide an explicit root index acknowledgement for scanning bots."""
    return PlainTextResponse("OcuGuard MCP SSE Server Framework Active. Query /sse to establish channel links.")

async def handle_server_card(request):
    """Advertise server metadata card configurations cleanly to bypass auto-scan limits."""
    return JSONResponse({
        "mcp_version": "1.0.0",
        "name": "ocuguard-spatial-middleware",
        "version": "2.0.0",
        "endpoints": {
            "sse": "/sse",
            "messages": "/messages"
        }
    })

# Unified ASGI route table accepting both GET and POST handshakes safely
app = Starlette(
    routes=[
        Route("/", endpoint=handle_root_index, methods=["GET", "POST"]),
        Route("/.well-known/mcp/server-card.json", endpoint=handle_server_card, methods=["GET"]),
        Route("/sse", endpoint=handle_sse_message_stream, methods=["GET", "POST"]),
        Route("/messages", endpoint=mcp_transport.handle_post_message, methods=["POST"])
    ]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)