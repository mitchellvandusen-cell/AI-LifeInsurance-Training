"""
GradingEngine: Produces the final JSON report card after a training session.

Grades every KPI with:
- A numeric score (0-100)
- A letter grade (A-F)
- Specific feedback with timestamps
- Actionable coaching notes

This is the deliverable the agent takes away from each session.
"""

from __future__ import annotations

from src.core.state_manager import StateManager
from src.engine.compliance_tracker import ComplianceTracker
from src.models.state import ConversationPhase, ObjectionType


def _letter_grade(score: float) -> str:
    if score >= 93:
        return "A"
    elif score >= 85:
        return "A-"
    elif score >= 80:
        return "B+"
    elif score >= 75:
        return "B"
    elif score >= 70:
        return "B-"
    elif score >= 65:
        return "C+"
    elif score >= 60:
        return "C"
    elif score >= 55:
        return "C-"
    elif score >= 50:
        return "D"
    else:
        return "F"


def _score_with_grade(score: float, label: str, feedback: str, coaching: str = "") -> dict:
    return {
        "metric": label,
        "score": round(score, 1),
        "grade": _letter_grade(score),
        "feedback": feedback,
        "coaching": coaching,
    }


class GradingEngine:
    """Produces comprehensive grading report from session state."""

    def grade(self, sm: StateManager, ct: ComplianceTracker) -> dict:
        """Generate the complete report card."""
        report = {
            "session_id": sm.state.session_id,
            "persona": {
                "name": sm.state.persona.name,
                "archetype": sm.state.persona.personality_notes.split(".")[0] if sm.state.persona.personality_notes else "Unknown",
                "age": sm.state.persona.age,
                "occupation": sm.state.persona.occupation,
            },
            "overall_score": 0.0,
            "overall_grade": "F",
            "would_close": False,
            "categories": {},
            "phase_analysis": {},
            "objection_analysis": {},
            "critical_moments": [],
            "top_strengths": [],
            "areas_for_improvement": [],
        }

        # ── Category Scores ────────────────────────────────────

        scores = {}

        # 1. TONALITY
        scores["tonality"] = self._grade_tonality(sm)

        # 2. RAPPORT & DISCOVERY
        scores["rapport_discovery"] = self._grade_rapport(sm)

        # 3. QUESTIONS
        scores["question_quality"] = self._grade_questions(sm)

        # 4. COMPLIANCE & AUTHORITY
        scores["compliance_authority"] = self._grade_compliance(sm, ct)

        # 5. FLOW
        scores["flow"] = self._grade_flow(sm)

        # 6. TRUST
        scores["trust_building"] = self._grade_trust(sm)

        # 7. SALES RESISTANCE MANAGEMENT
        scores["resistance_management"] = self._grade_resistance(sm)

        # 8. MEDICAL UNDERWRITING
        scores["medical_underwriting"] = self._grade_underwriting(sm)

        # 9. PREFRAMING
        scores["preframing"] = self._grade_preframing(sm)

        # 10. PRESENTATION
        scores["presentation"] = self._grade_presentation(sm)

        # 11. OBJECTION HANDLING
        scores["objection_handling"] = self._grade_objections(sm)

        report["categories"] = scores

        # ── Overall Score ───────────────────────────────────────

        weights = {
            "tonality": 0.08,
            "rapport_discovery": 0.12,
            "question_quality": 0.10,
            "compliance_authority": 0.10,
            "flow": 0.12,
            "trust_building": 0.10,
            "resistance_management": 0.08,
            "medical_underwriting": 0.08,
            "preframing": 0.10,
            "presentation": 0.07,
            "objection_handling": 0.05,
        }

        total = sum(
            scores[cat]["score"] * weights.get(cat, 0.05)
            for cat in scores
        )
        report["overall_score"] = round(total, 1)
        report["overall_grade"] = _letter_grade(total)

        # ── Would This Close? ──────────────────────────────────

        close_factors = [
            sm.state.hidden.trust_score > 60,
            sm.state.hidden.authority_score > 50,
            sm.state.hidden.sales_resistance < 45,
            sm.state.hidden.flow_integrity,
            sm.check_flag("consequence_established"),
            sm.check_flag("preframed_banking"),
            sm.check_flag("preframed_social_security"),
        ]
        close_pct = sum(1 for f in close_factors if f) / len(close_factors)
        report["would_close"] = close_pct >= 0.7
        report["close_probability"] = round(close_pct * 100, 1)

        # ── Phase Analysis ──────────────────────────────────────

        report["phase_analysis"] = self._analyze_phases(sm)

        # ── Objection Detail ────────────────────────────────────

        report["objection_analysis"] = self._analyze_objections(sm)

        # ── Strengths & Improvements ────────────────────────────

        sorted_cats = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        report["top_strengths"] = [
            {"category": cat, "score": data["score"], "grade": data["grade"]}
            for cat, data in sorted_cats[:3]
        ]
        report["areas_for_improvement"] = [
            {"category": cat, "score": data["score"], "coaching": data["coaching"]}
            for cat, data in sorted_cats[-3:]
            if data["score"] < 75
        ]

        return report

    # ── Individual Category Graders ─────────────────────────────

    def _grade_tonality(self, sm: StateManager) -> dict:
        history = sm.state.tonality_history
        if not history:
            return _score_with_grade(
                50, "Tonality", "No tonality data available (text-only mode).",
                "Use voice mode for tonality analysis."
            )

        total = len(history)
        confident = sum(1 for t in history if t.confident_tone)
        nervous = sum(1 for t in history if t.nervous_tone)
        strategic_pause = sum(1 for t in history if t.strategic_pause_detected)
        whisper = sum(1 for t in history if t.whisper_on_key_phrase)
        bad_inflection = sum(1 for t in history if t.upward_inflection_on_statements)
        good_inflection = sum(1 for t in history if t.downward_inflection_on_consequence)

        score = 50.0
        score += (confident / max(total, 1)) * 20
        score -= (nervous / max(total, 1)) * 25
        score += (strategic_pause / max(total, 1)) * 15
        score += (whisper / max(total, 1)) * 10
        score -= (bad_inflection / max(total, 1)) * 20
        score += (good_inflection / max(total, 1)) * 15
        score = max(0, min(100, score))

        feedback_parts = []
        if bad_inflection > 0:
            feedback_parts.append(f"Upward inflection on statements detected {bad_inflection}x — this makes you sound uncertain.")
        if strategic_pause > 0:
            feedback_parts.append(f"Strategic pauses used {strategic_pause}x — good technique.")
        if whisper > 0:
            feedback_parts.append(f"Power whisper/tone drop used {whisper}x — effective for emphasis.")
        if nervous > 0:
            feedback_parts.append(f"Nervous tone detected {nervous}x — practice controlling vocal tremor.")

        coaching = ""
        if bad_inflection > 2:
            coaching = "Practice making statements with downward inflection. Record yourself and listen back."
        elif nervous > 1:
            coaching = "Work on vocal confidence. Stand up while on calls, smile — it changes your tone."

        return _score_with_grade(
            score, "Tonality",
            " ".join(feedback_parts) if feedback_parts else "Tonality was adequate.",
            coaching,
        )

    def _grade_rapport(self, sm: StateManager) -> dict:
        score = sm.state.hidden.rapport_score
        flags = sm.state.flags

        feedback_parts = []
        if flags.goal_identified:
            feedback_parts.append("Goal identified.")
            score = max(score, score + 5)
        else:
            feedback_parts.append("MISSED: Never identified the client's goal.")
            score -= 15

        if flags.why_behind_goal_identified:
            feedback_parts.append("Uncovered the WHY behind the goal.")
            score += 10
        else:
            feedback_parts.append("MISSED: Never dug into WHY the goal matters.")
            score -= 10

        if flags.consequence_established:
            feedback_parts.append("Established consequence of inaction — critical for closing.")
            score += 15
        else:
            feedback_parts.append("MISSED: Never established what happens if they DON'T act. This is the #1 reason for 'I need to think about it' objections.")
            score -= 20

        score = max(0, min(100, score))

        coaching = ""
        if not flags.consequence_established:
            coaching = "Always ask: 'What happens if something happens to you and there's nothing in place?' Let the silence sit."
        elif not flags.why_behind_goal_identified:
            coaching = "After identifying the goal, ask 'Why is that important to you?' to get the emotional driver."

        return _score_with_grade(score, "Rapport & Discovery", " ".join(feedback_parts), coaching)

    def _grade_questions(self, sm: StateManager) -> dict:
        log = sm.state.conversation_log
        agent_turns = [m for m in log if m["role"] == "agent"]

        total_questions = 0
        advancing = 0
        for turn in agent_turns:
            text = turn.get("content", "")
            qs = text.count("?")
            total_questions += qs
            meta = turn.get("metadata", {})
            advancing += meta.get("advancing_questions", 0)

        if total_questions == 0:
            return _score_with_grade(30, "Question Quality", "No questions detected. Agent must ask questions to advance the sale.", "Practice discovery questions that lead to the goal, why, and consequence.")

        ratio = advancing / total_questions if total_questions > 0 else 0
        score = ratio * 100

        feedback = f"{total_questions} questions asked, {advancing} advanced the sale ({ratio * 100:.0f}% advancement rate)."
        coaching = ""
        if ratio < 0.5:
            coaching = "Focus on purpose-driven questions. Every question should either advance the sale or build rapport. Eliminate questions that don't do either."

        return _score_with_grade(score, "Question Quality", feedback, coaching)

    def _grade_compliance(self, sm: StateManager, ct: ComplianceTracker) -> dict:
        summary = ct.get_compliance_summary()
        ratio = summary["ratio"]
        total = summary["total_checks"]
        frame_events = summary["frame_control_events"]

        score = 50.0
        if total == 0:
            score = 25.0
            feedback = "No compliance checks attempted. Agent never tested micro-agreements."
            coaching = "Build compliance early: 'Grab a pen,' 'Does that make sense?' These small yeses lead to the big yes."
        else:
            score = ratio * 80 + 20  # Base 20 for attempting
            if frame_events > 0:
                score += min(frame_events * 5, 15)

            feedback = f"{total} compliance checks attempted, {summary['successful']} successful ({ratio * 100:.0f}% compliance rate). "
            feedback += f"Frame control events: {frame_events}. Trend: {summary['ladder_trend']}."

            coaching = ""
            if ratio < 0.5:
                coaching = "Your compliance rate is low. Make sure you're asking for small commitments early and often."
            elif summary["ladder_trend"] == "declining":
                coaching = "Compliance is declining over time. You may be losing authority. Strengthen your frame in later phases."

        score = max(0, min(100, score))
        final = _score_with_grade(score, "Compliance & Authority", feedback, coaching)
        final["authority_final"] = round(sm.state.hidden.authority_score, 1)
        return final

    def _grade_flow(self, sm: StateManager) -> dict:
        score = 80.0 if sm.state.hidden.flow_integrity else 30.0

        transitions = sm.state.phase_transitions
        backward = [t for t in transitions if t.get("was_backward")]
        if backward:
            score -= len(backward) * 15
            feedback = f"Flow BROKEN. {len(backward)} backward phase transition(s) detected. "
            feedback += "Agent jumped back to earlier phases, confusing the client."
            coaching = "Follow the framework linearly: Intro → Rapport → Underwriting → Preframe → Present → Close. Never backtrack."
        else:
            phases_hit = set(t["to"] for t in transitions)
            phases_hit.add(sm.state.current_phase.value)
            expected = {"intro", "rapport_discovery", "medical_underwriting", "preframing", "presentation"}
            missing = expected - phases_hit
            if missing:
                score -= len(missing) * 10
                feedback = f"Flow intact but {len(missing)} phase(s) skipped: {', '.join(missing)}."
                coaching = f"Make sure to cover all phases. You missed: {', '.join(missing)}."
            else:
                feedback = "Flow was clean and linear. Client knew where they were at all times."
                coaching = ""

        if sm.check_flag("preoccupation_broken"):
            score += 5
        else:
            score -= 10

        score = max(0, min(100, score))
        return _score_with_grade(score, "Flow & Framework", feedback, coaching)

    def _grade_trust(self, sm: StateManager) -> dict:
        trust = sm.state.hidden.trust_score
        score = trust

        feedback_parts = []
        if sm.check_flag("credentials_shared"):
            feedback_parts.append("Credentials shared with client.")
            score += 5
        else:
            feedback_parts.append("MISSED: Never shared credentials/licensing info.")
            score -= 10

        if trust > 70:
            feedback_parts.append(f"Final trust score: {trust:.0f}/100 — excellent.")
        elif trust > 50:
            feedback_parts.append(f"Final trust score: {trust:.0f}/100 — adequate but could improve.")
        else:
            feedback_parts.append(f"Final trust score: {trust:.0f}/100 — client did not trust you enough to buy.")

        coaching = ""
        if trust < 50:
            coaching = "Build trust through: sharing credentials, using the client's name, acknowledging their concerns, and using confident tonality."

        score = max(0, min(100, score))
        return _score_with_grade(score, "Trust Building", " ".join(feedback_parts), coaching)

    def _grade_resistance(self, sm: StateManager) -> dict:
        resistance = sm.state.hidden.sales_resistance
        # Lower resistance = better score
        score = 100.0 - resistance

        if resistance < 30:
            feedback = f"Sales resistance at {resistance:.0f}/100 — very low. Client was ready to buy."
        elif resistance < 50:
            feedback = f"Sales resistance at {resistance:.0f}/100 — manageable. Some lingering concerns."
        elif resistance < 70:
            feedback = f"Sales resistance at {resistance:.0f}/100 — high. Client was resistant."
        else:
            feedback = f"Sales resistance at {resistance:.0f}/100 — extremely high. Client was not going to buy."

        coaching = ""
        if resistance > 50:
            coaching = "Resistance is driven by lack of trust and authority. Focus on preframing, establishing consequence, and building compliance loops."

        return _score_with_grade(score, "Resistance Management", feedback, coaching)

    def _grade_underwriting(self, sm: StateManager) -> dict:
        score = 50.0

        if sm.check_flag("underwriting_clear"):
            score += 30
            feedback = "Medical underwriting completed successfully."
        else:
            feedback = "Medical underwriting was incomplete or unclear."

        if sm.check_flag("medication_history_complete"):
            score += 20
            feedback += " 10-year medication history covered."
        else:
            feedback += " MISSED: Did not complete 10-year medication history."
            score -= 10

        coaching = ""
        if not sm.check_flag("underwriting_clear"):
            coaching = "Follow a structured checklist: medications, conditions, hospitalizations, tobacco, height/weight, family history. Ask systematically, don't rush."

        score = max(0, min(100, score))
        return _score_with_grade(score, "Medical Underwriting", feedback, coaching)

    def _grade_preframing(self, sm: StateManager) -> dict:
        flags = sm.state.flags
        preframes = {
            "Banking": flags.preframed_banking,
            "Social Security": flags.preframed_social_security,
            "Next Steps": flags.preframed_next_steps,
        }

        done = sum(1 for v in preframes.values() if v)
        total = len(preframes)
        score = (done / total) * 100

        missed = [k for k, v in preframes.items() if not v]
        if missed:
            feedback = f"Preframed {done}/{total}. MISSED: {', '.join(missed)}."
            coaching = f"Always preframe sensitive requests BEFORE you need them. You missed preframing: {', '.join(missed)}."
        else:
            feedback = f"All {total} preframes completed. Excellent setup for a clean close."
            coaching = ""

        return _score_with_grade(score, "Preframing", feedback, coaching)

    def _grade_presentation(self, sm: StateManager) -> dict:
        score = 50.0
        flags = sm.state.flags
        feedback_parts = []

        if flags.pricing_presented:
            score += 15
            feedback_parts.append("Pricing presented.")
        else:
            feedback_parts.append("MISSED: Pricing not presented.")

        if flags.coverage_aligned_to_goals:
            score += 15
            feedback_parts.append("Coverage tied to client's stated goals.")
        else:
            feedback_parts.append("MISSED: Coverage not aligned to client's specific goals.")
            score -= 5

        if flags.benefits_explained:
            score += 10
            feedback_parts.append("Benefits explained.")
        else:
            feedback_parts.append("MISSED: Benefits not explained.")

        if flags.day_one_coverage_mentioned:
            score += 5
            feedback_parts.append("Day 1 coverage addressed.")

        if flags.term_duration_explained:
            score += 5
            feedback_parts.append("Term/duration explained.")

        coaching = ""
        if score < 60:
            coaching = "A strong presentation ties pricing to the client's SPECIFIC goals, explains benefits in plain language, and covers day 1 coverage and term duration."

        score = max(0, min(100, score))
        return _score_with_grade(score, "Presentation", " ".join(feedback_parts), coaching)

    def _grade_objections(self, sm: StateManager) -> dict:
        objections = sm.state.objections_raised
        if not objections:
            return _score_with_grade(
                75, "Objection Handling",
                "No objections raised — either the agent preframed perfectly or the session ended early.",
                "",
            )

        total = len(objections)
        isolated = sum(1 for o in objections if o.isolated)
        confirmed = sum(1 for o in objections if o.isolation_confirmed)
        resolved = sum(1 for o in objections if o.resolved)
        avg_conviction = 0.0
        if resolved > 0:
            avg_conviction = sum(
                o.resolution_conviction_score for o in objections if o.resolved
            ) / resolved

        score = 50.0
        if total > 0:
            score += (isolated / total) * 15  # Isolated
            score += (confirmed / total) * 15  # Confirmed isolation
            score += (resolved / total) * 20  # Resolved
            score += (avg_conviction / 100) * 10  # Quality of resolution

        # Penalty for not isolating
        not_isolated = total - isolated
        if not_isolated > 0:
            score -= not_isolated * 10

        feedback = (
            f"{total} objection(s) raised. {isolated} isolated, {confirmed} confirmed, "
            f"{resolved} resolved. Average conviction: {avg_conviction:.0f}/100."
        )

        coaching = ""
        if isolated < total:
            coaching = "Always isolate before handling: 'Is it just [X], or is there something else holding you back?' Then confirm: 'So if we solve [X], you're good to move forward?'"

        score = max(0, min(100, score))
        return _score_with_grade(score, "Objection Handling", feedback, coaching)

    # ── Phase Analysis ──────────────────────────────────────────

    def _analyze_phases(self, sm: StateManager) -> dict:
        transitions = sm.state.phase_transitions
        phase_data = {}
        for i, t in enumerate(transitions):
            phase_name = t["to"]
            if phase_name not in phase_data:
                phase_data[phase_name] = {
                    "entered_at_turn": t["turn"],
                    "was_backward": t.get("was_backward", False),
                }

        return phase_data

    # ── Objection Analysis ──────────────────────────────────────

    def _analyze_objections(self, sm: StateManager) -> dict:
        objections = sm.state.objections_raised
        return {
            "total": len(objections),
            "by_type": {
                "smokescreen": sum(1 for o in objections if o.objection_type == ObjectionType.SMOKESCREEN),
                "true_objection": sum(1 for o in objections if o.objection_type == ObjectionType.TRUE_OBJECTION),
                "condition": sum(1 for o in objections if o.objection_type == ObjectionType.CONDITION),
            },
            "resolved": sum(1 for o in objections if o.resolved),
            "unresolved": sum(1 for o in objections if not o.resolved),
            "details": [
                {
                    "category": o.category.value,
                    "type": o.objection_type.value,
                    "text": o.text,
                    "isolated": o.isolated,
                    "resolved": o.resolved,
                    "conviction": o.resolution_conviction_score,
                }
                for o in objections
            ],
        }
