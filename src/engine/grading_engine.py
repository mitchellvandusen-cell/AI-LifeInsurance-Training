"""
GradingEngine: Produces the final JSON report card after a training session.

ADAPTIVE GRADING — This engine only grades what actually happened in the call.
If the agent got stuck on an early objection and never reached preframing,
the report card doesn't penalize them for missing preframes. Instead, it
focuses on what went wrong WHERE they got stuck and how to get past it.

Every report card reflects the ACTUAL conversation, not a template of what
a full call "should" have been.

The grading engine acts as an expert closer who has seen it all.
"""

from __future__ import annotations

import time

from src.core.state_manager import StateManager
from src.engine.compliance_tracker import ComplianceTracker
from src.models.state import ConversationPhase, ObjectionType, SalesStyle

# ── Phase order for determining what was reached ──────────────
PHASE_ORDER = [
    ConversationPhase.INTRO,
    ConversationPhase.RAPPORT_DISCOVERY,
    ConversationPhase.MEDICAL_UNDERWRITING,
    ConversationPhase.PREFRAMING,
    ConversationPhase.PRESENTATION,
    ConversationPhase.OBJECTION_HANDLING,
    ConversationPhase.CLOSE,
]

# Each grading category maps to the EARLIEST phase it requires.
# None = always scoreable regardless of how far the call got.
CATEGORY_REQUIRED_PHASE = {
    "tonality": None,
    "rapport_discovery": ConversationPhase.RAPPORT_DISCOVERY,
    "question_quality": ConversationPhase.RAPPORT_DISCOVERY,
    "compliance_authority": None,
    "flow": None,
    "trust_building": None,
    "resistance_management": None,
    "medical_underwriting": ConversationPhase.MEDICAL_UNDERWRITING,
    "preframing": ConversationPhase.PREFRAMING,
    "presentation": ConversationPhase.PRESENTATION,
    "objection_handling": None,  # Scored only if objections occurred
}

PHASE_LABELS = {
    "intro": "Introduction",
    "rapport_discovery": "Rapport & Discovery",
    "medical_underwriting": "Medical Underwriting",
    "preframing": "Preframing",
    "presentation": "Presentation",
    "objection_handling": "Objection Handling",
    "close": "Close",
}


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
        "status": "scored",
        "feedback": feedback,
        "coaching": coaching,
        "pros": pros or [],
        "consequences": consequences or [],
    }


