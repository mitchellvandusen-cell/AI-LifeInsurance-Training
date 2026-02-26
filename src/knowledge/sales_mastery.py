"""
Sales Mastery Knowledge Base
============================

The expert brain behind every coaching decision.

This is NOT a collection of tips. This is a structured, theory-based encoding
of the world's most effective sales methodologies — distilled into frameworks
an AI coach can reference to give specific, measurable, actionable guidance.

Sources:
    - Jordan Belfort: Way of the Wolf / Straight Line Persuasion
    - Chris Voss: Never Split the Difference
    - Brian Tracy: Psychology of Selling
    - Zig Ziglar: Secrets of Closing the Sale
    - Grant Cardone: Sell or Be Sold
    - SPIN Selling (Neil Rackham)
    - Sandler Selling System
    - NLP-based rapport and behavioral influence

Design principle: Every piece of knowledge here must be TEACHABLE and MEASURABLE.
The AI coach must be able to explain WHY something works, demonstrate it,
evaluate a student's attempt, and give precise corrective feedback.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════════
# TONALITY — The most underrated weapon in sales
# Source: Jordan Belfort (Straight Line), Chris Voss (Late-Night FM DJ)
# ═══════════════════════════════════════════════════════════════════

TONALITY = {
    "core_principle": (
        "Tonality communicates more than words. A prospect decides whether to trust "
        "you, comply with you, or resist you based on HOW you sound — often before "
        "they process WHAT you said. Mastering tonality means controlling the "
        "subconscious signals your voice sends. Jordan Belfort identifies specific "
        "tonal patterns that trigger predictable psychological responses. Chris Voss "
        "emphasizes the 'late-night FM DJ voice' — calm, slow, downward-inflecting — "
        "as the single most disarming vocal tool in negotiation."
    ),

    "tones": {
        "declarative": {
            "description": "Downward inflection at the end of statements. Voice drops.",
            "psychology": (
                "Signals certainty and authority. The speaker believes what they are "
                "saying. The listener's brain registers this as fact, not opinion. "
                "Downward inflection bypasses the analytical filter — the prospect "
                "does not question statements delivered with declarative tonality."
            ),
            "when_to_use": [
                "Stating credentials or company background",
                "Presenting pricing — NEVER let price go up in inflection",
                "Closing statements — 'Here is what we are going to do'",
                "Reframing objections — certainty dissolves doubt",
                "Any statement you need the prospect to accept as truth",
            ],
            "common_mistake": (
                "Agents unconsciously use upward inflection on price statements, "
                "turning '$47 a month' into a question. This signals that even "
                "the agent thinks the price might be too high."
            ),
            "practice_drill": (
                "Say 'The monthly investment is forty-seven dollars' with your voice "
                "dropping on 'dollars'. Record yourself. If 'dollars' goes UP, you "
                "just told the prospect you are not sure about the price."
            ),
        },

        "question_inflection": {
            "description": "Upward inflection at the end. Voice rises.",
            "psychology": (
                "Invites response. Creates engagement. Makes the prospect feel heard. "
                "BUT — on statements, upward inflection signals uncertainty. The "
                "prospect hears a question mark where there should be a period."
            ),
            "when_to_use": [
                "Actual questions — discovery, rapport, qualification",
                "Micro-commitments — 'Does that make sense?' (upward is correct here)",
                "Checking understanding — 'Are you with me so far?'",
            ],
            "when_NOT_to_use": [
                "Price presentation — NEVER",
                "Credential sharing — sounds like you are asking permission to exist",
                "Closing — sounds like you are asking if they want to buy instead of leading them to buy",
                "Handling objections — sounds uncertain and unconfident",
            ],
            "practice_drill": (
                "Read a price statement five times. First three with upward inflection "
                "(hear how weak it sounds). Last two with downward. Feel the difference. "
                "That difference is the difference between closing and losing."
            ),
        },

        "scarcity_whisper": {
            "description": (
                "Volume drops. Speaking quieter, almost conspiratorial. As if sharing "
                "something private and important."
            ),
            "psychology": (
                "Belfort's 'reasonable man' tone. When you whisper or lower your voice, "
                "the prospect leans in — literally and psychologically. The brain "
                "interprets quiet speech as important and private. It creates an "
                "intimacy that builds trust and makes the information feel exclusive."
            ),
            "when_to_use": [
                "Sharing something the prospect should pay special attention to",
                "Creating urgency — 'Between you and me, this rate is not going to last'",
                "Consequence framing — lower voice when discussing what happens if they don't act",
                "Pricing — whisper the price, the prospect perceives it as a deal",
                "Building rapport — lowering voice creates intimacy",
            ],
            "practice_drill": (
                "Take your consequence question. Say it at normal volume. Then say it "
                "at 60% volume, slower. Notice how the second version FEELS heavier, "
                "more real, more important. That is the scarcity whisper."
            ),
        },

        "reasonable_man": {
            "description": (
                "Even, measured, calm. Not too high, not too low. Conversational. "
                "The voice of someone simply having an honest conversation."
            ),
            "psychology": (
                "From Belfort: this is the baseline tone that says 'I am a reasonable "
                "person having a reasonable conversation with you.' It disarms "
                "skepticism because there is nothing to be skeptical OF. The prospect "
                "cannot object to reasonableness."
            ),
            "when_to_use": [
                "Discovery phase — when asking about their life, goals, situation",
                "Medical underwriting — calm, professional, routine",
                "Building rapport — warm but controlled",
                "After handling an objection — return to calm baseline",
            ],
            "practice_drill": (
                "Imagine you are explaining to a friend why you chose your health "
                "insurance. No selling. No pitch. Just a person talking. That is "
                "the reasonable man tone. Record your discovery questions in this tone."
            ),
        },

        "certainty_absolute": {
            "description": (
                "Full conviction. Slightly louder. Pace slightly faster. Complete "
                "confidence without aggression."
            ),
            "psychology": (
                "Belfort's 'Three Tens': the prospect must reach certainty on three "
                "levels — the product, trust in YOU, and trust in the COMPANY. This "
                "tone directly transfers your certainty to them. Humans mirror the "
                "emotional state of the person they are speaking with. If you are "
                "certain, they become certain."
            ),
            "when_to_use": [
                "Presenting the solution after discovery — 'Based on everything you told me...'",
                "Credential sharing — 'I have been doing this for X years because...'",
                "When the prospect wavers — inject conviction",
                "The assumptive close — 'Great, let me get this started for you'",
            ],
            "practice_drill": (
                "Stand up. Take a breath. Say 'This is exactly what you need based "
                "on everything you have told me' as if you believe it with every cell "
                "in your body. Not loud. Not aggressive. Certain. Record it. Does it "
                "sound like someone who KNOWS, or someone who HOPES?"
            ),
        },

        "strategic_pause": {
            "description": "Intentional silence. 2-4 seconds after a key statement.",
            "psychology": (
                "Silence after a powerful statement forces the prospect to sit with it. "
                "Their brain fills the space with their own thoughts — usually confirming "
                "what you just said. Chris Voss uses this extensively: make a statement, "
                "then go silent. The prospect will either agree or reveal their true position. "
                "Either outcome is valuable."
            ),
            "when_to_use": [
                "After the consequence question — 'What happens to your family if...' [PAUSE]",
                "After presenting price — let them process before you speak again",
                "After an objection handle — give them space to accept the reframe",
                "After a closing question — whoever speaks first loses",
                "After a mirror or label (Voss technique)",
            ],
            "practice_drill": (
                "Ask your consequence question. Then count silently to four. It will "
                "feel like an eternity. It is not. It is four seconds. Those four seconds "
                "are where the sale is made — in the silence, not in the pitch."
            ),
        },

        "late_night_fm_dj": {
            "description": (
                "Chris Voss signature. Slow, calm, deep, soothing. Like a late-night "
                "radio host. Downward inflection. Unhurried."
            ),
            "psychology": (
                "The most disarming voice in negotiation. When someone uses this tone, "
                "the listener's defensive walls come down. It is nearly impossible to "
                "be aggressive toward someone using the FM DJ voice. Voss uses this when "
                "dealing with high-emotion situations, resistant prospects, or when "
                "delivering uncomfortable truths."
            ),
            "when_to_use": [
                "When the prospect is emotional or upset",
                "When handling a serious objection — don't match their energy",
                "When asking difficult questions — health history, financial situation",
                "When the prospect is rushing — slow them down with your pace",
                "During the consequence conversation",
            ],
            "practice_drill": (
                "Record yourself saying 'Tell me more about that' in your normal voice. "
                "Now say it as if you are a late-night radio host at 2am. Slow. Warm. "
                "Calm. The second version builds 3x more trust."
            ),
        },
    },

    "micro_tonality_shifts": {
        "description": (
            "Expert sellers shift tonality WITHIN a single sentence. The shift itself "
            "is a communication tool — it tells the prospect which words matter most."
        ),
        "examples": [
            {
                "sentence": "The monthly investment is forty-seven dollars",
                "shift": "Normal pace on 'the monthly investment is' → slight pause → "
                         "lower voice, downward inflection on 'forty-seven dollars'",
                "effect": "Price feels small and certain, not questioned",
            },
            {
                "sentence": "What happens to Sarah and the kids if something happens to you",
                "shift": "Normal on 'what happens to' → slower, softer on 'Sarah and "
                         "the kids' → pause → even softer on 'if something happens to you'",
                "effect": "The consequence becomes visceral and personal, not hypothetical",
            },
            {
                "sentence": "Based on everything you told me, this is exactly what you need",
                "shift": "Reasonable tone on 'based on everything you told me' → "
                         "certainty tone, slightly louder on 'this is exactly what you need'",
                "effect": "Bridges from empathy to conviction — I heard you AND I know the answer",
            },
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════
# RAPPORT & DISCOVERY — Building human connection + finding the sale
# Source: Voss (tactical empathy), Tracy (dominant buying motive),
#         Sandler (pain funnel), SPIN Selling
# ═══════════════════════════════════════════════════════════════════

RAPPORT_DISCOVERY = {
    "core_principle": (
        "Rapport is not small talk. Rapport is the prospect feeling UNDERSTOOD. "
        "Discovery is not an interrogation. Discovery is finding the prospect's "
        "pain, goal, and consequence — the three pillars that make a sale possible. "
        "Without genuine rapport, discovery feels invasive. Without discovery, "
        "you are presenting a solution to a problem you haven't identified. "
        "Brian Tracy: 'People buy for their reasons, not yours.' Your job in "
        "discovery is to find THEIR reasons."
    ),

    "tactical_empathy": {
        "source": "Chris Voss",
        "description": (
            "Understanding the other person's feelings and perspective, and then "
            "VERBALIZING that understanding. Not sympathy. Not agreement. Recognition. "
            "When a prospect feels recognized, their defenses lower."
        ),
        "techniques": {
            "mirroring": {
                "how": (
                    "Repeat the last 1-3 words of what the prospect said, with "
                    "upward inflection. Then go silent."
                ),
                "example": "Prospect: 'I just want to make sure my kids are taken care of.' "
                           "Agent: 'Taken care of?' [silence]",
                "why_it_works": (
                    "The prospect's brain interprets the mirror as genuine curiosity. "
                    "They elaborate — giving you deeper information than the original "
                    "statement. Mirroring gets people to reveal their real thoughts "
                    "without you asking a direct question."
                ),
                "practice": (
                    "In your next 10 conversations (sales or personal), mirror "
                    "at least once. Just repeat the last 2-3 words with a questioning "
                    "tone. Notice how people naturally expand."
                ),
            },
            "labeling": {
                "how": (
                    "Name the emotion you detect. Start with 'It sounds like...' or "
                    "'It seems like...' NEVER 'I think you feel...' (the 'I' makes it about you)."
                ),
                "example": "Agent: 'It sounds like this has been weighing on you for a while.'",
                "why_it_works": (
                    "Labeling an emotion REDUCES its intensity. When a prospect is "
                    "anxious about cost, labeling that anxiety ('It seems like the cost "
                    "is the main concern') actually makes them LESS anxious. The emotion "
                    "loses power when it is named."
                ),
                "practice": (
                    "After every prospect statement that has emotion behind it, "
                    "label it before asking your next question. 'It sounds like that "
                    "really matters to you.' Watch what happens."
                ),
            },
            "accusation_audit": {
                "how": (
                    "List every negative thing the prospect might think about you, "
                    "your company, or the product — BEFORE they say it. Preemptively "
                    "address the worst-case thoughts."
                ),
                "example": (
                    "'You are probably thinking this is just another insurance call, "
                    "and I am going to try to sell you something you don't need, and "
                    "it is going to take forever. I get it.'"
                ),
                "why_it_works": (
                    "Voss: 'When you label the negatives, they sound exaggerated when "
                    "said aloud, and the prospect often says No, it is not that bad. "
                    "They argue AGAINST their own objections.' By voicing their fears "
                    "first, you steal their power."
                ),
                "practice": (
                    "Before your next call, write down the three worst things the "
                    "prospect might be thinking. Then open the call by naming them. "
                    "Notice how the prospect relaxes."
                ),
            },
        },
    },

    "discovery_framework": {
        "three_pillars": {
            "goal": {
                "what": "What the prospect wants to achieve or protect.",
                "question_types": [
                    "What made you fill out that form? What were you looking into?",
                    "What is most important to you when it comes to protecting your family?",
                    "If you could have the perfect coverage, what would it look like?",
                ],
                "why_critical": (
                    "The goal gives you the target. Without it, you are presenting "
                    "features instead of solutions."
                ),
            },
            "why_behind_the_goal": {
                "what": (
                    "The deeper emotional reason behind the stated goal. The goal is "
                    "logical. The WHY is emotional. People buy on emotion."
                ),
                "question_types": [
                    "What made you start thinking about this now?",
                    "Why is this important to you specifically?",
                    "Tell me about [family member] — what is their situation?",
                ],
                "why_critical": (
                    "Brian Tracy: the dominant buying motive is always emotional. "
                    "Logic justifies, emotion decides. The WHY is the emotion."
                ),
            },
            "consequence": {
                "what": (
                    "What happens if they do NOT act. The cost of inaction. "
                    "This is the most powerful tool in the entire sales process."
                ),
                "question_types": [
                    "What happens to [family member] if something happens to you and this is not in place?",
                    "If you do not do anything about this, what does that look like in 5 years?",
                    "Walk me through what your family deals with if the worst happens and there is no coverage.",
                ],
                "why_critical": (
                    "Without consequence, there is no urgency. Without urgency, "
                    "there is no sale today. Every objection about timing traces "
                    "back to missing consequence. Zig Ziglar: 'People do not buy "
                    "drills. They buy holes.' But more than that — people buy to "
                    "AVOID the pain of not having the hole."
                ),
            },
        },

        "question_quality": {
            "open_vs_closed": {
                "open": {
                    "definition": "Cannot be answered with yes or no. Forces elaboration.",
                    "starts_with": ["What", "How", "Tell me about", "Walk me through", "Describe"],
                    "when_to_use": "Discovery, rapport, understanding the prospect's world",
                    "example": "What made you start thinking about life insurance?",
                },
                "closed": {
                    "definition": "Yes/no answer. Binary confirmation.",
                    "when_to_use": "Micro-commitments, compliance checks, confirming facts",
                    "example": "Does that make sense?",
                    "caution": (
                        "Too many closed questions in discovery feels like an interrogation. "
                        "The prospect feels cornered, not heard."
                    ),
                },
                "calibrated": {
                    "source": "Chris Voss",
                    "definition": (
                        "'How' and 'What' questions that give the prospect the illusion "
                        "of control while you direct the conversation."
                    ),
                    "examples": [
                        "How would you like to handle this?",
                        "What does a good outcome look like for you?",
                        "How am I supposed to do that? (to push back on unreasonable demands)",
                    ],
                    "why_powerful": (
                        "Calibrated questions make the prospect feel like they are in "
                        "control while you maintain direction. They cannot be answered "
                        "with yes or no, forcing the prospect to engage deeply."
                    ),
                },
            },

            "advancing_vs_throwaway": {
                "advancing": (
                    "Questions that move the sale forward. They uncover needs, "
                    "establish consequence, build urgency, or confirm commitment. "
                    "Every question should have a PURPOSE."
                ),
                "throwaway": (
                    "Questions that fill time but do not advance the sale. "
                    "'So, how is the weather?' is throwaway. 'What would it "
                    "mean for your family to have that security?' is advancing."
                ),
                "test": (
                    "After every question, ask yourself: 'Does the answer to this "
                    "bring me closer to helping them or closer to wasting time?' "
                    "If it does not advance, do not ask it."
                ),
            },

            "spin_framework": {
                "source": "Neil Rackham",
                "situation": "Questions about current facts and context (use sparingly — the prospect gets bored)",
                "problem": "Questions about difficulties, dissatisfaction, or concerns (surfaces the pain)",
                "implication": "Questions about consequences of the problem (amplifies the pain)",
                "need_payoff": "Questions about value of solving the problem (lets THEM sell themselves)",
                "example_flow": [
                    "Situation: 'What kind of coverage do you have right now?'",
                    "Problem: 'What concerns you most about your current situation?'",
                    "Implication: 'If that concern became reality, what happens to your family?'",
                    "Need-payoff: 'If we could address that concern today, how would that change things for you?'",
                ],
            },
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
# OBJECTION HANDLING — The art of isolating and resolving barriers
# Source: Belfort (Straight Line Looping), Voss (calibrated questions),
#         Ziglar (Feel-Felt-Found), Sandler (reversing)
# ═══════════════════════════════════════════════════════════════════

OBJECTION_HANDLING = {
    "core_principle": (
        "An objection is not a rejection. It is a REQUEST FOR MORE INFORMATION "
        "delivered through the lens of fear. The prospect is saying 'I am not there "
        "yet — help me get there.' Grant Cardone: 'The sale is not made when the "
        "customer says yes. The sale is made when the customer says no and you "
        "continue with grace and conviction.' An untrained agent hears 'no' and "
        "stops. A trained agent hears 'no' and starts."
    ),

    "belfort_straight_line_loop": {
        "source": "Jordan Belfort — Way of the Wolf",
        "concept": (
            "After an objection, you do NOT try to overcome it head-on. You LOOP "
            "back — acknowledge, empathize, then redirect to value. Then you close "
            "again. If another objection comes, loop again. Each loop builds conviction "
            "and peels back the layers until you reach the true barrier."
        ),
        "three_tens": {
            "description": (
                "Belfort's framework: the prospect must be at a 10 (on a scale of 1-10) "
                "on three dimensions before they will buy:"
            ),
            "product": "Do they believe the product solves their problem? (10 = absolute certainty)",
            "trust_in_you": "Do they trust YOU as the person delivering it? (10 = complete trust)",
            "trust_in_company": "Do they trust the COMPANY behind the product? (10 = no doubt)",
            "application": (
                "When a prospect objects, determine WHICH of the three tens is below threshold. "
                "An objection about timing is usually a '5' on Trust in You. An objection "
                "about price is usually a '6' on Product. Target the weakest ten, not the "
                "surface objection."
            ),
        },
        "loop_structure": [
            "Acknowledge — 'I hear you. That makes complete sense.'",
            "Deflect with empathy — 'And honestly, if I were in your shoes, I might feel the same way.'",
            "Redirect to value — 'But let me ask you this...' (back to consequence/goal)",
            "Ramp certainty — share a fact, story, or credential that raises the weakest Ten",
            "Close again — 'So with that in mind, let us go ahead and get this taken care of.'",
        ],
    },

    "voss_techniques": {
        "no_oriented_questions": {
            "concept": (
                "Chris Voss: Instead of pushing for 'yes', design questions that let "
                "the prospect say 'no'. 'No' gives the prospect a sense of control and "
                "safety. A prospect who feels in control is more likely to engage honestly."
            ),
            "examples": [
                "'Would it be ridiculous to take five minutes to look at this?' (They say 'No, not ridiculous')",
                "'Is it a bad idea to make sure your family is protected?' (They say 'No, it is not a bad idea')",
                "'Have you given up on finding the right coverage?' (They say 'No, I haven't given up')",
            ],
            "why_it_works": (
                "Every 'no' is actually a 'yes' in disguise. 'No, it is not ridiculous' = "
                "'Yes, I will give you five minutes.' But the prospect FEELS like they chose it."
            ),
        },
        "rule_of_three": {
            "concept": (
                "Get the prospect to agree to the same thing three different ways. "
                "The first yes is often reflexive. The second is confirmation. The third "
                "is commitment. If you cannot get them to agree three ways, their first "
                "yes was counterfeit."
            ),
        },
    },

    "ziglar_techniques": {
        "feel_felt_found": {
            "structure": (
                "'I understand how you feel. Many of my clients felt the same way. "
                "What they found was...'"
            ),
            "why_it_works": (
                "Validates emotion (feel). Normalizes it (felt — others had it too). "
                "Reframes with evidence (found — here is what happened). The prospect "
                "does not feel alone or wrong for objecting."
            ),
            "caution": (
                "This technique is overused and prospects may recognize it. "
                "Use the STRUCTURE but personalize the language. Do not say the "
                "literal words 'feel, felt, found' — internalize the framework."
            ),
        },
        "alternate_close": {
            "concept": (
                "Give two options, both of which result in moving forward. "
                "'Would you prefer the $250,000 or $500,000 coverage?' "
                "The prospect's brain shifts from 'should I buy' to 'which one'."
            ),
        },
        "assumptive_close": {
            "concept": (
                "Proceed as if the decision has already been made. "
                "'Great, let me pull up the application. Can you spell your last name for me?' "
                "The transition from discussion to action should be seamless."
            ),
        },
    },

    "isolation_protocol": {
        "description": (
            "The most critical skill in objection handling. Before you can resolve "
            "an objection, you must ISOLATE it — put it on an island."
        ),
        "three_tests": {
            "truth_test": {
                "what": "Is this the REAL objection or a smokescreen?",
                "how": "Probe beneath the surface. 'Besides that, is there anything else?'",
                "signal_of_smokescreen": (
                    "The prospect cannot articulate the objection clearly, shifts reasons, "
                    "or the stated concern does not match their emotional state."
                ),
            },
            "singularity_test": {
                "what": "Is this the ONLY barrier?",
                "how": "'If we could solve that one thing, is there anything else that would hold you back?'",
                "why": (
                    "If you resolve the stated objection and a new one immediately appears, "
                    "you never had the real objection. You were chasing smokescreens."
                ),
            },
            "commitment_test": {
                "what": "If this is resolved, will they act NOW?",
                "how": "'If I could address that concern right now, are you ready to move forward today?'",
                "why": (
                    "This test reveals whether the prospect is genuinely blocked by this "
                    "issue or is using it as a polite way to disengage."
                ),
            },
        },
    },

    "common_objections": {
        "i_need_to_think_about_it": {
            "root_cause": "Usually MONEY or missing CONSEQUENCE",
            "handle": (
                "Acknowledge → Probe the truth → Redirect to consequence. "
                "'I totally understand. And just so I can help you think through it — "
                "what specifically are you wanting to think about? Is it the coverage "
                "amount, the monthly cost, or something else?' Then: 'Because you told "
                "me earlier that [CONSEQUENCE]. That does not wait while we think.'"
            ),
        },
        "i_need_to_talk_to_my_spouse": {
            "root_cause": "DECISION_MAKER or masked MONEY",
            "handle": (
                "Hypothetical escalation. 'That makes sense. Let me ask you this — "
                "if you bring this to [spouse] and explain that for $X a month, your "
                "family has $Y of protection, what do you think they would say?' Then "
                "escalate: 'Say they had a rough day and said no — what would YOU do?'"
            ),
        },
        "its_too_expensive": {
            "root_cause": "MONEY — value not established relative to consequence",
            "handle": (
                "Reframe cost against consequence. 'I hear you. Let me put it this way — "
                "you told me that if something happened, [CONSEQUENCE]. That is the cost of "
                "NOT having this. We are talking about $X a month — less than [relatable "
                "comparison] — to make sure that never happens.'"
            ),
        },
        "im_not_interested": {
            "root_cause": "Preoccupation not broken or rapport failure",
            "handle": (
                "Pattern interrupt + redirect to their form fill. 'I totally get it — and "
                "honestly, most people say that on these calls. But you did fill out that "
                "form looking into coverage, right? Something made you do that. What was "
                "going on at the time?'"
            ),
        },
        "send_me_some_information": {
            "root_cause": "Polite dismissal — agent has not earned the conversation",
            "handle": (
                "Agree and redirect. 'Absolutely, I can do that. But so I know what to "
                "send you — what specifically are you looking for? Coverage amount? Pricing? "
                "I do not want to send you a generic package that does not apply to your "
                "situation.' This reopens discovery."
            ),
        },
    },
}


# ═══════════════════════════════════════════════════════════════════
# PREFRAMING & FRAME CONTROL — Controlling the conversation
# Source: Belfort (Straight Line), NLP (framing), Cardone (conviction)
# ═══════════════════════════════════════════════════════════════════

FRAME_CONTROL = {
    "core_principle": (
        "The person who controls the frame controls the conversation. "
        "Frame = the context through which information is interpreted. "
        "In sales, you must set the frame for every sensitive request BEFORE "
        "making it. A request without a frame is an ambush. A request with "
        "a frame is a logical next step."
    ),

    "preframing": {
        "banking_info": {
            "why": "The prospect needs to understand WHY financial information is needed before being asked.",
            "good_frame": (
                "'In just a minute, I am going to need your banking information. "
                "The reason is that coverage does not go into effect until the first "
                "payment is processed. Nothing is charged today — this just sets up "
                "the billing so your family is covered from day one.'"
            ),
            "bad_frame": "Asking for banking info with no context = prospect's guard goes up 10x",
        },
        "social_security": {
            "why": "SSN is the most sensitive information. Must be contextualized.",
            "good_frame": (
                "'The carrier requires your Social Security number to run the application. "
                "This is a secure, encrypted system — same as your bank uses. I cannot see "
                "it after this call, and it is only used for the application.'"
            ),
            "bad_frame": "Asking for SSN without context = trust destroyed, call ends",
        },
        "next_steps": {
            "why": (
                "The prospect should know what is coming BEFORE it comes. "
                "Surprises in a sales process create resistance."
            ),
            "good_frame": (
                "'Here is what we are going to do. I am going to ask you some health "
                "questions — takes about five minutes. Then I will show you exactly "
                "what you qualify for and how much it costs. If it makes sense, great. "
                "If not, no pressure. Sound good?'"
            ),
        },
    },

    "frame_recovery": {
        "description": (
            "When a prospect takes control of the conversation (asking rapid questions, "
            "challenging, going off-topic), the agent must redirect."
        ),
        "technique": (
            "Answer briefly → Bridge → Redirect with a question. "
            "'Great question. [Brief answer]. Now let me ask you this — [your question].' "
            "The redirect question takes control back."
        ),
        "rule": (
            "If the prospect asks three consecutive questions and you answer all three "
            "without redirecting, you have lost the frame. You are now being interviewed "
            "instead of conducting a consultation."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════
# OUTBOUND CALLING — Breaking preoccupation + the first 30 seconds
# Source: Belfort (Straight Line opening), Cardone (10X persistence)
# ═══════════════════════════════════════════════════════════════════

OUTBOUND_CALLING = {
    "core_principle": (
        "The first 10 seconds of an outbound call determine everything. The prospect "
        "did not wake up wanting to talk to you. They are in the middle of their life. "
        "Your job in the first 30 seconds is NOT to sell. It is to earn the right to "
        "have a conversation. Break their preoccupation, establish legitimacy, and "
        "give them a reason to stay on the line."
    ),

    "preoccupation_breaking": {
        "concept": (
            "The prospect is mentally somewhere else when they answer. They are cooking, "
            "driving, working, watching TV. Their brain is occupied. You must BREAK "
            "that preoccupation before anything you say will register."
        ),
        "techniques": [
            {
                "name": "Name + Reason + Permission",
                "structure": "'Hi [Name], this is [Agent] with [Company]. You filled out a form about life insurance — do you have a quick minute?'",
                "why": "Name gets attention. Form reference establishes legitimacy. Permission shows respect.",
            },
            {
                "name": "Pattern Interrupt",
                "structure": "'Hey [Name], real quick — you probably don't remember, but you looked into some coverage options online. Ring a bell?'",
                "why": "Casual tone disarms. 'Ring a bell?' is a question that forces engagement.",
            },
            {
                "name": "Voss Accusation Audit Opener",
                "structure": "'Hi [Name], I know you're probably busy and the last thing you want is a phone call — I'll be quick.'",
                "why": "Names their resistance before they can. Disarms the reflexive 'I'm busy.'",
            },
        ],
    },

    "first_30_seconds_checklist": [
        "State your name clearly (authority signal)",
        "Reference how you got their information (legitimacy)",
        "Give a brief, honest reason for the call",
        "Ask for permission to continue (builds compliance)",
        "Use declarative tonality — you BELONG here",
        "Do NOT pitch — earn the conversation first",
    ],
}


# ═══════════════════════════════════════════════════════════════════
# CLOSING — The natural conclusion of a well-run process
# Source: Ziglar (20+ techniques), Cardone (conviction), Belfort (assumptive)
# ═══════════════════════════════════════════════════════════════════

CLOSING = {
    "core_principle": (
        "Zig Ziglar: 'You can have everything in life you want, if you will just "
        "help enough other people get what they want.' Closing is not something you "
        "DO to someone. It is the natural conclusion of having served them well. "
        "If discovery was thorough, consequence was established, value was demonstrated, "
        "and trust was built — the close is a formality."
    ),

    "techniques": {
        "assumptive": {
            "how": "Proceed as if the decision is made. Transition from discussion to action.",
            "example": "'Alright, everything looks great. Let me get the application started — what is your full legal name?'",
            "when": "Trust and authority are high. Rapport established. No unresolved objections.",
        },
        "takeaway": {
            "how": "Gently suggest the product might not be for them. Scarcity of opportunity.",
            "example": "'You know what, based on your situation, this might actually not be the right fit. Let me ask you one more thing before we decide.'",
            "psychology": "Loss aversion. People want what they might not be able to have.",
        },
        "urgency_bridge": {
            "how": "Connect consequence to unpredictability of timing.",
            "example": "'You told me that if something happened, [CONSEQUENCE]. The thing is, nobody gets to choose when. Every day without this is a day your family is exposed.'",
            "when": "Consequence was established but prospect is delaying.",
        },
        "summary": {
            "how": "Recap everything they told you, then present the solution as the logical answer.",
            "example": "'So — you want to make sure [GOAL], because [WHY]. You told me what happens if you don't [CONSEQUENCE]. This plan gives you exactly that for [PRICE]. Make sense?'",
            "when": "Discovery was thorough. Prospect needs to hear it all connected.",
        },
    },

    "cardone_conviction": {
        "principle": (
            "Grant Cardone: 'The prospect can FEEL your level of belief. If you are "
            "at an 8 on conviction but the product requires a 10, you will not close. "
            "You must be at 10 — absolute certainty that this product will help this "
            "person — or the prospect senses the gap.' The sale happens when your "
            "conviction exceeds their resistance."
        ),
        "application": (
            "Before every close attempt, check: Do I genuinely believe this person "
            "needs this product? If yes, closing is an act of service, not pressure. "
            "If no, you have not finished discovery."
        ),
    },
}


# ═══════════════════════════════════════════════════════════════════
# PSYCHOLOGY OF SELLING — Why people buy
# Source: Tracy (Psychology of Selling), Cialdini (Influence),
#         Kahneman (Thinking Fast and Slow)
# ═══════════════════════════════════════════════════════════════════

BUYING_PSYCHOLOGY = {
    "core_principle": (
        "Brian Tracy: 'People buy emotionally and justify logically.' Every "
        "purchase decision starts in the limbic system (emotional brain) and "
        "is then rationalized by the prefrontal cortex (logical brain). Your "
        "presentation must activate BOTH — emotion first, logic second."
    ),

    "six_principles_of_influence": {
        "source": "Robert Cialdini — Influence",
        "reciprocity": "Give value first. When you help someone, they feel obligated to reciprocate.",
        "commitment_consistency": "Get small commitments early. People stay consistent with prior commitments.",
        "social_proof": "'Others in your situation chose...' Humans follow the crowd, especially under uncertainty.",
        "authority": "Demonstrate expertise. Credentials, experience, specific knowledge builds authority.",
        "liking": "People buy from people they like. Rapport, humor, genuine interest = likability.",
        "scarcity": "Limited availability increases value. 'This rate is available today' (only if TRUE).",
    },

    "loss_aversion": {
        "source": "Daniel Kahneman",
        "principle": (
            "People feel the pain of loss 2.5x more intensely than the pleasure of gain. "
            "Framing coverage as 'protecting against loss' is 2.5x more powerful than "
            "'gaining security.' Consequence-based selling works BECAUSE of loss aversion."
        ),
    },

    "dominant_buying_motive": {
        "source": "Brian Tracy",
        "concept": (
            "Every prospect has ONE dominant reason they will buy. Everything else "
            "is secondary. Your job in discovery is to find that ONE reason and "
            "make it the centerpiece of your presentation."
        ),
        "types": [
            "Fear of loss (most powerful for insurance — 'what happens if...')",
            "Desire for gain (legacy building, peace of mind)",
            "Fear of criticism (what will others think if I don't provide)",
            "Love and belonging (protecting the people they love)",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE LADDER — Small yeses lead to the big yes
# Source: Cialdini (commitment/consistency), Belfort (compliance patterns)
# ═══════════════════════════════════════════════════════════════════

COMPLIANCE_LADDER = {
    "core_principle": (
        "You never ask for the sale without first building a pattern of agreement. "
        "Small yeses — micro-commitments — train the prospect's brain to say yes. "
        "By the time you ask for the big yes, their brain is already in agreement mode."
    ),
    "micro_commitments": [
        "'Can you grab a pen real quick?' (first physical compliance)",
        "'Does that make sense?' (after explaining a concept)",
        "'Fair enough?' (after a statement)",
        "'Are you with me so far?' (during a longer explanation)",
        "'Can you do that for me?' (before asking for information)",
        "'Sound reasonable?' (after preframing)",
    ],
    "escalation": (
        "Start with easy, non-threatening requests (grab a pen). Build to medium "
        "(does that make sense). By the time you ask for banking info or SSN, "
        "the prospect has already said yes 8-10 times. The pattern carries."
    ),
}


# ═══════════════════════════════════════════════════════════════════
# MODULE DEFINITIONS — What the training modules teach
# ═══════════════════════════════════════════════════════════════════

TRAINING_MODULES = {
    "tonality_mastery": {
        "name": "Tonality Mastery",
        "description": "Master the 7 core tones. Learn when, why, and how each tone works.",
        "skills_taught": [
            "Declarative (downward inflection) for authority and price",
            "Question inflection for genuine discovery",
            "Scarcity whisper for urgency and intimacy",
            "Reasonable man for rapport and trust",
            "Absolute certainty for conviction and closing",
            "Strategic pause for emotional weight",
            "Late-night FM DJ for de-escalation",
            "Micro-shifts within sentences",
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
        "description": "Ask questions that advance the sale. Learn question types, sequencing, and purpose.",
        "skills_taught": [
            "Open vs closed vs calibrated questions",
            "SPIN framework (Situation, Problem, Implication, Need-payoff)",
            "Advancing vs throwaway questions",
            "Mirroring (Voss technique)",
            "Labeling (Voss technique)",
            "Goal, Why, Consequence discovery sequence",
            "Sandler pain funnel",
        ],
        "measurement": [
            "Does the question advance the conversation toward a sale?",
            "Is the question open when it should be open?",
            "Is the question building toward consequence?",
            "Does the agent use calibrated questions for control?",
            "Is the agent asking or interrogating?",
        ],
    },

    "objection_handling": {
        "name": "Objection Handling",
        "description": "Learn to isolate, identify root cause, and resolve objections.",
        "skills_taught": [
            "Smokescreen vs true objection vs condition",
            "Three-test isolation protocol",
            "Belfort straight line loop",
            "Voss no-oriented questions",
            "Ziglar feel-felt-found framework",
            "Hypothetical escalation for third-party deferral",
            "Financial reframe using established consequence",
            "Urgency reframe for timing objections",
        ],
        "measurement": [
            "Does agent isolate BEFORE attempting to resolve?",
            "Can agent identify the root cause (money, time, decision maker)?",
            "Does agent loop back to value after acknowledging?",
            "Does agent stay calm and empathetic during objection?",
            "Does the resolution connect to the prospect's own stated consequence?",
        ],
    },

    "rapport_building": {
        "name": "Rapport & Discovery",
        "description": "Build genuine human connection and uncover the three pillars.",
        "skills_taught": [
            "Tactical empathy (Voss)",
            "Mirroring and labeling",
            "Accusation audit",
            "Goal-Why-Consequence discovery sequence",
            "Active listening indicators",
            "Matching energy and pace",
            "Authentic curiosity vs scripted rapport",
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
        "description": "Set expectations before requests. Maintain conversational control.",
        "skills_taught": [
            "Preframing sensitive requests (banking, SSN, medical)",
            "Setting the conversation roadmap",
            "Frame recovery after losing control",
            "Answer-bridge-redirect technique",
            "Compliance ladder building",
            "Conviction and authority projection",
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
        "description": "Repetition mastery — practice your script with an easy-going AI client until it sounds natural, not rehearsed.",
        "skills_taught": [
            "Natural delivery — saying the words without sounding scripted",
            "Conversational flow — script as a guide, not a prison",
            "Adaptive responses — handling off-script moments naturally",
            "Tonality variety — same words, different emotional delivery",
            "Confidence through repetition — muscle memory for your pitch",
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
        "description": "Complete end-to-end call with a realistic AI prospect. All skills combined.",
        "skills_taught": ["All of the above integrated into a complete sales call"],
        "measurement": ["Complete grading engine evaluation across all 11 KPIs"],
    },
}


# ═══════════════════════════════════════════════════════════════════
# HOMEWORK — Cross-session pattern detection and targeted assignments
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
            ],
            "homework_type": "tonality_mastery module with specific drills",
        },
        "discovery_patterns": {
            "indicators": [
                "Frequently missing consequence establishment",
                "Shallow discovery — goal identified but WHY never explored",
                "Too many closed questions in discovery",
                "Questions do not build on previous answers",
            ],
            "homework_type": "question_mastery module + discovery role-play",
        },
        "objection_patterns": {
            "indicators": [
                "Objections rarely isolated before resolution attempt",
                "Same objection type causes failure across sessions",
                "Agent argues instead of empathizing",
                "Never loops back to consequence during objection handle",
            ],
            "homework_type": "objection_handling module + targeted scenarios",
        },
        "flow_patterns": {
            "indicators": [
                "Frequent backward phase transitions",
                "Missing entire phases (skipping preframing)",
                "No clear structure to the conversation",
                "Agent follows the prospect instead of leading",
            ],
            "homework_type": "preframing_control module + structure drills",
        },
        "closing_patterns": {
            "indicators": [
                "High rapport but low close rate",
                "Never uses assumptive close",
                "Gives up after first objection",
                "Does not connect close to established consequence",
            ],
            "homework_type": "closing drills + conviction practice",
        },
    },
}


def get_knowledge_for_module(module_key: str) -> dict:
    """Return the relevant knowledge sections for a specific training module."""
    module_knowledge = {
        "tonality_mastery": {
            "tonality": TONALITY,
            "module": TRAINING_MODULES["tonality_mastery"],
        },
        "question_mastery": {
            "rapport_discovery": RAPPORT_DISCOVERY,
            "module": TRAINING_MODULES["question_mastery"],
        },
        "objection_handling": {
            "objection_handling": OBJECTION_HANDLING,
            "module": TRAINING_MODULES["objection_handling"],
        },
        "rapport_building": {
            "rapport_discovery": RAPPORT_DISCOVERY,
            "buying_psychology": BUYING_PSYCHOLOGY,
            "module": TRAINING_MODULES["rapport_building"],
        },
        "preframing_control": {
            "frame_control": FRAME_CONTROL,
            "compliance_ladder": COMPLIANCE_LADDER,
            "module": TRAINING_MODULES["preframing_control"],
        },
        "script_practice": {
            "module": TRAINING_MODULES["script_practice"],
        },
        "full_call_simulation": {
            "tonality": TONALITY,
            "rapport_discovery": RAPPORT_DISCOVERY,
            "objection_handling": OBJECTION_HANDLING,
            "frame_control": FRAME_CONTROL,
            "closing": CLOSING,
            "buying_psychology": BUYING_PSYCHOLOGY,
            "compliance_ladder": COMPLIANCE_LADDER,
            "module": TRAINING_MODULES["full_call_simulation"],
        },
    }
    return module_knowledge.get(module_key, {})


def get_all_knowledge() -> dict:
    """Return every knowledge section for comprehensive coaching."""
    return {
        "tonality": TONALITY,
        "rapport_discovery": RAPPORT_DISCOVERY,
        "objection_handling": OBJECTION_HANDLING,
        "frame_control": FRAME_CONTROL,
        "outbound_calling": OUTBOUND_CALLING,
        "closing": CLOSING,
        "buying_psychology": BUYING_PSYCHOLOGY,
        "compliance_ladder": COMPLIANCE_LADDER,
    }
