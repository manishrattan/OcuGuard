import asyncio
import json
import mcp
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
from app import process_direct_agent_tool, process_single_frame
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
                    "input_string": {"type": "string", "description": "Supplied OCR-like text or optional voice-to-text transcript; not a clinical input."},
                    "agent_mode": {
                        "type": "string", 
                        "enum": ["EYE_SENTINEL", "OCUGUARD_CORE", "GAZE_COMPASS", "TABULAR_LAYOUT_SPEECH", "ERGONOMIC_SCHEDULE", "AMBIENT_LUMINANCE", "BE_MY_EYES", "ANISEIKONIA_SCALING", "METAMORPHOPSIA_GRID_REMAPPER", "BIOFEEDBACK_ANXIETY_SENTINEL"]
                    },
                    "pitch": {"type": "number", "description": "Supplied head pitch angle in degrees."},
                    "roll": {"type": "number", "description": "Roll rotation metric."},
                    "yaw": {"type": "number", "description": "Supplied yaw rotation angle in degrees."},
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
                        "description": "Optional synthetic environment/context flags."
                    },
                    "history": {
                        "type": "object",
                        "properties": {
                            "cataract_surgery": {"type": "boolean"},
                            "years_since_surgery": {"type": "number"},
                            "diabetic_retinopathy": {"type": "boolean"},
                            "retinal_disease": {"type": "boolean"},
                            "previous_detachment": {"type": "boolean"},
                            "age_over_50": {"type": "boolean"},
                            "postural_tracking_baseline": {"type": "number"},
                            "ambient_lighting_sensitivity": {"type": "string"},
                            "workplace_ergonomic_goals": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "description": "Optional synthetic profile flags and preferences."
                    }
                },
                "required": ["user_id", "input_string", "agent_mode", "pitch", "yaw"]
            }
        ),
        types.Tool(
            name="ocuguard_calibrate_vision",
            description="Generate an experimental text scaling transform from a supplied perceived-size difference.",
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
            description="Evaluate vocal stress and panic phrases to deliver empathetic reassurance grounded in 12-to-18 month neuroadaptation milestones.",
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

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent]:
    """Execute the core sub-agent matrix loop when an LLM requests it."""
    if name not in {
        "evaluate_wearable_stream",
        "ocuguard_calibrate_vision",
        "ocuguard_remap_text_grid",
        "ocuguard_triage_anxiety",
    }:
        raise ValueError(f"Unknown tool requested: {name}")
        
    if not arguments:
        raise ValueError("Missing arguments for tool execution")

    try:
        if name == "evaluate_wearable_stream":
            response_payload = process_single_frame(arguments)
        else:
            response_payload = process_direct_agent_tool(name, arguments)
        
        return [
            types.TextContent(
                type="text",
                text=(
                    f"Status: {response_payload.get('status', 'UNKNOWN')}\n"
                    f"Action Required: {response_payload.get('action_required', response_payload.get('cognitive_reassurance_string', ''))}\n"
                    f"Reasoning: {response_payload.get('reasoning', response_payload.get('cognitive_reassurance_string', ''))}\n"
                    f"Result: {json.dumps(response_payload, sort_keys=True)}"
                )
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