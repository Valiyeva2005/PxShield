"""
PixelShield – Password Strength Meter
Estimates password strength using entropy, pattern analysis, and common
password checks. Returns a score (0–100), grade (A–F), and Rich-formatted
feedback suitable for CLI display.

Scoring model (max 100 pts):
  - Length score     (0-30)
  - Character set    (0-25): lowercase, uppercase, digits, symbols
  - Entropy bits     (0-25): Shannon entropy × weight
  - Pattern penalty  (-30): keyboard walks, repeats, dictionary words
  - Bonus            (+10): mixed character classes bonus
"""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# Common passwords to instant-fail.
_COMMON_PASSWORDS = {
    "password", "123456", "password1", "qwerty", "abc123", "letmein",
    "monkey", "dragon", "master", "123456789", "welcome", "login",
    "admin", "admin123", "iloveyou", "sunshine", "princess", "football",
    "passw0rd", "password123", "pixelshield", "secret", "test",
}

_KEYBOARD_WALKS = [
    "qwerty", "qwertyuiop", "asdfgh", "asdfghjkl", "zxcvbn", "zxcvbnm",
    "1234567890", "0987654321",
]


@dataclass
class StrengthResult:
    """Password strength evaluation result."""

    password_length: int
    score: int              # 0-100
    grade: str              # A F E D C B A
    entropy_bits: float
    crack_time_display: str
    suggestions: list[str] = field(default_factory=list)
    is_common: bool = False
    has_lowercase: bool = False
    has_uppercase: bool = False
    has_digits: bool = False
    has_symbols: bool = False

    @property
    def is_acceptable(self) -> bool:
        """True when the password meets minimum PixelShield requirements."""
        return self.score >= 40 and not self.is_common and self.password_length >= 8


