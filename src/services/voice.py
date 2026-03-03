"""
xAI Grok Voice Agent API integration — production-grade speech pipeline.

Manages WebSocket connections to wss://api.x.ai/v1/realtime for
real-time speech-to-speech training sessions.

Architecture:
  Browser mic audio → Backend WS → xAI Voice API → AI client voice → Backend WS → Browser
  Training engine intercepts transcriptions between turns to update behavioral state.

The VoiceSession runs its own receive loop as an independent background task.
Browser connections come and go (reconnects), but the xAI session persists.
The browser callback is swappable — reconnects just swap where events go.

Transcript pipeline:
  Raw xAI events come in as multiple partial/duplicate transcription.completed
  events per utterance. The TranscriptPipeline class collapses these into clean,
  single-emission turns using:
    1. Debounced buffering (collapse progressive extensions)
    2. Duplicate / prefix / overlap detection
    3. Echo fingerprinting (reject text that mirrors recent coach speech)

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
import re
import time
from collections import deque
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


# ══════════════════════════════════════════════════════════════
# TRANSCRIPT PIPELINE
# Production-grade dedup, debounce, and echo rejection for
# messy real-time speech-to-text events.
# ══════════════════════════════════════════════════════════════

# Regex to detect stutter artifacts: 3+ consecutive repeated words
# e.g., "my my my my name" or "the the the the audio"
_STUTTER_RE = re.compile(r'\b(\w+)(?:\s*,?\s+\1){2,}\b', re.IGNORECASE)


def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace for comparison."""
    return " ".join(text.lower().split())


def _word_overlap_ratio(a: str, b: str) -> float:
    """Jaccard similarity between two texts' word sets (0.0–1.0)."""
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def clean_stutter_artifacts(text: str) -> str:
    """Remove repeated-word stutter artifacts caused by audio echo.

    "yeah yeah yeah my my my my name is" → "yeah my name is"
    Preserves intentional emphasis (max 2 repeats).
    """
    def _dedup_run(match: re.Match) -> str:
        word = match.group(1)
        return word
    return _STUTTER_RE.sub(_dedup_run, text).strip()


