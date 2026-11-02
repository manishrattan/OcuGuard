import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import ValidationError

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
    name="ocuguard-spatial",
    version="2.0.0"
)

def _tool_catalog() -> List[types.Tool]:
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
                        "description": "Supplied OCR-like text or optional voice-to-text transcript; not a clinical input."
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
                            "ANISEIKONIA_SCALING",
                            "METAMORPHOPSIA_GRID_REMAPPER",
                            "BIOFEEDBACK_ANXIETY_SENTINEL"
                        ]
                    },
                    "pitch": {
                        "type": "number", 
                        "description": "Supplied head pitch angle in degrees."
                    },
                    "roll": {"type": "number", "description": "Supplied roll rotation angle in degrees."},
                    "yaw": {
                        "type": "number", 
                        "description": "Supplied yaw rotation angle in degrees."
                    },
                    "gaze_x": {"type": "number"},
                    "gaze_y": {"type": "number"},
                    "target_x": {"type": "number"},
                    "target_y": {"type": "number"},
                    "blind_x": {"type": "number"},
                    "blind_y": {"type": "number"},
                    "blind_r": {"type": "number"},
                    "confidence": {"type": "number", "description": "Manual synthetic Be My Eyes confidence percentage, from 0 to 100; not computed from an image."},
                    "posture_hold_duration": {"type": "number"},
                    "ambient_light_intensity": {"type": "number"},
                    "contrast_adaptation_mode": {"type": "string", "enum": ["standard", "high_contrast", "low_contrast"]},
                    "visual_field_clearance": {"type": "number"},
                    "perceived_size_delta": {"type": "number"},
                    "text_wavy_index": {"type": "number"},
                    "vocal_stress_score": {"type": "number", "description": "Manually supplied synthetic score from 0 to 1; not inferred from voice."},
                    "multimodal_flags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list strings flagging unique environmental conditions or urgent user contexts (e.g., ['shadow', 'sudden', 'driving_context'])."
                    },
                    "history": {
                        "type": "object",
                        "properties": {
                            "cataract_surgery": {"type": "boolean", "description": "True if the wearer has a history of post-cataract vision recovery restrictions."},
                            "years_since_surgery": {"type": "number", "description": "Synthetic profile duration since surgery."},
                            "age_over_50": {"type": "boolean", "description": "True if the wearer matches demographic criteria for elevated clinical risk windows."},
                            "retinal_disease": {"type": "boolean", "description": "True if pre-existing retinal anomalies are configured within user preferences."},
                            "diabetic_retinopathy": {"type": "boolean", "description": "True if active diabetic microvascular telemetry weights apply."},
                            "previous_detachment": {"type": "boolean", "description": "True if the user profile tracks structural detachment history."},
                            "postural_tracking_baseline": {"type": "number"},
                            "ambient_lighting_sensitivity": {"type": "string"},
                            "workplace_ergonomic_goals": {"type": "array", "items": {"type": "string"}}
                        },
                        "description": "User-configured health history toggles used by the triage engine to multiplicatively calculate warning metrics."
                    }
                },
                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
            }
        ),
        types.Tool(
            name="ocuguard_calibrate_vision",
            description=(
                "Generate an experimental text scaling transform from a supplied perceived-size difference."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "visual_field_clearance": {"type": "number", "description": "Current visible field clearance ratio."},
                    "perceived_size_delta": {"type": "number", "description": "Measured asymmetric perceived size delta."},
                    "oem_platform": {"type": "string", "description": "Target OEM platform identifier."}
                },
                "required": ["perceived_size_delta"]
            }
        ),
        types.Tool(
            name="ocuguard_remap_text_grid",
            description="Generate an experimental grid-warp transform from a supplied text-waviness value.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text_wavy_index": {"type": "number", "description": "Synthetic text-waviness value from 0 to 1."},
                    "oem_platform": {"type": "string", "description": "Target OEM platform identifier."}
                },
                "required": ["text_wavy_index"]
            }
        ),
        types.Tool(
            name="ocuguard_triage_anxiety",
            description=(
                "Evaluate vocal stress and panic phrases to deliver empathetic reassurance grounded in 12-to-18 month neuroadaptation milestones."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "input_string": {"type": "string", "description": "Supplied synthetic transcript text; not analyzed from audio."},
                    "vocal_stress_score": {"type": "number", "description": "Manually supplied synthetic score from 0 to 1; not measured from audio."},
                    "oem_platform": {"type": "string", "description": "Target OEM platform identifier."}
                },
                "required": ["input_string", "vocal_stress_score"]
            }
        )
    ]


