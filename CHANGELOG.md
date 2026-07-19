# Changelog

All notable changes to PixelShield are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] – 2026-07-19

### Added

#### Core Cryptography
- **ChaCha20-Poly1305** cipher (`core/chacha.py`) – RFC 8439 stream cipher; faster than AES on
  devices without hardware AES acceleration; authenticated (AEAD), 12-byte nonce + 16-byte tag.
  Fully integrated into the encrypt/decrypt pipeline and CLI (`--algorithm chacha20`).

#### Steganography
- **LSB Steganography** (`core/stego.py`) – hides arbitrary bytes inside an RGB carrier image by
  modifying the least-significant bit of each colour channel.  Maximum pixel delta is ±1, making
  the modification visually indistinguishable.
- Carrier format: `[4B payload_len][embedded_bytes]` (big-endian).
- **Password mode** (CLI default): a fresh 16-byte Argon2id salt is generated at embed-time,
  prepended to the AES-256-GCM ciphertext, and stored inside the carrier image so that `reveal`
  can rederive the exact same key from the password — no external key file required.
- **Key mode** (programmatic): pass a 32-byte raw key; no salt is embedded (backwards-compatible
  with the existing test suite).
- `stego capacity` command reports width, height, and byte capacity for any carrier image.
- 10 unit tests: embed/extract roundtrip, capacity, encryption roundtrip, tamper detection,
  pixel-delta bounds, and the zero-length payload edge case.

#### Security
- **Password Strength Meter** (`security/strength.py`) – evaluates passwords and returns a
  structured `StrengthResult` with score 0-100, grade A–F, entropy bits, estimated crack time,
  and Rich-formatted terminal feedback.  Shown automatically during `encrypt` and `stego hide`.
- Scoring caps: passwords shorter than 6 characters score at most 35; shorter than 8 at most 45.
- Common-password, keyboard-walk, and repeated-character penalties.

#### CLI
- `stego hide`    – embed a text string or file payload inside a carrier image (AES-encrypted).
- `stego reveal`  – extract and decrypt a hidden payload from a stego image.
- `stego capacity`– report the maximum payload capacity of a carrier image.

### Fixed
- **Stego reveal key mismatch** – `reveal` previously generated a fresh Argon2id salt on every
  call, making it impossible to decrypt a payload that was hidden with `hide`.  Fixed by embedding
  the KDF salt inside the carrier image (password mode) so that `reveal` always rederives the
  correct key.
- **Empty-payload edge case** – `LSBSteganography.extract()` no longer raises `ValueError` when
  the embedded payload length is zero; it returns `b""` instead.
- **Short-password scoring** – passwords shorter than 6 characters are now capped at score ≤ 35
  (previously a 4-character password with all four character classes could score > 50).

### Testing
- 180 tests total (up from 126), all passing.
- New test files: `test_stego.py` (10), `test_histogram.py` (7), `test_metadata.py` (7),
  `test_profiles.py` (11), `test_perf_report.py` (5), `test_strength.py` (18),
  `test_updater.py` (8), `test_encrypt_chacha.py` (8), `test_hybrid.py` (9).

---

## [1.0.0] – 2026-07-18

### Added

#### Core Cryptography
- **AES-256-GCM** (authenticated encryption with associated data)
- **AES-256-CBC** (with PKCS7 padding and random IV)
- **Hybrid RSA-2048 + AES-256-GCM** – envelope encryption; RSA wraps the session key
- **Argon2id** key derivation (OWASP-recommended; time_cost=3, memory=64MB)
- **SHA-256 integrity verification** embedded in `.psh` container

#### Pixel Obfuscation Pipeline
- **Pixel Shuffle** – seeded NumPy permutation of pixel positions (reversible)
- **Channel Rotation** – random RGB channel permutation keyed to the derived seed
- **Bit Rotation** – circular left/right shift of 8-bit pixel values
- **Chaotic Map** – logistic map `x(n+1) = r·x·(1-x)` for pixel permutation
- **Noise Injection** – optional Gaussian noise before encryption
- **Lossless Compression** – optional zlib before AES encryption

#### Security
- EXIF metadata stripping (GPS, camera, author, date – everything)
- Input validation: file type, password strength, algorithm, directory checks
- Secure file wiping (multi-pass random overwrite + delete)
- No raw passwords ever stored or logged

#### CLI (Typer + Rich)
- `encrypt` – full single-image encryption with all options
- `decrypt` – full decryption with integrity verification
- `batch`   – batch-encrypt all images in a directory
- `benchmark` – wall-time + CPU + memory benchmark over N runs
- `interactive` – guided TUI wizard (no flags needed)
- `profile`  – `list | save | delete` named configuration profiles
- `update`   – auto-update checker against PyPI

#### Analysis & Reporting
- **Shannon entropy** analysis (before vs. after encryption)
- **RGB histogram** comparison plots (original | encrypted | difference)
- **Performance reports** (wall time, CPU time, RSS memory, throughput MB/s)

#### Configuration Profiles (5 built-ins)
- `fast` – AES-256-GCM only, no pixel ops
- `balanced` – AES-256-GCM + pixel shuffle + channel rotation
- `paranoid` – all pixel ops + chaos + noise + compression + histogram
- `hybrid` – RSA+AES envelope encryption
- `analysis` – balanced + entropy + histogram (full analysis mode)

#### DevSecOps
- GitHub Actions workflow: ruff · bandit · pip-audit · detect-secrets · pytest · Docker build
- Multi-stage non-root `Dockerfile`
- `docker-compose.yml` with volume mounts and security hardening
- `Makefile` with `install`, `test`, `lint`, `security`, `all-checks`, `demo`, `docker-build`
- `pyproject.toml` with ruff and bandit configuration

#### Testing
- 126 unit and integration tests across all modules
- Full encrypt → decrypt roundtrip tests (GCM, CBC, hybrid, chaos, bit-rotation, compression)
- Tamper-detection tests (wrong password, flipped bytes, wrong AAD)
- Profile, performance-report, updater, histogram, and metadata tests

#### Documentation
- Professional `README.md` with architecture diagram, CLI reference, security model
- `CHANGELOG.md` (this file)
- `scripts/demo.py` – programmatic API demonstration
- Inline docstrings on every public class and method

---

## [Unreleased]

### Planned
- RSA/ECC key-file authentication (alternative to password)
- GPU-accelerated pixel operations (NumPy/CuPy)
- Web dashboard (FastAPI + React)
- FIPS 140-2 compliance mode
- Interactive TUI with Textual
- Streaming encryption for very large images
