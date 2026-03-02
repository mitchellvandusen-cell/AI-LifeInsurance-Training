"""
xAI Grok Voice Agent API integration.
Manages WebSocket connections to wss://api.x.ai/v1/realtime for
real-time speech-to-speech training sessions.

Architecture:
  Browser mic audio → Backend WS → xAI Voice API → AI client voice → Backend WS → Browser
  Training engine intercepts transcriptions between turns to update behavioral state.

xAI event reference (differs from OpenAI):
  Audio out:     response.output_audio.delta
  Transcript:    response.output_audio_transcript.delta / .done
  User speech:   conversation.item.input_audio_transcription.completed
  VAD:           input_audio_buffer.speech_started / speech_stopped / committed
  Session:       session.created / session.updated
  Response:      response.created / response.done
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import traceback
from typing import Callable, Optional

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_WS_URL = "wss://api.x.ai/v1/realtime"

# Available voices: Ara (F), Rex (M), Sal (neutral), Eve (F), Leo (M)
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
            logger.error("[%s] XAI_API_KEY not set", self.session_id)
            return False

        logger.info("[%s] Connecting to xAI Voice API (%s)...", self.session_id, XAI_WS_URL)
        try:
            self.xai_ws = await asyncio.wait_for(
                websockets.connect(
                    uri=XAI_WS_URL,
                    additional_headers={"Authorization": f"Bearer {XAI_API_KEY}"},
                    max_size=None,       # No limit on message size for audio
                    ping_interval=15,    # Send ping every 15s to keep connection alive
                    ping_timeout=20,     # Wait 20s for pong (generous to avoid false drops)
                    close_timeout=10,
                ),
                timeout=20,
            )
            self.connected = True
            logger.info("[%s] Connected to xAI Voice API", self.session_id)

            # Configure session
            await self._configure_session()
            return True

        except asyncio.TimeoutError:
            logger.error("[%s] xAI connection timed out (20s)", self.session_id)
            self.connected = False
            return False
        except Exception as e:
            logger.error("[%s] Failed to connect to xAI: %s", self.session_id, e, exc_info=True)
            self.connected = False
            return False

    async def reconnect(self) -> bool:
        """Reconnect to xAI after a connection drop. Retries up to 3 times."""
        for attempt in range(1, 4):
            logger.warning("[%s] Reconnecting to xAI (attempt %d/3)...", self.session_id, attempt)
            self.connected = False
            if self.xai_ws:
                try:
                    await self.xai_ws.close()
                except Exception:
                    pass
                self.xai_ws = None

            await asyncio.sleep(min(attempt * 2, 6))  # 2s, 4s, 6s backoff

            success = await self.connect()
            if success:
                logger.info("[%s] Reconnected to xAI on attempt %d", self.session_id, attempt)
                return True

        logger.error("[%s] Failed to reconnect to xAI after 3 attempts", self.session_id)
        return False

    async def _configure_session(self):
        """Send session.update with training system prompt and voice config."""
        config = {
            "type": "session.update",
            "session": {
                "voice": self.voice,
                "instructions": self.system_prompt,
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "input_audio_transcription": {"model": "whisper-large-v3"},
                "audio": {
                    "input": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                    "output": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                },
            },
        }
        await self.xai_ws.send(json.dumps(config))
        logger.info("[%s] Session configured: voice=%s, rate=%d", self.session_id, self.voice, SAMPLE_RATE)

    async def trigger_greeting(self):
        """Trigger the AI to speak first without waiting for user input.

        Sends a response.create event to the xAI Realtime API, which causes the
        model to generate a response based on its system instructions immediately.
        This is used for training modules where the AI coach should greet the
        student and begin the guided lesson before the student speaks.
        """
        if not self.connected or not self.xai_ws:
            return
        try:
            await self.xai_ws.send(json.dumps({"type": "response.create"}))
            logger.info("[%s] Triggered AI greeting (response.create)", self.session_id)
        except Exception as e:
            logger.error("[%s] Error triggering greeting: %s", self.session_id, e)

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
        try:
            await self.xai_ws.send(json.dumps(update))
            logger.debug("[%s] Instructions updated (turn %d)", self.session_id, self._turn_count)
        except Exception as e:
            logger.error("[%s] Error updating instructions: %s", self.session_id, e)

    async def send_audio(self, audio_base64: str):
        """Forward audio chunk from browser to xAI."""
        if not self.connected or not self.xai_ws:
            return
        msg = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64,
        }
        try:
            await self.xai_ws.send(json.dumps(msg))
        except Exception as e:
            logger.error("[%s] Error sending audio: %s", self.session_id, e)
            self.connected = False

    async def receive_events(self, send_to_browser: Callable):
        """
        Listen for events from xAI and forward audio/transcripts to browser.
        This runs as a long-lived async task for the duration of the session.

        send_to_browser: async function that sends JSON to the browser WebSocket
        """
        if not self.xai_ws:
            logger.error("[%s] No xAI WebSocket in receive_events", self.session_id)
            return

        try:
            async for message in self.xai_ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning("[%s] Non-JSON message from xAI (%d bytes)", self.session_id, len(message))
                    continue

                event_type = data.get("type", "")

                # ── Audio response chunks → browser ──────────────
                # xAI uses response.output_audio.delta (not response.audio.delta)
                if event_type in ("response.output_audio.delta", "response.audio.delta"):
                    delta = data.get("delta", "")
                    if delta:
                        await send_to_browser({
                            "type": "audio",
                            "data": delta,
                        })

                # ── Agent transcript (what the user/agent said) ───
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = data.get("transcript", "")
                    if text:
                        self._current_agent_text = text
                        self._turn_count += 1
                        logger.info("[%s] Agent said (turn %d): %.80s...", self.session_id, self._turn_count, text)
                        await send_to_browser({
                            "type": "transcript",
                            "role": "agent",
                            "text": text,
                            "turn": self._turn_count,
                        })
                        # Callback for training engine
                        if self.on_agent_transcript:
                            try:
                                await self.on_agent_transcript(text, self._turn_count)
                            except Exception as e:
                                logger.error("[%s] Error in on_agent_transcript callback: %s", self.session_id, e, exc_info=True)

                # ── Client transcript delta (streaming) ──────────
                # xAI: response.output_audio_transcript.delta
                elif event_type in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
                    delta = data.get("delta", "")
                    self._current_client_text += delta
                    await send_to_browser({
                        "type": "transcript_delta",
                        "role": "client",
                        "delta": delta,
                    })

                # ── Client transcript complete ───────────────────
                # xAI: response.output_audio_transcript.done
                elif event_type in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
                    text = data.get("transcript", self._current_client_text)
                    if text:
                        logger.info("[%s] Client said (turn %d): %.80s...", self.session_id, self._turn_count, text)
                        await send_to_browser({
                            "type": "transcript",
                            "role": "client",
                            "text": text,
                            "turn": self._turn_count,
                        })
                        if self.on_client_transcript:
                            try:
                                await self.on_client_transcript(text, self._turn_count)
                            except Exception as e:
                                logger.error("[%s] Error in on_client_transcript callback: %s", self.session_id, e, exc_info=True)
                    self._current_client_text = ""

                # ── Response complete ────────────────────────────
                elif event_type == "response.done":
                    logger.debug("[%s] Response complete", self.session_id)
                    await send_to_browser({
                        "type": "status",
                        "status": "listening",
                    })

                # ── Speech detected (user starts talking) ────────
                elif event_type == "input_audio_buffer.speech_started":
                    logger.debug("[%s] Speech detected", self.session_id)
                    await send_to_browser({
                        "type": "status",
                        "status": "recording",
                    })

                # ── Speech stopped (processing) ──────────────────
                elif event_type in ("input_audio_buffer.speech_stopped", "input_audio_buffer.committed"):
                    logger.debug("[%s] Speech ended, processing...", self.session_id)
                    await send_to_browser({
                        "type": "status",
                        "status": "processing",
                    })

                # ── Session lifecycle ─────────────────────────────
                elif event_type == "session.created":
                    logger.info("[%s] Session created by xAI", self.session_id)
                    await send_to_browser({
                        "type": "status",
                        "status": "connected",
                    })

                elif event_type == "session.updated":
                    logger.debug("[%s] Session config updated by xAI", self.session_id)

                # ── Response lifecycle (informational) ────────────
                elif event_type == "response.created":
                    logger.debug("[%s] AI generating response...", self.session_id)
                    await send_to_browser({
                        "type": "status",
                        "status": "responding",
                    })

                elif event_type in ("response.output_item.added", "response.output_item.done"):
                    pass  # Lifecycle event, no action needed

                elif event_type in ("response.output_audio.done", "response.audio.done"):
                    pass  # Audio stream finished, response.done handles status

                # ── Transcription failed ─────────────────────────
                elif event_type == "conversation.item.input_audio_transcription.failed":
                    error = data.get("error", {}).get("message", "Transcription failed")
                    logger.warning("[%s] Transcription failed: %s", self.session_id, error)

                # ── Error handling ───────────────────────────────
                elif event_type == "error":
                    error_data = data.get("error", {})
                    error_msg = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code", "unknown")
                    logger.error("[%s] xAI error [%s]: %s", self.session_id, error_code, error_msg)
                    await send_to_browser({
                        "type": "error",
                        "message": error_msg,
                    })

                # ── Catch-all: log unknown events for debugging ──
                else:
                    preview = json.dumps(data)[:200]
                    logger.debug("[%s] Unhandled event: %s | %s", self.session_id, event_type, preview)

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("[%s] xAI connection closed: code=%s, reason=%s", self.session_id, e.code, e.reason)
            # Attempt auto-reconnect instead of giving up
            try:
                await send_to_browser({
                    "type": "status",
                    "status": "reconnecting",
                })
            except Exception:
                pass
            reconnected = await self.reconnect()
            if reconnected:
                logger.info("[%s] Resuming receive_events after reconnect", self.session_id)
                try:
                    await send_to_browser({
                        "type": "status",
                        "status": "ready",
                    })
                except Exception:
                    pass
                # Recursively resume listening on the new connection
                await self.receive_events(send_to_browser)
                return
            else:
                try:
                    await send_to_browser({
                        "type": "error",
                        "message": "Voice connection lost. Please end the session and try again.",
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error("[%s] Error in receive loop: %s", self.session_id, e, exc_info=True)
        finally:
            self.connected = False
            logger.info("[%s] receive_events loop ended", self.session_id)

    async def disconnect(self):
        """Close the xAI WebSocket connection."""
        self.connected = False
        if self.xai_ws:
            try:
                await self.xai_ws.close()
            except Exception:
                pass
        logger.info("[%s] Disconnected from xAI Voice API", self.session_id)

    def get_duration_seconds(self) -> int:
        return int(time.time() - self.start_time)

    def get_duration_minutes(self) -> int:
        return max(1, int((time.time() - self.start_time) / 60))
