"""Tests for AIConfig feature coverage."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import AIConfig


class TestAIConfigDefaults:
    """Test AIConfig default values."""

    def test_default_model_name(self) -> None:
        """Default model should be gemini-3-flash-preview."""
        cfg = AIConfig()
        assert cfg.model_name == "gemini-3-flash-preview"

    def test_default_temperature(self) -> None:
        """Default temperature should be 0.85."""
        cfg = AIConfig()
        assert cfg.temperature == 0.85

    def test_default_max_output_tokens(self) -> None:
        """Default max_output_tokens should be 300."""
        cfg = AIConfig()
        assert cfg.max_output_tokens == 300

    def test_default_personality_prefix_empty(self) -> None:
        """Default personality_prefix should be empty string."""
        cfg = AIConfig()
        assert cfg.personality_prefix == ""

    def test_default_persona_preset(self) -> None:
        """Default persona_preset should be insightful_expert."""
        cfg = AIConfig()
        assert cfg.persona_preset == "insightful_expert"


class TestAIConfigValidation:
    """Test AIConfig validation rules."""

    def test_temperature_min_valid(self) -> None:
        """Temperature of 0.0 should be valid."""
        cfg = AIConfig(temperature=0.0)
        assert cfg.temperature == 0.0

    def test_temperature_max_valid(self) -> None:
        """Temperature of 2.0 should be valid."""
        cfg = AIConfig(temperature=2.0)
        assert cfg.temperature == 2.0

    def test_temperature_below_min_invalid(self) -> None:
        """Temperature below 0.0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIConfig(temperature=-0.1)

    def test_temperature_above_max_invalid(self) -> None:
        """Temperature above 2.0 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIConfig(temperature=2.1)

    def test_max_tokens_min_valid(self) -> None:
        """max_output_tokens of 50 should be valid."""
        cfg = AIConfig(max_output_tokens=50)
        assert cfg.max_output_tokens == 50

    def test_max_tokens_max_valid(self) -> None:
        """max_output_tokens of 1000 should be valid."""
        cfg = AIConfig(max_output_tokens=1000)
        assert cfg.max_output_tokens == 1000

    def test_max_tokens_below_min_invalid(self) -> None:
        """max_output_tokens below 50 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIConfig(max_output_tokens=49)

    def test_max_tokens_above_max_invalid(self) -> None:
        """max_output_tokens above 1000 should raise ValidationError."""
        with pytest.raises(ValidationError):
            AIConfig(max_output_tokens=1001)


class TestAIConfigCustomValues:
    """Test AIConfig accepts custom values."""

    def test_custom_model_name(self) -> None:
        """Should accept custom model name."""
        cfg = AIConfig(model_name="gemini-pro")
        assert cfg.model_name == "gemini-pro"

    def test_custom_personality_prefix(self) -> None:
        """Should accept custom personality_prefix."""
        cfg = AIConfig(personality_prefix="Be concise and witty.")
        assert cfg.personality_prefix == "Be concise and witty."

    def test_custom_persona_preset(self) -> None:
        """Should accept custom persona_preset."""
        cfg = AIConfig(persona_preset="supportive_cheerleader")
        assert cfg.persona_preset == "supportive_cheerleader"


class TestAIConfigImmutable:
    """Test AIConfig is immutable (frozen)."""

    def test_config_is_frozen(self) -> None:
        """AIConfig should be frozen (immutable)."""
        cfg = AIConfig()
        with pytest.raises((ValidationError, TypeError)):
            cfg.temperature = 0.5  # type: ignore[misc]
