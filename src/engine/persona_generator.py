"""
ClientPersonaGenerator: Creates realistic AI client personas using:
- Chase Hughes 6-Axis behavioral profiling
- FACE model (Frequency, Amount, Complexity, Emotion)
- Life insurance industry demographics

Each persona is a coherent behavioral profile, not random numbers.
Archetypes ensure realistic, trainable scenarios.
"""

from __future__ import annotations

import random
from typing import Optional

from src.models.state import ClientPersona, FACEProfile, SixAxisProfile


# ── Archetype Definitions ──────────────────────────────────────────
# Each archetype defines behavioral tendencies and realistic attributes.

ARCHETYPES = [
    {
        "name": "The Skeptical Professional",
        "description": "High-income, researched, wants data not emotion",
        "age_range": (35, 55),
        "occupations": ["Engineer", "Accountant", "Attorney", "IT Manager", "Financial Analyst"],
        "income_range": (80000, 200000),
        "six_axis": {"focus": (40, 60), "openness": (20, 40), "connection": (20, 40),
                     "expectancy": (15, 35), "compliance": (30, 50), "suggestibility": (20, 40)},
        "face": {"frequency_of_questions": (60, 85), "amount_of_resistance": (50, 75),
                 "complexity_of_objections": (70, 90), "emotional_volatility": (10, 30)},
        "health_pool": [[], ["blood pressure medication"], ["cholesterol medication"]],
        "pain_points": ["leaving family unprotected", "estate planning gaps", "tax implications"],
        "budget_sensitivity": (20, 40),
        "skepticism_level": (65, 85),
        "baseline_trust": (25, 40),
        "will_test_frame": True,
        "talkativeness": (20, 40),
    },
    {
        "name": "The Concerned Parent",
        "description": "Middle-income, emotionally driven, worried about kids",
        "age_range": (28, 45),
        "occupations": ["Teacher", "Nurse", "Sales Manager", "Small Business Owner", "Office Manager"],
        "income_range": (40000, 85000),
        "six_axis": {"focus": (50, 70), "openness": (50, 70), "connection": (40, 65),
                     "expectancy": (25, 45), "compliance": (55, 75), "suggestibility": (50, 70)},
        "face": {"frequency_of_questions": (40, 60), "amount_of_resistance": (30, 50),
                 "complexity_of_objections": (30, 50), "emotional_volatility": (50, 75)},
        "health_pool": [[], ["anxiety medication"], ["birth control", "anxiety medication"]],
        "pain_points": ["kids growing up without a parent", "mortgage payment", "daycare costs"],
        "budget_sensitivity": (50, 70),
        "skepticism_level": (30, 50),
        "baseline_trust": (40, 60),
        "will_test_frame": False,
        "talkativeness": (50, 70),
    },
    {
        "name": "The Retired Grandparent",
        "description": "Fixed income, wants legacy, may have health issues",
        "age_range": (60, 78),
        "occupations": ["Retired Teacher", "Retired Factory Worker", "Retired Postal Worker",
                        "Retired Nurse", "Retired Military"],
        "income_range": (25000, 55000),
        "six_axis": {"focus": (40, 60), "openness": (35, 55), "connection": (40, 65),
                     "expectancy": (20, 40), "compliance": (45, 65), "suggestibility": (40, 60)},
        "face": {"frequency_of_questions": (30, 50), "amount_of_resistance": (35, 55),
                 "complexity_of_objections": (20, 40), "emotional_volatility": (30, 50)},
        "health_pool": [
            ["blood pressure medication", "cholesterol medication"],
            ["diabetes medication", "blood pressure medication"],
            ["blood pressure medication", "cholesterol medication", "aspirin"],
            ["metformin", "lisinopril", "atorvastatin"],
        ],
        "pain_points": ["funeral costs", "leaving something for grandkids", "not being a burden"],
        "budget_sensitivity": (60, 85),
        "skepticism_level": (40, 60),
        "baseline_trust": (35, 55),
        "will_test_frame": False,
        "talkativeness": (55, 80),
    },
    {
        "name": "The Busy Executive",
        "description": "Time-poor, direct, wants efficiency, will test you",
        "age_range": (40, 60),
        "occupations": ["VP of Operations", "Regional Manager", "Business Owner",
                        "Director of Sales", "CFO"],
        "income_range": (120000, 350000),
        "six_axis": {"focus": (55, 75), "openness": (25, 45), "connection": (20, 40),
                     "expectancy": (30, 50), "compliance": (35, 55), "suggestibility": (20, 40)},
        "face": {"frequency_of_questions": (50, 70), "amount_of_resistance": (40, 60),
                 "complexity_of_objections": (60, 80), "emotional_volatility": (10, 25)},
        "health_pool": [[], ["blood pressure medication"], ["cholesterol medication", "anxiety medication"]],
        "pain_points": ["business succession", "key person insurance", "estate taxes"],
        "budget_sensitivity": (10, 30),
        "skepticism_level": (50, 70),
        "baseline_trust": (30, 45),
        "will_test_frame": True,
        "talkativeness": (25, 45),
    },
    {
        "name": "The Reluctant Spouse",
        "description": "Called because spouse insisted, not personally motivated",
        "age_range": (30, 55),
        "occupations": ["Stay-at-home Parent", "Part-time Worker", "Retail Associate",
                        "Administrative Assistant", "Truck Driver"],
        "income_range": (20000, 60000),
        "six_axis": {"focus": (30, 50), "openness": (25, 45), "connection": (30, 50),
                     "expectancy": (10, 30), "compliance": (50, 70), "suggestibility": (45, 65)},
        "face": {"frequency_of_questions": (20, 40), "amount_of_resistance": (55, 75),
                 "complexity_of_objections": (25, 45), "emotional_volatility": (40, 60)},
        "health_pool": [[], ["anxiety medication"], ["blood pressure medication"]],
        "pain_points": ["spouse's wishes", "kids' future", "doesn't really see the point"],
        "budget_sensitivity": (65, 85),
        "skepticism_level": (55, 75),
        "baseline_trust": (25, 40),
        "will_test_frame": False,
        "talkativeness": (15, 35),
    },
    {
        "name": "The Recently Widowed",
        "description": "Lost spouse, now realizes the importance, emotionally raw",
        "age_range": (45, 70),
        "occupations": ["Retired", "School Cafeteria Worker", "Church Secretary",
                        "Home Health Aide", "Librarian"],
        "income_range": (20000, 50000),
        "six_axis": {"focus": (45, 65), "openness": (55, 75), "connection": (50, 70),
                     "expectancy": (20, 40), "compliance": (55, 75), "suggestibility": (60, 80)},
        "face": {"frequency_of_questions": (30, 50), "amount_of_resistance": (20, 40),
                 "complexity_of_objections": (15, 35), "emotional_volatility": (70, 90)},
        "health_pool": [
            ["anxiety medication", "blood pressure medication"],
            ["antidepressant", "blood pressure medication"],
        ],
        "pain_points": ["doesn't want kids to go through what they went through",
                        "learned the hard way", "funeral costs were devastating"],
        "budget_sensitivity": (70, 90),
        "skepticism_level": (20, 40),
        "baseline_trust": (45, 65),
        "will_test_frame": False,
        "talkativeness": (40, 65),
    },
    {
        "name": "The Young Invincible",
        "description": "Under 35, doesn't think they need it, hard to create urgency",
        "age_range": (22, 34),
        "occupations": ["Software Developer", "Marketing Coordinator", "Electrician",
                        "Restaurant Manager", "Freelancer"],
        "income_range": (35000, 90000),
        "six_axis": {"focus": (30, 50), "openness": (35, 55), "connection": (30, 50),
                     "expectancy": (10, 25), "compliance": (30, 50), "suggestibility": (25, 45)},
        "face": {"frequency_of_questions": (30, 50), "amount_of_resistance": (60, 80),
                 "complexity_of_objections": (40, 60), "emotional_volatility": (20, 40)},
        "health_pool": [[], [], ["adderall"]],
        "pain_points": ["student loans co-signed by parents", "new mortgage", "just got married"],
        "budget_sensitivity": (50, 70),
        "skepticism_level": (55, 75),
        "baseline_trust": (30, 50),
        "will_test_frame": True,
        "talkativeness": (45, 65),
    },
    {
        "name": "The Informed Shopper",
        "description": "Has quotes from other companies, comparing, wants best deal",
        "age_range": (35, 65),
        "occupations": ["Accountant", "Project Manager", "Real Estate Agent",
                        "Pharmacist", "Insurance Claims Adjuster"],
        "income_range": (50000, 120000),
        "six_axis": {"focus": (55, 75), "openness": (30, 50), "connection": (25, 45),
                     "expectancy": (20, 40), "compliance": (35, 55), "suggestibility": (25, 45)},
        "face": {"frequency_of_questions": (65, 85), "amount_of_resistance": (45, 65),
                 "complexity_of_objections": (60, 80), "emotional_volatility": (15, 35)},
        "health_pool": [[], ["blood pressure medication"], ["thyroid medication"]],
        "pain_points": ["getting the best rate", "understanding policy differences",
                        "comparing carriers"],
        "budget_sensitivity": (40, 60),
        "skepticism_level": (50, 70),
        "baseline_trust": (30, 50),
        "will_test_frame": True,
        "talkativeness": (40, 60),
    },
]

