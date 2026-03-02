"""
Road to Mastery — 35-Day Curriculum
====================================

A structured day-by-day progression through all training modules.
Designed to take a new agent from zero to mastery by layering skills:

  Phase 1 (Days 1-7):   Mindset & Voice Foundation
  Phase 2 (Days 8-14):  Connection & Discovery
  Phase 3 (Days 15-21): Frame Control & Influence
  Phase 4 (Days 22-28): Behavioral Science & Objection Mastery
  Phase 5 (Days 29-35): Integration & Full Call Mastery

Each day has 2-3 activities. Each activity is one focused training session
with a specific module and topic. Users complete activities at their own pace
— "Day 1" doesn't mean calendar day, it means training day.
"""

from __future__ import annotations

PHASES = [
    {
        "id": "foundation",
        "name": "Mindset & Voice Foundation",
        "description": "Build the unshakeable mindset and vocal authority that separates closers from callers.",
        "days": [1, 7],
        "color": "#F59E0B",
    },
    {
        "id": "connection",
        "name": "Connection & Discovery",
        "description": "Master rapport-building and the art of asking questions that advance the sale.",
        "days": [8, 14],
        "color": "#06B6D4",
    },
    {
        "id": "control",
        "name": "Frame Control & Influence",
        "description": "Set expectations, maintain control, and reframe resistance using NLP and behavioral psychology.",
        "days": [15, 21],
        "color": "#8B5CF6",
    },
    {
        "id": "mastery",
        "name": "Behavioral Science & Objection Mastery",
        "description": "Read people, adapt in real time, and handle any objection with confidence.",
        "days": [22, 28],
        "color": "#EF4444",
    },
    {
        "id": "integration",
        "name": "Integration & Full Call Mastery",
        "description": "Put everything together. Script practice, full call simulations, and graduation.",
        "days": [29, 35],
        "color": "#10B981",
    },
]

