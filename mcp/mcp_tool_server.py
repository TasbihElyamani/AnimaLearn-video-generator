"""AnimaLearn — MCP Tool Server (5 tools via stdio)"""
import json, sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import Tool, TextContent
from src.tools import *
from src.media.tts_engine import generate_tts
from src.media.animation_generator import generate_animation
from src.media.avatar_generator import generate_avatar_clip
from src.media.video_compositor import compose_video
from src.media.subtitle_burner import burn_subtitles
from src.agents.research_agent import fetch_url_content

server = Server("animalearn-mcp")

@server.list_tools()
async def list_tools():
    return [
        Tool(name="generate_tts", description="Text to speech audio", inputSchema=GenerateTTSInput.model_json_schema()),
        Tool(name="generate_animation", description="AI animated scene clip", inputSchema=GenerateAnimationInput.model_json_schema()),
        Tool(name="generate_avatar_clip", description="Talking avatar video", inputSchema=GenerateAvatarInput.model_json_schema()),
        Tool(name="compose_video", description="Assemble clips into video", inputSchema=ComposeVideoInput.model_json_schema()),
        Tool(name="burn_subtitles", description="Burn subtitles into video", inputSchema=BurnSubtitlesInput.model_json_schema()),
        Tool(name="fetch_reference", description="Fetch URL text content", inputSchema=FetchReferenceInput.model_json_schema()),
    ]

@server.call_tool()
async def call_tool(name, args):
    try:
        if name == "generate_tts":
            r = generate_tts(args["text"], args["output_path"], args.get("voice","en-US-AriaNeural"))
        elif name == "generate_animation":
            r = generate_animation(args["prompt"], args["output_path"], args.get("background_color","#0b3d91"),
                                   args.get("text_overlay",""), args.get("duration_seconds",5))
        elif name == "generate_avatar_clip":
            r = generate_avatar_clip(args["text"], args["output_path"], args.get("avatar_image_url",""))
        elif name == "compose_video":
            r = compose_video(args["clip_paths"], args.get("audio_paths",[]), args["output_path"])
        elif name == "burn_subtitles":
            r = burn_subtitles(args["video_path"], args["subtitles"], args["output_path"])
        elif name == "fetch_reference":
            c = fetch_url_content(args["url"], args.get("max_tokens",15000)*4)
            r = {"text":c.get("text","")[:60000],"source_url":args["url"],"token_count":len(c.get("text","").split()),"title":c.get("title","")}
        else:
            r = {"error": f"Unknown tool: {name}"}
        return [TextContent(type="text", text=json.dumps(r))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error":str(e)}))]

if __name__ == "__main__":
    asyncio.run(run_server(server))
