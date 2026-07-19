"""Tests for security modules: password derivation, key manager, validator."""

import pytest

from security.password import PasswordManager
from security.key_manager import KeyManager, KeyMaterial
from security.validator import (
    ValidationError,
    validate_password,
    validate_algorithm,
    SUPPORTED_ALGORITHMS,
)


class TestPasswordManager:
    def test_derive_key_length(self):
        pm = PasswordManager(hash_len=32)
        salt = pm.generate_salt()
        key = pm.derive_key("secure_password_here!", salt)
        assert len(key) == 32

    def test_different_salts_different_keys(self):
        pm = PasswordManager()
        s1 = pm.generate_salt()
        s2 = pm.generate_salt()
        k1 = pm.derive_key("password", s1)
        k2 = pm.derive_key("password", s2)
        assert k1 != k2

    def test_same_params_same_key(self):
        pm = PasswordManager()
        salt = pm.generate_salt()
        k1 = pm.derive_key("password", salt)
        k2 = pm.derive_key("password", salt)
        assert k1 == k2

    def test_empty_password_raises(self):
        pm = PasswordManager()
        with pytest.raises(ValueError):
            pm.derive_key("", pm.generate_salt())

    def test_short_salt_raises(self):
        pm = PasswordManager()
        with pytest.raises(ValueError):
            pm.derive_key("password", b"short")

    def test_seed_is_integer(self):
        pm = PasswordManager()
        salt = pm.generate_salt()
        seed = pm.derive_seed("password", salt)
        assert isinstance(seed, int)
        assert seed >= 0


class TestKeyManager:
    def test_generate_and_derive_key(self):
        km = KeyManager()
        material = km.generate_key_material()
        key = km.derive_key("my_password_123!", material)
        assert len(key) == 32

    def test_save_and_load_metadata(self, tmp_path):
        km = KeyManager()
        material = km.generate_key_material(algorithm="aes-256-gcm")
        path = tmp_path / "metadata.json"
        km.save_metadata(material, path)
        loaded = km.load_metadata(path)
        assert loaded.salt == material.salt
        assert loaded.algorithm == material.algorithm

    def test_roundtrip_key_derivation(self):
        km = KeyManager()
        material = km.generate_key_material()
        k1 = km.derive_key("secret", material)
        k2 = km.derive_key("secret", material)
        assert k1 == k2


class TestValidator:
    def test_valid_password(self):
        validate_password("securepassword")  # Should not raise

    def test_short_password_raises(self):
        with pytest.raises(ValidationError):
            validate_password("short")

    def test_empty_password_raises(self):
        with pytest.raises(ValidationError):
            validate_password("")

    def test_valid_algorithms(self):
        for algo in SUPPORTED_ALGORITHMS:
            result = validate_algorithm(algo)
            assert result == algo.lower()

    def test_invalid_algorithm_raises(self):
        with pytest.raises(ValidationError):
            validate_algorithm("rsa-2048")

    def test_algorithm_case_insensitive(self):
        result = validate_algorithm("AES-256-GCM")
        assert result == "aes-256-gcm"