@mcp_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    return _tool_catalog()


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: Optional[Dict[str, Any]]
) -> List[types.TextContent]:
    """
    Route tool triggers straight down into the localized sub-agent evaluations.
    """
    if name not in [
        "evaluate_wearable_stream",
        "ocuguard_calibrate_vision",
        "ocuguard_remap_text_grid",
        "ocuguard_triage_anxiety",
    ] or not arguments:
        raise ValueError("Invalid parameters or unrecognized tool identifier passed to execution endpoint.")

    try:
        if name == "evaluate_wearable_stream":
            from app import process_single_frame
            response_payload = process_single_frame(arguments)
        else:
            from app import process_direct_agent_tool
            response_payload = process_direct_agent_tool(name, arguments)

        status = response_payload.get("status", "UNKNOWN")
        action = response_payload.get(
            "action_required",
            response_payload.get("cognitive_reassurance_string", ""),
        )
        reasoning = response_payload.get(
            "reasoning",
            response_payload.get("cognitive_reassurance_string", ""),
        )
        
        output_text = (
            f"Status/Severity Ring: {status}\n"
            f"Action Required: {action}\n"
            f"Orchestration Reasoning: {reasoning}\n"
            f"Result: {json.dumps(response_payload, sort_keys=True)}"
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

# Stateless JSON-RPC fallback for requests that do not have an SSE session.
def _jsonrpc_error(request_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


async def process_stateless_jsonrpc(request: Request) -> Response:
    """
    Safely captures concurrent stateless JSON-RPC discovery payloads from external crawlers.
    """
    rpc_id: Any = None
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return _jsonrpc_error(None, -32700, "Parse error")
            
        body = json.loads(body_bytes)
        if not isinstance(body, dict):
            return _jsonrpc_error(None, -32600, "Invalid Request")

        rpc_id = body.get("id")
        method = body.get("method")
        if body.get("jsonrpc") != "2.0" or not isinstance(method, str) or not method:
            return _jsonrpc_error(rpc_id, -32600, "Invalid Request")
        if "id" not in body:
            return Response(status_code=202)
        
        if method == "tools/list":
            tools = [
                tool.model_dump(by_alias=True, exclude_none=True)
                for tool in _tool_catalog()
            ]
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {"tools": tools},
                }
            )
        elif method == "tools/call":
            params = body.get("params")
            if not isinstance(params, dict):
                return _jsonrpc_error(rpc_id, -32602, "Invalid params")
            tool_name = params.get("name")
            arguments = params.get("arguments")
            supported_tools = {
                "evaluate_wearable_stream",
                "ocuguard_calibrate_vision",
                "ocuguard_remap_text_grid",
                "ocuguard_triage_anxiety",
            }
            if tool_name not in supported_tools or not isinstance(arguments, dict):
                return _jsonrpc_error(rpc_id, -32602, "Invalid params")

            try:
                if tool_name == "evaluate_wearable_stream":
                    from app import process_single_frame

                    data = process_single_frame(arguments)
                else:
                    from app import process_direct_agent_tool

                    data = process_direct_agent_tool(tool_name, arguments)
            except (ValidationError, TypeError, ValueError):
                return _jsonrpc_error(rpc_id, -32602, "Invalid tool arguments")
            except Exception:
                logger.exception("Stateless MCP tool execution failed.")
                return _jsonrpc_error(rpc_id, -32603, "Tool execution failed")

            summary = (
                f"Status: {data.get('status', 'UNKNOWN')}\n"
                f"Action Required: {data.get('action_required', data.get('cognitive_reassurance_string', ''))}\n"
                f"Reasoning: {data.get('reasoning', data.get('cognitive_reassurance_string', ''))}"
            )
            return JSONResponse(
                {
                    "jsonrpc": "2.0",
                    "id": rpc_id,
                    "result": {
                        "content": [{"type": "text", "text": summary}],
                        "structuredContent": {"data": data},
                        "isError": False,
                    },
                }
            )
            
        elif method == "resources/list":
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"resources": []}})
        elif method == "prompts/list":
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"prompts": []}})
        elif method == "triggers/list":
            return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": {"triggers": [], "events": []}})
        elif method == "initialize":
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
            
        return _jsonrpc_error(rpc_id, -32601, "Method not found")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _jsonrpc_error(None, -32700, "Parse error")

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