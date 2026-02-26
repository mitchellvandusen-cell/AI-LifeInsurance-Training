"""
Homework Engine
===============

Analyzes patterns across multiple sessions to identify systemic skill gaps
and generate targeted homework assignments.

This is not single-session grading. This looks at 10+ calls simultaneously
to find the patterns a single session cannot reveal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class HomeworkAssignment:
    """A single homework assignment targeting a specific skill gap."""
    skill_area: str              # e.g. "tonality", "discovery", "objection_handling"
    priority: int                # 1 = highest priority (biggest impact on close rate)
    title: str
    description: str             # What to practice and why
    module_key: str              # Training module to use
    drills: list[str]            # Specific exercises to complete
    success_criteria: list[str]  # How to know you have improved
    sessions_to_complete: int    # Recommended practice sessions


@dataclass
class HomeworkReport:
    """Complete homework report from cross-session analysis."""
    user_id: str
    sessions_analyzed: int
    overall_assessment: str           # Big picture narrative
    strengths: list[dict]             # What they do well consistently
    weaknesses: list[dict]            # Patterns that cost closes
    assignments: list[HomeworkAssignment]
    recommended_focus_order: list[str]  # Priority order of modules


class HomeworkEngine:
    """
    Analyzes report cards across sessions to find patterns and generate
    targeted homework.
    """

    def __init__(self, min_sessions: int = 5):
        self.min_sessions = min_sessions

    def analyze(self, report_cards: list[dict]) -> Optional[HomeworkReport]:
        """
        Analyze multiple report cards and generate homework.

        report_cards: list of report card dicts from the database,
                     each containing full_report, categories, etc.
        """
        if len(report_cards) < self.min_sessions:
            return None

        user_id = str(report_cards[0].get("user_id", "unknown"))

        # Extract category scores across all sessions
        all_scores = self._extract_all_scores(report_cards)
        all_reports = self._extract_full_reports(report_cards)

        # Analyze patterns
        tonality_analysis = self._analyze_tonality_patterns(all_scores, all_reports)
        discovery_analysis = self._analyze_discovery_patterns(all_scores, all_reports)
        objection_analysis = self._analyze_objection_patterns(all_scores, all_reports)
        flow_analysis = self._analyze_flow_patterns(all_scores, all_reports)
        close_analysis = self._analyze_close_patterns(all_scores, all_reports)

        # Build strengths and weaknesses
        strengths = self._identify_strengths(all_scores)
        weaknesses = self._identify_weaknesses(all_scores)

        # Generate assignments based on patterns
        assignments = []
        analyses = [
            tonality_analysis,
            discovery_analysis,
            objection_analysis,
            flow_analysis,
            close_analysis,
        ]
        for analysis in analyses:
            if analysis["needs_work"]:
                assignments.append(self._build_assignment(analysis))

        # Sort by priority (biggest impact on close rate first)
        assignments.sort(key=lambda a: a.priority)

        # Build overall assessment narrative
        overall = self._build_overall_assessment(
            len(report_cards), all_scores, strengths, weaknesses, assignments
        )

        # Focus order
        focus_order = [a.module_key for a in assignments]

        return HomeworkReport(
            user_id=user_id,
            sessions_analyzed=len(report_cards),
            overall_assessment=overall,
            strengths=strengths,
            weaknesses=weaknesses,
            assignments=assignments,
            recommended_focus_order=focus_order,
        )

    def _extract_all_scores(self, report_cards: list[dict]) -> dict:
        """Extract category scores from all sessions into a unified structure."""
        import json
        scores = {}
        for rc in report_cards:
            cats = rc.get("categories", {})
            if isinstance(cats, str):
                cats = json.loads(cats)

            for cat_key, cat_data in (cats.items() if isinstance(cats, dict) else []):
                if cat_key not in scores:
                    scores[cat_key] = []
                score = cat_data.get("score", 0) if isinstance(cat_data, dict) else 0
                scores[cat_key].append(score)

        return scores

    def _extract_full_reports(self, report_cards: list[dict]) -> list[dict]:
        """Extract full reports from report cards."""
        import json
        reports = []
        for rc in report_cards:
            fr = rc.get("full_report", {})
            if isinstance(fr, str):
                fr = json.loads(fr)
            if fr:
                reports.append(fr)
        return reports

    def _avg(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 0

    def _trend(self, values: list[float]) -> str:
        """Determine if scores are improving, declining, or flat."""
        if len(values) < 3:
            return "insufficient_data"
        first_half = self._avg(values[:len(values) // 2])
        second_half = self._avg(values[len(values) // 2:])
        diff = second_half - first_half
        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        return "flat"

    def _analyze_tonality_patterns(self, scores: dict, reports: list) -> dict:
        """Check for systemic tonality issues."""
        tonality_scores = scores.get("tonality", [])
        avg = self._avg(tonality_scores)
        trend = self._trend(tonality_scores)

        needs_work = avg < 65 or trend == "declining"
        indicators = []

        if avg < 50:
            indicators.append("Consistently low tonality scores — monotone or mismatched delivery")
        if avg < 65:
            indicators.append("Tonality not reinforcing the message — voice working against the words")
        if trend == "declining":
            indicators.append("Tonality declining over sessions — may be developing bad habits")

        return {
            "area": "tonality",
            "needs_work": needs_work,
            "avg_score": round(avg, 1),
            "trend": trend,
            "indicators": indicators,
            "impact": "high" if avg < 50 else "medium",
        }

    def _analyze_discovery_patterns(self, scores: dict, reports: list) -> dict:
        """Check for systemic discovery/rapport issues."""
        rapport_scores = scores.get("rapport_discovery", [])
        question_scores = scores.get("question_quality", [])

        rapport_avg = self._avg(rapport_scores)
        question_avg = self._avg(question_scores)
        combined_avg = (rapport_avg + question_avg) / 2

        # Check if consequence is consistently missed
        consequence_missed = 0
        for r in reports:
            close_factors = r.get("close_factors", {})
            if not close_factors.get("consequence_established"):
                consequence_missed += 1
        consequence_miss_rate = consequence_missed / len(reports) if reports else 0

        needs_work = combined_avg < 65 or consequence_miss_rate > 0.5
        indicators = []

        if rapport_avg < 60:
            indicators.append("Rapport scores consistently low — not building human connection")
        if question_avg < 60:
            indicators.append("Question quality weak — not asking advancing questions")
        if consequence_miss_rate > 0.5:
            indicators.append(
                f"Consequence not established in {consequence_miss_rate * 100:.0f}% of sessions — "
                "this is the #1 reason for lost closes"
            )

        return {
            "area": "discovery",
            "needs_work": needs_work,
            "avg_score": round(combined_avg, 1),
            "trend": self._trend(rapport_scores),
            "indicators": indicators,
            "impact": "critical" if consequence_miss_rate > 0.5 else "high",
            "consequence_miss_rate": round(consequence_miss_rate * 100, 1),
        }

    def _analyze_objection_patterns(self, scores: dict, reports: list) -> dict:
        """Check for systemic objection handling issues."""
        oh_scores = scores.get("objection_handling", [])
        resistance_scores = scores.get("resistance_management", [])

        oh_avg = self._avg(oh_scores)
        resistance_avg = self._avg(resistance_scores)
        combined = (oh_avg + resistance_avg) / 2

        # Check objection resolution patterns
        total_raised = 0
        total_resolved = 0
        for r in reports:
            obj_analysis = r.get("objection_analysis", {})
            total_raised += obj_analysis.get("total_raised", 0)
            total_resolved += obj_analysis.get("total_resolved", 0)

        resolution_rate = total_resolved / total_raised if total_raised > 0 else 0

        needs_work = combined < 60 or resolution_rate < 0.4
        indicators = []

        if resolution_rate < 0.3:
            indicators.append("Very low objection resolution rate — objections are ending sales")
        if oh_avg < 55:
            indicators.append("Not isolating objections before attempting to resolve them")
        if resistance_avg < 55:
            indicators.append("Resistance management weak — not looping back to value")

        return {
            "area": "objection_handling",
            "needs_work": needs_work,
            "avg_score": round(combined, 1),
            "trend": self._trend(oh_scores),
            "indicators": indicators,
            "impact": "critical" if resolution_rate < 0.3 else "high",
            "resolution_rate": round(resolution_rate * 100, 1),
        }

    def _analyze_flow_patterns(self, scores: dict, reports: list) -> dict:
        """Check for structural/flow issues across sessions."""
        flow_scores = scores.get("flow", [])
        preframing_scores = scores.get("preframing", [])

        flow_avg = self._avg(flow_scores)
        preframe_avg = self._avg(preframing_scores)
        combined = (flow_avg + preframe_avg) / 2

        # Check for phase skipping patterns
        flow_broken_count = 0
        for r in reports:
            close_factors = r.get("close_factors", {})
            if not close_factors.get("flow_intact"):
                flow_broken_count += 1
        flow_break_rate = flow_broken_count / len(reports) if reports else 0

        needs_work = combined < 60 or flow_break_rate > 0.4
        indicators = []

        if flow_avg < 55:
            indicators.append("Conversation lacks structure — jumping between topics")
        if preframe_avg < 55:
            indicators.append("Not preframing sensitive requests — causing trust damage at close")
        if flow_break_rate > 0.4:
            indicators.append(f"Flow integrity broken in {flow_break_rate * 100:.0f}% of sessions")

        return {
            "area": "flow_control",
            "needs_work": needs_work,
            "avg_score": round(combined, 1),
            "trend": self._trend(flow_scores),
            "indicators": indicators,
            "impact": "high" if flow_break_rate > 0.4 else "medium",
        }

    def _analyze_close_patterns(self, scores: dict, reports: list) -> dict:
        """Check closing patterns."""
        trust_scores = scores.get("trust_building", [])
        compliance_scores = scores.get("compliance_authority", [])

        trust_avg = self._avg(trust_scores)
        compliance_avg = self._avg(compliance_scores)

        # Close probability trend
        close_probs = [r.get("close_probability", 0) for r in reports]
        close_avg = self._avg(close_probs)
        would_close_count = sum(1 for r in reports if r.get("would_close"))
        close_rate = would_close_count / len(reports) if reports else 0

        # High rapport but low close = not transitioning from rapport to close
        rapport_close_gap = trust_avg > 65 and close_avg < 50

        needs_work = close_rate < 0.3 or rapport_close_gap
        indicators = []

        if close_rate < 0.3:
            indicators.append(f"Would-close rate only {close_rate * 100:.0f}% — below acceptable threshold")
        if rapport_close_gap:
            indicators.append("High rapport but low close rate — building relationship but not transitioning to sale")
        if compliance_avg < 50:
            indicators.append("Not building compliance ladder — no pattern of small yeses before the big ask")

        return {
            "area": "closing",
            "needs_work": needs_work,
            "avg_score": round(close_avg, 1),
            "trend": self._trend(close_probs),
            "indicators": indicators,
            "impact": "critical" if close_rate < 0.2 else "high",
            "close_rate": round(close_rate * 100, 1),
        }

    def _identify_strengths(self, scores: dict) -> list[dict]:
        """Find consistently strong areas."""
        strengths = []
        for cat, values in scores.items():
            avg = self._avg(values)
            trend = self._trend(values)
            if avg >= 70:
                strengths.append({
                    "category": cat,
                    "avg_score": round(avg, 1),
                    "trend": trend,
                    "note": f"Consistently strong in {cat.replace('_', ' ')}",
                })
        strengths.sort(key=lambda s: s["avg_score"], reverse=True)
        return strengths[:5]

    def _identify_weaknesses(self, scores: dict) -> list[dict]:
        """Find consistently weak areas."""
        weaknesses = []
        for cat, values in scores.items():
            avg = self._avg(values)
            trend = self._trend(values)
            if avg < 60:
                weaknesses.append({
                    "category": cat,
                    "avg_score": round(avg, 1),
                    "trend": trend,
                    "note": f"{cat.replace('_', ' ')} needs focused practice",
                })
        weaknesses.sort(key=lambda w: w["avg_score"])
        return weaknesses[:5]

    def _build_assignment(self, analysis: dict) -> HomeworkAssignment:
        """Build a homework assignment from an analysis result."""
        area = analysis["area"]

        assignment_map = {
            "tonality": {
                "module": "tonality_mastery",
                "title": "Tonality Transformation",
                "description": (
                    "Your voice is not reinforcing your message. When your tonality "
                    "does not match your intent, the prospect hears uncertainty even when "
                    "your words are confident. This module will rebuild your vocal delivery "
                    "from the ground up."
                ),
                "drills": [
                    "Declarative drill: Practice price statements with downward inflection",
                    "Whisper drill: Deliver consequence questions at 60% volume",
                    "Pause drill: Ask consequence question then hold silence for 4 seconds",
                    "Certainty drill: Conviction statements with full confidence",
                    "Shift drill: Two tones in one sentence",
                ],
                "criteria": [
                    "Price statements consistently delivered with downward inflection",
                    "At least 2 strategic pauses per session",
                    "Tone varies appropriately by context (not monotone)",
                    "Tonality score above 70 in next 3 sessions",
                ],
                "sessions": 5,
                "priority": 2,
            },
            "discovery": {
                "module": "question_mastery",
                "title": "Discovery Deep Dive",
                "description": (
                    "You are not getting deep enough in discovery. The consequence — what "
                    "happens if they DON'T act — is the foundation of urgency. Without it, "
                    "every objection about timing is unbeatable. This is your #1 priority."
                ),
                "drills": [
                    "Goal-Why-Consequence sequence: Find all three in every practice",
                    "Open question drill: 10 discovery questions, all open-ended",
                    "Mirroring practice: Mirror the prospect at least 3 times per call",
                    "Consequence question practice: Delivery with weight and pause",
                ],
                "criteria": [
                    "Consequence established in 80%+ of sessions",
                    "Goal and Why identified before moving to underwriting",
                    "Question quality score above 70",
                    "At least one mirror per discovery phase",
                ],
                "sessions": 5,
                "priority": 1,
            },
            "objection_handling": {
                "module": "objection_handling",
                "title": "Objection Mastery",
                "description": (
                    "Objections are ending your sales. The pattern shows you are either "
                    "giving up at the first no or trying to resolve without isolating first. "
                    "This module will make objections your opportunity to close."
                ),
                "drills": [
                    "Isolation protocol: Three-test sequence on every objection",
                    "Root cause identification: Surface → real barrier",
                    "Straight line loop: Acknowledge, empathize, redirect, ramp, close",
                    "Spouse deferral handling: Hypothetical escalation",
                    "Objection gauntlet: Handle 5 objections in rapid succession",
                ],
                "criteria": [
                    "Objection resolution rate above 50%",
                    "Every objection isolated before resolution attempt",
                    "Root cause identified correctly in 80%+ of objections",
                    "Conviction score above 60 on resolution attempts",
                ],
                "sessions": 5,
                "priority": 1,
            },
            "flow_control": {
                "module": "preframing_control",
                "title": "Structure & Frame Control",
                "description": (
                    "Your conversations lack structure. Without a clear flow, the prospect "
                    "feels lost, trust erodes, and sensitive requests feel like ambushes. "
                    "This module teaches you to lead the conversation with confidence."
                ),
                "drills": [
                    "Preframe every sensitive request before asking",
                    "Frame recovery: Answer-bridge-redirect when prospect takes control",
                    "Compliance ladder: Build 8+ micro-commitments before close",
                    "Roadmap setting: Tell the prospect what's coming before it comes",
                ],
                "criteria": [
                    "Flow integrity maintained in 80%+ of sessions",
                    "All sensitive requests preframed",
                    "Frame recovered within 2 turns when lost",
                    "Preframing score above 70",
                ],
                "sessions": 4,
                "priority": 2,
            },
            "closing": {
                "module": "preframing_control",
                "title": "Closing with Conviction",
                "description": (
                    "You are building rapport but not converting it into closes. The gap "
                    "between connection and commitment is where sales die. This module bridges "
                    "that gap."
                ),
                "drills": [
                    "Assumptive close transitions: Practice the seamless shift from discussion to action",
                    "Conviction check: Before closing, confirm you believe the prospect needs this",
                    "Summary close: Recap Goal-Why-Consequence and present solution as logical answer",
                    "Post-objection close: After handling an objection, close again immediately",
                ],
                "criteria": [
                    "Would-close rate above 50%",
                    "Close attempt made within 2 turns of objection resolution",
                    "Compliance ladder of 8+ yeses before close",
                    "Close probability above 60% average",
                ],
                "sessions": 4,
                "priority": 1,
            },
        }

        config = assignment_map.get(area, {
            "module": "full_call_simulation",
            "title": f"Focused Practice: {area.replace('_', ' ').title()}",
            "description": f"Targeted practice on {area.replace('_', ' ')}.",
            "drills": ["Complete 3 focused practice sessions"],
            "criteria": ["Score above 70 in target area"],
            "sessions": 3,
            "priority": 3,
        })

        return HomeworkAssignment(
            skill_area=area,
            priority=config["priority"],
            title=config["title"],
            description=config["description"],
            module_key=config["module"],
            drills=config["drills"],
            success_criteria=config["criteria"],
            sessions_to_complete=config["sessions"],
        )

    def _build_overall_assessment(
        self,
        session_count: int,
        scores: dict,
        strengths: list[dict],
        weaknesses: list[dict],
        assignments: list[HomeworkAssignment],
    ) -> str:
        """Build a narrative assessment of the agent's performance across sessions."""
        all_avgs = {k: self._avg(v) for k, v in scores.items()}
        overall_avg = self._avg(list(all_avgs.values()))

        strength_text = ", ".join(s["category"].replace("_", " ") for s in strengths[:3])
        weakness_text = ", ".join(w["category"].replace("_", " ") for w in weaknesses[:3])

        if overall_avg >= 75:
            level = "strong"
            tone = (
                f"Across {session_count} sessions, your overall performance is solid. "
                f"Your strengths are in {strength_text}. "
            )
        elif overall_avg >= 55:
            level = "developing"
            tone = (
                f"Across {session_count} sessions, you are building skill but have "
                f"clear gaps to close. Your strengths are {strength_text}, but "
                f"{weakness_text} need focused work. "
            )
        else:
            level = "foundation"
            tone = (
                f"Across {session_count} sessions, the data shows you are in the "
                f"early stages of skill development. {weakness_text} are costing you "
                f"closes. The good news: these are all trainable skills. "
            )

        if assignments:
            priority_text = (
                f"Your highest-impact homework is '{assignments[0].title}' — "
                f"{assignments[0].description[:200]}"
            )
        else:
            priority_text = "Continue with full call simulations to maintain your edge."

        return f"{tone}{priority_text}"
