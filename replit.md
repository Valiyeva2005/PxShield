# PixelShield

Advanced image encryption CLI tool combining AES-256 cryptography with multi-layer pixel manipulation — designed for security professionals, researchers, and privacy-conscious users.

## Run & Operate

```bash
# Activate the project environment
cd PixelShield

# Basic encrypt (prompts for password)
python3 pixelshield.py encrypt photo.png

# Decrypt
python3 pixelshield.py decrypt output/photo.psh

# Batch encrypt a folder
python3 pixelshield.py batch ./images/

# Hybrid RSA+AES (no password)
python3 pixelshield.py encrypt photo.png --algorithm hybrid

# Interactive wizard
python3 pixelshield.py interactive

# Profiles
python3 pixelshield.py profile list
python3 pixelshield.py encrypt photo.png --profile paranoid

# Benchmark
python3 pixelshield.py benchmark photo.png --runs 5

# Check for updates
python3 pixelshield.py update

# Run tests
python3 -m pytest tests/ -v

# Quick demo (generates a synthetic image + full encrypt/decrypt)
python3 scripts/demo.py

# Developer shortcuts via Makefile
make test
make lint
make security
make demo
```

## Stack

- Python 3.12
- Cryptography: `pycryptodome` (AES-256-GCM/CBC, RSA-2048), `argon2-cffi` (Argon2id KDF), `cryptography`
- Image processing: `Pillow`, `numpy`, `opencv-python-headless`
- Analysis: `matplotlib` (histograms), custom Shannon entropy
- CLI: `typer`, `rich`, `tqdm`
- Config: `pyyaml`, `loguru`
- Testing: `pytest`, `pytest-cov`
- DevSecOps: `ruff`, `bandit`, `pip-audit`, `detect-secrets`

## Where things live

| Path | Purpose |
|---|---|
| `pixelshield.py` | Main entry point |
| `cli/app.py` | Typer app + banner + plugin loader |
| `cli/commands.py` | All CLI commands |
| `cli/interactive.py` | Interactive wizard |
| `core/encrypt.py` | Encryption pipeline orchestrator |
| `core/decrypt.py` | Decryption pipeline orchestrator |
| `core/aes.py` | AES-256 GCM/CBC |
| `core/hybrid.py` | RSA-2048 + AES-256-GCM hybrid |
| `core/pixel_shuffle.py` | Seeded pixel permutation |
| `core/channel_rotation.py` | RGB channel permutation |
| `core/bit_rotation.py` | Circular bit rotation |
| `core/chaos.py` | Logistic map chaotic shuffler |
| `core/integrity.py` | SHA-256 hash + verify |
| `core/entropy.py` | Shannon entropy analysis |
| `core/histogram.py` | RGB histogram plots |
| `core/metadata.py` | EXIF metadata stripping |
| `security/key_manager.py` | Key material lifecycle |
| `security/password.py` | Argon2id key derivation |
| `security/validator.py` | Input validation |
| `utils/logger.py` | Loguru rotating logger |
| `utils/config.py` | YAML config manager |
| `utils/helpers.py` | Timer, secure wipe, resource snapshot |
| `utils/profiles.py` | Named encryption profiles |
| `utils/updater.py` | Auto-update checker |
| `utils/perf_report.py` | CPU/memory performance reports |
| `plugins/` | Drop-in plugin system |
| `tests/` | 112 unit + integration tests |
| `config.yaml` | Default configuration |
| `Makefile` | Developer shortcuts |
| `scripts/demo.py` | Programmatic API demo |

## Architecture decisions

- **OpenAPI-free**: PixelShield is a pure Python CLI tool, not a web service — no API layer needed.
- **Argon2id for KDF**: OWASP-recommended for password hashing; `time_cost=3, memory=64MB` tuned for ~0.5s derivation to resist brute-force.
- **GCM as default**: AES-256-GCM provides authenticated encryption — any ciphertext tampering is detected on decryption. CBC mode is provided for compatibility.
- **Container format (.psh)**: `[4B header_len][JSON header][ciphertext]`. The header stores the Argon2id salt, algorithm params, ops list, SHA-256 hash, and GCM AAD — everything needed to decrypt, nothing that reveals the key.
- **Pixel ops before AES**: They break spatial correlation and raise entropy of the pre-encryption data, adding defence-in-depth. They are keyed to the Argon2id-derived seed, so they're as strong as the password.
- **Hybrid mode uses RSA-OAEP-SHA256**: The session key (32 bytes, random) is wrapped with RSA-2048 OAEP. This follows the same envelope encryption pattern as GPG, AWS KMS, and PGP.

## User preferences

- Language: Azerbaijani/Turkish ("davam" = continue)
- Project: PixelShield Python CLI security tool
- Build everything completely and test before finishing

## Gotchas

- Run tests from inside `PixelShield/` directory: `cd PixelShield && python3 -m pytest tests/ -v`
- `hybrid` algorithm generates RSA keys on first run; subsequent decrypt needs `--rsa-key output/<name>_private.pem`
- RSA key generation (2048-bit) takes ~0.5s; benchmark skips hybrid mode by default
- Plugin system only activates when `plugins.enabled: true` in `config.yaml`
- `secure_wipe` (`--wipe`) on SSDs is best-effort (CoW filesystems don't guarantee overwrite)
