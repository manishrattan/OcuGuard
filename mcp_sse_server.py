import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse

# Official Model Context Protocol Engine Core & Type Validation Imports
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
async def handle_list_tools() -> List[types.Tool]:
    """
    Expose the OcuGuard multi-agent pipeline inputs to external LLMs.
    
    Returns:
        List[types.Tool]: Supported tool schemas with rigorous Pydantic data modeling definitions.
    """
    return [
        types.Tool(
            name="evaluate_wearable_stream",
            description=(
                "Stateless edge middleware to optimize visual-to-acoustic metadata layouts, "
                "evaluate triage keywords, and monitor orientation ergonomics on smart eyewear."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string", 
                        "description": "Anonymized hardware node token or wearer UUID."
                    },
                    "input_string": {
                        "type": "string", 
                        "description": "OCR structure string, vague symptom, or audio transcription phrase to triage."
                    },
                    "agent_mode": {
                        "type": "string", 
                        "description": "Target sub-agent plugin layer to direct the tracking payload into.",
                        "enum": [
                            "EYE_SENTINEL", 
                            "OCUGUARD_CORE", 
                            "GAZE_COMPASS", 
                            "TABULAR_LAYOUT_SPEECH", 
                            "ERGONOMIC_SCHEDULE", 
                            "AMBIENT_LUMINANCE", 
                            "BE_MY_EYES",
                            "PRE_OP_BRIDGE"
                        ]
                    },
                    "pitch": {
                        "type": "number", 
                        "description": "Horizontal X-axis inertial head tracking telemetry metric."
                    },
                    "yaw": {
                        "type": "number", 
                        "description": "Vertical Y-axis pan coordinate matrix vector tracking metric."
                    },
                    "multimodal_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional background structural triggers or contextual indicators (e.g., 'shadow', 'sudden')."
                    },
                    "history": {
                        "type": "object",
                        "properties": {
                            "cataract_surgery": {"type": "boolean"},
                            "age_over_50": {"type": "boolean"},
                            "retinal_disease": {"type": "boolean"},
                            "diabetic_retinopathy": {"type": "boolean"},
                            "previous_detachment": {"type": "boolean"}
                        },
                        "description": "User-configured medical/post-surgical risk background switches for weighting rules."
                    }
                },
                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
            }
        )
    ]

@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]]
) -> List[types.TextContent]:
    """
    Route tool triggers straight down into the localized sub-agent evaluations.
    
    Args:
        name (str): The requested tool call identifier.
        arguments (Optional[Dict[str, Any]]): Arbitrary runtime telemetry variables passed down by the client.
        
    Returns:
        List[types.TextContent]: Structured string block response carrying compliance tags, reasoning, and actions.
    """
    if name != "evaluate_wearable_stream" or not arguments:
        raise ValueError("Invalid parameters or unrecognized tool identifier passed to execution endpoint.")

    try:
        # Dynamically import the core framework processor to prevent circular dependency lockups
        from app import process_single_frame
        
        # Execute the unified supervisor agent telemetry array validation pipeline
        response_payload = process_single_frame(arguments)
        
        # Pull key operational fields natively, falling back gracefully to standard structures if empty
        status = response_payload.get("status", response_payload.get("data", {}).get("status", "URGENT"))
        action = response_payload.get("action_required", response_payload.get("data", {}).get("action_required", ""))
        reasoning = response_payload.get("reasoning", response_payload.get("data", {}).get("reasoning", ""))
        
        output_text = (
            f"Status/Severity Ring: {status}\n"
            f"Action Required: {action}\n"
            f"Orchestration Reasoning: {reasoning}"
        )
        
        return [types.TextContent(type="text", text=output_text)]
        
    except Exception as e:
        logger.error(f"Execution error within underlying agent plugin matrix pipeline: {str(e)}")
        return [
            types.TextContent(
                type="text", 
                text=f"OcuGuard Pipeline Exception encountered during sensor serialization: {str(e)}"
            )
        ]

# 2. Initialize the core transport layer with the relative messages endpoint path
mcp_transport = SseServerTransport("/messages")
app = FastAPI(
    title="OcuGuard Spatial Middleware Backend", 
    description="Adaptive Spatial Computing telemetry translation engine running over native MCP SSE bindings."
)

# Shared mock router engine to bypass the lack of session_id during validation crawls
async def process_stateless_jsonrpc(request: Request) -> JSONResponse:
    """
    Safely captures concurrent stateless JSON-RPC discovery payloads from external crawlers
    and outputs valid protocol payloads to bypass session layer exceptions.
    """
    try:
        # Securely read the raw bytes block without destroying or blocking the ASGI network stream
        body_bytes = await request.body()
        if not body_bytes:
            return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error: Empty Payload."}})
            
        body = json.loads(body_bytes.decode("utf-8"))
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
                            "description": (
                                "Stateless edge middleware to optimize visual-to-acoustic layouts, "
                                "evaluate triage keywords, and monitor orientation ergonomics on smart eyewear."
                            ),
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "user_id": {"type": "string"},
                                    "input_string": {"type": "string"},
                                    "agent_mode": {"type": "string"},
                                    "pitch": {"type": "number"},
                                    "yaw": {"type": "number"},
                                    "multimodal_flags": {"type": "array", "items": {"type": "string"}},
                                    "history": {"type": "object"}
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
    except Exception as e:
        logger.error(f"Error handling stateless proxy crawler call structure: {e}")
        
    # Default safe fallback block for empty or malformed validation arrays to prevent 400 crashes
    return JSONResponse({"jsonrpc": "2.0", "id": 1, "result": {}})

@app.get("/")
async def handle_root_get():
    """Provide an explicit root index acknowledgement for scanning browsers and uptime watchdogs."""
    return PlainTextResponse("OcuGuard MCP SSE Server Framework Active. Query /sse to establish channel links.")

@app.post("/")
async def handle_root_post(request: Request):
    """Proxy fallback endpoint: Gracefully intercept and respond to stateless scanner payloads."""
    if not request.query_params.get("session_id"):
        return await process_stateless_jsonrpc(request)
    return await mcp_transport.handle_post_message(request.scope, request._receive, request._send)

@app.get("/.well-known/mcp/server-card.json")
async def handle_server_card():
    """Advertise server card endpoints to allow automatic tool mapping discovery across registries."""
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
    # Execute web container on local port 3000 matching deployment blueprints
    uvicorn.run(app, host="0.0.0.0", port=3000)