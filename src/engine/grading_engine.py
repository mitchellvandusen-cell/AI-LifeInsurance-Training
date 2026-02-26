"""
GradingEngine: Produces the final JSON report card after a training session.

This is NOT a prescriptive "one right way" grader. It recognizes multiple
valid selling styles and grades each on its own merits while noting the
real-world consequences of each approach.

You can close with high energy and pressure. You can close consultatively.
Both work — but each has trade-offs the agent needs to understand.

The grading engine acts as an expert closer who has seen it all.
"""

from __future__ import annotations

from src.core.state_manager import StateManager
from src.engine.compliance_tracker import ComplianceTracker
from src.models.state import ConversationPhase, ObjectionType, SalesStyle


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


def _score_with_grade(
    score: float,
    label: str,
    feedback: str,
    coaching: str = "",
    pros: list[str] | None = None,
    consequences: list[str] | None = None,
) -> dict:
    return {
        "metric": label,
        "score": round(max(0, min(100, score)), 1),
        "grade": _letter_grade(max(0, min(100, score))),
        "feedback": feedback,
        "coaching": coaching,
        "pros": pros or [],
        "consequences": consequences or [],
    }


# ── Style-specific coaching wisdom ─────────────────────────────

STYLE_ANALYSIS = {
    SalesStyle.HIGH_ENERGY: {
        "name": "High-Energy / Assumptive Close",
        "description": (
            "You're running a direct, high-energy approach — assumptive closes, "
            "urgency-driven language, minimal discovery. This CAN work and many "
            "top producers use it."
        ),
        "pros": [
            "Fast call times — more dials, more at-bats per day.",
            "Works exceptionally well on leads with high urgency (recently widowed, health scare, spouse pressure).",
            "Decisiveness is attractive — some clients WANT to be told what to do.",
            "Can close clients who would have otherwise delayed and fallen off.",
        ],
        "consequences": [
            "Higher chargeback rate — clients who feel pushed cancel within the free-look period.",
            "Lower persistency — 13-month lapse rates go up because the 'why' wasn't established.",
            "Complaint risk — some clients feel sold, not served, and file complaints with carriers.",
            "Burnout — high-pressure selling is emotionally exhausting for the agent long-term.",
            "Referral rate drops — pressured clients don't refer friends and family.",
        ],
        "overall_coaching": (
            "Your energy is an asset. The key is channeling it into consequence-driven "
            "urgency instead of pressure-driven urgency. When the client feels THEIR OWN "
            "reason to act NOW (because you established what happens if they don't), you "
            "get the same close rate with a fraction of the chargebacks. Keep the pace, "
            "lose the push."
        ),
    },
    SalesStyle.CONSULTATIVE: {
        "name": "Consultative / Discovery-Based",
        "description": (
            "You're running a methodical, question-driven approach — deep discovery, "
            "consequence establishment, patient build. This is the foundation of "
            "professional selling."
        ),
        "pros": [
            "Highest persistency — clients who understand WHY they bought don't cancel.",
            "Lowest chargeback rate — no buyer's remorse when the decision was their idea.",
            "Referral machine — clients who felt heard and served refer their entire family.",
            "Scales with your career — this approach works better as your book grows.",
            "Carrier relationships thrive — clean business means better contracts.",
        ],
        "consequences": [
            "Longer call times — fewer dials per day if you're not efficient.",
            "Can over-discover — spending 45 minutes on rapport when the client was ready at 15.",
            "Risk of being too passive — consultative doesn't mean you don't close.",
            "Some high-urgency leads need a push. Pure consultative can lose 'ready-now' buyers.",
        ],
        "overall_coaching": (
            "You have the right foundation. The biggest risk for consultative sellers is "
            "staying in discovery too long and being afraid to present and close. Remember: "
            "asking for the business IS serving the client. If you've established the "
            "consequence and they need coverage, NOT closing them is doing them a disservice. "
            "Consultative + decisive closing = unstoppable."
        ),
    },
    SalesStyle.RELATIONSHIP: {
        "name": "Relationship / Rapport-Heavy",
        "description": (
            "You're a natural connector — strong rapport, warm tonality, people like you "
            "immediately. You sell through trust and likability."
        ),
        "pros": [
            "Clients love you — you're 'their' insurance person for life.",
            "Incredible referral rate — people send their mom, sister, neighbor.",
            "Very low complaint rate — even if something goes wrong, they call you first.",
            "Enjoyable career — you genuinely connect with people all day.",
        ],
        "consequences": [
            "Can lack structure — spending 30 minutes talking about grandkids but never getting to underwriting.",
            "Close rate drops when you avoid the uncomfortable parts (asking for money, SSN, banking).",
            "Some clients will 'friend-zone' you — they love talking to you but never buy.",
            "Without urgency or consequence, rapport alone doesn't close deals.",
            "Risk of taking rejection personally because you genuinely connected.",
        ],
        "overall_coaching": (
            "Your warmth is rare and valuable. The upgrade is adding STRUCTURE to your "
            "natural style. You don't need to change WHO you are — you need a framework "
            "that channels your rapport into a sale. Build rapport WITH PURPOSE: every "
            "personal question should connect back to their coverage needs. Time your "
            "transition from rapport to business — you'll know when they're ready because "
            "you're already great at reading people."
        ),
    },
    SalesStyle.HYBRID: {
        "name": "Hybrid / Adaptive",
        "description": (
            "You're mixing approaches — some consultative discovery, some high-energy "
            "urgency, some rapport building. This can be powerful if intentional."
        ),
        "pros": [
            "Versatile — you can match the client's personality and adjust.",
            "Not locked into one gear — you can push when needed and pull back when not.",
            "Indicates sales maturity — experienced agents naturally blend styles.",
        ],
        "consequences": [
            "If unintentional, can feel inconsistent to the client — warm one minute, pushy the next.",
            "Hard to diagnose what's working if you don't know which mode you're in.",
            "May indicate uncertainty about your own process — are you adapting or wandering?",
        ],
        "overall_coaching": (
            "The question is: are you adapting intentionally or just winging it? "
            "Great agents ARE hybrid — they read the client and adjust. But they know "
            "exactly which gear they're in and why. Pick a base style (consultative is "
            "usually the strongest foundation) and add tools from other styles as needed. "
            "Name your modes: 'I'm in discovery mode' → 'Now I'm in urgency mode.' "
            "Intentional adaptation beats accidental style-switching every time."
        ),
    },
    SalesStyle.UNKNOWN: {
        "name": "Insufficient Data",
        "description": "Not enough conversation to determine your selling style.",
        "pros": [],
        "consequences": [],
        "overall_coaching": "Complete a full training call for style analysis.",
    },
}


