"""
Configuration for InsuranceGrokBot.
Load from environment variables or .env file.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # LLM Settings
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "claude-sonnet-4-20250514"))
    llm_max_tokens: int = 500

    # Server Settings
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")

    # Score Defaults
    initial_trust: float = 50.0
    initial_authority: float = 50.0
    initial_resistance: float = 50.0

    # Thresholds
    low_trust_threshold: float = 35.0
    low_authority_threshold: float = 40.0
    high_resistance_threshold: float = 70.0
    engagement_hangup_threshold: float = 15.0

    # Objection Config
    objection_isolation_trust_threshold: float = 55.0
    objection_acceptance_trust_threshold: float = 55.0
    objection_acceptance_authority_threshold: float = 50.0

    # Compliance Config
    compliance_penalty_phase: int = 2  # Phase index where penalty kicks in
    compliance_penalty_amount: float = 20.0

    def validate(self) -> list[str]:
        """Return list of configuration warnings."""
        warnings = []
        if not self.anthropic_api_key and not self.openai_api_key:
            warnings.append("No LLM API key configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY.")
        return warnings


# Singleton
config = Config()