def _not_reached(label: str, phase_needed: str, context_tip: str = "") -> dict:
    """Return a category result for a phase that was never reached."""
    phase_label = PHASE_LABELS.get(phase_needed, phase_needed.replace("_", " ").title())
    return {
        "metric": label,
        "score": None,
        "grade": "N/R",
        "status": "not_reached",
        "feedback": f"Conversation ended before the {phase_label} phase.",
        "coaching": context_tip or (
            f"Focus on getting past earlier objections so you can reach "
            f"the {phase_label} part of the call."
        ),
        "pros": [],
        "consequences": [],
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
    """Produces comprehensive, adaptive, phase-aware grading report."""

    def grade(self, sm: StateManager, ct: ComplianceTracker) -> dict:
        """Generate the complete report card — only grades what actually happened."""
        # Detect sales style before grading
        style = sm.detect_sales_style()
        style_info = STYLE_ANALYSIS.get(style, STYLE_ANALYSIS[SalesStyle.UNKNOWN])

        # ── Determine call context ───────────────────────────────
        phases_reached = self._get_phases_reached(sm)
        call_duration = sm.state.elapsed_seconds or (time.time() - sm.state.started_at)
        last_phase = sm.state.current_phase
        early_objections = self._detect_early_objections(sm)
        is_short_call = call_duration < 120  # Under 2 minutes

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
            # ── Adaptive context (NEW) ──
            "call_context": {
                "duration_seconds": round(call_duration),
                "is_short_call": is_short_call,
                "phases_reached": [p.value for p in phases_reached],
                "last_phase": last_phase.value,
                "last_phase_label": PHASE_LABELS.get(last_phase.value, last_phase.value),
                "total_turns": sm.state.turn_number,
                "early_smokescreens": [
                    {
                        "text": o.text,
                        "category": o.category.value,
                        "turn": o.raised_at_turn,
                    }
                    for o in early_objections
                ],
                "call_ended_early": is_short_call or len(phases_reached) <= 2,
                "adaptive_note": self._build_adaptive_note(
                    sm, phases_reached, early_objections, is_short_call
                ),
            },
            "categories": {},
            "deal_killers": {},
            "phase_analysis": {},
            "objection_analysis": {},
            "top_strengths": [],
            "areas_for_improvement": [],
        }

        # ── Category Scores (ADAPTIVE) ─────────────────────────────

        scores = {}
        for cat_key, required_phase in CATEGORY_REQUIRED_PHASE.items():
            if required_phase and required_phase not in phases_reached:
                # Phase not reached — don't penalize
                label = self._category_label(cat_key)
                scores[cat_key] = _not_reached(
                    label,
                    required_phase.value,
                    self._not_reached_tip(cat_key, sm, phases_reached),
                )
            else:
                # Phase was reached — score normally
                scores[cat_key] = self._grade_category(cat_key, sm, ct, style)

        report["categories"] = scores

        # ── Overall Score (only from scored categories) ──────────────

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

        # Only include categories that were actually scored
        scored_cats = {
            k: v for k, v in scores.items()
            if v.get("status") == "scored" and v.get("score") is not None
        }
        active_weights = {k: weights.get(k, 0.05) for k in scored_cats}
        weight_sum = sum(active_weights.values())

        if weight_sum > 0:
            total = sum(
                scored_cats[cat]["score"] * (active_weights[cat] / weight_sum)
                for cat in scored_cats
            )
        else:
            total = 0.0

        report["overall_score"] = round(total, 1)
        report["overall_grade"] = _letter_grade(total)

        # ── Deal-Killers (ADAPTIVE) ──────────────────────────────

        report["deal_killers"] = self._analyze_deal_killers(sm, phases_reached)

        # ── Would This Close? (ADAPTIVE) ─────────────────────────

        report.update(
            self._analyze_close_probability(sm, phases_reached)
        )

        # ── Phase & Objection Analysis ───────────────────────────

        report["phase_analysis"] = self._analyze_phases(sm)
        report["objection_analysis"] = self._analyze_objections(sm)

        # ── Strengths & Improvements (only from scored) ──────────

        scored_items = [
            (cat, data)
            for cat, data in scores.items()
            if data.get("status") == "scored" and data.get("score") is not None
        ]
        sorted_cats = sorted(scored_items, key=lambda x: x[1]["score"], reverse=True)

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

    # ── Adaptive Context Helpers ──────────────────────────────────

    def _get_phases_reached(self, sm: StateManager) -> list[ConversationPhase]:
        """Determine which phases were actually entered during the conversation."""
        phases = {ConversationPhase.INTRO}  # Always start in intro
        phases.add(sm.state.current_phase)
        for t in sm.state.phase_transitions:
            try:
                phases.add(ConversationPhase(t["to"]))
            except (ValueError, KeyError):
                pass
        return sorted(phases, key=lambda p: PHASE_ORDER.index(p))

    def _detect_early_objections(self, sm: StateManager) -> list:
        """Find objections raised in the first 30 seconds or first 2 turns.
        These are almost always smokescreens — reflexive pushback, not real."""
        early = []
        for o in sm.state.objections_raised:
            if o.raised_at_turn <= 2:
                early.append(o)
        return early

    def _build_adaptive_note(
        self, sm, phases_reached, early_objections, is_short_call
    ) -> str:
        """Build a human-readable note explaining why the report card is adaptive."""
        parts = []

        if is_short_call:
            duration = sm.state.elapsed_seconds or (time.time() - sm.state.started_at)
            parts.append(
                f"This was a short call ({int(duration)}s). The report card only "
                f"evaluates what actually happened — categories for phases you "
                f"didn't reach are marked 'Not Reached' and don't affect your score."
            )

        if early_objections:
            obj_texts = [o.text[:60] for o in early_objections]
            parts.append(
                f"The client threw early objection(s) ({', '.join(obj_texts)}). "
                f"Objections in the first 30 seconds are almost always smokescreens — "
                f"reflexive pushback, not real concerns. The key is getting past them "
                f"to start the actual conversation."
            )

        if len(phases_reached) <= 2:
            last = PHASE_LABELS.get(
                sm.state.current_phase.value, sm.state.current_phase.value
            )
            parts.append(
                f"The conversation didn't progress past {last}. "
                f"Your score reflects only the phases you reached."
            )

        return " ".join(parts) if parts else ""

    def _not_reached_tip(
        self, cat_key: str, sm: StateManager, phases_reached: list
    ) -> str:
        """Context-specific tip for a category that wasn't reached."""
        tips = {
            "rapport_discovery": (
                "The conversation ended before discovery. Focus on handling the "
                "initial objection to buy time: 'I completely understand — I just "
                "need 30 seconds to make sure I have the right file. Can you grab "
                "a pen real quick?' This re-engages them."
            ),
            "question_quality": (
                "You didn't get to ask discovery questions. The first priority is "
                "breaking preoccupation and getting the client to stay on the line."
            ),
            "medical_underwriting": (
                "The call ended before underwriting. This section requires getting "
                "through discovery first — focus on earlier phases."
            ),
            "preframing": (
                "The call ended before you could preframe. Preframing happens after "
                "underwriting — work on getting through the earlier objections first."
            ),
            "presentation": (
                "The call ended before the presentation. Focus on mastering the "
                "earlier phases so you earn the right to present."
            ),
        }
        return tips.get(cat_key, "")

    def _category_label(self, cat_key: str) -> str:
        """Human-readable label for a category key."""
        labels = {
            "tonality": "Tonality",
            "rapport_discovery": "Rapport & Discovery",
            "question_quality": "Question Quality",
            "compliance_authority": "Confidence & Conversational Control",
            "flow": "Flow & Framework",
            "trust_building": "Trust Building",
            "resistance_management": "Resistance Management",
            "medical_underwriting": "Medical Underwriting",
            "preframing": "Preframing",
            "presentation": "Presentation",
            "objection_handling": "Objection Handling",
        }
        return labels.get(cat_key, cat_key.replace("_", " ").title())

    def _grade_category(
        self, cat_key: str, sm: StateManager, ct: ComplianceTracker, style: SalesStyle
    ) -> dict:
        """Dispatch to the appropriate grader for a category."""
        graders = {
            "tonality": lambda: self._grade_tonality(sm, style),
            "rapport_discovery": lambda: self._grade_rapport(sm, style),
            "question_quality": lambda: self._grade_questions(sm, style),
            "compliance_authority": lambda: self._grade_compliance(sm, ct, style),
            "flow": lambda: self._grade_flow(sm, style),
            "trust_building": lambda: self._grade_trust(sm, style),
            "resistance_management": lambda: self._grade_resistance(sm, style),
            "medical_underwriting": lambda: self._grade_underwriting(sm),
            "preframing": lambda: self._grade_preframing(sm),
            "presentation": lambda: self._grade_presentation(sm, style),
            "objection_handling": lambda: self._grade_objections(sm, style),
        }
        grader = graders.get(cat_key)
        if grader:
            return grader()
        return _score_with_grade(0, cat_key, "Unknown category.")

    # ── Deal-Killers (ADAPTIVE) ──────────────────────────────────

    def _analyze_deal_killers(self, sm: StateManager, phases_reached: list) -> dict:
        """The three things that kill every deal — adapted to what actually happened."""
        flags = sm.state.flags
        reached_presentation = ConversationPhase.PRESENTATION in phases_reached
        reached_discovery = ConversationPhase.RAPPORT_DISCOVERY in phases_reached
        reached_preframing = ConversationPhase.PREFRAMING in phases_reached

        # MONEY
        if not reached_presentation and not reached_preframing:
            money_details = {
                "status": "not_applicable",
                "coaching": (
                    "The conversation ended before pricing came up. Money objections "
                    "become relevant once you present — focus on getting there first."
                ),
            }
        else:
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

        # TIME / URGENCY
        # "Call me back" IS a time-related objection even in intro
        time_objection_in_call = any(
            o.root_cause.value == "time" or o.category.value in ("timing", "think_about_it")
            for o in sm.state.objections_raised
        )
        if not reached_discovery and not time_objection_in_call:
            time_details = {
                "status": "not_applicable",
                "coaching": (
                    "The call ended before urgency could be established. Urgency "
                    "comes from the consequence question in discovery — focus on "
                    "getting past the initial objection first."
                ),
            }
        elif time_objection_in_call and not reached_discovery:
            # They hit a time objection early (like "call me back")
            time_details = {
                "status": "early_objection",
                "coaching": (
                    "'Call me back' or 'now isn't a good time' in the first 30 seconds "
                    "is almost always a smokescreen — they're not actually busy, they're "
                    "trying to get off the phone with a stranger. The handle: 'I completely "
                    "understand — I just need 30 seconds to make sure I've got the right "
                    "information on file. Can you grab a pen real quick?' This buys you time "
                    "to break preoccupation and earn the conversation. If they truly can't "
                    "talk: 'No problem — when's the best time to reach you, morning or afternoon?' "
                    "Pin them to a specific callback."
                ),
            }
        else:
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

        # DECISION MAKER
        dm_objection_raised = any(
            o.root_cause.value == "decision_maker"
            for o in sm.state.objections_raised
        )
        if not dm_objection_raised and not reached_presentation:
            dm_details = {
                "status": "not_applicable",
                "coaching": (
                    "Decision-maker concerns didn't come up in this call. They "
                    "typically surface during presentation or close — focus on "
                    "getting through earlier phases first."
                ),
            }
        else:
            dm_persona = sm.state.persona.decision_maker
            dm_confirmed = dm_persona or any(
                o.decision_maker_confirmed for o in sm.state.objections_raised
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

    # ── Close Probability (ADAPTIVE) ─────────────────────────────

    def _analyze_close_probability(self, sm: StateManager, phases_reached: list) -> dict:
        """Adaptive close probability — only counts factors that were reachable."""
        all_factors = {
            "trust_above_60": {
                "met": sm.state.hidden.trust_score > 60,
                "always_applicable": True,
            },
            "authority_above_50": {
                "met": sm.state.hidden.authority_score > 50,
                "always_applicable": True,
            },
            "resistance_below_45": {
                "met": sm.state.hidden.sales_resistance < 45,
                "always_applicable": True,
            },
            "flow_intact": {
                "met": sm.state.hidden.flow_integrity,
                "always_applicable": True,
            },
            "consequence_established": {
                "met": sm.check_flag("consequence_established"),
                "requires": ConversationPhase.RAPPORT_DISCOVERY,
            },
            "preframed_banking": {
                "met": sm.check_flag("preframed_banking"),
                "requires": ConversationPhase.PREFRAMING,
            },
            "preframed_social_security": {
                "met": sm.check_flag("preframed_social_security"),
                "requires": ConversationPhase.PREFRAMING,
            },
            "urgency_created": {
                "met": sm.check_flag("consequence_established"),
                "requires": ConversationPhase.RAPPORT_DISCOVERY,
            },
            "decision_maker_confirmed": {
                "met": sm.state.persona.decision_maker or any(
                    o.decision_maker_confirmed for o in sm.state.objections_raised
                ),
                "always_applicable": True,
            },
        }

        applicable_factors = {}
        for name, info in all_factors.items():
            required = info.get("requires")
            if info.get("always_applicable") or (required and required in phases_reached):
                applicable_factors[name] = info["met"]

        met = sum(1 for v in applicable_factors.values() if v)
        total_applicable = len(applicable_factors) or 1
        close_pct = (met / total_applicable) * 100

        return {
            "would_close": close_pct >= 70,
            "close_probability": round(close_pct, 1),
            "close_factors": applicable_factors,
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
        """Grade confidence and conversational control.

        Authority is NOT about being aggressive or 'alpha'. It's about:
        - Confidence in your voice and delivery
        - Control of the conversation flow
        - The client following your lead because they trust your expertise
        - Building a compliance ladder of micro-agreements
        - Redirecting gracefully when the client tries to take over
        """
        summary = ct.get_compliance_summary()
        ratio = summary["ratio"]
        total = summary["total_checks"]
        frame_events = summary["frame_control_events"]
        authority = sm.state.hidden.authority_score
        pros = []
        consequences = []

        if total == 0:
            score = 25.0
            feedback = "No compliance checks attempted."
            consequences.append(
                "Without micro-agreements, the client never practices saying 'yes' "
                "to you. Build a compliance ladder — small agreements that lead to "
                "the big one."
            )
            coaching = (
                "Confidence comes from preparation and control. Start with small "
                "requests: 'Grab a pen for me.' 'Does that make sense?' 'Fair enough?' "
                "Each small 'yes' builds the client's comfort following your lead. "
                "This isn't about being pushy — it's about guiding the conversation "
                "so the client always knows what's happening next."
            )
        else:
            score = ratio * 80 + 20
            if frame_events > 0:
                score += min(frame_events * 5, 15)
                pros.append(
                    f"Redirected the conversation {frame_events}x when the client "
                    f"went off track — this shows confident leadership without being "
                    f"aggressive."
                )

            if ratio > 0.7:
                pros.append(
                    f"Strong compliance rate ({ratio * 100:.0f}%) — the client "
                    f"was comfortable following your lead."
                )
            elif ratio < 0.4:
                consequences.append(
                    "Low compliance rate means the client wasn't agreeing with small "
                    "things. When someone doesn't say 'yes' to easy questions, asking "
                    "for their bank account feels like a giant leap."
                )

            feedback = (
                f"{total} compliance checks, {summary['successful']} successful "
                f"({ratio * 100:.0f}%). Frame redirects: {frame_events}. "
                f"Trend: {summary['ladder_trend']}."
            )

            coaching = ""
            if summary["ladder_trend"] == "declining":
                coaching = (
                    "The client's compliance was declining — they were pulling away. "
                    "When you feel this happening, slow down, reconnect to their WHY, "
                    "and rebuild. Don't push harder — that makes it worse. Show empathy, "
                    "acknowledge their concern, then gently guide back."
                )

        # Authority-specific coaching (confidence, not aggression)
        if authority < 40:
            if not coaching:
                coaching = (
                    "Authority isn't about being loud or dominant — it's about being "
                    "so prepared and confident that the client naturally follows your "
                    "lead. Think of a doctor: they don't yell at you to take your "
                    "medicine — they explain why you need it, and you trust them. "
                    "Build authority through: 1) Credentials — tell them who you are "
                    "and why you're qualified. 2) Certainty — speak in statements, not "
                    "questions. 'Here's what I recommend' not 'Would you maybe want...?' "
                    "3) Structure — always know what comes next. 4) Empathy — listening "
                    "builds more authority than talking."
                )
            pros_to_add = []
        elif authority > 70:
            pros.append(
                f"Strong conversational confidence ({authority:.0f}/100) — you guided "
                f"the call with natural leadership."
            )

        score = max(0, min(100, score))
        final = _score_with_grade(
            score, "Confidence & Conversational Control",
            feedback, coaching, pros, consequences,
        )
        final["authority_final"] = round(authority, 1)
        return final

    def _grade_flow(self, sm: StateManager, style: SalesStyle) -> dict:
        """Grade flow — ADAPTIVE: only penalize for missing phases that were reachable."""
        phases_reached = self._get_phases_reached(sm)
        score = 80.0 if sm.state.hidden.flow_integrity else 30.0
        pros = []
        consequences = []

        transitions = sm.state.phase_transitions
        backward = [t for t in transitions if t.get("was_backward")]
        if backward:
            score -= len(backward) * 15
            consequences.append(f"{len(backward)} backward transitions — jumping back to earlier phases confuses the client and kills trust.")
            feedback = f"Flow BROKEN. {len(backward)} backward phase transition(s) detected."
            coaching = "Intro -> Rapport -> Underwriting -> Preframe -> Present -> Close. Write it on a sticky note. Never go backward."
        else:
            # Only flag "missing" phases if the call got far enough that they
            # should have been covered. E.g. if we're in presentation but
            # skipped underwriting, that's a real skip. But if we never got
            # past intro, missing everything after is expected, not a failure.
            last_phase_idx = max(
                (PHASE_ORDER.index(p) for p in phases_reached),
                default=0,
            )
            phases_hit = set(p.value for p in phases_reached)
            # Only check phases UP TO the last phase reached
            expected_up_to = {
                PHASE_ORDER[i].value
                for i in range(last_phase_idx + 1)
                if PHASE_ORDER[i] != ConversationPhase.OBJECTION_HANDLING
            }
            missing = expected_up_to - phases_hit
            if missing:
                score -= len(missing) * 10
                missing_labels = [PHASE_LABELS.get(m, m) for m in missing]
                consequences.append(f"Skipped phases: {', '.join(missing_labels)}. Each phase sets up the next.")
                feedback = f"Flow intact but skipped {len(missing)} phase(s): {', '.join(missing_labels)}."
                coaching = f"Cover: {', '.join(missing_labels)}. Each phase has a job — skipping it creates objections later."
            else:
                if len(phases_reached) <= 2:
                    feedback = f"Call ended early in {PHASE_LABELS.get(sm.state.current_phase.value, 'intro')} — flow was linear for the phases covered."
                    coaching = "Focus on getting past early objections to cover more ground."
                else:
                    pros.append("Clean, linear progression through all phases covered.")
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

        # Identify early smokescreens
        early_smokescreens = [
            o for o in objections if o.raised_at_turn <= 2
        ]

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

        # Early smokescreen recognition
        if early_smokescreens:
            smokescreen_texts = [o.text[:40] for o in early_smokescreens]
            feedback_prefix = (
                f"Early smokescreen(s) detected: {', '.join(smokescreen_texts)}. "
                f"Objections in the first 30 seconds are almost always reflexive — "
                f"the client is trying to end a call with a stranger, not raising "
                f"a real concern. "
            )
        else:
            feedback_prefix = ""

        feedback = (
            feedback_prefix
            + f"{total} objection(s). {isolated} isolated, {resolved} resolved, "
            f"{dm_tested} decision-maker tested. Conviction: {avg_conviction:.0f}/100."
        )

        coaching = ""
        if early_smokescreens and not any(o.resolved for o in early_smokescreens):
            coaching = (
                "For early smokescreens ('call me back', 'not interested', 'I already "
                "have coverage'): Don't try to handle them logically — the client isn't "
                "thinking logically yet. They're reflexively trying to end the call. "
                "Pattern interrupt: 'I completely understand — I'm just updating your "
                "file real quick. While I have you, can you grab a pen?' This bypasses "
                "the reflex and engages them. Once they're engaged, the real conversation starts."
            )
        elif isolated < total:
            coaching = (
                "The isolation framework: 1) Acknowledge ('I totally understand'). "
                "2) Isolate ('Is it just the [money/timing/etc], or is there something else?'). "
                "3) Test ('If we could solve that, would you be comfortable moving forward?'). "
                "4) Solve ('Here's what I can do...'). "
                "For spouse objections: 'What do you think she'd like about this?' -> "
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
                    "early_smokescreen": o.raised_at_turn <= 2,
                }
                for o in objections
            ],
        }
