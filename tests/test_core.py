"""
Tests for core components: StateManager, Orchestrator, and Engines.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.state_manager import StateManager
from src.engine.compliance_tracker import ComplianceTracker
from src.engine.grading_engine import GradingEngine
from src.engine.objection_engine import ObjectionEngine
from src.engine.persona_generator import PersonaGenerator
from src.engine.phase_manager import PhaseManager
from src.engine.tonality_processor import TonalityProcessor
from src.models.state import (
    ConversationPhase,
    ObjectionCategory,
    ObjectionType,
    SessionState,
    TonalitySnapshot,
)


def test_state_manager_initialization():
    sm = StateManager()
    assert sm.state.hidden.trust_score == 50.0
    assert sm.state.hidden.authority_score == 50.0
    assert sm.state.hidden.sales_resistance == 50.0
    assert sm.state.current_phase == ConversationPhase.INTRO
    assert sm.state.hidden.flow_integrity is True
    print("[PASS] StateManager initialization")


def test_score_adjustments():
    sm = StateManager()
    sm.adjust_trust(10)
    assert sm.state.hidden.trust_score == 60.0

    sm.adjust_authority(-20)
    assert sm.state.hidden.authority_score == 30.0

    # Test clamping
    sm.adjust_trust(200)
    assert sm.state.hidden.trust_score == 100.0

    sm.adjust_trust(-300)
    assert sm.state.hidden.trust_score == 0.0
    print("[PASS] Score adjustments and clamping")


def test_phase_advancement():
    sm = StateManager()
    result = sm.advance_phase(ConversationPhase.RAPPORT_DISCOVERY)
    assert result is True
    assert sm.state.current_phase == ConversationPhase.RAPPORT_DISCOVERY

    # Backward skip breaks flow
    result = sm.advance_phase(ConversationPhase.INTRO)
    assert result is False
    assert sm.state.hidden.flow_integrity is False
    print("[PASS] Phase advancement and flow integrity")


def test_objection_lifecycle():
    sm = StateManager()
    sm.advance_phase(ConversationPhase.PRESENTATION)

    # Raise objection
    obj = sm.raise_objection(
        ObjectionCategory.BUDGET,
        ObjectionType.TRUE_OBJECTION,
        "That's more than I was hoping to spend."
    )
    assert obj is not None
    assert not obj.isolated
    assert not obj.locked

    # Isolate
    sm.isolate_objection(ObjectionCategory.BUDGET)
    assert sm.state.objections_raised[-1].isolated is True

    # Confirm isolation
    sm.confirm_isolation(ObjectionCategory.BUDGET)
    assert sm.state.objections_raised[-1].isolation_confirmed is True

    # Resolve
    sm.resolve_objection(ObjectionCategory.BUDGET, conviction=75.0)
    assert sm.state.objections_raised[-1].locked is True
    assert sm.is_objection_locked(ObjectionCategory.BUDGET)

    # Cannot raise again
    obj2 = sm.raise_objection(
        ObjectionCategory.BUDGET,
        ObjectionType.TRUE_OBJECTION,
        "It's still too expensive."
    )
    assert obj2 is None
    print("[PASS] Objection lifecycle (raise, isolate, confirm, resolve, lock)")


def test_compliance_tracking():
    sm = StateManager()
    sm.record_compliance_attempt(True)
    sm.record_compliance_attempt(True)
    sm.record_compliance_attempt(False)
    assert sm.get_compliance_ratio() == 2 / 3
    assert sm.state.compliance_checks_attempted == 3
    assert sm.state.compliance_checks_successful == 2
    print("[PASS] Compliance tracking")


def test_tonality_processing():
    tp = TonalityProcessor()

    # Test with metadata
    metadata = {
        "pitch_end_direction": "rising",
        "utterance_type": "statement",
        "pause_after_seconds": 3.0,
        "confidence_indicators": {"vocal_tremor": False, "pitch_stability": 0.9, "volume_consistency": 0.9},
    }
    snapshot = tp.process_metadata(metadata)
    assert snapshot.upward_inflection_on_statements is True
    assert snapshot.strategic_pause_detected is True
    assert snapshot.confident_tone is True

    # Test text-only
    snapshot2 = tp.process_text_only("So you're saying this is a good plan?")
    assert isinstance(snapshot2, TonalitySnapshot)
    print("[PASS] Tonality processing")


def test_persona_generation():
    gen = PersonaGenerator()

    # Random persona
    persona = gen.generate(seed=42)
    assert persona.name
    assert persona.age > 0
    assert persona.occupation

    # Specific archetype
    persona2 = gen.generate(archetype_name="The Skeptical Professional", seed=42)
    assert "Skeptical Professional" in persona2.personality_notes

    # All archetypes
    archetypes = gen.get_archetype_names()
    assert len(archetypes) == 8
    print(f"[PASS] Persona generation ({len(archetypes)} archetypes)")


def test_phase_manager():
    pm = PhaseManager()
    sm = StateManager()

    # Detect intro
    detected = pm.detect_phase("Hi, my name is John and I'm calling because you filled out a form.", sm)
    assert detected == ConversationPhase.INTRO

    # Detect medical
    detected = pm.detect_phase("Can you tell me what medications you're currently taking?", sm)
    assert detected == ConversationPhase.MEDICAL_UNDERWRITING

    # Detect presentation
    detected = pm.detect_phase("So the coverage would be $50 per month for a $250,000 term life policy.", sm)
    assert detected == ConversationPhase.PRESENTATION

    # Analyze a turn
    analysis = pm.analyze_agent_turn(
        "Tell me, what's important to you about getting coverage? Why is that important?",
        sm,
    )
    assert analysis["questions_asked"] >= 1
    print("[PASS] Phase manager detection")


def test_objection_engine():
    oe = ObjectionEngine()
    sm = StateManager()

    # No objection in intro by default (trust/authority at 50)
    sm.advance_phase(ConversationPhase.INTRO)
    # Intro objections should trigger
    obj = oe.evaluate(sm)
    assert obj is not None  # Intro smokescreens are always possible

    # Banking objection when not preframed
    sm2 = StateManager()
    sm2.advance_phase(ConversationPhase.PRESENTATION)
    obj2 = oe.evaluate(sm2)
    assert obj2 is not None
    print("[PASS] Objection engine conditional triggers")


def test_compliance_tracker():
    ct = ComplianceTracker()
    sm = StateManager()

    # Detect compliance attempt
    attempts = ct.detect_compliance_attempt("Can you grab a pen for me real quick?")
    assert len(attempts) > 0
    assert attempts[0]["type"] == "pen_ready"

    # Detect frame redirect
    is_redirect = ct.detect_frame_redirect(
        "Great question, I appreciate you asking that. Now, let me ask you — what's most important to you about this coverage?"
    )
    assert is_redirect is True
    print("[PASS] Compliance tracker")


def test_grading_engine():
    ge = GradingEngine()
    sm = StateManager()
    ct = ComplianceTracker()

    # Set up some state
    sm.set_flag("goal_identified", True)
    sm.set_flag("consequence_established", True)
    sm.set_flag("preframed_banking", True)
    sm.set_flag("preframed_social_security", True)
    sm.set_flag("preframed_next_steps", True)
    sm.adjust_trust(20)
    sm.adjust_authority(15)

    report = ge.grade(sm, ct)
    assert "overall_score" in report
    assert "overall_grade" in report
    assert "categories" in report
    assert "would_close" in report
    assert len(report["categories"]) == 11
    print(f"[PASS] Grading engine — Overall: {report['overall_score']}/100 ({report['overall_grade']})")


def test_full_conversation_flow():
    """Simulate a mini conversation through the orchestrator."""
    from src.core.orchestrator import ConversationOrchestrator

    orch = ConversationOrchestrator(seed=42)

    # Turn 1: Intro
    result = orch.process_agent_turn(
        "Hi, is this John? Great, my name is Mike, I'm a licensed agent with National Life. "
        "The reason for my call is you filled out a form online about getting some life insurance "
        "information. Does that ring a bell?"
    )
    assert result["turn_number"] == 1
    assert result["system_prompt"]

    # Simulate client response
    orch.process_client_response("Uh yeah, I think I did fill something out. What's this about?")

    # Turn 2: Rapport
    result2 = orch.process_agent_turn(
        "Perfect. So tell me, what got you interested in looking at coverage? "
        "What's most important to you?"
    )
    assert result2["turn_number"] == 2

    # Turn 3: Getting state
    state = orch.get_current_state()
    assert "trust_score" in state

    # End session
    report = orch.end_session()
    assert report["session_id"]
    assert report["categories"]
    print(f"[PASS] Full conversation flow — Session: {report['session_id'][:8]}")


def test_resistance_calculation():
    sm = StateManager()
    # With trust and authority at 50, resistance should be 50
    initial_resistance = sm.state.hidden.sales_resistance

    # Boost trust and authority
    sm.adjust_trust(30)
    sm.adjust_authority(30)
    # Resistance should decrease
    assert sm.state.hidden.sales_resistance < initial_resistance

    # Missing preframes in presentation phase should spike resistance
    sm.advance_phase(ConversationPhase.PRESENTATION)
    sm._recalculate_resistance()
    # Should have penalty for missing preframes and consequence
    assert sm.state.hidden.sales_resistance > 0
    print("[PASS] Resistance calculation with preframe penalties")


def test_root_cause_mapping():
    """Verify objections carry the correct root cause."""
    from src.models.state import ObjectionRootCause
    sm = StateManager()
    sm.advance_phase(ConversationPhase.PRESENTATION)

    # Think about it = MONEY
    obj = sm.raise_objection(
        ObjectionCategory.THINK_ABOUT_IT,
        ObjectionType.SMOKESCREEN,
        "I need to think about it.",
        root_cause=ObjectionRootCause.MONEY,
    )
    assert obj.root_cause == ObjectionRootCause.MONEY

    # Spouse = DECISION_MAKER
    obj2 = sm.raise_objection(
        ObjectionCategory.SPOUSE_APPROVAL,
        ObjectionType.SMOKESCREEN,
        "Let me talk to my wife.",
        root_cause=ObjectionRootCause.DECISION_MAKER,
    )
    assert obj2.root_cause == ObjectionRootCause.DECISION_MAKER
    print("[PASS] Root cause mapping")


def test_objection_handle_analysis():
    """Test the new analyze_agent_handle method."""
    from src.engine.objection_engine import ObjectionEngine
    oe = ObjectionEngine()
    sm = StateManager()

    # Test isolation detection
    analysis = oe.analyze_agent_handle(sm, "Is it just the budget, or is there something else holding you back?")
    assert analysis["attempted_isolation"] is True
    assert analysis["asked_followup"] is True

    # Test hypothetical + decision maker probe (the spouse scenario)
    analysis2 = oe.analyze_agent_handle(
        sm,
        "What do you think she'd like about this? Let's say she had a really bad day "
        "and she comes home and says NO — what would you do?"
    )
    assert analysis2["hypothetical_test"] is True
    assert analysis2["decision_maker_probe"] is True

    # Test empathy detection
    analysis3 = oe.analyze_agent_handle(sm, "I totally understand, that makes sense.")
    assert analysis3["empathy_shown"] is True

    # Test pressure detection
    analysis4 = oe.analyze_agent_handle(sm, "Let's get this done right now, lock in the rate today!")
    assert analysis4["pressure_detected"] is True

    # Test consequence redirect
    analysis5 = oe.analyze_agent_handle(sm, "Remember you said if something happened your wife would lose the house. What happens if we wait?")
    assert analysis5["redirect_to_consequence"] is True

    print("[PASS] Objection handle analysis")


def test_sales_style_detection():
    """Test sales style detection from conversation patterns."""
    sm = StateManager()

    # Simulate consultative style (many questions, empathy, consequence)
    for i in range(5):
        sm.increment_turn()
        sm.log_message("agent", "Tell me, what's important to you about this coverage? Why is that important? What happens if you don't get it?")
        sm.log_message("client", "Yeah, I want to protect my family.")

    style = sm.detect_sales_style()
    assert style.value in ("consultative", "hybrid", "unknown")
    print(f"[PASS] Sales style detection (detected: {style.value})")


def test_deal_killers_in_report():
    """Test that the grading report includes deal-killer analysis."""
    from src.engine.grading_engine import GradingEngine
    ge = GradingEngine()
    sm = StateManager()
    ct = ComplianceTracker()

    sm.set_flag("consequence_established", True)
    sm.set_flag("preframed_banking", True)
    report = ge.grade(sm, ct)

    assert "deal_killers" in report
    assert "money" in report["deal_killers"]
    assert "time" in report["deal_killers"]
    assert "decision_maker" in report["deal_killers"]
    assert "sales_style" in report
    assert "pros" in report["sales_style"]
    assert "consequences" in report["sales_style"]
    print(f"[PASS] Deal killers in report (style: {report['sales_style']['detected']})")


def test_spouse_objection_lock_via_hypothetical():
    """Test the full spouse objection lifecycle via hypothetical testing."""
    from src.core.orchestrator import ConversationOrchestrator
    orch = ConversationOrchestrator(seed=42)

    # Agent does intro
    orch.process_agent_turn("Hi, is this John? My name is Mike, I'm calling about the form you filled out.")
    orch.process_client_response("Yeah, what's this about?")

    # Manually set up a spouse objection
    from src.models.state import ObjectionRootCause
    obj = orch.sm.raise_objection(
        ObjectionCategory.SPOUSE_APPROVAL,
        ObjectionType.SMOKESCREEN,
        "I need to talk to my wife first.",
        root_cause=ObjectionRootCause.DECISION_MAKER,
    )
    orch._pending_objection = obj

    # Agent handles with hypothetical
    result = orch.handle_objection_response(
        "I totally understand. What do you think she'd like about this? "
        "Let's say she had a really bad day, comes home, you bring it up, "
        "she says NO — what would you do?"
    )
    assert result["hypothetical_tested"] is True
    assert result["decision_maker_probed"] is True
    # With default trust at 50 and hypothetical + DM probe, should resolve
    assert result.get("resolved", False) is True
    assert orch.sm.is_objection_locked(ObjectionCategory.SPOUSE_APPROVAL)
    print("[PASS] Spouse objection locked via hypothetical testing")


def test_grading_pros_and_consequences():
    """Verify report categories include pros and consequences."""
    from src.engine.grading_engine import GradingEngine
    ge = GradingEngine()
    sm = StateManager()
    ct = ComplianceTracker()

    # Don't set consequence — should generate consequences in report
    report = ge.grade(sm, ct)
    rapport_grade = report["categories"]["rapport_discovery"]
    assert "pros" in rapport_grade
    assert "consequences" in rapport_grade
    # Missing consequence should produce consequences
    assert len(rapport_grade["consequences"]) > 0
    print("[PASS] Grading pros and consequences present")


if __name__ == "__main__":
    test_state_manager_initialization()
    test_score_adjustments()
    test_phase_advancement()
    test_objection_lifecycle()
    test_compliance_tracking()
    test_tonality_processing()
    test_persona_generation()
    test_phase_manager()
    test_objection_engine()
    test_compliance_tracker()
    test_grading_engine()
    test_full_conversation_flow()
    test_resistance_calculation()
    test_root_cause_mapping()
    test_objection_handle_analysis()
    test_sales_style_detection()
    test_deal_killers_in_report()
    test_spouse_objection_lock_via_hypothetical()
    test_grading_pros_and_consequences()
    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
