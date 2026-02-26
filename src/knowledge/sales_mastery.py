"""
Sales Mastery — Structural Definitions Only
=============================================

ARCHITECTURE: State-Constrained Latent Knowledge Activation
------------------------------------------------------------

This file previously contained 1400+ lines of hardcoded sales theory dictionaries
(TONALITY, RAPPORT_DISCOVERY, OBJECTION_HANDLING, FRAME_CONTROL, etc.).

That theory has been REMOVED. The system now uses Latent Knowledge Activation —
the LLM's pre-trained neural weights already contain everything Belfort, Voss,
Miner, Tracy, Ziglar, Cardone, Sandler, Rackham, Kahneman, Cialdini, and every
other expert ever published. Instead of pasting their work into prompts, we
activate that knowledge with precise "Expert Directives" in the prompt layer
(see src/prompts/module_prompts.py and src/prompts/system_prompt.py).

What REMAINS in this file:
    - TRAINING_MODULES: Structural metadata (module names, descriptions, skills
      lists) used by the API to list available modules. This is DATA, not theory.
    - HOMEWORK_ANALYSIS: Pattern categories for cross-session analysis. This is
      STRUCTURAL, not coaching content.

Why this is better:
    1. Zero maintenance — no dictionaries to update when methodologies evolve
    2. Infinite knowledge — the LLM knows every framework, not just what we typed
    3. Hyper-lean code — prompts went from thousands of lines to focused directives
    4. Reliability — Python handles deterministic state, LLM handles psychology
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════
# MODULE DEFINITIONS — Structural metadata for the API layer
# These define WHAT exists, not HOW to teach it (the LLM handles that)
# ═══════════════════════════════════════════════════════════════════

TRAINING_MODULES = {
    "tonality_mastery": {
        "name": "Tonality Mastery",
        "description": (
            "Master the core sales tonalities: Declarative, Question, Scarcity Whisper, "
            "Reasonable Man, Absolute Certainty, Strategic Pause, and Late-Night FM DJ. "
            "Learn when, why, and how each tone works — grounded in Belfort's Straight Line, "
            "Voss's tactical empathy, and Mehrabian's vocal influence research."
        ),
        "skills_taught": [
            "Declarative (downward inflection) for authority and price — Belfort",
            "Question inflection for genuine discovery — conversational dynamics",
            "Scarcity whisper for urgency and intimacy — Cialdini's Scarcity Principle",
            "Reasonable man for rapport and trust — Voss/Sandler disarming approach",
            "Absolute certainty for conviction and closing — Belfort's Three Tens",
            "Strategic pause for emotional weight — Kahneman's System 2 activation",
            "Late-night FM DJ for de-escalation — Voss (Never Split the Difference)",
            "Micro-tonality shifts within sentences — advanced Belfort technique",
            "Mehrabian's 38% rule — tone carries more than words on the phone",
        ],
        "measurement": [
            "Can agent use declarative on price statements consistently?",
            "Does agent whisper on consequence statements?",
            "Does agent pause after key questions?",
            "Does agent match tone to context (not monotone)?",
            "Can agent shift within a single sentence?",
        ],
    },

    "question_mastery": {
        "name": "Question Mastery",
        "description": (
            "Ask questions that advance the sale. Master NEPQ (Miner), SPIN (Rackham), "
            "Sandler Pain Funnel, Voss calibrated questions, and the Goal-Why-Consequence "
            "discovery sequence. Learn to diagnose before prescribing."
        ),
        "skills_taught": [
            "Open vs closed vs calibrated questions — conversational control",
            "NEPQ sequence (Jeremy Miner) — Situation, Problem, Solution, Consequence",
            "SPIN framework (Neil Rackham) — Situation, Problem, Implication, Need-payoff",
            "Sandler Pain Funnel — surface pain to emotional core",
            "Advancing vs throwaway questions — only ask what moves the sale",
            "Mirroring (Voss technique) — repeat last 1-3 words as question",
            "Labeling (Voss technique) — 'It sounds like...' emotional validation",
            "Goal-Why-Consequence discovery sequence — the three pillars",
            "Gap Selling diagnostics (Keenan) — current state vs desired future state",
        ],
        "measurement": [
            "Does the question advance the conversation toward a sale?",
            "Is the question open when it should be open?",
            "Is the question building toward consequence?",
            "Does the agent use calibrated questions for control?",
            "Is the agent asking or interrogating?",
            "Does the agent use NEPQ/SPIN sequencing or random questions?",
        ],
    },

    "objection_handling": {
        "name": "Objection Handling",
        "description": (
            "Learn to isolate, identify root cause, and resolve objections using "
            "Belfort's Straight Line Loop, Voss's tactical empathy, Miner's NEPQ, "
            "Ziglar's Feel-Felt-Found, Blount's Ledge Technique, Sandler's Negative "
            "Reverse, and behavioral psychology of resistance (Brehm's Reactance)."
        ),
        "skills_taught": [
            "Smokescreen vs true objection vs condition — classification",
            "Three-test isolation protocol — Truth, Singularity, Commitment",
            "Three deal-killers — Money, Time, Decision Maker (root cause mapping)",
            "Belfort Straight Line Loop — acknowledge, empathize, redirect, ramp, close",
            "Voss no-oriented questions — 'Would it be a terrible idea if...'",
            "Voss tactical empathy for objections — label the emotion, then resolve",
            "Ziglar Feel-Felt-Found framework — genuine empathy, not a script",
            "Blount's Ledge Technique — pause, acknowledge, redirect",
            "Miner NEPQ consequence redirect — let the prospect's own pain overcome",
            "Sandler Negative Reverse — 'Maybe this isn't for you'",
            "Hopkins Porcupine — answer an objection with a question",
            "Hypothetical escalation for third-party deferral",
            "Financial reframe using established consequence (Kahneman loss aversion)",
            "Urgency reframe for timing objections — connect to unpredictability",
            "Psychological Reactance awareness (Brehm) — empathy dissolves, pressure amplifies",
        ],
        "measurement": [
            "Does agent isolate BEFORE attempting to resolve?",
            "Can agent identify the root cause (money, time, decision maker)?",
            "Does agent loop back to value after acknowledging?",
            "Does agent stay calm and empathetic during objection?",
            "Does the resolution connect to the prospect's own stated consequence?",
            "Can agent use multiple frameworks for the same objection?",
        ],
    },

    "rapport_building": {
        "name": "Rapport & Discovery",
        "description": (
            "Build genuine human connection using Voss's tactical empathy, Carnegie's "
            "influence principles, Cialdini's Liking and Reciprocity, NLP rapport "
            "techniques, and active listening. Uncover the three discovery pillars: "
            "Goal, Why Behind the Goal, and Consequence."
        ),
        "skills_taught": [
            "Tactical empathy (Voss) — understanding, not agreeing",
            "Mirroring (Voss) — repeat last 1-3 words, pause, let them elaborate",
            "Labeling (Voss) — 'It sounds like...' to validate emotions",
            "Accusation audit (Voss) — preempt negative thoughts",
            "Dale Carnegie principles — genuine interest, use their name, listen more",
            "Cialdini's Liking — similarity, genuine compliments, cooperation",
            "Cialdini's Reciprocity — give value first, receive openness",
            "NLP rapport — match energy, pace, vocabulary, breathing patterns",
            "Goal-Why-Consequence discovery sequence",
            "Active listening vs passive hearing — the prospect can FEEL the difference",
            "Brian Tracy's dominant buying motive — find the ONE thing that matters most",
            "Loss aversion framing (Kahneman) — 'What happens if you DON'T act?'",
        ],
        "measurement": [
            "Did the prospect share personal details voluntarily?",
            "Did the agent identify goal, why, and consequence?",
            "Was the rapport genuine or formulaic?",
            "Did the agent use the prospect's own words back to them?",
            "Did rapport lead to deeper discovery or just small talk?",
        ],
    },

    "preframing_control": {
        "name": "Preframing & Frame Control",
        "description": (
            "Set expectations before requests and maintain conversational control. "
            "Master Belfort's frame control, Sandler's upfront contracts, Cialdini's "
            "Consistency and Authority principles, compliance ladder psychology, and "
            "Nudge Theory (Thaler) for choice architecture."
        ),
        "skills_taught": [
            "Preframing sensitive requests — banking, SSN, medical (Belfort)",
            "Sandler Upfront Contracts — set mutual expectations in first 60 seconds",
            "Setting the conversation roadmap — eliminate surprises",
            "Frame recovery — Answer-Bridge-Redirect when prospect takes control",
            "Cialdini's Consistency/Commitment — compliance ladder building",
            "Cialdini's Authority projection — lead, don't follow",
            "Brehm's Reactance awareness — preframing prevents resistance",
            "Nudge architecture (Thaler) — make compliance the path of least resistance",
            "Conviction and authority projection — Belfort's certainty principle",
            "Assumptive transitions (Hopkins/Tracy) — the close as a logical next step",
        ],
        "measurement": [
            "Was every sensitive request preframed before being asked?",
            "Did the agent maintain frame or lose it?",
            "How quickly did the agent recover frame when challenged?",
            "Was the conversation structured or aimless?",
            "Did the agent build compliance before the close?",
        ],
    },

    "script_practice": {
        "name": "Script Practice",
        "description": (
            "Repetition mastery — practice your script with an easy-going AI client "
            "until it sounds natural, not rehearsed. Build confidence through repetition "
            "(Carol Dweck's Growth Mindset), develop tonal variety (Belfort), and achieve "
            "Ziglar's 'transference of feeling' through authentic delivery."
        ),
        "skills_taught": [
            "Natural delivery — saying the words without sounding scripted",
            "Conversational flow — script as a guide, not a prison",
            "Adaptive responses — handling off-script moments naturally",
            "Tonality variety — same words, different emotional delivery (Belfort)",
            "Confidence through repetition — muscle memory for your pitch",
            "Transference of feeling (Ziglar) — if you believe it, they believe it",
        ],
        "measurement": [
            "Does the agent sound like they're reading or conversing?",
            "Can the agent recover when the client goes slightly off-script?",
            "Does the delivery sound confident and natural?",
            "Is there tonal variety or monotone recitation?",
            "Would a real client feel engaged or lectured?",
        ],
    },

    "full_call_simulation": {
        "name": "Full Call Simulation",
        "description": (
            "Complete end-to-end call with a realistic AI prospect. All skills combined — "
            "tonality, rapport, discovery, objection handling, preframing, frame control, "
            "and closing. Graded across 11 KPIs by the adaptive grading engine."
        ),
        "skills_taught": ["All of the above integrated into a complete sales call"],
        "measurement": ["Complete grading engine evaluation across all 11 KPIs"],
    },
}


# ═══════════════════════════════════════════════════════════════════
# HOMEWORK — Structural pattern categories for cross-session analysis
# The actual coaching text is generated by the LLM (report_analyzer.py)
# ═══════════════════════════════════════════════════════════════════

HOMEWORK_ANALYSIS = {
    "core_principle": (
        "After 10+ calls, patterns emerge that a single session cannot reveal. "
        "Homework is not punishment — it is precision training. The coach identifies "
        "the SPECIFIC skill gap that is costing you the most closes, then assigns "
        "targeted practice to close that gap."
    ),

    "pattern_categories": {
        "tonality_patterns": {
            "indicators": [
                "Consistently low tonality scores across sessions",
                "Price statements always delivered with upward inflection",
                "No variation in tone (monotone delivery)",
                "Fails to use strategic pause at key moments",
                "No Scarcity Whisper on consequence/urgency moments",
                "No FM DJ voice when prospect shows resistance",
            ],
            "homework_type": "tonality_mastery module with specific drills",
        },
        "discovery_patterns": {
            "indicators": [
                "Frequently missing consequence establishment",
                "Shallow discovery — goal identified but WHY never explored",
                "Too many closed questions in discovery (not NEPQ/SPIN)",
                "Questions do not build on previous answers",
                "No mirroring or labeling used (Voss techniques absent)",
                "Gap between current state and future state not established",
            ],
            "homework_type": "question_mastery module + discovery role-play",
        },
        "objection_patterns": {
            "indicators": [
                "Objections rarely isolated before resolution attempt",
                "Same objection type causes failure across sessions",
                "Agent argues instead of empathizing (triggers reactance)",
                "Never loops back to consequence during objection handle",
                "Only uses one framework — no flexibility across methodologies",
                "Spouse deferral never tested with hypothetical escalation",
            ],
            "homework_type": "objection_handling module + targeted scenarios",
        },
        "flow_patterns": {
            "indicators": [
                "Frequent backward phase transitions",
                "Missing entire phases (skipping preframing)",
                "No clear structure to the conversation",
                "Agent follows the prospect instead of leading",
                "No upfront contract or roadmap set",
                "Sensitive requests sprung without preframing",
            ],
            "homework_type": "preframing_control module + structure drills",
        },
        "closing_patterns": {
            "indicators": [
                "High rapport but low close rate (rapport-to-close gap)",
                "Never uses assumptive close or summary close",
                "Gives up after first objection instead of looping",
                "Does not connect close to established consequence",
                "No compliance ladder built — big ask without small yeses",
                "Lacks conviction — sounds uncertain at the close",
            ],
            "homework_type": "closing drills + conviction practice",
        },
    },
}
