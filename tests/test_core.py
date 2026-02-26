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
    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)