class PasswordStrengthMeter:
    """Evaluate password strength and produce actionable feedback.

    Usage::

        meter = PasswordStrengthMeter()
        result = meter.evaluate("MyS3cur3P@ss!")
        print(result.grade, result.score, result.crack_time_display)
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, password: str) -> StrengthResult:
        """Evaluate *password* and return a :class:`StrengthResult`.

        Args:
            password: Password string to evaluate.

        Returns:
            :class:`StrengthResult` with score, grade, entropy, and tips.
        """
        length = len(password)

        # ── Feature extraction ──────────────────────────────────────
        has_lower  = bool(re.search(r"[a-z]", password))
        has_upper  = bool(re.search(r"[A-Z]", password))
        has_digit  = bool(re.search(r"\d",    password))
        has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))
        is_common  = password.lower().strip() in _COMMON_PASSWORDS

        charset_size = self._charset_size(has_lower, has_upper, has_digit, has_symbol)
        entropy = length * math.log2(charset_size) if charset_size > 1 else 0.0

        # ── Scoring ─────────────────────────────────────────────────
        score = 0

        # Length (max 30).
        length_score = min(30, int(length * 2.5))
        score += length_score

        # Character set diversity (max 25).
        classes = sum([has_lower, has_upper, has_digit, has_symbol])
        charset_score = classes * 6   # 6 pts each → max 24 + 1 bonus
        score += min(25, charset_score)

        # Entropy (max 25).
        entropy_score = min(25, int(entropy / 3))
        score += entropy_score

        # Mixed-class bonus (max 10).
        if classes >= 3:
            score += 5
        if classes == 4:
            score += 5

        # ── Penalties ───────────────────────────────────────────────
        # Very short passwords are capped regardless of character variety.
        if length < 6:
            score = min(score, 35)
        elif length < 8:
            score = min(score, 45)

        if is_common:
            score = min(score, 5)

        if self._has_repeat_chars(password):
            score = max(0, score - 10)

        if self._has_keyboard_walk(password):
            score = max(0, score - 15)

        if self._has_sequential(password):
            score = max(0, score - 10)

        score = max(0, min(100, score))

        # ── Grade ───────────────────────────────────────────────────
        grade = self._score_to_grade(score)

        # ── Crack-time estimate ─────────────────────────────────────
        crack_time = self._crack_time_display(entropy)

        # ── Suggestions ─────────────────────────────────────────────
        suggestions: list[str] = []
        if is_common:
            suggestions.append("This is one of the most commonly used passwords – choose something unique.")
        if length < 12:
            suggestions.append(f"Increase length (currently {length}; aim for 12+).")
        if not has_lower:
            suggestions.append("Add lowercase letters (a-z).")
        if not has_upper:
            suggestions.append("Add uppercase letters (A-Z).")
        if not has_digit:
            suggestions.append("Add digits (0-9).")
        if not has_symbol:
            suggestions.append("Add symbols (!@#$%^&* etc.).")
        if self._has_keyboard_walk(password):
            suggestions.append("Avoid keyboard walks (e.g. 'qwerty', '1234').")
        if self._has_repeat_chars(password):
            suggestions.append("Avoid repeated characters (e.g. 'aaa', '111').")
        if not suggestions and score >= 80:
            suggestions.append("Excellent password – just don't reuse it elsewhere.")

        return StrengthResult(
            password_length=length,
            score=score,
            grade=grade,
            entropy_bits=round(entropy, 2),
            crack_time_display=crack_time,
            suggestions=suggestions,
            is_common=is_common,
            has_lowercase=has_lower,
            has_uppercase=has_upper,
            has_digits=has_digit,
            has_symbols=has_symbol,
        )

    def format_bar(self, score: int, width: int = 20) -> str:
        """Return an ASCII progress bar representing *score* (0-100).

        Args:
            score: Score between 0 and 100.
            width: Bar width in characters.

        Returns:
            Formatted bar string e.g. ``[████████░░░░░░░░░░░░]  45/100``.
        """
        filled = int((score / 100) * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]  {score}/100"

    def rich_summary(self, result: StrengthResult) -> str:
        """Build a Rich-markup string summarising *result* for terminal display.

        Args:
            result: Evaluated :class:`StrengthResult`.

        Returns:
            Rich-markup string suitable for ``console.print()``.
        """
        colour = {
            "F": "bold red", "E": "red",
            "D": "yellow",   "C": "yellow",
            "B": "green",    "A": "bold green",
        }.get(result.grade, "white")

        bar = self.format_bar(result.score)
        lines = [
            f"  Password strength: [{colour}]{result.grade}  {bar}[/{colour}]",
            f"  Entropy   : {result.entropy_bits:.1f} bits",
            f"  Crack time: {result.crack_time_display}",
        ]
        chars_detail = "  Characters:"
        if result.has_lowercase: chars_detail += " [green]a-z ✓[/green]"
        else:                    chars_detail += " [dim]a-z ✗[/dim]"
        if result.has_uppercase: chars_detail += " [green]A-Z ✓[/green]"
        else:                    chars_detail += " [dim]A-Z ✗[/dim]"
        if result.has_digits:    chars_detail += " [green]0-9 ✓[/green]"
        else:                    chars_detail += " [dim]0-9 ✗[/dim]"
        if result.has_symbols:   chars_detail += " [green]!@# ✓[/green]"
        else:                    chars_detail += " [dim]!@# ✗[/dim]"
        lines.append(chars_detail)

        if result.suggestions:
            lines.append("  Suggestions:")
            for tip in result.suggestions:
                lines.append(f"    [dim]• {tip}[/dim]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _charset_size(lower: bool, upper: bool, digit: bool, symbol: bool) -> int:
        size = 0
        if lower:  size += 26
        if upper:  size += 26
        if digit:  size += 10
        if symbol: size += 32
        return max(size, 1)

    @staticmethod
    def _has_repeat_chars(password: str) -> bool:
        return bool(re.search(r"(.)\1{2,}", password))

    @staticmethod
    def _has_keyboard_walk(password: str) -> bool:
        lp = password.lower()
        return any(walk in lp for walk in _KEYBOARD_WALKS)

    @staticmethod
    def _has_sequential(password: str) -> bool:
        for i in range(len(password) - 2):
            a, b, c = ord(password[i]), ord(password[i+1]), ord(password[i+2])
            if b - a == 1 and c - b == 1:
                return True
            if a - b == 1 and b - c == 1:
                return True
        return False

    @staticmethod
    def _score_to_grade(score: int) -> str:
        if score >= 90: return "A"
        if score >= 75: return "B"
        if score >= 55: return "C"
        if score >= 40: return "D"
        if score >= 20: return "E"
        return "F"

    @staticmethod
    def _crack_time_display(entropy_bits: float) -> str:
        """Estimate online crack time assuming 10 billion guesses/second (GPU cluster)."""
        if entropy_bits <= 0:
            return "instantly"
        guesses_per_second = 10_000_000_000   # 10 billion/s (Hashcat benchmark)
        seconds = (2 ** entropy_bits) / guesses_per_second
        if seconds < 1:       return "less than 1 second"
        if seconds < 60:      return f"{int(seconds)} seconds"
        if seconds < 3600:    return f"{int(seconds/60)} minutes"
        if seconds < 86400:   return f"{int(seconds/3600)} hours"
        if seconds < 2592000: return f"{int(seconds/86400)} days"
        if seconds < 3.15e7:  return f"{int(seconds/2592000)} months"
        if seconds < 3.15e10: return f"{int(seconds/3.15e7)} years"
        if seconds < 3.15e13: return f"{int(seconds/3.15e10)}K years"
        return "centuries (effectively uncrackable)"


# Module-level singleton.
strength_meter = PasswordStrengthMeter()
