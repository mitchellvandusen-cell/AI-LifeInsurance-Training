"""
xAI Grok Voice Agent API integration.
Manages WebSocket connections to wss://api.x.ai/v1/realtime for
real-time speech-to-speech training sessions.

Architecture:
  Browser mic audio → Backend WS → xAI Voice API → AI client voice → Backend WS → Browser
  Training engine intercepts transcriptions between turns to update behavioral state.

The VoiceSession runs its own receive loop as an independent background task.
Browser connections come and go (reconnects), but the xAI session persists.
The browser callback is swappable — reconnects just swap where events go.

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

    The receive loop runs as an independent background task.
    Browser connections are decoupled — the send_to_browser callback
    can be swapped at any time (e.g. on browser reconnect) without
    disrupting the xAI connection.
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

        # Swappable browser callback — set/swap via set_browser_callback()
        self._send_to_browser: Optional[Callable] = None

        # Background receive task
        self._receive_task: Optional[asyncio.Task] = None
        self._keepalive_task: Optional[asyncio.Task] = None

        # Transcript accumulation
        self._current_agent_text = ""
        self._current_client_text = ""
        self._turn_count = 0

    def set_browser_callback(self, callback: Optional[Callable]):
        """Set or swap the browser send callback. Thread-safe for asyncio."""
        self._send_to_browser = callback

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
                    max_size=None,        # No limit on message size for audio
                    ping_interval=None,   # DISABLE library pings — they can clash with xAI
                    ping_timeout=None,    # We handle keepalive ourselves
                    close_timeout=10,
                ),
                timeout=20,
            )
            self.connected = True
            logger.info("[%s] Connected to xAI Voice API", self.session_id)

            # Configure session
            await self._configure_session()

            # Start the independent receive loop and keepalive
            self._start_background_tasks()

            return True

        except asyncio.TimeoutError:
            logger.error("[%s] xAI connection timed out (20s)", self.session_id)
            self.connected = False
            return False
        except Exception as e:
            logger.error("[%s] Failed to connect to xAI: %s", self.session_id, e, exc_info=True)
            self.connected = False
            return False

    def _start_background_tasks(self):
        """Start the receive loop and keepalive as independent background tasks."""
        if self._receive_task and not self._receive_task.done():
            return  # Already running
        self._receive_task = asyncio.create_task(
            self._receive_loop(), name=f"xai_receive_{self.session_id}"
        )
        self._keepalive_task = asyncio.create_task(
            self._xai_keepalive(), name=f"xai_keepalive_{self.session_id}"
        )

    async def _xai_keepalive(self):
        """Send periodic input_audio_buffer.commit to keep xAI connection alive.

        The xAI Realtime API may close idle connections. We send a lightweight
        no-op event periodically to signal the connection is still active.
        We also do a WebSocket-level ping/pong manually.
        """
        try:
            while self.connected and self.xai_ws:
                await asyncio.sleep(15)
                if not self.connected or not self.xai_ws:
                    break
                try:
                    # Send a WebSocket ping manually
                    pong = await self.xai_ws.ping()
                    await asyncio.wait_for(pong, timeout=10)
                    logger.debug("[%s] xAI keepalive pong received", self.session_id)
                except asyncio.TimeoutError:
                    logger.warning("[%s] xAI keepalive pong timed out — connection may be dead", self.session_id)
                except Exception as e:
                    logger.warning("[%s] xAI keepalive error: %s", self.session_id, e)
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("[%s] xAI keepalive loop error: %s", self.session_id, e)

    async def reconnect(self) -> bool:
        """Reconnect to xAI after a connection drop. Retries up to 5 times."""
        for attempt in range(1, 6):
            logger.warning("[%s] Reconnecting to xAI (attempt %d/5)...", self.session_id, attempt)
            self.connected = False
            if self._keepalive_task and not self._keepalive_task.done():
                self._keepalive_task.cancel()
            if self.xai_ws:
                try:
                    await self.xai_ws.close()
                except Exception:
                    pass
                self.xai_ws = None

            await asyncio.sleep(min(attempt * 2, 8))  # 2s, 4s, 6s, 8s, 8s backoff

            success = await self.connect()
            if success:
                logger.info("[%s] Reconnected to xAI on attempt %d", self.session_id, attempt)
                return True

        logger.error("[%s] Failed to reconnect to xAI after 5 attempts", self.session_id)
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
                    "prefix_padding_ms": 500,
                    "silence_duration_ms": 1200,
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
        """Trigger the AI to speak first without waiting for user input."""
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

    async def _send_browser(self, msg: dict):
        """Send a message to the browser via the current callback (if any)."""
        cb = self._send_to_browser
        if cb:
            try:
                await cb(msg)
            except Exception:
                pass  # Browser might be disconnected — that's OK

    async def _receive_loop(self):
        """
        Independent long-lived loop that receives events from xAI.
        Forwards to browser via the swappable callback.
        This task runs for the entire session lifetime, surviving browser
        reconnects.
        """
        if not self.xai_ws:
            logger.error("[%s] No xAI WebSocket in _receive_loop", self.session_id)
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
                if event_type in ("response.output_audio.delta", "response.audio.delta"):
                    delta = data.get("delta", "")
                    if delta:
                        await self._send_browser({"type": "audio", "data": delta})

                # ── Agent transcript (what the user said) ─────────
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = data.get("transcript", "")
                    if text:
                        self._current_agent_text = text
                        self._turn_count += 1
                        logger.info("[%s] Agent said (turn %d): %.80s...", self.session_id, self._turn_count, text)
                        await self._send_browser({
                            "type": "transcript", "role": "agent",
                            "text": text, "turn": self._turn_count,
                        })
                        if self.on_agent_transcript:
                            try:
                                await self.on_agent_transcript(text, self._turn_count)
                            except Exception as e:
                                logger.error("[%s] on_agent_transcript error: %s", self.session_id, e, exc_info=True)

                # ── Client transcript delta (streaming) ──────────
                elif event_type in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
                    delta = data.get("delta", "")
                    self._current_client_text += delta
                    await self._send_browser({"type": "transcript_delta", "role": "client", "delta": delta})

                # ── Client transcript complete ───────────────────
                elif event_type in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
                    text = data.get("transcript", self._current_client_text)
                    if text:
                        logger.info("[%s] Client said (turn %d): %.80s...", self.session_id, self._turn_count, text)
                        await self._send_browser({
                            "type": "transcript", "role": "client",
                            "text": text, "turn": self._turn_count,
                        })
                        if self.on_client_transcript:
                            try:
                                await self.on_client_transcript(text, self._turn_count)
                            except Exception as e:
                                logger.error("[%s] on_client_transcript error: %s", self.session_id, e, exc_info=True)
                    self._current_client_text = ""

                # ── Response complete ────────────────────────────
                elif event_type == "response.done":
                    logger.debug("[%s] Response complete", self.session_id)
                    await self._send_browser({"type": "status", "status": "listening"})

                # ── Speech detected (user starts talking) ────────
                elif event_type == "input_audio_buffer.speech_started":
                    logger.debug("[%s] Speech detected", self.session_id)
                    await self._send_browser({"type": "status", "status": "recording"})

                # ── Speech stopped (processing) ──────────────────
                elif event_type in ("input_audio_buffer.speech_stopped", "input_audio_buffer.committed"):
                    logger.debug("[%s] Speech ended, processing...", self.session_id)
                    await self._send_browser({"type": "status", "status": "processing"})

                # ── Session lifecycle ─────────────────────────────
                elif event_type == "session.created":
                    logger.info("[%s] xAI session created", self.session_id)
                    await self._send_browser({"type": "status", "status": "connected"})

                elif event_type == "session.updated":
                    logger.debug("[%s] Session config updated by xAI", self.session_id)

                elif event_type == "response.created":
                    logger.debug("[%s] AI generating response...", self.session_id)
                    await self._send_browser({"type": "status", "status": "responding"})

                elif event_type in ("response.output_item.added", "response.output_item.done",
                                    "response.output_audio.done", "response.audio.done"):
                    pass  # Lifecycle events

                elif event_type == "conversation.item.input_audio_transcription.failed":
                    error = data.get("error", {}).get("message", "Transcription failed")
                    logger.warning("[%s] Transcription failed: %s", self.session_id, error)

                elif event_type == "error":
                    error_data = data.get("error", {})
                    error_msg = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code", "unknown")
                    logger.error("[%s] xAI error [%s]: %s", self.session_id, error_code, error_msg)
                    await self._send_browser({"type": "error", "message": error_msg})

                else:
                    preview = json.dumps(data)[:200]
                    logger.debug("[%s] Unhandled event: %s | %s", self.session_id, event_type, preview)

            # If we get here, the async for loop exited normally (clean close)
            # Log the close details
            close_code = getattr(self.xai_ws, 'close_code', None)
            close_reason = getattr(self.xai_ws, 'close_reason', None)
            logger.warning(
                "[%s] xAI WebSocket closed normally: code=%s, reason=%s",
                self.session_id, close_code, close_reason,
            )

        except websockets.exceptions.ConnectionClosed as e:
            logger.warning("[%s] xAI connection closed abnormally: code=%s, reason=%s", self.session_id, e.code, e.reason)
        except asyncio.CancelledError:
            logger.info("[%s] Receive loop cancelled (session ending)", self.session_id)
            return  # Don't try to reconnect on intentional cancellation
        except Exception as e:
            logger.error("[%s] Error in receive loop: %s", self.session_id, e, exc_info=True)

        # ── Auto-reconnect ──────────────────────────────────
        # If we get here, xAI connection died. Try to reconnect.
        self.connected = False
        await self._send_browser({"type": "status", "status": "reconnecting"})

        reconnected = await self.reconnect()
        if reconnected:
            logger.info("[%s] Receive loop restarted after reconnect", self.session_id)
            await self._send_browser({"type": "status", "status": "ready"})
            # reconnect() already called connect() which starts new background tasks
        else:
            logger.error("[%s] Give up reconnecting — session over", self.session_id)
            await self._send_browser({
                "type": "error",
                "message": "Voice connection lost. Please end the session and try again.",
            })

    async def wait_for_completion(self, timeout: float = None):
        """Wait for the receive loop to finish (xAI session ends)."""
        if self._receive_task:
            try:
                await asyncio.wait_for(self._receive_task, timeout=timeout)
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                pass

    async def disconnect(self):
        """Close the xAI WebSocket connection and stop background tasks."""
        self.connected = False
        self._send_to_browser = None  # Detach browser

        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except (asyncio.CancelledError, Exception):
                pass

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