class TranscriptPipeline:
    """Processes raw xAI transcript events into clean, single-emission turns.

    xAI's Realtime API fires multiple ``transcription.completed`` events for
    a single utterance — progressive extensions as the user keeps talking,
    exact duplicates from retry/reconnect, and echo artifacts from coach
    audio bleeding into the mic.  This class collapses all of that into one
    clean transcript per actual user turn.

    Usage in VoiceSession:
        pipeline = TranscriptPipeline(session_id)
        # On each transcription.completed event:
        pipeline.receive(text)           # buffer it
        pipeline.start_debounce(flush)   # (re)start the timer
        # On response.created:
        pipeline.flush_now()             # emit immediately
    """

    # How long to wait after the last transcript event before emitting.
    # This allows progressive extensions to collapse into one emission.
    # Tuned for coaching sessions where the student pauses to think.
    DEBOUNCE_SECONDS = 2.0

    # If a new transcript arrives within this window after the last
    # emission, merge it with the previous emission rather than
    # creating a new line. Handles VAD mid-sentence splits: the VAD
    # fires speech_stopped, emits half the sentence, then the user
    # continues and a new transcript arrives for the second half.
    MERGE_WINDOW_SECONDS = 4.0

    # If >60% of the agent's words overlap with recent coach speech,
    # it's likely echo, not the user talking.
    ECHO_OVERLAP_THRESHOLD = 0.60

    def __init__(self, session_id: str):
        self.session_id = session_id

        # ── Buffer state ─────────────────────────────────────
        self._pending_text: str = ""
        self._debounce_task: Optional[asyncio.Task] = None

        # ── History for dedup ────────────────────────────────
        self._last_emitted_text: str = ""
        self._last_emitted_norm: str = ""
        self._last_emit_time: float = 0.0

        # ── Coach speech ring buffer for echo detection ──────
        # Stores the last N coach utterances (normalized).
        self._recent_coach: deque[str] = deque(maxlen=8)

        # ── Callback to invoke on flush ──────────────────────
        self._flush_callback: Optional[Callable] = None

        # ── Merge tracking ───────────────────────────────────
        # Set True when receive() merges with a previous emission.
        # Read by VoiceSession's flush callback to decide whether
        # to send 'transcript' (new line) or 'replace_transcript'.
        self._next_emit_is_merge: bool = False

        # ── Stats ────────────────────────────────────────────
        self.events_received: int = 0
        self.events_emitted: int = 0
        self.events_dropped_dedup: int = 0
        self.events_dropped_echo: int = 0
        self.events_merged: int = 0

    # ── Public API ───────────────────────────────────────────

    def receive(self, text: str) -> bool:
        """Buffer an incoming transcript. Returns False if dropped as duplicate."""
        text = text.strip()
        if not text:
            return False

        self.events_received += 1
        norm = _normalize(text)

        # ── Drop exact duplicates of pending or last-emitted ─
        if norm == _normalize(self._pending_text):
            self.events_dropped_dedup += 1
            return False
        if norm == self._last_emitted_norm:
            self.events_dropped_dedup += 1
            return False

        # ── Progressive extension: keep the longer version ───
        pending_norm = _normalize(self._pending_text)
        if pending_norm and (norm.startswith(pending_norm) or pending_norm.startswith(norm)):
            self._pending_text = text if len(norm) >= len(pending_norm) else self._pending_text
            self.events_dropped_dedup += 1
            return True

        # ── Extension of last emitted (late arrival) ─────────
        if self._last_emitted_norm and norm.startswith(self._last_emitted_norm):
            self._pending_text = text
            self.events_dropped_dedup += 1
            return True

        # ── Echo detection ───────────────────────────────────
        if self._is_echo(norm):
            self.events_dropped_echo += 1
            logger.info(
                "[%s] Dropped echo transcript: %.60s...",
                self.session_id, text,
            )
            return False

        # ── Merge window: continuation of the same turn ──────
        # If this transcript arrives shortly after a previous
        # emission and there's nothing pending, the VAD likely
        # split a single utterance mid-sentence. Merge with the
        # last emission by prepending it as pending text.
        if (
            not self._pending_text
            and self._last_emitted_text
            and self._last_emit_time > 0
            and (time.time() - self._last_emit_time) < self.MERGE_WINDOW_SECONDS
        ):
            self._pending_text = self._last_emitted_text + " " + text
            self._next_emit_is_merge = True
            self.events_merged += 1
            logger.info(
                "[%s] Merged continuation: ...%s + %s",
                self.session_id,
                self._last_emitted_text[-30:],
                text[:30],
            )
            return True

        # ── Genuinely new transcript ─────────────────────────
        self._next_emit_is_merge = False
        self._pending_text = text
        return True

    def record_coach_speech(self, text: str):
        """Track coach utterances for echo detection."""
        norm = _normalize(text)
        if norm:
            self._recent_coach.append(norm)

    def start_debounce(self, callback: Callable):
        """Start (or restart) the debounce timer. Callback is called on flush."""
        self._flush_callback = callback
        self._cancel_debounce()
        self._debounce_task = asyncio.create_task(self._debounce_wait())

    async def flush_now(self) -> Optional[str]:
        """Cancel debounce timer and emit pending text immediately.

        Returns the emitted text, or None if nothing was pending.
        """
        self._cancel_debounce()
        return await self._emit()

    def has_pending(self) -> bool:
        return bool(self._pending_text)

    # ── Internal ─────────────────────────────────────────────

    def _is_echo(self, norm_text: str) -> bool:
        """Check if this transcript is just echoed coach audio."""
        if not self._recent_coach:
            return False
        # Check against each recent coach utterance
        for coach_norm in self._recent_coach:
            overlap = _word_overlap_ratio(norm_text, coach_norm)
            if overlap >= self.ECHO_OVERLAP_THRESHOLD:
                return True
        return False

    def _cancel_debounce(self):
        if self._debounce_task and not self._debounce_task.done():
            self._debounce_task.cancel()
            self._debounce_task = None

    async def _debounce_wait(self):
        try:
            await asyncio.sleep(self.DEBOUNCE_SECONDS)
            await self._emit()
        except asyncio.CancelledError:
            pass  # Debounce was restarted or flushed early

    async def _emit(self) -> Optional[str]:
        """Emit the pending text via callback and update history."""
        text = self._pending_text
        if not text:
            return None

        # Clean stutter artifacts before emitting
        cleaned = clean_stutter_artifacts(text)
        if cleaned != text:
            logger.info(
                "[%s] Cleaned stutter: '%s' → '%s'",
                self.session_id, text[:60], cleaned[:60],
            )
            text = cleaned

        self._pending_text = ""
        self._last_emitted_text = text
        self._last_emitted_norm = _normalize(text)
        self._last_emit_time = time.time()
        self.events_emitted += 1

        if self._flush_callback:
            try:
                await self._flush_callback(text)
            except Exception as e:
                logger.error("[%s] Flush callback error: %s", self.session_id, e, exc_info=True)

        return text

    def get_stats(self) -> dict:
        """Return pipeline statistics for logging/debugging."""
        return {
            "received": self.events_received,
            "emitted": self.events_emitted,
            "dropped_dedup": self.events_dropped_dedup,
            "dropped_echo": self.events_dropped_echo,
            "merged": self.events_merged,
        }


