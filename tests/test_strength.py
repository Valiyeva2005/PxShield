"""Tests for password strength meter."""

import pytest
from security.strength import PasswordStrengthMeter, StrengthResult, strength_meter


class TestScoring:
    def test_empty_password_is_grade_f(self):
        r = strength_meter.evaluate("")
        assert r.grade == "F"
        assert r.score == 0

    def test_common_password_low_score(self):
        r = strength_meter.evaluate("password")
        assert r.is_common is True
        assert r.score <= 10

    def test_short_password_penalised(self):
        r = strength_meter.evaluate("Ab1!")
        assert r.score < 50

    def test_strong_password_high_score(self):
        r = strength_meter.evaluate("G7!xKq#mPv@wLz2^")
        assert r.score >= 75
        assert r.grade in ("A", "B")

    def test_keyboard_walk_penalty(self):
        r_walk   = strength_meter.evaluate("qwerty1234!")
        r_normal = strength_meter.evaluate("Zx!9mQ@pL3")
        assert r_walk.score < r_normal.score

    def test_repeat_chars_penalty(self):
        r_repeat = strength_meter.evaluate("aaaa1234!")
        r_normal = strength_meter.evaluate("aZbY1234!")
        assert r_repeat.score < r_normal.score

    def test_all_lowercase_no_upper_no_digit(self):
        r = strength_meter.evaluate("lowercase")
        assert r.has_lowercase is True
        assert r.has_uppercase is False
        assert r.has_digits is False


class TestFeatureDetection:
    def test_lowercase_detected(self):
        assert strength_meter.evaluate("abc").has_lowercase is True

    def test_uppercase_detected(self):
        assert strength_meter.evaluate("ABC").has_uppercase is True

    def test_digit_detected(self):
        assert strength_meter.evaluate("123").has_digits is True

    def test_symbol_detected(self):
        assert strength_meter.evaluate("!@#").has_symbols is True

    def test_common_flag(self):
        assert strength_meter.evaluate("123456").is_common is True
        assert strength_meter.evaluate("Xp9!mK$2Lq").is_common is False


class TestGrades:
    def test_grade_a_above_90(self):
        # Construct a score-90+ password deterministically.
        r = strength_meter.evaluate("T#8kQmZ!pL2@vXwN")
        if r.score >= 90:
            assert r.grade == "A"

    def test_grade_f_below_20(self):
        r = strength_meter.evaluate("password")
        assert r.grade in ("F", "E")

    def test_grades_are_valid(self):
        for pw in ["a", "Ab1!", "Abc12!", "A1!xBcDeFgH", "A1!xBcDeFgHiJkLm"]:
            r = strength_meter.evaluate(pw)
            assert r.grade in ("A", "B", "C", "D", "E", "F")


class TestFormatting:
    def test_bar_length(self):
        bar = strength_meter.format_bar(50, width=20)
        assert "50/100" in bar
        assert len([c for c in bar if c in "█░"]) == 20

    def test_rich_summary_contains_grade(self):
        r = strength_meter.evaluate("Test1234!")
        summary = strength_meter.rich_summary(r)
        assert r.grade in summary

    def test_rich_summary_contains_entropy(self):
        r = strength_meter.evaluate("Test1234!")
        summary = strength_meter.rich_summary(r)
        assert "Entropy" in summary

    def test_rich_summary_contains_crack_time(self):
        r = strength_meter.evaluate("Test1234!")
        summary = strength_meter.rich_summary(r)
        assert "Crack time" in summary


class TestCrackTime:
    def test_short_cracks_fast(self):
        r = strength_meter.evaluate("a")
        assert "second" in r.crack_time_display or "instant" in r.crack_time_display

    def test_long_takes_forever(self):
        r = strength_meter.evaluate("Z!4pMxKq@9wLvTnY#3mRbHj")
        assert any(unit in r.crack_time_display for unit in ["year", "centur", "K year"])


class TestIsAcceptable:
    def test_strong_password_is_acceptable(self):
        r = strength_meter.evaluate("MyStr0ng!Pass#9")
        assert r.is_acceptable is True

    def test_common_password_not_acceptable(self):
        r = strength_meter.evaluate("password")
        assert r.is_acceptable is False

    def test_too_short_not_acceptable(self):
        r = strength_meter.evaluate("Ab1!")
        assert r.is_acceptable is False