# ── Name pools ──────────────────────────────────────────────────────

MALE_NAMES = [
    "James", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony",
    "Mark", "Donald", "Steven", "Paul", "Andrew", "Kenneth", "George",
    "Edward", "Brian", "Ronald", "Timothy", "Jason", "Jeffrey", "Frank",
    "Gary", "Raymond", "Gerald", "Carl", "Roger", "Wayne", "Keith", "Larry",
]

FEMALE_NAMES = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret",
    "Sandra", "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle",
    "Carol", "Amanda", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
    "Cynthia", "Kathleen", "Amy", "Angela", "Shirley", "Brenda", "Teresa",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Anderson", "Taylor", "Thomas",
    "Jackson", "White", "Harris", "Martin", "Thompson", "Robinson", "Clark",
    "Lewis", "Lee", "Walker", "Hall", "Allen", "Young", "King", "Wright",
    "Scott", "Green", "Baker", "Adams", "Nelson", "Hill", "Campbell",
]

MARITAL_STATUSES = ["Single", "Married", "Divorced", "Widowed"]


# ── Script-to-Persona Matching ─────────────────────────────────────────
# Analyzes script content to determine the ideal client archetype.

# Product type detection keywords → archetype mapping
SCRIPT_PRODUCT_SIGNALS = [
    {
        "product": "final_expense",
        "keywords": ["final expense", "final expenses", "funeral", "burial",
                      "cremation", "end of life", "passing away", "funeral costs",
                      "burial costs", "leave behind", "not be a burden",
                      "fixed income", "ages 50", "ages 60", "whole life",
                      "guaranteed issue", "simplified issue", "no medical exam",
                      "graded benefit", "senior", "cover funeral"],
        "archetypes": ["The Retired Grandparent", "The Recently Widowed"],
        "fallback_archetype": "The Retired Grandparent",
    },
    {
        "product": "term_life",
        "keywords": ["term life", "term policy", "20 year", "30 year", "term insurance",
                      "mortgage protection", "income replacement", "breadwinner",
                      "family protection", "kids", "children", "young family",
                      "affordable coverage", "convertible term"],
        "archetypes": ["The Concerned Parent", "The Young Invincible", "The Reluctant Spouse"],
        "fallback_archetype": "The Concerned Parent",
    },
    {
        "product": "iul",
        "keywords": ["indexed universal", "iul", "cash value", "living benefits",
                      "accumulation", "retirement supplement", "tax free",
                      "tax-free", "market upside", "floor protection",
                      "s&p 500", "index", "wealth building"],
        "archetypes": ["The Skeptical Professional", "The Busy Executive", "The Informed Shopper"],
        "fallback_archetype": "The Skeptical Professional",
    },
    {
        "product": "whole_life",
        "keywords": ["whole life", "permanent coverage", "cash value", "legacy",
                      "estate planning", "wealth transfer", "dividends",
                      "guaranteed death benefit", "permanent insurance"],
        "archetypes": ["The Busy Executive", "The Skeptical Professional", "The Retired Grandparent"],
        "fallback_archetype": "The Skeptical Professional",
    },
    {
        "product": "mortgage_protection",
        "keywords": ["mortgage protection", "mortgage", "home loan", "house payment",
                      "pay off the house", "pay off the mortgage", "homeowner"],
        "archetypes": ["The Concerned Parent", "The Reluctant Spouse"],
        "fallback_archetype": "The Concerned Parent",
    },
    {
        "product": "general_life",
        "keywords": ["life insurance", "coverage", "policy", "rates", "carriers",
                      "underwriting", "field underwriter", "shop the rates",
                      "top carriers"],
        "archetypes": ["The Concerned Parent", "The Retired Grandparent",
                       "The Informed Shopper", "The Skeptical Professional"],
        "fallback_archetype": "The Concerned Parent",
    },
]

