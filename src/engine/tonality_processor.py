"""
TonalityProcessor: Ingests audio metadata alongside STT text
and produces TonalitySnapshot objects for the StateManager.

In production, audio metadata comes from the STT pipeline (e.g., Deepgram,
AssemblyAI, or custom prosody analysis). This module defines the interface
and processes whatever metadata is available.
"""

from __future__ import annotations

from src.models.state import TonalitySnapshot


# Thresholds for classification
PAUSE_STRATEGIC_MIN_SECONDS = 1.5
PAUSE_STRATEGIC_MAX_SECONDS = 5.0
SPEAKING_RATE_SLOW_WPM = 100
SPEAKING_RATE_FAST_WPM = 180
SPEAKING_RATE_NORMAL_LOW = 120
SPEAKING_RATE_NORMAL_HIGH = 160


class TonalityProcessor:
    """
    Converts raw audio metadata into structured TonalitySnapshot.
    Designed to accept metadata from any STT provider.
    """

    def process_metadata(self, metadata: dict) -> TonalitySnapshot:
        """
        Process raw audio metadata into a TonalitySnapshot.

        Expected metadata keys (all optional):
        - pitch_contour: list[float] - pitch values over time
        - pitch_end_direction: str - "rising", "falling", "flat"
        - utterance_type: str - "statement", "question"
        - pause_before_seconds: float
        - pause_after_seconds: float
        - speaking_rate_wpm: float
        - volume_db: float
        - volume_shifts: list[dict] with {position, direction, magnitude}
        - filler_words: list[str] - detected fillers ("um", "uh", etc.)
        - emphasis_words: list[dict] with {word, intensity}
        - confidence_score: float - STT confidence in tone analysis
        """
        snapshot = TonalitySnapshot()

        # ── Inflection Analysis ─────────────────────────────────

        pitch_direction = metadata.get("pitch_end_direction", "flat")
        utterance_type = metadata.get("utterance_type", "unknown")

        if pitch_direction == "rising" and utterance_type == "statement":
            snapshot.upward_inflection_on_statements = True

        if pitch_direction == "falling" and utterance_type == "question":
            snapshot.downward_inflection_on_questions = True

        # Consequence questions get special treatment
        is_consequence_q = metadata.get("is_consequence_question", False)
        if pitch_direction == "falling" and is_consequence_q:
            snapshot.downward_inflection_on_consequence = True

        # ── Pause Analysis ──────────────────────────────────────

        pause_after = metadata.get("pause_after_seconds", 0.0)
        pause_before = metadata.get("pause_before_seconds", 0.0)
        max_pause = max(pause_after, pause_before)
        snapshot.pause_duration_seconds = max_pause

        if PAUSE_STRATEGIC_MIN_SECONDS <= max_pause <= PAUSE_STRATEGIC_MAX_SECONDS:
            snapshot.strategic_pause_detected = True

        # ── Stutter / Filler Analysis ───────────────────────────

        fillers = metadata.get("filler_words", [])
        speaking_rate = metadata.get("speaking_rate_wpm", 0.0)
        snapshot.speaking_rate_wpm = speaking_rate

        # Strategic stuttering: 1-2 fillers at normal pace = thinking on the spot
        # Excessive fillers at fast pace = nervous
        if 1 <= len(fillers) <= 2 and SPEAKING_RATE_NORMAL_LOW <= speaking_rate <= SPEAKING_RATE_NORMAL_HIGH:
            snapshot.strategic_stutter_detected = True

        # ── Volume / Whisper Analysis ───────────────────────────

        volume_shifts = metadata.get("volume_shifts", [])
        for shift in volume_shifts:
            if shift.get("direction") == "down" and shift.get("magnitude", 0) > 5:
                snapshot.whisper_on_key_phrase = True
                snapshot.tone_shift_detected = True
            elif shift.get("direction") == "up" and shift.get("magnitude", 0) > 5:
                snapshot.tone_shift_detected = True

        # ── Overall Tone Classification ─────────────────────────

        confidence_indicators = metadata.get("confidence_indicators", {})
        vocal_tremor = confidence_indicators.get("vocal_tremor", False)
        pitch_stability = confidence_indicators.get("pitch_stability", 1.0)
        volume_consistency = confidence_indicators.get("volume_consistency", 1.0)

        if vocal_tremor or pitch_stability < 0.5:
            snapshot.nervous_tone = True

        if pitch_stability > 0.8 and volume_consistency > 0.8 and not vocal_tremor:
            snapshot.confident_tone = True

        return snapshot

    def process_text_only(self, text: str, context: dict | None = None) -> TonalitySnapshot:
        """
        Fallback for text-only mode (no audio metadata).
        Uses heuristic analysis of text patterns.
        This is a degraded mode — scores will be less precise.
        """
        snapshot = TonalitySnapshot()

        # Detect question marks on statements (heuristic)
        sentences = text.split(".")
        for sentence in sentences:
            stripped = sentence.strip()
            if stripped.endswith("?") and not any(
                stripped.lower().startswith(w)
                for w in ["what", "how", "why", "when", "where", "who", "do", "does",
                          "did", "is", "are", "was", "were", "can", "could", "would",
                          "should", "will", "have", "has"]
            ):
                # Statement phrased as question = upward inflection
                snapshot.upward_inflection_on_statements = True

        # Detect ellipsis or "..." as pauses
        if "..." in text or "—" in text:
            snapshot.strategic_pause_detected = True
            snapshot.pause_duration_seconds = 2.0

        # Default to neutral tone in text-only mode
        snapshot.confident_tone = True

        return snapshot