class GradingEngine:
    """Produces comprehensive, style-aware grading report from session state."""

    def grade(self, sm: StateManager, ct: ComplianceTracker) -> dict:
        """Generate the complete report card."""
        # Detect sales style before grading
        style = sm.detect_sales_style()
        style_info = STYLE_ANALYSIS.get(style, STYLE_ANALYSIS[SalesStyle.UNKNOWN])

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
            "close_probability": 0.0,
            "sales_style": {
                "detected": style.value,
                "name": style_info["name"],
                "description": style_info["description"],
                "pros": style_info["pros"],
                "consequences": style_info["consequences"],
                "coaching": style_info["overall_coaching"],
            },
            "categories": {},
            "deal_killers": {},
            "phase_analysis": {},
            "objection_analysis": {},
            "top_strengths": [],
            "areas_for_improvement": [],
        }

        # ── Category Scores ────────────────────────────────────

        scores = {}
        scores["tonality"] = self._grade_tonality(sm, style)
        scores["rapport_discovery"] = self._grade_rapport(sm, style)
        scores["question_quality"] = self._grade_questions(sm, style)
        scores["compliance_authority"] = self._grade_compliance(sm, ct, style)
        scores["flow"] = self._grade_flow(sm, style)
        scores["trust_building"] = self._grade_trust(sm, style)
        scores["resistance_management"] = self._grade_resistance(sm, style)
        scores["medical_underwriting"] = self._grade_underwriting(sm)
        scores["preframing"] = self._grade_preframing(sm)
        scores["presentation"] = self._grade_presentation(sm, style)
        scores["objection_handling"] = self._grade_objections(sm, style)

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

        # ── Three Deal-Killers Analysis ─────────────────────────

        report["deal_killers"] = self._analyze_deal_killers(sm)

        # ── Would This Close? ──────────────────────────────────

        close_factors = {
            "trust_above_60": sm.state.hidden.trust_score > 60,
            "authority_above_50": sm.state.hidden.authority_score > 50,
            "resistance_below_45": sm.state.hidden.sales_resistance < 45,
            "flow_intact": sm.state.hidden.flow_integrity,
            "consequence_established": sm.check_flag("consequence_established"),
            "preframed_banking": sm.check_flag("preframed_banking"),
            "preframed_social_security": sm.check_flag("preframed_social_security"),
            "urgency_created": sm.check_flag("consequence_established"),
            "decision_maker_confirmed": sm.state.persona.decision_maker or any(
                o.decision_maker_confirmed for o in sm.state.objections_raised
            ),
        }
        met = sum(1 for v in close_factors.values() if v)
        total_factors = len(close_factors)
        close_pct = met / total_factors
        report["would_close"] = close_pct >= 0.7
        report["close_probability"] = round(close_pct * 100, 1)
        report["close_factors"] = {k: v for k, v in close_factors.items()}

        # ── Phase & Objection Analysis ──────────────────────────

        report["phase_analysis"] = self._analyze_phases(sm)
        report["objection_analysis"] = self._analyze_objections(sm)

        # ── Strengths & Improvements ────────────────────────────

        sorted_cats = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)
        report["top_strengths"] = [
            {"category": cat, "score": data["score"], "grade": data["grade"],
             "pros": data.get("pros", [])}
            for cat, data in sorted_cats[:3]
        ]
        report["areas_for_improvement"] = [
            {"category": cat, "score": data["score"], "coaching": data["coaching"],
             "consequences": data.get("consequences", [])}
            for cat, data in sorted_cats[-3:]
            if data["score"] < 75
        ]

        return report

    # ── Deal-Killers (Money, Time, Decision Maker) ──────────────

    def _analyze_deal_killers(self, sm: StateManager) -> dict:
        """The three things that kill every deal. Grade each."""
        flags = sm.state.flags

        # MONEY: Was the budget addressed? Was value reframed?
        money_ok = sm.state.hidden.sales_resistance < 50
        money_details = {
            "status": "resolved" if money_ok else "unresolved",
            "resistance_level": round(sm.state.hidden.sales_resistance, 1),
            "preframed_banking": flags.preframed_banking,
            "preframed_ssn": flags.preframed_social_security,
            "budget_objection_raised": any(
                o.root_cause.value == "money" and not o.locked
                for o in sm.state.objections_raised
            ),
            "coaching": (
                "Money objections are almost never about the money — they're about "
                "the VALUE not being clear. When a client says 'that's too much,' "
                "they're really saying 'you haven't shown me why it's worth it.' "
                "Tie pricing back to their specific consequence: 'You said if something "
                "happened, your wife would lose the house. For $47/month — less than "
                "your cable bill — that never happens.'"
            ) if not money_ok else "Budget was manageable for this client.",
        }

        # TIME: Was urgency established?
        time_ok = flags.consequence_established
        time_details = {
            "status": "resolved" if time_ok else "unresolved",
            "consequence_established": flags.consequence_established,
            "coaching": (
                "Without urgency, there's no reason to act today. The client will "
                "'think about it' forever. Urgency comes from the CONSEQUENCE question: "
                "'What happens to your family if something happens to you tomorrow and "
                "nothing is in place?' That question creates the urgency — not your "
                "pressure. The client has to feel their OWN reason to act now."
            ) if not time_ok else "Urgency was established through consequence.",
        }

        # DECISION MAKER: Is the person on the phone the one who says yes?
        dm_persona = sm.state.persona.decision_maker
        dm_confirmed = dm_persona or any(
            o.decision_maker_confirmed for o in sm.state.objections_raised
        )
        dm_objection_raised = any(
            o.root_cause.value == "decision_maker"
            for o in sm.state.objections_raised
        )
        dm_details = {
            "status": "confirmed" if dm_confirmed else ("challenged" if dm_objection_raised else "not_tested"),
            "persona_is_dm": dm_persona,
            "dm_objection_raised": dm_objection_raised,
            "coaching": (
                "When someone says 'I need to talk to my spouse,' they're almost "
                "always the decision maker — they just don't want to decide alone. "
                "The move: 'What do you think she'd like about this?' (gets them "
                "selling it to themselves). Then: 'Let's say she had a bad day, she "
                "comes home, you bring it up, she says NO. What are you going to do?' "
                "When they say 'I'd do it anyway' — that objection is dead. They just "
                "told you they don't need permission. Lock it and move on."
            ) if not dm_confirmed else "Decision maker was confirmed.",
        }

        return {
            "money": money_details,
            "time": time_details,
            "decision_maker": dm_details,
        }

    # ── Individual Category Graders (Style-Aware) ───────────────

    def _grade_tonality(self, sm: StateManager, style: SalesStyle) -> dict:
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

        feedback_parts = []
        pros = []
        consequences = []

        if confident > nervous:
            pros.append("Confident tone signals competence and puts the client at ease.")
        if strategic_pause > 0:
            pros.append(f"Strategic pauses used {strategic_pause}x — forces client to think deeply about what you just said.")
        if whisper > 0:
            pros.append(f"Tone drops on key phrases {whisper}x — creates intimacy and importance.")
        if bad_inflection > 0:
            consequences.append(f"Upward inflection on {bad_inflection} statements — makes you sound like you're asking permission rather than guiding.")
        if nervous > 0:
            consequences.append(f"Nervous tone detected {nervous}x — clients can hear uncertainty and it erodes trust.")

        if style == SalesStyle.HIGH_ENERGY:
            feedback_parts.append("High-energy style: your confidence reads well. Watch for crossing from confident to pushy in tonality.")
        elif style == SalesStyle.CONSULTATIVE:
            feedback_parts.append("Consultative style: strategic pauses and downward inflection are your best tools. They create weight.")

        coaching = ""
        if bad_inflection > 2:
            coaching = "Record yourself for 10 calls. Every time you catch an upward inflection on a statement, pause and re-deliver it with downward inflection. It changes everything."
        elif nervous > 1:
            coaching = "Stand up while on calls. Smile. Power pose for 2 minutes before dialing. Your body affects your voice more than you think."

        return _score_with_grade(
            score, "Tonality",
            " ".join(feedback_parts) if feedback_parts else "Tonality was adequate.",
            coaching, pros, consequences,
        )

    def _grade_rapport(self, sm: StateManager, style: SalesStyle) -> dict:
        score = sm.state.hidden.rapport_score
        flags = sm.state.flags
        pros = []
        consequences = []

        feedback_parts = []
        if flags.goal_identified:
            feedback_parts.append("Goal identified.")
            pros.append("Knowing the client's goal lets you tie everything back to THEIR reason, not yours.")
            score = max(score, score + 5)
        else:
            feedback_parts.append("MISSED: Never identified the client's goal.")
            consequences.append("Without a goal, your presentation is generic — and generic doesn't close.")
            score -= 15

        if flags.why_behind_goal_identified:
            feedback_parts.append("Uncovered the WHY behind the goal.")
            pros.append("The WHY is the emotional driver. Facts tell, emotions sell.")
            score += 10
        else:
            feedback_parts.append("MISSED: Never dug into WHY the goal matters.")
            consequences.append("Without the WHY, you're selling a product. With the WHY, you're solving a problem.")
            score -= 10

        if flags.consequence_established:
            feedback_parts.append("Established consequence of inaction.")
            pros.append("The consequence question is the most powerful tool in sales. It creates urgency from the CLIENT's own words, not your pressure.")
            score += 15
        else:
            feedback_parts.append("MISSED: Never established what happens if they DON'T act.")
            consequences.append("Without consequence, 90% of 'I need to think about it' and 'let me talk to my spouse' objections become unavoidable. The client has no urgency.")
            score -= 20

        coaching = ""
        if not flags.consequence_established:
            coaching = (
                "The consequence question: 'What happens to [wife/kids/grandkids] "
                "if something happens to you and there's nothing in place?' Then be "
                "QUIET. Let the silence do the work. When they answer, THAT becomes "
                "your urgency for the rest of the call. Every objection gets answered "
                "with 'Remember, you said [their consequence].' This one question "
                "prevents 90% of smokescreens."
            )
        elif not flags.why_behind_goal_identified:
            coaching = "After the goal: 'Why is that important to you?' Simple. Powerful. Gets to the emotion."

        if style == SalesStyle.RELATIONSHIP and score > 60:
            pros.append("Your rapport-building is your superpower — just make sure it leads somewhere.")
        elif style == SalesStyle.HIGH_ENERGY and not flags.consequence_established:
            consequences.append("High-energy without consequence = pressure without purpose. The client feels sold, not served.")

        return _score_with_grade(score, "Rapport & Discovery", " ".join(feedback_parts), coaching, pros, consequences)

    def _grade_questions(self, sm: StateManager, style: SalesStyle) -> dict:
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
            return _score_with_grade(
                30, "Question Quality",
                "No questions detected.",
                "Questions are how you control the conversation. Whoever asks the questions controls the frame.",
                [], ["No questions = no discovery = no close."]
            )

        ratio = advancing / total_questions if total_questions > 0 else 0
        score = ratio * 100

        pros = []
        consequences = []
        if ratio > 0.7:
            pros.append("Most of your questions advanced the sale — efficient and purposeful.")
        if ratio < 0.4:
            consequences.append("Too many questions that don't advance the sale waste the client's time and your authority.")

        if style == SalesStyle.HIGH_ENERGY and total_questions < 5:
            consequences.append("Low question count with high energy = telling, not selling. Even high-energy closers ask questions to find the lever.")

        feedback = f"{total_questions} questions asked, {advancing} advanced the sale ({ratio * 100:.0f}% advancement rate)."
        coaching = ""
        if ratio < 0.5:
            coaching = "Every question should do one of three things: identify the goal, uncover the why, or establish the consequence. If it doesn't do one of those, cut it."

        return _score_with_grade(score, "Question Quality", feedback, coaching, pros, consequences)

    def _grade_compliance(self, sm: StateManager, ct: ComplianceTracker, style: SalesStyle) -> dict:
        summary = ct.get_compliance_summary()
        ratio = summary["ratio"]
        total = summary["total_checks"]
        frame_events = summary["frame_control_events"]
        pros = []
        consequences = []

        if total == 0:
            score = 25.0
            feedback = "No compliance checks attempted."
            consequences.append("Without micro-agreements, the client never practices saying 'yes' to you. The first 'yes' you ask for shouldn't be for their bank account.")
            coaching = "Start early: 'Grab a pen for me.' 'Does that make sense?' 'Fair enough?' Each small yes builds toward the big yes."
        else:
            score = ratio * 80 + 20
            if frame_events > 0:
                score += min(frame_events * 5, 15)
                pros.append(f"Regained frame control {frame_events}x — shows you can redirect without losing the client.")

            if ratio > 0.7:
                pros.append(f"Strong compliance rate ({ratio * 100:.0f}%) — client was following your lead.")
            elif ratio < 0.4:
                consequences.append("Low compliance rate means the client wasn't agreeing with you on small things. The big ask will feel like a leap.")

            feedback = f"{total} compliance checks, {summary['successful']} successful ({ratio * 100:.0f}%). Frame events: {frame_events}. Trend: {summary['ladder_trend']}."

            coaching = ""
            if summary["ladder_trend"] == "declining":
                coaching = "Compliance declining = you're losing them. When you feel compliance dropping, slow down, reconnect to their why, then rebuild."

        score = max(0, min(100, score))
        final = _score_with_grade(score, "Compliance & Authority", feedback, coaching, pros, consequences)
        final["authority_final"] = round(sm.state.hidden.authority_score, 1)
        return final

    def _grade_flow(self, sm: StateManager, style: SalesStyle) -> dict:
        score = 80.0 if sm.state.hidden.flow_integrity else 30.0
        pros = []
        consequences = []

        transitions = sm.state.phase_transitions
        backward = [t for t in transitions if t.get("was_backward")]
        if backward:
            score -= len(backward) * 15
            consequences.append(f"{len(backward)} backward transitions — jumping back to earlier phases confuses the client and kills trust.")
            feedback = f"Flow BROKEN. {len(backward)} backward phase transition(s) detected."
            coaching = "Intro → Rapport → Underwriting → Preframe → Present → Close. Write it on a sticky note. Never go backward."
        else:
            phases_hit = set(t["to"] for t in transitions)
            phases_hit.add(sm.state.current_phase.value)
            expected = {"intro", "rapport_discovery", "medical_underwriting", "preframing", "presentation"}
            missing = expected - phases_hit
            if missing:
                score -= len(missing) * 10
                consequences.append(f"Skipped phases: {', '.join(missing)}. Each phase sets up the next — skip one and the rest crumble.")
                feedback = f"Flow intact but {len(missing)} phase(s) skipped: {', '.join(missing)}."
                coaching = f"Cover: {', '.join(missing)}. Each phase has a job — skipping it creates objections later."
            else:
                pros.append("Clean, linear progression through all phases. The client always knew where they were.")
                feedback = "Flow was clean and linear."
                coaching = ""

        if sm.check_flag("preoccupation_broken"):
            score += 5
            pros.append("Broke preoccupation early — client's attention was captured.")
        else:
            score -= 10
            consequences.append("Never broke preoccupation — the client was still thinking about whatever they were doing when you called.")

        score = max(0, min(100, score))
        return _score_with_grade(score, "Flow & Framework", feedback, coaching, pros, consequences)

    def _grade_trust(self, sm: StateManager, style: SalesStyle) -> dict:
        trust = sm.state.hidden.trust_score
        score = trust
        pros = []
        consequences = []

        if sm.check_flag("credentials_shared"):
            pros.append("Shared credentials — legitimacy established.")
            score += 5
        else:
            consequences.append("Never shared credentials. Clients on the phone with a stranger need to know you're real.")
            score -= 10

        if trust > 70:
            pros.append(f"Final trust: {trust:.0f}/100 — client trusted you enough to share personal info and buy.")
        elif trust < 50:
            consequences.append(f"Final trust: {trust:.0f}/100 — insufficient for a close. The client didn't believe you enough.")

        coaching = ""
        if trust < 50 and style == SalesStyle.HIGH_ENERGY:
            coaching = (
                "High energy works when trust is high. When trust is low, energy feels "
                "like pressure. Build trust FIRST — credentials, empathy, name usage — "
                "then bring the energy."
            )
        elif trust < 50:
            coaching = "Trust = credentials + tonality + relevance. Share who you are, sound confident, make every question about THEM."

        score = max(0, min(100, score))
        return _score_with_grade(score, "Trust Building", f"Final trust: {trust:.0f}/100.", coaching, pros, consequences)

    def _grade_resistance(self, sm: StateManager, style: SalesStyle) -> dict:
        resistance = sm.state.hidden.sales_resistance
        score = 100.0 - resistance
        pros = []
        consequences = []

        if resistance < 30:
            pros.append("Client was ready to buy — minimal resistance remaining.")
        elif resistance < 50:
            pros.append("Resistance manageable — some concerns but closeable.")
        elif resistance > 70:
            consequences.append("Extremely high resistance. Multiple unresolved concerns.")

        if style == SalesStyle.HIGH_ENERGY and resistance > 50:
            consequences.append(
                "High-energy approach with high resistance = the client felt pushed. "
                "When you push against resistance, it pushes back harder. Consider: "
                "lower the resistance FIRST (consequence, empathy, discovery), THEN "
                "bring the energy to close."
            )
            coaching = "Resistance drops when the client feels understood, not pressured. Lead with questions, not statements."
        elif resistance > 50:
            coaching = "Resistance is a symptom, not the disease. The root cause is usually missing consequence, missing trust, or missing preframes."
        else:
            coaching = ""

        return _score_with_grade(score, "Resistance Management", f"Final resistance: {resistance:.0f}/100.", coaching, pros, consequences)

    def _grade_underwriting(self, sm: StateManager) -> dict:
        score = 50.0
        pros = []
        consequences = []

        if sm.check_flag("underwriting_clear"):
            score += 30
            pros.append("Clean underwriting — application will process smoothly.")
        else:
            consequences.append("Incomplete underwriting = declined applications, amended policies, and callbacks. Do it right the first time.")

        if sm.check_flag("medication_history_complete"):
            score += 20
            pros.append("10-year medication history covered — carrier won't kick this back.")
        else:
            consequences.append("Missing medication history is the #1 reason for application amendments. Carriers check everything.")
            score -= 10

        coaching = ""
        if not sm.check_flag("underwriting_clear"):
            coaching = (
                "Checklist: medications (name, dose, how long), conditions, hospitalizations, "
                "surgeries, tobacco, height/weight, family history (heart, cancer, diabetes), "
                "mental health, pending tests. Make it conversational, not an interrogation. "
                "'Any medications? Great, which ones? How long have you been on those?'"
            )

        score = max(0, min(100, score))
        return _score_with_grade(score, "Medical Underwriting", "", coaching, pros, consequences)

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
        pros = []
        consequences = []

        missed = [k for k, v in preframes.items() if not v]
        if not missed:
            pros.append("All preframes complete — the close will be frictionless.")
            coaching = ""
        else:
            for m in missed:
                if m == "Banking":
                    consequences.append("No banking preframe = guaranteed objection when you ask for the routing number. A 10-second preframe prevents a 5-minute objection handle.")
                elif m == "Social Security":
                    consequences.append("No SSN preframe = 'Why do you need my social?' objection. Preframe it: 'The application requires your social to verify identity — same as any insurance application.'")
                elif m == "Next Steps":
                    consequences.append("No next-steps preframe = the client doesn't know what's coming. Surprises create resistance.")
            coaching = f"Preframe BEFORE you need it. Missed: {', '.join(missed)}."

        feedback = f"Preframed {done}/{total}." + (f" Missed: {', '.join(missed)}." if missed else "")
        return _score_with_grade(score, "Preframing", feedback, coaching, pros, consequences)

    def _grade_presentation(self, sm: StateManager, style: SalesStyle) -> dict:
        score = 50.0
        flags = sm.state.flags
        pros = []
        consequences = []

        if flags.pricing_presented:
            score += 15
        else:
            consequences.append("Pricing not presented — can't close without a number.")

        if flags.coverage_aligned_to_goals:
            score += 15
            pros.append("Coverage tied to the client's stated goal — this makes the price meaningful, not abstract.")
        else:
            consequences.append("Coverage not tied to goals — a number without context is just a number. Tie it back: 'You said you want $X for [their goal].'")
            score -= 5

        if flags.benefits_explained:
            score += 10
            pros.append("Benefits explained — client understands what they're getting.")

        if flags.day_one_coverage_mentioned:
            score += 5

        if flags.term_duration_explained:
            score += 5

        coaching = ""
        if style == SalesStyle.HIGH_ENERGY and score < 70:
            coaching = "Even with energy and urgency, the presentation needs structure. State the price, tie it to their goal, explain the benefits in plain English, and ask for the business."
        elif score < 60:
            coaching = "Present simply: '[Name], based on what you told me — [their goal] — here's what I found for you. $X/month gets you $Y in coverage, effective day one, permanent, with living benefits. Does that sound like what you were looking for?'"

        score = max(0, min(100, score))
        return _score_with_grade(score, "Presentation", "", coaching, pros, consequences)

    def _grade_objections(self, sm: StateManager, style: SalesStyle) -> dict:
        objections = sm.state.objections_raised
        if not objections:
            return _score_with_grade(
                75, "Objection Handling",
                "No objections raised — either flawless preframing or short session.",
                "",
                ["Clean call with no objections is the RESULT of great preframing, not luck."],
                [],
            )

        total = len(objections)
        isolated = sum(1 for o in objections if o.isolated)
        dm_tested = sum(1 for o in objections if o.hypothetical_tested)
        resolved = sum(1 for o in objections if o.resolved)
        avg_conviction = 0.0
        if resolved > 0:
            avg_conviction = sum(
                o.resolution_conviction_score for o in objections if o.resolved
            ) / resolved

        score = 50.0
        pros = []
        consequences = []

        if total > 0:
            score += (isolated / total) * 15
            score += (resolved / total) * 25
            score += (avg_conviction / 100) * 10

        if dm_tested > 0:
            score += 10
            pros.append(f"Decision-maker tested via hypothetical {dm_tested}x — once they say 'I'd do it anyway,' that objection is dead forever.")

        not_isolated = total - isolated
        if not_isolated > 0:
            score -= not_isolated * 8
            consequences.append(
                f"{not_isolated} objection(s) handled without isolation. Isolation means: "
                "'If we solve THIS, are you good to move forward?' Without it, you're "
                "solving imaginary problems while the real one hides."
            )

        if resolved > 0:
            pros.append(f"Resolved {resolved}/{total} objections with avg conviction {avg_conviction:.0f}/100.")

        feedback = (
            f"{total} objection(s). {isolated} isolated, {resolved} resolved, "
            f"{dm_tested} decision-maker tested. Conviction: {avg_conviction:.0f}/100."
        )

        coaching = ""
        if isolated < total:
            coaching = (
                "The isolation framework: 1) Acknowledge ('I totally understand'). "
                "2) Isolate ('Is it just the [money/timing/etc], or is there something else?'). "
                "3) Test ('If we could solve that, would you be comfortable moving forward?'). "
                "4) Solve ('Here's what I can do...'). "
                "For spouse objections: 'What do you think she'd like about this?' → "
                "'Say she had a bad day, comes home, you bring it up, she says NO — "
                "what would you do?' When they say 'I'd do it anyway' — it's over. Lock it."
            )

        score = max(0, min(100, score))
        return _score_with_grade(score, "Objection Handling", feedback, coaching, pros, consequences)

    # ── Analysis Sections ───────────────────────────────────────

    def _analyze_phases(self, sm: StateManager) -> dict:
        transitions = sm.state.phase_transitions
        phase_data = {}
        for t in transitions:
            phase_name = t["to"]
            if phase_name not in phase_data:
                phase_data[phase_name] = {
                    "entered_at_turn": t["turn"],
                    "was_backward": t.get("was_backward", False),
                }
        return phase_data

    def _analyze_objections(self, sm: StateManager) -> dict:
        objections = sm.state.objections_raised
        return {
            "total": len(objections),
            "by_type": {
                "smokescreen": sum(1 for o in objections if o.objection_type == ObjectionType.SMOKESCREEN),
                "true_objection": sum(1 for o in objections if o.objection_type == ObjectionType.TRUE_OBJECTION),
                "condition": sum(1 for o in objections if o.objection_type == ObjectionType.CONDITION),
            },
            "by_root_cause": {
                "money": sum(1 for o in objections if o.root_cause.value == "money"),
                "time": sum(1 for o in objections if o.root_cause.value == "time"),
                "decision_maker": sum(1 for o in objections if o.root_cause.value == "decision_maker"),
            },
            "resolved": sum(1 for o in objections if o.resolved),
            "unresolved": sum(1 for o in objections if not o.resolved),
            "details": [
                {
                    "category": o.category.value,
                    "type": o.objection_type.value,
                    "root_cause": o.root_cause.value,
                    "text": o.text,
                    "isolated": o.isolated,
                    "hypothetical_tested": o.hypothetical_tested,
                    "resolved": o.resolved,
                    "conviction": o.resolution_conviction_score,
                }
                for o in objections
            ],
        }