# Lead type detection → adjusts persona context
LEAD_TYPE_SIGNALS = {
    "aged": ["aged lead", "weeks ago", "months ago", "didn't get updated",
             "did you end up finding", "remember this", "what ended up happening"],
    "new": ["speed to lead", "just had a second", "request you put in",
            "just received", "new lead", "within 5 min", "exclusive lead"],
    "facebook": ["facebook", "fb lead", "facebook lead", "put in some info online",
                 "probably facebook", "saw something online"],
}


def analyze_script_for_persona(script_content: str, script_type_override: str = "") -> dict:
    """
    Analyze script content to determine the best client persona match.

    If script_type_override is provided (e.g. 'final_expense', 'iul'), it forces
    the product type instead of relying on keyword detection. This is set by the
    user when they tag their script with a type.

    Returns a dict with:
      - product_type: detected insurance product
      - archetype_name: best matching archetype name
      - lead_type: 'new', 'aged', 'facebook', or 'unknown'
      - confidence: how confident the match is (number of keyword hits)
    """
    lower = script_content.lower()

    # If user explicitly tagged the script type, use that directly
    if script_type_override:
        override = script_type_override.strip().lower()
        for signal in SCRIPT_PRODUCT_SIGNALS:
            if signal["product"] == override:
                # Detect lead type from content still
                lead_type = "unknown"
                for ltype, keywords in LEAD_TYPE_SIGNALS.items():
                    if any(kw in lower for kw in keywords):
                        lead_type = ltype
                        break
                return {
                    "product_type": signal["product"],
                    "archetype_name": signal["archetypes"][0] if signal["archetypes"] else signal["fallback_archetype"],
                    "archetype_pool": signal["archetypes"],
                    "lead_type": lead_type,
                    "confidence": 100,  # User-specified = maximum confidence
                }

    # Detect product type — score each product, prefer specific over generic
    best_product = None
    best_score = 0
    best_archetypes = []
    fallback = "The Concerned Parent"

    for signal in SCRIPT_PRODUCT_SIGNALS:
        score = sum(1 for kw in signal["keywords"] if kw in lower)
        # Penalize the generic catch-all so specific products win ties
        if signal["product"] == "general_life":
            score = max(0, score - 2)
        if score > best_score:
            best_score = score
            best_product = signal["product"]
            best_archetypes = signal["archetypes"]
            fallback = signal["fallback_archetype"]

    # Detect lead type
    lead_type = "unknown"
    for ltype, keywords in LEAD_TYPE_SIGNALS.items():
        if any(kw in lower for kw in keywords):
            lead_type = ltype
            break

    # Pick archetype — use mastery level to rotate through options
    archetype_name = fallback if not best_archetypes else best_archetypes[0]

    return {
        "product_type": best_product or "general_life",
        "archetype_name": archetype_name,
        "archetype_pool": best_archetypes or [archetype_name],
        "lead_type": lead_type,
        "confidence": best_score,
    }


