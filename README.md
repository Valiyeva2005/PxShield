# 🛡️ PixelShield

![Security Pipeline](https://img.shields.io/github/actions/workflow/status/yourusername/pixelshield/security.yml?label=security%20pipeline&style=flat-square)
![Tests](https://img.shields.io/github/actions/workflow/status/yourusername/pixelshield/security.yml?label=tests&style=flat-square)
![Coverage](https://img.shields.io/codecov/c/github/yourusername/pixelshield?style=flat-square)
![Python](https://img.shields.io/badge/python-3.12%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Bandit](https://img.shields.io/badge/security-bandit-yellow?style=flat-square)
![Ruff](https://img.shields.io/badge/code%20style-ruff-orange?style=flat-square)

> **Advanced image encryption CLI tool** combining AES-256 cryptography with multi-layer pixel manipulation — designed for security professionals, researchers, and privacy-conscious users.

---

## Overview

PixelShield is a production-quality Linux CLI application that protects images through a layered encryption pipeline:

1. **Metadata removal** — strips all EXIF data (GPS, camera, author, dates)
2. **Pixel-space obfuscation** — shuffles pixels, rotates channels, rotates bits
3. **Chaos scrambling** — logistic map-based pseudo-random permutation
4. **AES-256 encryption** — GCM (authenticated) or CBC mode
5. **Integrity verification** — SHA-256 hash before and after encryption
6. **Entropy & histogram analysis** — cryptographic quality metrics

The result is a `.psh` container that bundles the ciphertext, key derivation parameters (but never the key or password), and metadata needed for decryption.

---

## Features

| Feature | Description |
|---|---|
| 🔐 AES-256 GCM / CBC | Authenticated encryption with random IV/nonce |
| 🔑 Argon2id KDF | OWASP-recommended password-based key derivation |
| 🔀 Pixel Shuffle | Deterministic, reversible pixel permutation |
| 🌈 Channel Rotation | Random RGB channel order permutation |
| ⚙️ Bit Rotation | Circular bit-shift of pixel values |
| 🌀 Chaotic Map | Logistic map pseudo-random permutation |
| 🗑️ Metadata Removal | Strips all EXIF / GPS / camera data |
| ✅ Integrity Check | SHA-256 hash verification |
| 📊 Entropy Analysis | Shannon entropy before/after comparison |
| 📈 Histogram Analysis | RGB histogram comparison plots |
| 💉 Noise Injection | Optional Gaussian noise injection |
| 🗜️ Compression | Optional lossless pre-encryption compression |
| 📁 Batch Processing | Encrypt entire directories |
| ⚡ Progress Bars | Rich-powered real-time progress display |
| 📝 Detailed Logging | Rotating log files with Loguru |
| 🐳 Docker Support | Multi-stage, non-root Docker image |
| 🔒 DevSecOps CI | ruff · bandit · pip-audit · detect-secrets · pytest |

---

## Architecture

```
PixelShield/
├── cli/                    # Typer CLI — commands & app bootstrap
│   ├── app.py              # Entry point, banner, app registration
│   └── commands.py         # encrypt / decrypt / batch / benchmark
│
├── core/                   # Cryptographic & image processing pipeline
│   ├── encrypt.py          # Full encryption orchestrator
│   ├── decrypt.py          # Full decryption orchestrator
│   ├── aes.py              # AES-256 GCM / CBC implementation
│   ├── pixel_shuffle.py    # Seeded pixel permutation
│   ├── channel_rotation.py # RGB channel permutation
│   ├── bit_rotation.py     # Circular bit rotation
│   ├── chaos.py            # Logistic map chaotic shuffler
│   ├── integrity.py        # SHA-256 hash generation & verification
│   ├── entropy.py          # Shannon entropy analysis
│   ├── histogram.py        # RGB histogram plotting
│   └── metadata.py         # EXIF metadata removal
│
├── security/               # Key & password management
│   ├── key_manager.py      # Key material lifecycle
│   ├── password.py         # Argon2id key derivation
│   └── validator.py        # Input validation & sanitisation
│
├── utils/                  # Shared utilities
│   ├── logger.py           # Loguru-based logging
│   ├── config.py           # YAML configuration manager
│   └── helpers.py          # Timer, file I/O, secure wipe, resources
│
├── plugins/                # Drop-in plugin system
├── tests/                  # pytest test suite
├── output/                 # Default encrypted output directory
├── logs/                   # Rotating log files
│
├── config.yaml             # Default configuration
├── pixelshield.py          # CLI entry point
├── setup.py                # Package install script
├── requirements.txt        # Python dependencies
├── Dockerfile              # Multi-stage production image
├── docker-compose.yml      # Compose configuration
└── .github/workflows/
    └── security.yml        # CI/CD security pipeline
```

### Encryption Pipeline

```
Input Image
    │
    ▼
[1] Strip EXIF Metadata
    │
    ▼
[2] Pixel Shuffle  ──── seed(Argon2id(password, salt))
    │
    ▼
[3] Chaos Shuffle  ──── Logistic Map x(n+1) = r·x·(1-x)
    │
    ▼
[4] Channel Rotation ── permute(R, G, B) → e.g. GBR
    │
    ▼
[5] Bit Rotation ─────── circular_left(pixel, n_bits)
    │
    ▼
[6] (Optional) Noise + Compression
    │
    ▼
[7] AES-256-GCM / CBC Encryption
    │
    ▼
[8] .psh Container  ──── [header][IV/nonce][tag][ciphertext]
    │
    ▼
Output: encrypted.psh  +  metadata.json  +  hash.sha256
        entropy.txt     +  histogram.png
```

---

## Installation

### Prerequisites

- Python 3.12+
- pip

### From source

```bash
git clone https://github.com/yourusername/pixelshield.git
cd pixelshield
pip install -r requirements.txt
python pixelshield.py --help
```

### Install as CLI tool

```bash
pip install -e .
pixelshield --help
```

### Docker

```bash
docker build -t pixelshield .

# Encrypt
docker run --rm -it \
  -v $(pwd)/images:/app/images:ro \
  -v $(pwd)/output:/app/output \
  pixelshield encrypt images/photo.png --entropy --histogram

# Decrypt
docker run --rm -it \
  -v $(pwd)/output:/app/output \
  pixelshield decrypt output/photo.psh
```

---

## Usage

### Encrypt an image

```bash
# Basic (prompts for password)
python pixelshield.py encrypt photo.png

# All options
python pixelshield.py encrypt photo.png \
  --password "my_secure_password" \
  --algorithm aes-256-gcm \
  --shuffle \
  --chaos \
  --noise \
  --entropy \
  --histogram \
  --remove-metadata \
  --verify \
  --output output/photo_encrypted.psh \
  --verbose
```

### Decrypt an image

```bash
python pixelshield.py decrypt output/photo.psh \
  --password "my_secure_password" \
  --verify \
  --output output/photo_restored.png
```

### Batch encrypt a directory

```bash
python pixelshield.py batch ./images/ \
  --password "my_secure_password" \
  --shuffle \
  --entropy \
  --out-dir ./encrypted/
```

### Benchmark

```bash
python pixelshield.py benchmark photo.png --runs 5
```

---

## CLI Reference

### `encrypt`

| Option | Default | Description |
|---|---|---|
| `IMAGE` | required | Path to source image |
| `--password` / `-p` | (prompt) | Encryption password |
| `--algorithm` / `-a` | `aes-256-gcm` | `aes-256-gcm` \| `aes-256-cbc` \| `hybrid` |
| `--shuffle` / `--no-shuffle` | `True` | Apply pixel shuffle |
| `--chaos` | `False` | Apply logistic map chaos shuffle |
| `--bit-rotation` | `False` | Apply circular bit rotation |
| `--noise` | `False` | Inject Gaussian noise |
| `--entropy` / `--no-entropy` | `True` | Compute entropy analysis |
| `--histogram` | `False` | Generate histogram plot |
| `--remove-metadata` | `True` | Strip EXIF metadata |
| `--verify` | `True` | Compute SHA-256 integrity hash |
| `--compress` | `False` | Apply lossless compression first |
| `--wipe` | `False` | Securely wipe source after encryption |
| `--output` / `-o` | auto | Output `.psh` file path |
| `--out-dir` | `output/` | Output directory |
| `--verbose` / `-v` | `False` | Verbose logging |

### `decrypt`

| Option | Default | Description |
|---|---|---|
| `ENCRYPTED_FILE` | required | Path to `.psh` file |
| `--password` / `-p` | (prompt) | Decryption password |
| `--verify` / `--no-verify` | `True` | Verify integrity after decryption |
| `--output` / `-o` | auto | Output image path |
| `--out-dir` | `output/` | Output directory |

### `batch`

| Option | Default | Description |
|---|---|---|
| `DIRECTORY` | required | Directory containing images |
| `--password` / `-p` | (prompt) | Encryption password |
| `--out-dir` | `output/` | Output directory |
| (all encrypt options) | — | Same as `encrypt` |

---

## Output Files

| File | Description |
|---|---|
| `image.psh` | Encrypted container (header + ciphertext) |
| `image.metadata.json` | Key parameters, algorithm, operations applied |
| `image.sha256` | SHA-256 integrity hash of the original |
| `image.entropy.txt` | Entropy comparison report |
| `image.histogram.png` | RGB histogram plots (if `--histogram`) |
| `logs/encrypt.log` | Detailed encryption log |
| `logs/decrypt.log` | Detailed decryption log |

---

## Security Model

### Key Derivation

- **Algorithm:** Argon2id (winner of Password Hashing Competition)
- **Parameters:** time_cost=3, memory_cost=64MB, parallelism=4, key_len=32 bytes
- **Password never stored** — only the random salt is persisted
- **Unique salt per encryption** — prevents rainbow table attacks

### Encryption

- **AES-256-GCM** (recommended): Authenticated encryption with Associated Data (AEAD). Detects any tampering of the ciphertext or header.
- **AES-256-CBC**: Classic mode with PKCS7 padding and random IV. Integrity verified via SHA-256.
- **Random IV/nonce** generated for every encryption operation.

### Pixel Obfuscation

The layered pixel-space operations are designed to:
1. Break spatial correlation before AES encryption
2. Make frequency analysis attacks harder
3. Increase statistical randomness of the pre-encryption data

These are applied before AES encryption — they add defence-in-depth, not primary security.

### Container Format (.psh)

```
┌──────────────────────────────────────────────────────────┐
│  4 bytes: header length (big-endian uint32)              │
├──────────────────────────────────────────────────────────┤
│  N bytes: JSON header                                    │
│    - version                                             │
│    - image shape (H, W, C)                               │
│    - key material (salt, algorithm, Argon2 params)       │
│    - operations applied                                  │
│    - AES mode                                            │
│    - SHA-256 hash of original image                      │
├──────────────────────────────────────────────────────────┤
│  Remainder: AES ciphertext                               │
│    GCM: [nonce (16B)] [tag (16B)] [ciphertext]           │
│    CBC: [IV (16B)] [ciphertext]                          │
└──────────────────────────────────────────────────────────┘
```

---

## Algorithms

### Logistic Map (Chaos)

```
x(n+1) = r * x(n) * (1 - x(n))
```

With `r ∈ (3.57, 4.0]` the system is fully chaotic — tiny changes in initial conditions produce completely different sequences. PixelShield seeds x₀ from the Argon2id-derived key, making the chaotic sequence cryptographically anchored to the password.

### Argon2id

The hybrid of Argon2i (side-channel resistance) and Argon2d (GPU resistance). Configured for ~0.5s derivation time per attempt, making brute-force attacks computationally expensive.

### Shannon Entropy

```
H(X) = -Σ p(x) * log₂(p(x))
```

Maximum is 8.0 bits/byte for uniformly distributed data. Good encryption should push entropy close to this maximum, indicating that no statistical patterns remain.

---

## Screenshots

_Screenshots will be added once the first public release is available._

---

## DevSecOps Pipeline

The GitHub Actions workflow (`.github/workflows/security.yml`) runs on every push and pull request:

| Step | Tool | Purpose |
|---|---|---|
| Lint | `ruff` | PEP8 + security linting rules |
| SAST | `bandit` | Static security analysis |
| Dependency audit | `pip-audit` | Known CVE scanning |
| Secret detection | `detect-secrets` | Prevent credential leaks |
| Tests | `pytest` | Unit + integration tests with coverage |
| Docker build | Docker | Verify image builds successfully |

---

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run full test suite
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_aes.py -v

# Run with coverage report
pytest --cov=. --cov-report=html
```

---

## Future Improvements

- [ ] ChaCha20-Poly1305 support
- [ ] RSA/ECC hybrid encryption for key exchange
- [ ] Steganography mode (hide encrypted data inside a carrier image)
- [ ] GPU-accelerated pixel operations
- [ ] Web UI wrapper
- [ ] Key file support (in addition to passwords)
- [ ] Encrypted output streaming for very large images
- [ ] FIPS 140-2 compliance mode
- [ ] Auto-update checker
- [ ] Interactive TUI mode (Textual)

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Run tests and linting (`pytest && ruff check .`)
4. Submit a pull request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

> **Disclaimer:** PixelShield is provided for educational and research purposes. The authors are not responsible for misuse. Always ensure you have the legal right to encrypt the images you process.