# ══════════════════════════════════════════════════════════════
# VOICE SESSION
# ══════════════════════════════════════════════════════════════

class VoiceSession:
    """
    Manages a single voice training session with xAI.
    Bridges browser WebSocket <-> xAI WebSocket, intercepting
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
        self._current_client_text = ""
        self._turn_count = 0
        self._response_start_time = 0.0  # Track when AI response audio starts

        # Production transcript pipeline — handles dedup, debounce, echo
        self._pipeline = TranscriptPipeline(session_id)

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
                    # Lower threshold = less likely to falsely detect end-of-speech.
                    # 0.5 was cutting users off mid-sentence ("go ahead and..." -> "Go").
                    "threshold": 0.35,
                    # Capture more of the start of utterances so first words aren't clipped
                    "prefix_padding_ms": 600,
                    # Allow natural mid-sentence pauses (breathing, thinking)
                    # without the VAD triggering end-of-turn. This is a coaching
                    # session, not a customer support bot — the student needs time
                    # to think, breathe, and formulate responses. 3.5s + our 2s
                    # debounce gives ~4s effective pause tolerance before the
                    # system considers the user's turn complete.
                    "silence_duration_ms": 3500,
                },
                "input_audio_transcription": {"model": "whisper-large-v3"},
                "audio": {
                    "input": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                    "output": {"format": {"type": AUDIO_FORMAT, "rate": SAMPLE_RATE}},
                },
                # Allow longer AI responses to prevent speech cutoff on coaching turns.
                # The coach often delivers multi-sentence feedback, demonstrations, and
                # exercises — default token limits can truncate these mid-sentence.
                "max_response_output_tokens": 4096,
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

    # ── Agent (user) transcript emission ─────────────────────

    async def _on_pipeline_flush(self, text: str):
        """Called by TranscriptPipeline when a clean transcript is ready.

        If the pipeline merged this text with a previous emission (VAD
        split mid-sentence), we send a ``replace_transcript`` message so
        the frontend updates the last agent line in-place rather than
        appending a new one.
        """
        is_merge = self._pipeline._next_emit_is_merge
        # Clear the flag immediately — it's been consumed
        self._pipeline._next_emit_is_merge = False

        if is_merge:
            # Merged continuation — replace the last agent line
            logger.info("[%s] Agent said (merged turn %d): %.80s...", self.session_id, self._turn_count, text)
            await self._send_browser({
                "type": "replace_transcript", "role": "agent",
                "text": text, "turn": self._turn_count,
            })
        else:
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

    # ── Main receive loop ────────────────────────────────────

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

                # ── Audio response chunks -> browser ──────────────
                if event_type in ("response.output_audio.delta", "response.audio.delta"):
                    delta = data.get("delta", "")
                    if delta:
                        # Track when audio stream starts for transcript pacing
                        if self._response_start_time == 0.0:
                            self._response_start_time = time.time()
                        await self._send_browser({"type": "audio", "data": delta})

                # ── Agent transcript (what the user said) ─────────
                # xAI fires multiple transcription.completed events per
                # utterance. The pipeline collapses them into a single
                # clean emission via debounce + dedup + echo rejection.
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    text = data.get("transcript", "")
                    if text:
                        accepted = self._pipeline.receive(text)
                        if accepted:
                            self._pipeline.start_debounce(self._on_pipeline_flush)

                # ── Client transcript delta (streaming) ──────────
                elif event_type in ("response.output_audio_transcript.delta", "response.audio_transcript.delta"):
                    delta = data.get("delta", "")
                    self._current_client_text += delta
                    # Include elapsed time since audio started so frontend can
                    # pace text display to match speech playback speed
                    elapsed = time.time() - self._response_start_time if self._response_start_time else 0
                    await self._send_browser({
                        "type": "transcript_delta", "role": "client", "delta": delta,
                        "elapsed": round(elapsed, 2),
                    })

                # ── Client transcript complete ───────────────────
                elif event_type in ("response.output_audio_transcript.done", "response.audio_transcript.done"):
                    text = data.get("transcript", self._current_client_text)
                    if text:
                        # Record coach speech for echo detection
                        self._pipeline.record_coach_speech(text)
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
                    self._response_start_time = 0.0  # Reset for next response

                # ── Response complete ────────────────────────────
                elif event_type == "response.done":
                    response_data = data.get("response", {})
                    status_details = response_data.get("status_details", {})
                    response_status = response_data.get("status", "completed")

                    if response_status == "cancelled":
                        # Response was cancelled (barge-in or explicit cancel).
                        # Do NOT send 'listening' — the user is speaking and
                        # 'recording' status was already sent by speech_started.
                        logger.info("[%s] Response cancelled (barge-in)", self.session_id)
                        self._current_client_text = ""
                        self._response_start_time = 0.0
                        # Tell browser to clear any partial coach transcript
                        await self._send_browser({"type": "clear_streaming"})
                    elif response_status == "incomplete":
                        reason = status_details.get("reason", "unknown")
                        logger.warning(
                            "[%s] Response TRUNCATED (reason=%s) — AI speech was cut off",
                            self.session_id, reason,
                        )
                        # Auto-continue only for token-limit truncation,
                        # NOT for turn_detected (user barge-in)
                        if reason in ("max_output_tokens", "length"):
                            logger.info("[%s] Auto-continuing truncated response...", self.session_id)
                            try:
                                await self.xai_ws.send(json.dumps({
                                    "type": "response.create",
                                    "response": {
                                        "instructions": "You were cut off mid-sentence. Continue EXACTLY where you left off — pick up the sentence naturally. Do NOT repeat what you already said. Do NOT start over.",
                                    },
                                }))
                            except Exception as e:
                                logger.error("[%s] Error auto-continuing: %s", self.session_id, e)
                        else:
                            # Truncated for other reason (turn_detected, etc.)
                            await self._send_browser({"type": "status", "status": "listening"})
                    else:
                        logger.debug("[%s] Response complete", self.session_id)
                        await self._send_browser({"type": "status", "status": "listening"})

                # ── Speech detected (user starts talking) ────────
                # If the AI is currently responding, this is a barge-in.
                # Cancel the in-flight response so the AI stops generating
                # audio and the user doesn't hear overlapping speech.
                elif event_type == "input_audio_buffer.speech_started":
                    if self._response_start_time != 0.0:
                        logger.info("[%s] Barge-in detected — cancelling active response", self.session_id)
                        try:
                            await self.xai_ws.send(json.dumps({"type": "response.cancel"}))
                        except Exception as e:
                            logger.warning("[%s] Failed to cancel response on barge-in: %s", self.session_id, e)
                        self._response_start_time = 0.0
                    else:
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
                    # AI is about to speak — flush any pending agent
                    # transcript immediately so it's logged before the
                    # coach's response.
                    await self._pipeline.flush_now()
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

        # Flush any pending agent transcript before shutdown
        await self._pipeline.flush_now()

        # Log pipeline stats for diagnostics
        stats = self._pipeline.get_stats()
        logger.info(
            "[%s] Transcript pipeline stats: received=%d emitted=%d "
            "dropped_dedup=%d dropped_echo=%d merged=%d",
            self.session_id,
            stats["received"], stats["emitted"],
            stats["dropped_dedup"], stats["dropped_echo"],
            stats["merged"],
        )

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
