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

# 1. Instantiate the Server object cleanly with strictly supported SDK constructor keys
mcp_server = Server(
    name="ocuguard-spatial-middleware",
    version="2.0.0"
)

@mcp_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """
    Expose the OcuGuard multi-agent pipeline inputs to external LLMs with strict semantic descriptions.
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
                        "description": "The anonymized unique hardware node token or tracking UUID assigned to the consumer eyewear device."
                    },
                    "input_string": {
                        "type": "string", 
                        "description": "The textual payload to analyze, supporting raw OCR transcriptions, document text, or verbal symptom phrases."
                    },
                    "agent_mode": {
                        "type": "string", 
                        "description": "The specific operational sub-agent plugin designed to process the structural context of the telemetry frame.",
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
                        "description": "The real-time horizontal X-axis tracking metric captured from the eyewear's on-board inertial measurement unit (IMU)."
                    },
                    "yaw": {
                        "type": "number", 
                        "description": "The real-time vertical Y-axis rotational tracking metric captured from the eyewear's coordinate spatial matrix."
                    },
                    "multimodal_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list strings flagging unique environmental conditions or urgent user contexts (e.g., ['shadow', 'sudden', 'driving_context'])."
                    },
                    "history": {
                        "type": "object",
                        "properties": {
                            "cataract_surgery": {"type": "boolean", "description": "True if the wearer has a history of post-cataract vision recovery restrictions."},
                            "age_over_50": {"type": "boolean", "description": "True if the wearer matches demographic criteria for elevated clinical risk windows."},
                            "retinal_disease": {"type": "boolean", "description": "True if pre-existing retinal anomalies are configured within user preferences."},
                            "diabetic_retinopathy": {"type": "boolean", "description": "True if active diabetic microvascular telemetry weights apply."},
                            "previous_detachment": {"type": "boolean", "description": "True if the user profile tracks structural history of structural detachment paths."}
                        },
                        "description": "User-configured health history toggles used by the triage engine to multiplicatively calculate warning metrics."
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
    """
    if name != "evaluate_wearable_stream" or not arguments:
        raise ValueError("Invalid parameters or unrecognized tool identifier passed to execution endpoint.")

    try:
        from app import process_single_frame
        response_payload = process_single_frame(arguments)
        
        status = response_payload.get("status", response_payload.get("data", {}).get("status", "URGENT"))
        action = response_payload.get("action_required", response_payload.get("data", {}).get("action_required", ""))
        reasoning = response_payload.get("reasoning", response_payload.get("data", {}).get("reasoning", ""))
        
        output_text = (
            f"Status/Severity Ring: {status}\n"
            f"Action Required: {action}\n"
            f"Orchestration Reasoning: {reasoning}"
        )
        
        # Explicit constructor formatting clears Pylance rules smoothly
        return [
            types.TextContent(
                type="text", 
                text=output_text,
                annotations=types.Annotations(
                    audience=["user", "assistant"],
                    priority=1.0
                )
            )
        ]
    except Exception as e:
        logger.error(f"Execution error within underlying agent pipeline: {str(e)}")
        return [types.TextContent(type="text", text=f"OcuGuard Pipeline Exception: {str(e)}")]

# 2. Initialize the core transport layer with the relative messages endpoint path
mcp_transport = SseServerTransport("/messages")
app = FastAPI(title="OcuGuard Spatial Middleware Backend")

# Shared mock router engine to bypass the lack of session_id during validation crawls
async def process_stateless_jsonrpc(request: Request) -> JSONResponse:
    """
    Safely captures concurrent stateless JSON-RPC discovery payloads from external crawlers.
    """
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}})
            
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
                                    "user_id": {"type": "string", "description": "The anonymized tracking UUID."},
                                    "input_string": {"type": "string", "description": "The text payload to analyze."},
                                    "agent_mode": {"type": "string", "description": "The specific sub-agent plugin mode."},
                                    "pitch": {"type": "number", "description": "Horizontal X-axis tracking metric."},
                                    "yaw": {"type": "number", "description": "Vertical Y-axis tracking metric."},
                                    "multimodal_flags": {"type": "array", "items": {"type": "string"}, "description": "Optional background triggers."},
                                    "history": {"type": "object", "description": "User risk preferences."}
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
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"triggers": [], "events": []}})
        elif "initialize" in method:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "ocuguard-spatial-middleware", 
                        "version": "2.0.0",
                        "description": "Stateless adaptive middleware optimizing ergonomic telemetry and spatial computing pipelines for smart eyewear.",
                        "homepage": "https://github.com/manishrattan/ocuguard-spatial",
                        "icon": "https://raw.githubusercontent.com/manishrattan/ocuguard-spatial/main/icon.png"
                    }
                }
            })
            
        return JSONResponse({
            "jsonrpc": "2.0", 
            "id": rpc_id, 
            "result": {"tools": [], "resources": [], "prompts": [], "triggers": [], "events": []}
        })
    except Exception as e:
        logger.error(f"Error handling stateless proxy crawler call structure: {e}")
        
    return JSONResponse({
        "jsonrpc": "2.0", 
        "id": 1, 
        "result": {"tools": [], "resources": [], "prompts": [], "triggers": [], "events": []}
    })

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
    """
    Advertise enriched metadata server card definitions matching strict Smithery schema rules.
    This precise layout satisfies all Server Metadata validation checkpoints.
    """
    return JSONResponse({
        "mcp_version": "1.0.0",
        "name": "ocuguard-spatial-middleware",
        "version": "2.0.0",
        "description": "Stateless adaptive middleware optimizing ergonomic telemetry and spatial computing pipelines for smart eyewear.",
        "homepage": "https://github.com/manishrattan/ocuguard-spatial",
        "icon": "https://raw.githubusercontent.com/manishrattan/ocuguard-spatial/main/icon.png",
        "app": {
            "name": "ocuguard-spatial-middleware",
            "version": "2.0.0",
            "description": "Stateless adaptive middleware optimizing ergonomic telemetry and spatial computing pipelines for smart eyewear.",
            "homepage": "https://github.com/manishrattan/ocuguard-spatial",
            "icon": "https://raw.githubusercontent.com/manishrattan/ocuguard-spatial/main/icon.png"
        },
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