CURRICULUM = [
    # ═══════════════════════════════════════════════════
    # PHASE 1: Mindset & Voice Foundation (Days 1-7)
    # ═══════════════════════════════════════════════════
    {
        "day": 1,
        "title": "10X Your Foundation",
        "description": "Set massive goals and learn the vocal authority that commands attention.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 0, "label": "Cardone 10X Massive Action"},
            {"module": "tonality_mastery", "topic_index": 0, "label": "Belfort Power Tones"},
        ],
    },
    {
        "day": 2,
        "title": "Conviction & Power",
        "description": "Deepen your conviction and sharpen your tonal shifts within sentences.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 0, "label": "Cardone 10X Massive Action"},
            {"module": "tonality_mastery", "topic_index": 0, "label": "Belfort Power Tones"},
        ],
    },
    {
        "day": 3,
        "title": "The Savage Mindset",
        "description": "Activate your killer instinct and learn the voice that de-escalates any situation.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 1, "label": "Elliott Savage Sales Mindset"},
            {"module": "tonality_mastery", "topic_index": 1, "label": "Voss De-escalation Voice"},
        ],
    },
    {
        "day": 4,
        "title": "Rejection as Fuel",
        "description": "Transform rejection into motivation and master scarcity tone.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 1, "label": "Elliott Savage Sales Mindset"},
            {"module": "tonality_mastery", "topic_index": 2, "label": "Scarcity & Urgency Tone"},
        ],
    },
    {
        "day": 5,
        "title": "Peak State",
        "description": "Master your physiology to drive peak psychology, and refine question inflection.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 2, "label": "Robbins Peak State Management"},
            {"module": "tonality_mastery", "topic_index": 3, "label": "Question Inflection"},
        ],
    },
    {
        "day": 6,
        "title": "Mental Toughness",
        "description": "Callus your mind and master the urgency whisper.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 3, "label": "Goggins Mental Toughness"},
            {"module": "tonality_mastery", "topic_index": 2, "label": "Scarcity & Urgency Tone"},
        ],
    },
    {
        "day": 7,
        "title": "Programming for Success",
        "description": "Program your subconscious and polish your question tone.",
        "phase": "foundation",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 4, "label": "Hill Autosuggestion & Desire"},
            {"module": "tonality_mastery", "topic_index": 3, "label": "Question Inflection"},
            {"module": "mindset_mastery", "topic_index": 1, "label": "Elliott Savage Sales Mindset"},
        ],
    },

    # ═══════════════════════════════════════════════════
    # PHASE 2: Connection & Discovery (Days 8-14)
    # ═══════════════════════════════════════════════════
    {
        "day": 8,
        "title": "Tactical Empathy",
        "description": "Learn to truly understand your prospect — mirroring, labeling, and the NEPQ framework.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 0, "label": "Voss Tactical Empathy Toolkit"},
            {"module": "question_mastery", "topic_index": 0, "label": "NEPQ Framework"},
        ],
    },
    {
        "day": 9,
        "title": "Deep Listening",
        "description": "Go deeper with empathy and sharpen your questioning sequence.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 0, "label": "Voss Tactical Empathy Toolkit"},
            {"module": "question_mastery", "topic_index": 0, "label": "NEPQ Framework"},
        ],
    },
    {
        "day": 10,
        "title": "Influence & SPIN",
        "description": "Carnegie's timeless influence principles meet Rackham's SPIN methodology.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 1, "label": "Carnegie Influence Principles"},
            {"module": "question_mastery", "topic_index": 1, "label": "SPIN Selling Questions"},
        ],
    },
    {
        "day": 11,
        "title": "Liking & Pain",
        "description": "Build instant connection with Cialdini's liking principle and drill into the pain funnel.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 2, "label": "Cialdini Liking & Reciprocity"},
            {"module": "question_mastery", "topic_index": 2, "label": "Sandler Pain Funnel"},
        ],
    },
    {
        "day": 12,
        "title": "The Three Pillars",
        "description": "Uncover Goal, Why, and Consequence — the discovery sequence that closes deals.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 3, "label": "Goal-Why-Consequence Discovery"},
            {"module": "question_mastery", "topic_index": 3, "label": "Voss Calibrated Questions"},
        ],
    },
    {
        "day": 13,
        "title": "Selling the Gap",
        "description": "Master NLP rapport matching and Gap Selling's current-vs-future discovery.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 4, "label": "NLP Rapport & Matching"},
            {"module": "question_mastery", "topic_index": 4, "label": "Gap Selling Discovery"},
        ],
    },
    {
        "day": 14,
        "title": "Discovery Mastery Review",
        "description": "Combine all discovery skills — empathy, questions, and the three pillars together.",
        "phase": "connection",
        "activities": [
            {"module": "rapport_building", "topic_index": 3, "label": "Goal-Why-Consequence Discovery"},
            {"module": "question_mastery", "topic_index": 0, "label": "NEPQ Framework"},
            {"module": "rapport_building", "topic_index": 0, "label": "Voss Tactical Empathy Toolkit"},
        ],
    },

    # ═══════════════════════════════════════════════════
    # PHASE 3: Frame Control & Influence (Days 15-21)
    # ═══════════════════════════════════════════════════
    {
        "day": 15,
        "title": "Interiority & Buying State",
        "description": "Build an internal frame stronger than your prospect's and create emotional engagement.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 0, "label": "Wilde Interiority & Buying State"},
            {"module": "preframing_control", "topic_index": 4, "label": "Sandler Upfront Contracts"},
        ],
    },
    {
        "day": 16,
        "title": "Frame Control",
        "description": "Master Belfort's conviction projection and Wilde's buying state activation.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 0, "label": "Wilde Interiority & Buying State"},
            {"module": "preframing_control", "topic_index": 2, "label": "Belfort Frame Control"},
        ],
    },
    {
        "day": 17,
        "title": "Sleight of Mouth",
        "description": "Learn instant reframes — Redefine, Consequence, Counter-example, Intent, Chunk Up/Down.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 1, "label": "Wilde Sleight of Mouth"},
            {"module": "preframing_control", "topic_index": 5, "label": "Hughes Identity Frames & 6-Axis"},
        ],
    },
    {
        "day": 18,
        "title": "Advanced Reframing",
        "description": "Deepen your Sleight of Mouth toolkit and build the compliance ladder.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 1, "label": "Wilde Sleight of Mouth"},
            {"module": "preframing_control", "topic_index": 6, "label": "Cialdini Compliance Ladder"},
        ],
    },
    {
        "day": 19,
        "title": "Identity Shift",
        "description": "Help prospects see themselves as action-takers and paint an irresistible protected future.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 3, "label": "Wilde Identity Shift & Irresistible Future"},
            {"module": "preframing_control", "topic_index": 2, "label": "Belfort Frame Control"},
        ],
    },
    {
        "day": 20,
        "title": "The Compliance Ladder",
        "description": "Build effortless compliance through Cialdini's consistency principle and upfront contracts.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 6, "label": "Cialdini Compliance Ladder"},
            {"module": "preframing_control", "topic_index": 4, "label": "Sandler Upfront Contracts"},
        ],
    },
    {
        "day": 21,
        "title": "Frame Control Mastery Review",
        "description": "Integrate all frame control skills — interiority, reframing, and compliance together.",
        "phase": "control",
        "activities": [
            {"module": "preframing_control", "topic_index": 0, "label": "Wilde Interiority & Buying State"},
            {"module": "preframing_control", "topic_index": 1, "label": "Wilde Sleight of Mouth"},
            {"module": "preframing_control", "topic_index": 3, "label": "Wilde Identity Shift & Irresistible Future"},
        ],
    },

    # ═══════════════════════════════════════════════════
    # PHASE 4: Behavioral Science & Objection Mastery (Days 22-28)
    # ═══════════════════════════════════════════════════
    {
        "day": 22,
        "title": "Reading People",
        "description": "Learn to read compliance signals and master the Straight Line objection loop.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 0, "label": "Hughes Behavioral Table"},
            {"module": "objection_handling", "topic_index": 0, "label": "Belfort Straight Line Loop"},
        ],
    },
    {
        "day": 23,
        "title": "Signals & Loops",
        "description": "Deepen behavioral reading and perfect the acknowledge-empathize-redirect loop.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 0, "label": "Hughes Behavioral Table"},
            {"module": "objection_handling", "topic_index": 0, "label": "Belfort Straight Line Loop"},
        ],
    },
    {
        "day": 24,
        "title": "The 6-Axis & Empathy Defuse",
        "description": "Master Hughes' 6-Axis influence model and Voss's tactical empathy for objections.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 1, "label": "Hughes 6-Axis & FATE Model"},
            {"module": "objection_handling", "topic_index": 1, "label": "Voss Tactical Empathy Defuse"},
        ],
    },
    {
        "day": 25,
        "title": "Personality Adaptation",
        "description": "Adapt your approach with DISC profiling and handle objections with Feel-Felt-Found.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 2, "label": "DISC Behavioral Adaptation"},
            {"module": "objection_handling", "topic_index": 2, "label": "Ziglar Feel-Felt-Found"},
        ],
    },
    {
        "day": 26,
        "title": "System 1 & Consequence",
        "description": "Know which brain system you're speaking to and let the prospect's own pain overcome objections.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 3, "label": "Kahneman System 1 & System 2"},
            {"module": "objection_handling", "topic_index": 3, "label": "Miner NEPQ Consequence Redirect"},
        ],
    },
    {
        "day": 27,
        "title": "Applied Influence & Reverse Psychology",
        "description": "Deploy Cialdini's principles based on behavioral signals and master the Negative Reverse.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 4, "label": "Cialdini Applied Influence"},
            {"module": "objection_handling", "topic_index": 4, "label": "Sandler Negative Reverse"},
        ],
    },
    {
        "day": 28,
        "title": "Authority & Root Cause",
        "description": "Build perceived authority and learn to isolate the true objection from smokescreens.",
        "phase": "mastery",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 5, "label": "Hughes Authority Ladder"},
            {"module": "objection_handling", "topic_index": 5, "label": "Isolation & Root Cause Mapping"},
            {"module": "behavioral_profiling", "topic_index": 6, "label": "Sapolsky Neurochemistry of Trust"},
        ],
    },

    # ═══════════════════════════════════════════════════
    # PHASE 5: Integration & Full Call Mastery (Days 29-35)
    # ═══════════════════════════════════════════════════
    {
        "day": 29,
        "title": "Growth Mindset & Conviction",
        "description": "Embrace failure as feedback, build unshakeable product conviction.",
        "phase": "integration",
        "activities": [
            {"module": "mindset_mastery", "topic_index": 5, "label": "Dweck Growth Mindset"},
            {"module": "mindset_mastery", "topic_index": 6, "label": "Conviction & Call Reluctance"},
        ],
    },
    {
        "day": 30,
        "title": "Trust Chemistry & Review",
        "description": "Understand the biology of trust and revisit your savage mindset.",
        "phase": "integration",
        "activities": [
            {"module": "behavioral_profiling", "topic_index": 6, "label": "Sapolsky Neurochemistry of Trust"},
            {"module": "behavioral_profiling", "topic_index": 1, "label": "Hughes 6-Axis & FATE Model"},
            {"module": "objection_handling", "topic_index": 3, "label": "Miner NEPQ Consequence Redirect"},
        ],
    },
    {
        "day": 31,
        "title": "Script Mastery I",
        "description": "Practice your script until it sounds natural, not rehearsed. First full integration.",
        "phase": "integration",
        "activities": [
            {"module": "script_practice", "topic_index": None, "label": "Script Practice Session"},
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
        ],
    },
    {
        "day": 32,
        "title": "Script Mastery II",
        "description": "Refine your delivery and handle an AI prospect end-to-end.",
        "phase": "integration",
        "activities": [
            {"module": "script_practice", "topic_index": None, "label": "Script Practice Session"},
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
        ],
    },
    {
        "day": 33,
        "title": "Full Integration",
        "description": "All skills combined — tonality, rapport, discovery, framing, objections, and close.",
        "phase": "integration",
        "activities": [
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
        ],
    },
    {
        "day": 34,
        "title": "Elite Performance",
        "description": "Push for excellence. Two back-to-back full simulations with all skills graded.",
        "phase": "integration",
        "activities": [
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
            {"module": "full_call_simulation", "topic_index": None, "label": "Full Call Simulation"},
        ],
    },
    {
        "day": 35,
        "title": "Graduation Day",
        "description": "Your final test. Prove you've mastered every skill. You are now a top 1% closer.",
        "phase": "integration",
        "activities": [
            {"module": "full_call_simulation", "topic_index": None, "label": "Graduation Call — Full Simulation"},
            {"module": "full_call_simulation", "topic_index": None, "label": "Graduation Call — Prove Your Mastery"},
        ],
    },
]

TOTAL_DAYS = len(CURRICULUM)
TOTAL_ACTIVITIES = sum(len(d["activities"]) for d in CURRICULUM)
