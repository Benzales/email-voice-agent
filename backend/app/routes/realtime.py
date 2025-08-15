import os
import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from ..mcp_bootstrap import get_gmail_agent
from ..utils.gmail_helpers import parse_gmail_search_results


router = APIRouter()


SYSTEM_INSTRUCTION = (
    "You are a voice-driven Gmail assistant with full access to the Gmail API through tools.\n"
    "PRIMARY BEHAVIOR - Single Email Focus:\n"
    "- You will be provided with information for ONE email at a time\n"
    "- Announce ONLY: sender and subject\n"
    "- After reading the email, ask what the user would like to do\n"
    "- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next\n"
    "- CRITICAL: After you execute ANY action on an email (via tools), immediately call complete_current_email.\n"
    "- If the user says 'skip', 'next', or 'continue', immediately call complete_current_email.\n"
    "- Do NOT ask what to do next after completing an action - just call complete_current_email.\n"
    "Important: Archiving means gmail_modify_email with removeLabelIds: [\"INBOX\"].\n"
)


def build_gemini_tools_from_mcp(tools_result) -> List[types.Tool]:
    tools: List[types.Tool] = []
    for tool in getattr(tools_result, 'tools', []) or []:
        parameters: Dict[str, Any] = {}
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            parameters = {k: v for k, v in tool.inputSchema.items() if k not in ["additionalProperties", "$schema"]}
        tools.append(types.Tool(function_declarations=[{
            "name": getattr(tool, 'name', ''),
            "description": getattr(tool, 'description', ''),
            "parameters": parameters,
        }]))
    # Custom complete_current_email tool
    tools.append(types.Tool(function_declarations=[{
        "name": "complete_current_email",
        "description": "Complete processing of the current email and move to the next one.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }]))
    return tools


@router.websocket("/realtime")
async def realtime(websocket: WebSocket):
    await websocket.accept()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        await websocket.send_text('{"type":"status","message":"Server missing GEMINI_API_KEY"}')
        await websocket.close()
        return

    model = os.getenv("GEMINI_REALTIME_MODEL", "gemini-live-2.5-flash-preview")
    debug_dump = os.getenv("DEBUG_AUDIO_DUMP", "0") == "1"

    gmail_agent = get_gmail_agent()

    # Fetch inbox
    try:
        search_result = await gmail_agent.call_tool(
            "gmail_search_emails", arguments={"query": "in:inbox", "maxResults": 50}
        )
        emails = parse_gmail_search_results(search_result)
    except Exception as e:
        await websocket.send_text(f'{{"type":"status","message":"Failed to load inbox: {str(e)}"}}')
        emails = []

    if not emails:
        await websocket.send_text('{"type":"status","message":"No emails found in inbox"}')
        await websocket.close()
        return

    current_index = 0

    # Build tools
    try:
        tools_result = await gmail_agent.list_tools()
        gemini_tools = build_gemini_tools_from_mcp(tools_result)
    except Exception as e:
        await websocket.send_text(f'{{"type":"status","message":"Failed to list tools: {str(e)}"}}')
        await websocket.close()
        return

    client = genai.Client(api_key=api_key)
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,
        "system_instruction": [SYSTEM_INSTRUCTION],
    }

    def _extract_wav_pcm(payload: bytes):
        # Detect simple WAV header (RIFF....WAVE)
        try:
            if len(payload) >= 44 and payload[0:4] == b'RIFF' and payload[8:12] == b'WAVE':
                # fmt chunk starts at 12, but may be extended; scan for 'fmt ' and 'data'
                idx = 12
                sample_rate = 24000
                data_start = None
                data_len = None
                while idx + 8 <= len(payload):
                    chunk_id = payload[idx:idx+4]
                    chunk_size = int.from_bytes(payload[idx+4:idx+8], 'little', signed=False)
                    idx += 8
                    if chunk_id == b'fmt ':
                        # audio format (2 bytes), num channels (2), sample rate (4), skip extended
                        if idx + 16 <= len(payload):
                            sample_rate = int.from_bytes(payload[idx+4:idx+8], 'little', signed=False)
                    elif chunk_id == b'data':
                        data_start = idx
                        data_len = min(chunk_size, len(payload) - idx)
                        break
                    idx += chunk_size
                if data_start is not None and data_len is not None:
                    return payload[data_start:data_start+data_len], sample_rate
        except Exception:
            pass
        return payload, 24000

    def _float32_to_pcm16_le(chunk: bytes) -> bytes:
        try:
            if len(chunk) % 4 != 0:
                return b""
            import struct
            out = bytearray(len(chunk) // 2)
            o = 0
            for (f,) in struct.iter_unpack('<f', chunk):
                # clamp and scale
                if f > 1.0:
                    f = 1.0
                elif f < -1.0:
                    f = -1.0
                v = int(f * 32767.0) if f >= 0 else int(f * 32768.0)
                struct.pack_into('<h', out, o, v)
                o += 2
            return bytes(out)
        except Exception:
            return b""

    def _maybe_b64_decode(chunk: bytes) -> tuple[bytes, bool]:
        try:
            import base64
            # Quick heuristic: chunk is ASCII base64 (no whitespace) and length multiple of 4
            if len(chunk) % 4 == 0 and all(c in b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in chunk[:64]):
                dec = base64.b64decode(chunk, validate=True)
                if dec:
                    return dec, True
        except Exception:
            pass
        return chunk, False

    def _decode_to_pcm16(chunk: bytes) -> tuple[bytes, int, str]:
        """Decode an arbitrary audio chunk to PCM16 mono; try base64->decode, float32, pydub, WAV strip."""
        # Try base64 first
        bchunk, was_b64 = _maybe_b64_decode(chunk)
        how_prefix = 'b64>' if was_b64 else ''
        # Try float32 -> PCM16
        f32_pcm = _float32_to_pcm16_le(bchunk)
        if f32_pcm:
            return f32_pcm, 24000, how_prefix + 'float32->pcm16'
        try:
            from pydub import AudioSegment
            from io import BytesIO
            seg = AudioSegment.from_file(BytesIO(bchunk))
            if seg.frame_rate != 24000:
                seg = seg.set_frame_rate(24000)
            if seg.channels != 1:
                seg = seg.set_channels(1)
            if seg.sample_width != 2:
                seg = seg.set_sample_width(2)
            return seg.raw_data, 24000, how_prefix + 'pydub'
        except Exception:
            pcm, sr = _extract_wav_pcm(bchunk)
            return pcm, sr or 24000, how_prefix + 'wav-strip'

    async def forward_ws_audio_to_gemini(session):
        rx_bytes = 0
        try:
            while True:
                message = await websocket.receive()
                if message.get("type") == "websocket.disconnect":
                    break
                if "bytes" in message and message["bytes"]:
                    try:
                        rx_bytes += len(message["bytes"]) or 0
                        await session.send_realtime_input(
                            audio=types.Blob(data=message["bytes"], mime_type="audio/pcm;rate=16000")
                        )
                        if rx_bytes < 1_000_000 and rx_bytes % 65536 < 4096:
                            await websocket.send_text(f'{{"type":"status","message":"rx_audio_bytes={rx_bytes}"}}')
                    except Exception:
                        pass
                elif "text" in message and message["text"]:
                    txt = message["text"].strip()
                    if txt == "stop":
                        break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def send_initial_prompt(session, idx: int):
        e = emails[idx]
        sender = e.get("from", "Unknown")
        subject = e.get("subject", "No subject")
        email_id = e.get("id", "")
        text = (
            f"Please read me this email and ask what I'd like to do with it. "
            f"The email is: From {sender} - {subject} [Current email ID: {email_id}]."
        )
        await session.send_realtime_input(text=text)

    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            await websocket.send_text('{"type":"ready"}')

            forward_task = asyncio.create_task(forward_ws_audio_to_gemini(session))
            await send_initial_prompt(session, current_index)

            down_sample_rate = 24000
            dump_count = 0
            async for response in session.receive():
                try:
                    if response.data is not None:
                        try:
                            chunk = bytes(response.data)
                            pcm, sr, how = _decode_to_pcm16(chunk)
                            down_sample_rate = sr or down_sample_rate
                            if debug_dump and dump_count < 3:
                                try:
                                    base = f"/tmp/gemini_down_{dump_count}"
                                    with open(base + ".raw", "wb") as f:
                                        f.write(chunk)
                                    with open(base + ".pcm", "wb") as f:
                                        f.write(pcm)
                                    hex_preview = chunk[:32].hex()
                                    await websocket.send_text(
                                        f'{{"type":"status","message":"dumped:{base} hex:{hex_preview}"}}'
                                    )
                                except Exception:
                                    pass
                                dump_count += 1
                            await websocket.send_text(
                                f'{{"type":"status","message":"down_audio_bytes={len(pcm)},sr={down_sample_rate},fmt={how}"}}'
                            )
                            await websocket.send_bytes(pcm)
                        except Exception:
                            try:
                                await websocket.send_text('{"type":"status","message":"send_bytes_failed"}')
                            except Exception:
                                pass
                    elif response.tool_call:
                        function_responses = []
                        advance_to_next = False
                        for fc in response.tool_call.function_calls:
                            if fc.name == "complete_current_email":
                                if current_index < len(emails) - 1:
                                    current_index += 1
                                    function_responses.append(types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": "Moving to next email..."}
                                    ))
                                    advance_to_next = True
                                else:
                                    function_responses.append(types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": "You've reached the end of your inbox."}
                                    ))
                                    advance_to_next = False
                                    await websocket.send_text('{"type":"complete"}')
                            else:
                                try:
                                    result = await gmail_agent.call_tool(fc.name, arguments=dict(fc.args))
                                    response_content: Dict[str, Any] = {}
                                    if hasattr(result, 'content') and result.content:
                                        text_parts = []
                                        for item in result.content:
                                            if hasattr(item, 'text'):
                                                text_parts.append(item.text)
                                        response_content["result"] = "\n".join(text_parts)
                                    else:
                                        response_content["result"] = "Tool executed successfully"
                                    function_responses.append(types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response=response_content
                                    ))
                                except Exception as tool_error:
                                    function_responses.append(types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.id,
                                        response={"result": f"Error: {str(tool_error)}"}
                                    ))

                        if function_responses:
                            await session.send_tool_response(function_responses=function_responses)
                        if advance_to_next:
                            await send_initial_prompt(session, current_index)
                except Exception:
                    pass

            try:
                await asyncio.wait_for(forward_task, timeout=1.0)
            except Exception:
                pass

    except Exception as e:
        try:
            await websocket.send_text(f'{{"type":"status","message":"Realtime session error: {str(e)}"}}')
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


