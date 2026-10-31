import asyncio
import mcp
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from app import process_single_frame
from agents.aniseikonia_scaling_agent import AniseikoniaScalingAgent
from agents.metamorphopsia_grid_remapper_agent import MetamorphopsiaGridRemapperAgent
from agents.biofeedback_anxiety_sentinel_agent import BiofeedbackAnxietySentinelAgent

# Initialize the official MCP Server object
server = Server("ocuguard-spatial-middleware")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Expose the OcuGuard tool definition to the LLM context."""
    return [
        types.Tool(
            name="evaluate_wearable_stream",
            description="Stateless edge middleware to optimize visual-to-acoustic metadata layouts, process kinematics, and monitor user-calibrated orientation ergonomics.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "Anonymized hardware node ID."},
                    "input_string": {"type": "string", "description": "OCR document string or voice annotation transcript."},
                    "agent_mode": {
                        "type": "string", 
                        "enum": ["EYE_SENTINEL", "OCUGUARD_CORE", "GAZE_COMPASS", "TABULAR_LAYOUT_SPEECH", "ERGONOMIC_SCHEDULE", "AMBIENT_LUMINANCE", "BE_MY_EYES", "ANISEIKONIA_SCALING", "METAMORPHOPSIA_GRID_REMAPPER", "BIOFEEDBACK_ANXIETY_SENTINEL"]
                    },
                    "pitch": {"type": "number", "description": "Horizontal head tilt angle metric."},
                    "yaw": {"type": "number", "description": "Vertical pan rotation coordinate."}
                },
                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
            }
        ),
        types.Tool(
            name="ocuguard_calibrate_vision",
            description="Generate calibrated UI transformations for perceived size and text warping distortions, returning a safe scale factor and CSS warp matrix.",
            inputSchema={
                "type": "object",
                "properties": {
                    "visual_field_clearance": {"type": "number", "description": "Current visible field clearance ratio."},
                    "perceived_size_delta": {"type": "number", "description": "Measured asymmetric perceived size delta."},
                    "text_wavy_index": {"type": "number", "description": "Degree of text waviness perceived by the user."},
                    "oem_platform": {"type": "string", "description": "Target OEM platform identifier."}
                },
                "required": ["visual_field_clearance", "perceived_size_delta", "text_wavy_index"]
            }
        ),
        types.Tool(
            name="ocuguard_triage_anxiety",
            description="Evaluate vocal stress and panic phrases to deliver empathetic reassurance grounded in 12-to-18 month neuroadaptation milestones.",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_string": {"type": "string", "description": "Captured user transcript or anxiety phrase."},
                    "vocal_stress_score": {"type": "number", "description": "Normalized vocal stress score from biofeedback sensors."},
                    "oem_platform": {"type": "string", "description": "Target OEM platform identifier."}
                },
                "required": ["input_string", "vocal_stress_score"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent]:
    """Execute the core sub-agent matrix loop when an LLM requests it."""
    if name != "evaluate_wearable_stream":
        raise ValueError(f"Unknown tool requested: {name}")
        
    if not arguments:
        raise ValueError("Missing arguments for tool execution")

    try:
        response_payload = process_single_frame(arguments)
        
        return [
            types.TextContent(
                type="text",
                text=f"Status: {response_payload['status']}\nAction Required: {response_payload['action_required']}\nReasoning: {response_payload['reasoning']}"
            )
        ]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing OcuGuard pipeline: {str(e)}")]

async def main():
    import mcp.server.stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_server):
        await server.run(
            read_stream,
            write_server,
            InitializationOptions(
                server_name="ocuguard-spatial-middleware",
                server_version="2.0.0",
                capabilities=types.ServerCapabilities(
                    tools=types.ToolsCapability(listChanged=None)
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())