class PersonaGenerator:
    """Generates randomized but coherent AI client personas."""

    def generate(self, archetype_name: Optional[str] = None, seed: Optional[int] = None) -> ClientPersona:
        """
        Generate a persona. If archetype_name is None, picks randomly.
        Seed for reproducibility in testing.
        """
        if seed is not None:
            random.seed(seed)

        if archetype_name:
            archetype = next(
                (a for a in ARCHETYPES if a["name"] == archetype_name), None
            )
            if not archetype:
                archetype = random.choice(ARCHETYPES)
        else:
            archetype = random.choice(ARCHETYPES)

        # Generate demographics
        gender = random.choice(["male", "female"])
        if gender == "male":
            first_name = random.choice(MALE_NAMES)
        else:
            first_name = random.choice(FEMALE_NAMES)
        last_name = random.choice(LAST_NAMES)

        age = random.randint(*archetype["age_range"])
        occupation = random.choice(archetype["occupations"])
        income = random.randint(*archetype["income_range"])

        # Marital status weighted by archetype
        if archetype["name"] == "The Recently Widowed":
            marital_status = "Widowed"
        elif archetype["name"] == "The Reluctant Spouse":
            marital_status = "Married"
        else:
            weights = [15, 50, 25, 10]  # Single, Married, Divorced, Widowed
            marital_status = random.choices(MARITAL_STATUSES, weights=weights, k=1)[0]

        # Dependents
        if marital_status == "Single" and age < 30:
            dependents = random.choices([0, 1], weights=[80, 20], k=1)[0]
        elif marital_status == "Married":
            dependents = random.choices([0, 1, 2, 3, 4], weights=[10, 25, 35, 20, 10], k=1)[0]
        else:
            dependents = random.choices([0, 1, 2, 3], weights=[20, 30, 30, 20], k=1)[0]

        # Health conditions and medications
        health_set = random.choice(archetype["health_pool"])
        medications = list(health_set)
        health_conditions = self._meds_to_conditions(medications)

        # Tobacco
        tobacco = random.random() < 0.15  # 15% tobacco use

        # Existing coverage
        existing = None
        if random.random() < 0.3:
            existing = random.choice([
                "Small group policy through work ($25k)",
                "Old whole life policy from 20 years ago ($10k)",
                "Term policy expiring next year ($100k)",
                "No coverage at all",
            ])

        # Reason for inquiry
        pain = random.choice(archetype["pain_points"])
        reason = self._build_reason(pain, age, marital_status, dependents)

        # Chase Hughes 6-Axis profile
        six_axis = SixAxisProfile(
            focus=random.uniform(*archetype["six_axis"]["focus"]),
            openness=random.uniform(*archetype["six_axis"]["openness"]),
            connection=random.uniform(*archetype["six_axis"]["connection"]),
            expectancy=random.uniform(*archetype["six_axis"]["expectancy"]),
            compliance=random.uniform(*archetype["six_axis"]["compliance"]),
            suggestibility=random.uniform(*archetype["six_axis"]["suggestibility"]),
        )

        # FACE profile
        face = FACEProfile(
            frequency_of_questions=random.uniform(*archetype["face"]["frequency_of_questions"]),
            amount_of_resistance=random.uniform(*archetype["face"]["amount_of_resistance"]),
            complexity_of_objections=random.uniform(*archetype["face"]["complexity_of_objections"]),
            emotional_volatility=random.uniform(*archetype["face"]["emotional_volatility"]),
        )

        # Spouse involvement
        spouse_involvement = "none"
        if marital_status == "Married":
            spouse_involvement = random.choice(["none", "aware", "on_the_line", "decision_maker"])

        # Build personality notes
        personality_notes = self._build_personality_notes(archetype, six_axis, age)

        return ClientPersona(
            gender=gender,
            name=f"{first_name} {last_name}",
            age=age,
            occupation=occupation,
            marital_status=marital_status,
            dependents=dependents,
            annual_income=income,
            existing_coverage=existing,
            health_conditions=health_conditions,
            medications=medications,
            tobacco_use=tobacco,
            reason_for_inquiry=reason,
            pain_points=archetype["pain_points"],
            personality_notes=personality_notes,
            six_axis=six_axis,
            face_profile=face,
            decision_maker=archetype["name"] != "The Reluctant Spouse",
            spouse_involvement=spouse_involvement,
            budget_sensitivity=random.uniform(*archetype["budget_sensitivity"]),
            skepticism_level=random.uniform(*archetype["skepticism_level"]),
            urgency=random.uniform(20, 80),
            baseline_trust=random.uniform(*archetype["baseline_trust"]),
            talkativeness=random.uniform(*archetype["talkativeness"]),
            will_test_frame_control=archetype["will_test_frame"],
            frame_test_frequency=random.uniform(0.1, 0.4) if archetype["will_test_frame"] else 0.05,
        )

    def generate_for_script(self, script_content: str, mastery_level: int = 0,
                            practice_count: int = 0) -> ClientPersona:
        """
        Generate a persona that matches the script's product type and target market.
        Uses mastery_level to rotate through progressively harder archetypes.
        """
        analysis = analyze_script_for_persona(script_content)
        pool = analysis["archetype_pool"]

        # At lower mastery (0-2), use the easiest/most natural archetype for the product
        # At higher mastery (3-5), rotate to harder archetypes from the pool
        if mastery_level <= 2:
            archetype_name = pool[0]
        else:
            # Rotate through the pool based on practice count for variety
            idx = practice_count % len(pool)
            archetype_name = pool[idx]

        persona = self.generate(archetype_name=archetype_name)

        # Override persona attributes based on mastery level for difficulty scaling
        if mastery_level <= 1:
            # Easy: warmer, more trusting, less resistant
            persona.baseline_trust = min(80, persona.baseline_trust + 20)
            persona.skepticism_level = max(10, persona.skepticism_level - 20)
            persona.face_profile.amount_of_resistance = max(10, persona.face_profile.amount_of_resistance - 15)
            persona.will_test_frame_control = False
        elif mastery_level >= 4:
            # Hard: more skeptical, tests frame, higher resistance
            persona.skepticism_level = min(95, persona.skepticism_level + 15)
            persona.baseline_trust = max(15, persona.baseline_trust - 10)
            persona.face_profile.amount_of_resistance = min(90, persona.face_profile.amount_of_resistance + 10)
            persona.will_test_frame_control = True

        return persona

    def get_archetype_names(self) -> list[str]:
        return [a["name"] for a in ARCHETYPES]

    def _meds_to_conditions(self, medications: list[str]) -> list[str]:
        med_to_condition = {
            "blood pressure medication": "High blood pressure",
            "lisinopril": "High blood pressure",
            "cholesterol medication": "High cholesterol",
            "atorvastatin": "High cholesterol",
            "diabetes medication": "Type 2 diabetes",
            "metformin": "Type 2 diabetes",
            "anxiety medication": "Anxiety",
            "antidepressant": "Depression",
            "aspirin": "Heart disease prevention",
            "thyroid medication": "Thyroid condition",
            "adderall": "ADHD",
            "birth control": "",
        }
        conditions = []
        for med in medications:
            condition = med_to_condition.get(med.lower(), "")
            if condition and condition not in conditions:
                conditions.append(condition)
        return conditions

    def _build_reason(self, pain: str, age: int, marital: str, deps: int) -> str:
        templates = [
            f"Concerned about {pain}",
            f"Wants coverage because of {pain}",
            f"Spouse asked them to look into coverage for {pain}",
            f"Saw an ad and realized they need to address {pain}",
            f"A friend recently passed and it made them think about {pain}",
        ]
        return random.choice(templates)

    def _build_personality_notes(self, archetype: dict, six_axis: SixAxisProfile, age: int) -> str:
        notes = [f"Archetype: {archetype['name']} - {archetype['description']}."]

        if six_axis.focus > 65:
            notes.append("Naturally focused, stays on topic, hard to distract.")
        elif six_axis.focus < 35:
            notes.append("Easily distracted. Agent will need to work to keep attention.")

        if six_axis.openness > 65:
            notes.append("Willing to share personal details and emotional context freely.")
        elif six_axis.openness < 35:
            notes.append("Guarded. Gives short answers, deflects personal questions.")

        if six_axis.connection > 65:
            notes.append("Quick to bond, mirrors language, responds to warmth and humor.")
        elif six_axis.connection < 35:
            notes.append("Emotionally distant. Hard to build rapport. Keeps things transactional.")

        if six_axis.compliance > 65:
            notes.append("Follows directions easily. Grabs the pen, confirms info without pushback.")
        elif six_axis.compliance < 35:
            notes.append("Resistant to directives. Questions why they need to do things.")

        if six_axis.suggestibility > 65:
            notes.append("Accepts reframes and presuppositions. Doesn't challenge assumptions.")
        elif six_axis.suggestibility < 35:
            notes.append("Analytical and skeptical. Challenges every assumption and reframe.")

        if six_axis.expectancy > 50:
            notes.append("Already somewhat optimistic about getting coverage. Uses forward-looking language.")
        elif six_axis.expectancy < 25:
            notes.append("Low expectancy. Doesn't see this going anywhere. Hard to create anticipation.")

        return " ".join(notes)
