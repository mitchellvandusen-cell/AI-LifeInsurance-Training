"""
xAI Grok Voice Agent API integration.
Manages WebSocket connections to wss://api.x.ai/v1/realtime for
real-time speech-to-speech training sessions.

Architecture:
  Browser mic audio → Backend WS → xAI Voice API → AI client voice → Backend WS → Browser
  Training engine intercepts transcriptions between turns to update behavioral state.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Callable, Optional

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_WS_URL = "wss://api.x.ai/v1/realtime"

# Available voices: Ara, Rex, Sal, Eve, Leo
DEFAULT_VOICE = "Sal"
SAMPLE_RATE = 24000
AUDIO_FORMAT = "audio/pcm"


class VoiceSession:
    """
    Manages a single voice training session with xAI.
    Bridges browser WebSocket ↔ xAI WebSocket, intercepting
    transcriptions to feed the training engine.
    """

    def __init__(
        self,
        session_id: str,
        system_prompt: str,
        voice: str = DEFAULT_VOICE,
        on_agent_transcript: Optional[Callable] = None,
        on_client_transcript: Optional[Callable] = None,
        on_state_update: Optional[Callable] = None,
    ):
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.voice = voice
        self.xai_ws: Optional[ClientConnection] = None
        self.connected = False
        self.start_time = time.time()

        # Callbacks
        self.on_agent_transcript = on_agent_transcript
        self.on_client_transcript = on_client_transcript
        self.on_state_update = on_state_update

        # Transcript accumulation
        self._current_agent_text = ""
        self._current_client_text = ""
        self._turn_count = 0

    async def connect(self) -> bool:
        """Establish WebSocket connection to xAI Voice Agent API."""
        if not XAI_API_KEY:
            print(f"[VOICE][{self.session_id}] ERROR: XAI_API_KEY not set")
            return False

        print(f"[VOICE][{self.session_id}] Connecting to xAI Voice API...")
        try:
            self.xai_ws = await asyncio.wait_for(
                websockets.connect(
                    uri=XAI_WS_URL,
                    additional_headers={"Authorization": f"Bearer {XAI_API_KEY}"},
                ),
                timeout=10,
            )
            self.connected = True
            print(f"[VOICE][{self.session_id}] Connected to xAI Voice API")

            # Configure session
            await self._configure_session()
            return True

        except asyncio.TimeoutError:
            print(f"[VOICE][{self.session_id}] ERROR: xAI connection timed out (10s)")
            self.connected = False
            return False
        except Exception as e:
            print(f"[VOICE][{self.session_id}] ERROR: Failed to connect to xAI: {e}")
            self.connected = False
            return False

    async def _configure_session(self):
        """Send session.update with training system prompt and voice config."""
        config = {
            "type": "session.update",
            "session": {
                "voice": self.voice,
                "instructions": self.system_prompt,
                "turn_detection": {"type": "server_vad"},
                "input_audio_transcription": {"model": "whisper-1"},
                "audio": {
                    "input": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                    "output": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                },
            },
        }
        await self.xai_ws.send(json.dumps(config))
        logger.info(f"[{self.session_id}] Session configured: voice={self.voice}")

    async def update_instructions(self, new_prompt: str):
        """Update the system prompt mid-session (after state changes)."""
        if not self.connected or not self.xai_ws:
            return
        self.system_prompt = new_prompt
        update = {
            "type": "session.update",
            "session": {
                "instructions": new_prompt,
            },
        }
        await self.xai_ws.send(json.dumps(update))
        logger.debug(f"[{self.session_id}] Instructions updated (turn {self._turn_count})")

    async def send_audio(self, audio_base64: str):
        """Forward audio chunk from browser to xAI."""
        if not self.connected or not self.xai_ws:
            return
        msg = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64,
        }
        await self.xai_ws.send(json.dumps(msg))

    async def receive_events(self, send_to_browser: Callable):
        """
        Listen for events from xAI and forward audio/transcripts to browser.
        This runs as a long-lived async task for the duration of the session.

        send_to_browser: async function that sends JSON to the browser WebSocket
        """
        if not self.xai_ws:
            return

        try:
            async for message in self.xai_ws:
                data = json.loads(message)
                event_type = data.get("type", "")

                # ── Audio response chunks → browser ──────────────
                if event_type == "response.audio.delta":
                    await send_to_browser({
                        "type": "audio",
                        "data": data.get("delta", ""),
                    })

                # ── Agent transcript (what the agent said) ───────
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = data.get("transcript", "")
                    if text:
                        self._current_agent_text = text
                        self._turn_count += 1
                        await send_to_browser({
                            "type": "transcript",
                            "role": "agent",
                            "text": text,
                            "turn": self._turn_count,
                        })
                        # Callback for training engine
                        if self.on_agent_transcript:
                            await self.on_agent_transcript(text, self._turn_count)

                # ── Client transcript delta (streaming) ──────────
                elif event_type == "response.audio_transcript.delta":
                    delta = data.get("delta", "")
                    self._current_client_text += delta
                    await send_to_browser({
                        "type": "transcript_delta",
                        "role": "client",
                        "delta": delta,
                    })

                # ── Client transcript complete ───────────────────
                elif event_type == "response.audio_transcript.done":
                    text = data.get("transcript", self._current_client_text)
                    if text:
                        await send_to_browser({
                            "type": "transcript",
                            "role": "client",
                            "text": text,
                            "turn": self._turn_count,
                        })
                        if self.on_client_transcript:
                            await self.on_client_transcript(text, self._turn_count)
                    self._current_client_text = ""

                # ── Response complete ────────────────────────────
                elif event_type == "response.done":
                    await send_to_browser({
                        "type": "status",
                        "status": "listening",
                    })

                # ── Speech detected ──────────────────────────────
                elif event_type == "input_audio_buffer.speech_started":
                    await send_to_browser({
                        "type": "status",
                        "status": "recording",
                    })

                # ── Speech stopped (processing) ──────────────────
                elif event_type == "input_audio_buffer.speech_stopped":
                    await send_to_browser({
                        "type": "status",
                        "status": "processing",
                    })

                # ── Session created ──────────────────────────────
                elif event_type == "session.created":
                    await send_to_browser({
                        "type": "status",
                        "status": "connected",
                    })

                # ── Error handling ───────────────────────────────
                elif event_type == "error":
                    error_msg = data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"[{self.session_id}] xAI error: {error_msg}")
                    await send_to_browser({
                        "type": "error",
                        "message": error_msg,
                    })

        except websockets.exceptions.ConnectionClosed:
            print(f"[VOICE][{self.session_id}] xAI connection closed")
        except Exception as e:
            print(f"[VOICE][{self.session_id}] Error in receive loop: {e}")
        finally:
            self.connected = False

    async def disconnect(self):
        """Close the xAI WebSocket connection."""
        self.connected = False
        if self.xai_ws:
            try:
                await self.xai_ws.close()
            except Exception:
                pass
        print(f"[VOICE][{self.session_id}] Disconnected from xAI Voice API")

    def get_duration_seconds(self) -> int:
        return int(time.time() - self.start_time)

    def get_duration_minutes(self) -> int:
        return max(1, int((time.time() - self.start_time) / 60))
