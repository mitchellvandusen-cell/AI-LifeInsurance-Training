"""
Sales Mastery — Structural Definitions Only
=============================================

ARCHITECTURE: State-Constrained Latent Knowledge Activation
------------------------------------------------------------

This file previously contained 1400+ lines of hardcoded sales theory dictionaries
(TONALITY, RAPPORT_DISCOVERY, OBJECTION_HANDLING, FRAME_CONTROL, etc.).

That theory has been REMOVED. The system now uses Latent Knowledge Activation —
the LLM's pre-trained neural weights already contain everything Belfort, Voss,
Miner, Tracy, Ziglar, Cardone, Sandler, Rackham, Kahneman, Cialdini, Wilde, and
every other expert ever published. Instead of pasting their work into prompts, we
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
        "topics": [
            {"name": "Belfort Power Tones", "anchor": "Jordan Belfort", "sessions": 3,
             "focus": "Declarative, Absolute Certainty, and micro-tonality shifts within sentences"},
            {"name": "Voss De-escalation Voice", "anchor": "Chris Voss", "sessions": 2,
             "focus": "Late-Night FM DJ, tactical empathy tone, and the Reasonable Man"},
            {"name": "Scarcity & Urgency Tone", "anchor": "Cialdini / Belfort", "sessions": 2,
             "focus": "Scarcity whisper, strategic pause, and urgency without pressure"},
            {"name": "Question Inflection", "anchor": "Mehrabian / Miner", "sessions": 2,
             "focus": "Upward inflection for discovery, calibrated question tone, and the 38% rule"},
        ],
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
        "topics": [
            {"name": "NEPQ Framework", "anchor": "Jeremy Miner", "sessions": 3,
             "focus": "Situation, Problem-Awareness, Solution-Awareness, and Consequence questions"},
            {"name": "SPIN Selling Questions", "anchor": "Neil Rackham", "sessions": 2,
             "focus": "Situation, Problem, Implication, and Need-Payoff question sequencing"},
            {"name": "Sandler Pain Funnel", "anchor": "David Sandler", "sessions": 2,
             "focus": "Drilling from surface pain to emotional core using layered questions"},
            {"name": "Voss Calibrated Questions", "anchor": "Chris Voss", "sessions": 2,
             "focus": "Mirroring, labeling, and 'How am I supposed to do that?' calibrated questions"},
            {"name": "Gap Selling Discovery", "anchor": "Keenan", "sessions": 2,
             "focus": "Current state vs desired future state — selling the gap"},
        ],
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
        "topics": [
            {"name": "Belfort Straight Line Loop", "anchor": "Jordan Belfort", "sessions": 3,
             "focus": "Acknowledge, empathize, redirect, ramp certainty, close — the loop that never ends"},
            {"name": "Voss Tactical Empathy Defuse", "anchor": "Chris Voss", "sessions": 2,
             "focus": "Label the emotion, no-oriented questions, and 'How am I supposed to do that?'"},
            {"name": "Ziglar Feel-Felt-Found", "anchor": "Zig Ziglar", "sessions": 2,
             "focus": "Genuine empathy framework — Feel their concern, others Felt the same, here's what they Found"},
            {"name": "Miner NEPQ Consequence Redirect", "anchor": "Jeremy Miner", "sessions": 2,
             "focus": "Let the prospect's own stated pain overcome their objection — consequence-based resolution"},
            {"name": "Sandler Negative Reverse", "anchor": "David Sandler", "sessions": 2,
             "focus": "'Maybe this isn't for you' — reverse psychology, Porcupine technique, and pattern interrupts"},
            {"name": "Isolation & Root Cause Mapping", "anchor": "Belfort / Hopkins", "sessions": 2,
             "focus": "Smokescreen vs true objection, Three-Test Protocol, and the three deal-killers"},
        ],
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
        "topics": [
            {"name": "Voss Tactical Empathy Toolkit", "anchor": "Chris Voss", "sessions": 3,
             "focus": "Mirroring, labeling, accusation audits, and the Late-Night FM DJ voice for deep rapport"},
            {"name": "Carnegie Influence Principles", "anchor": "Dale Carnegie", "sessions": 2,
             "focus": "Genuine interest, use their name, listen more than you talk, make them feel important"},
            {"name": "Cialdini Liking & Reciprocity", "anchor": "Robert Cialdini", "sessions": 2,
             "focus": "Similarity, genuine compliments, give value first — the psychology of instant connection"},
            {"name": "Goal-Why-Consequence Discovery", "anchor": "Tracy / Miner", "sessions": 3,
             "focus": "The three discovery pillars — uncover the goal, the WHY behind it, and the consequence of inaction"},
            {"name": "NLP Rapport & Matching", "anchor": "Bandler / Grinder", "sessions": 2,
             "focus": "Match energy, pace, vocabulary, and breathing — build unconscious rapport"},
        ],
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
        "name": "Preframing, Reframing & Frame Control",
        "description": (
            "Set expectations before requests, maintain conversational control, and "
            "reframe resistance using NLP language patterns. Master Belfort's frame "
            "control, Eli Wilde's Interiority and NLP frames (Sleight of Mouth, Belief "
            "Shifting, Buying State, Ascension Agreements, Identity Shift, Irresistible "
            "Future Formula), Chase Hughes' Identity Frames and 6-Axis Influence, "
            "Sandler's upfront contracts, Cialdini's Consistency and Authority principles, "
            "compliance ladder psychology, and Nudge Theory (Thaler)."
        ),
        "topics": [
            {"name": "Wilde Interiority & Buying State", "anchor": "Eli Wilde", "sessions": 3,
             "focus": "Superior interior frame, state-dependent decisions, and emotional engagement over logic"},
            {"name": "Wilde Sleight of Mouth", "anchor": "Eli Wilde / Robert Dilts", "sessions": 3,
             "focus": "Redefine, Consequence, Counter-example, Intent, Chunk Up/Down — instant reframes"},
            {"name": "Belfort Frame Control", "anchor": "Jordan Belfort", "sessions": 2,
             "focus": "Preframing sensitive requests, conviction projection, and the certainty principle"},
            {"name": "Wilde Identity Shift & Irresistible Future", "anchor": "Eli Wilde", "sessions": 2,
             "focus": "Help them see themselves as action-takers, paint a vivid protected future"},
            {"name": "Sandler Upfront Contracts", "anchor": "David Sandler", "sessions": 2,
             "focus": "Set mutual expectations in the first 60 seconds — eliminate surprises and resistance"},
            {"name": "Hughes Identity Frames & 6-Axis", "anchor": "Chase Hughes", "sessions": 2,
             "focus": "Shift self-concept through framing, Authority-Rapport-Reciprocity-Social Proof-Urgency-Commitment"},
            {"name": "Cialdini Compliance Ladder", "anchor": "Robert Cialdini / Thaler", "sessions": 2,
             "focus": "Consistency, commitment, authority projection, and nudge architecture for effortless compliance"},
        ],
        "skills_taught": [
            "Preframing sensitive requests — banking, SSN, medical (Belfort)",
            "Pre-suasion (Wilde/Cialdini) — frame the conversation before the pitch begins",
            "Interiority / Superior Interior (Wilde) — build an internal frame stronger than the prospect's",
            "Sandler Upfront Contracts — set mutual expectations in first 60 seconds",
            "Setting the conversation roadmap — eliminate surprises",
            "Frame recovery — Answer-Bridge-Redirect when prospect takes control",
            "Ascension Agreements (Wilde) — active commitment checkpoints that deepen buy-in",
            "Sleight of Mouth reframing (Wilde/Dilts) — Redefine, Consequence, Counter-example, Intent, Chunk Up/Down",
            "Belief Shifting (Wilde) — dismantle belief structures that create buying resistance",
            "Context and Meaning Reframing (Bandler/Grinder) — shift the frame, shift the meaning",
            "Buying State (Wilde) — state-dependent decisions driven by emotional engagement",
            "Identity Shift (Wilde) — help the prospect see themselves as someone who takes action",
            "Irresistible Future Formula (Wilde) — paint a vivid future that creates natural urgency",
            "Chase Hughes Identity Frames — shift the prospect's self-concept through conversational framing",
            "Chase Hughes 6-Axis Influence — Authority, Rapport, Reciprocity, Social Proof, Urgency, Commitment",
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
            "Did the agent project interiority — certainty and conviction — throughout?",
            "Did the agent use Sleight of Mouth or NLP reframes when resistance appeared?",
            "Did the agent create a buying state through emotional engagement (not just logic)?",
            "Were ascension agreements used to deepen commitment at key checkpoints?",
            "Did the agent paint an irresistible future tied to the prospect's specific goals?",
        ],
    },

    "behavioral_profiling": {
        "name": "Behavioral Profiling & Influence",
        "description": (
            "Master Chase Hughes' behavioral science frameworks for reading people and "
            "ethically influencing decisions. Learn the Behavioral Table for compliance "
            "signals, the 6-Axis Model of Influence, the FATE Model, Authority Ladder, "
            "Identity Framing, and the Compliance Gaining Sequence. Combined with the "
            "psychology of trust (Sapolsky), persuasion (Cialdini), and decision-making "
            "(Kahneman) to read prospects and adapt in real time."
        ),
        "topics": [
            {"name": "Hughes Behavioral Table", "anchor": "Chase Hughes", "sessions": 3,
             "focus": "Reading compliance signals, resistance cues, and deception indicators in real time"},
            {"name": "Hughes 6-Axis & FATE Model", "anchor": "Chase Hughes", "sessions": 3,
             "focus": "Authority, Rapport, Reciprocity, Social Proof, Urgency, Commitment + Focus, Authority, Tribe, Emotion"},
            {"name": "DISC Behavioral Adaptation", "anchor": "William Marston", "sessions": 2,
             "focus": "Dominance, Influence, Steadiness, Conscientiousness — adapt your pitch to their personality"},
            {"name": "Kahneman System 1 & System 2", "anchor": "Daniel Kahneman", "sessions": 2,
             "focus": "Know which brain system you're speaking to — fast intuition vs slow deliberation"},
            {"name": "Cialdini Applied Influence", "anchor": "Robert Cialdini", "sessions": 2,
             "focus": "The 7 principles in action — reading which principle to deploy based on behavioral signals"},
            {"name": "Hughes Authority Ladder", "anchor": "Chase Hughes", "sessions": 2,
             "focus": "Building perceived authority step by step, compliance gaining sequence, and identity framing"},
            {"name": "Sapolsky Neurochemistry of Trust", "anchor": "Robert Sapolsky", "sessions": 2,
             "focus": "Oxytocin, cortisol, dopamine in sales — the biology of trust and how to trigger it ethically"},
        ],
        "skills_taught": [
            "Chase Hughes Behavioral Table — reading compliance, resistance, and deception signals",
            "6-Axis Model of Influence (Hughes) — Authority, Rapport, Reciprocity, Social Proof, Urgency, Commitment",
            "FATE Model (Hughes) — Focus, Authority, Tribe, Emotion for behavioral influence",
            "Authority Ladder (Hughes) — building perceived authority step by step",
            "Identity Framing (Hughes) — shifting the prospect's self-concept through conversation",
            "Compliance Gaining Sequence (Hughes) — the specific order of influence techniques",
            "Behavioral Baselines — reading deviations from normal vocal behavior",
            "Micro-expressions and vocal cues — detecting hesitation, interest, and deception",
            "OCEAN/Big Five personality profiling — adapting approach to personality type",
            "DISC behavioral model — Dominance, Influence, Steadiness, Conscientiousness",
            "Cialdini's 7 Principles applied to behavioral profiling",
            "Kahneman's System 1/System 2 — knowing which system you're speaking to",
            "Sapolsky's neurochemistry of trust — oxytocin, cortisol, dopamine in sales",
            "Ethical influence vs manipulation — maintaining integrity in persuasion",
        ],
        "measurement": [
            "Can the agent identify the prospect's behavioral baseline?",
            "Does the agent adapt approach based on behavioral signals?",
            "Is the agent building authority systematically (not randomly)?",
            "Does the agent read compliance signals and advance when appropriate?",
            "Does the agent detect resistance signals and adjust before objections surface?",
            "Can the agent identify personality type and adapt communication style?",
            "Does the agent use identity framing ethically and effectively?",
        ],
    },

    "mindset_mastery": {
        "name": "Mindset & Confidence Mastery",
        "description": (
            "Build the unshakeable mindset of a top 1% closer. Combine Grant Cardone's "
            "10X Rule and massive action, Andy Elliott's savage sales mindset and killer "
            "instinct, Tony Robbins' state management and peak performance, David Goggins' "
            "mental toughness and callusing the mind, Napoleon Hill's autosuggestion and "
            "burning desire, and Carol Dweck's growth mindset. Transform fear, rejection, "
            "and self-doubt into fuel for relentless action."
        ),
        "topics": [
            {"name": "Cardone 10X Massive Action", "anchor": "Grant Cardone", "sessions": 3,
             "focus": "10X your goals AND effort, the fourth degree of action, dominate don't compete"},
            {"name": "Elliott Savage Sales Mindset", "anchor": "Andy Elliott", "sessions": 3,
             "focus": "Killer instinct, wolf mentality, rejection as fuel, morning attack routine"},
            {"name": "Robbins Peak State Management", "anchor": "Tony Robbins", "sessions": 2,
             "focus": "Physiology drives psychology, incantations, the Triad (Focus, Language, Physiology)"},
            {"name": "Goggins Mental Toughness", "anchor": "David Goggins", "sessions": 2,
             "focus": "Callusing the mind, the 40% Rule, Accountability Mirror, voluntary discomfort"},
            {"name": "Hill Autosuggestion & Desire", "anchor": "Napoleon Hill", "sessions": 2,
             "focus": "Programming the subconscious, burning desire as the starting point, Mastermind Principle"},
            {"name": "Dweck Growth Mindset", "anchor": "Carol Dweck", "sessions": 2,
             "focus": "Effort creates mastery, failure is feedback, fixed vs growth mindset in sales"},
            {"name": "Conviction & Call Reluctance", "anchor": "Elliott / Ziglar / Frankl", "sessions": 2,
             "focus": "Overcoming fear of rejection, building unshakeable product conviction, meaning drives resilience"},
        ],
        "skills_taught": [
            "Grant Cardone 10X Rule — 10X your goals AND 10X your effort",
            "Cardone's Massive Action — the fourth degree of action beyond normal",
            "Cardone's 'Sell or Be Sold' — someone is always being sold in every interaction",
            "Andy Elliott's Savage Sales Mindset — killer instinct and wolf mentality",
            "Elliott's rejection as fuel — using 'no' as motivation to sharpen skills",
            "Elliott's morning routine — cold showers, affirmations, visualization, attack mode",
            "Tony Robbins' State Management — physiology drives psychology (peak state)",
            "Robbins' Incantations — embodied affirmations with full physiology",
            "Robbins' Triad: Focus, Language, Physiology — the three levers of state",
            "David Goggins' Mental Toughness — callusing the mind through voluntary discomfort",
            "Goggins' 40% Rule — when you think you're done, you're only at 40%",
            "Goggins' Accountability Mirror — radical honesty about weaknesses",
            "Napoleon Hill's Autosuggestion — programming the subconscious for success",
            "Hill's Burning Desire — the starting point of all achievement",
            "Hill's Mastermind Principle — the power of aligned minds working together",
            "Carol Dweck's Growth Mindset — effort and practice create mastery, failure is feedback",
            "Viktor Frankl's Purpose — meaning drives resilience in any circumstance",
            "Daily confidence building routines and rituals",
            "Overcoming call reluctance and fear of rejection",
            "Building unshakeable conviction in your product and process",
        ],
        "measurement": [
            "Does the agent project confidence and conviction on the phone?",
            "Can the agent recover quickly from rejection without losing energy?",
            "Does the agent take massive action (Cardone) or make excuses?",
            "Does the agent have a morning routine that primes peak state (Elliott/Robbins)?",
            "Can the agent articulate WHY they believe in their product (conviction)?",
            "Does the agent embrace discomfort as growth (Goggins)?",
            "Does the agent treat failure as feedback (Dweck)?",
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
            "tonality, rapport, discovery, objection handling, preframing, reframing, "
            "frame control, interiority, and closing. Graded across 11 KPIs by the "
            "adaptive grading engine."
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
                "No Sleight of Mouth reframes attempted (Wilde NLP patterns absent)",
                "Spouse deferral never tested with hypothetical escalation",
            ],
            "homework_type": "objection_handling module + reframing drills (Wilde Sleight of Mouth)",
        },
        "flow_patterns": {
            "indicators": [
                "Frequent backward phase transitions",
                "Missing entire phases (skipping preframing)",
                "No clear structure to the conversation",
                "Agent follows the prospect instead of leading (weak interiority)",
                "No upfront contract or roadmap set",
                "Sensitive requests sprung without preframing",
                "No ascension agreements used at key checkpoints (Wilde)",
                "No buying state created — logic only, no emotional engagement",
            ],
            "homework_type": "preframing_control module + structure drills + interiority practice (Wilde)",
        },
        "closing_patterns": {
            "indicators": [
                "High rapport but low close rate (rapport-to-close gap)",
                "Never uses assumptive close or summary close",
                "Gives up after first objection instead of looping",
                "Does not connect close to established consequence",
                "No compliance ladder built — big ask without small yeses",
                "No ascension agreements — prospect never actively confirmed progression",
                "Lacks conviction — sounds uncertain at the close (weak interiority)",
                "No identity shift — prospect still sees decision as financial, not personal",
                "No irresistible future painted — prospect cannot visualize the protected life",
            ],
            "homework_type": "closing drills + conviction practice + Wilde buying state drills",
        },
    },
}
