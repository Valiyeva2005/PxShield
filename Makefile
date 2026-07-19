# ================================================================
# PixelShield – Developer Makefile
# ================================================================
# Targets:
#   make install      Install all dependencies
#   make test         Run the full test suite
#   make test-cov     Run tests with HTML coverage report
#   make lint         Run ruff linter
#   make security     Run bandit + pip-audit + detect-secrets
#   make all-checks   lint + security + test (full CI pipeline)
#   make clean        Remove generated artefacts
#   make demo         Run a quick encrypt/decrypt demo
#   make docker-build Build the Docker image
#   make docker-run   Run PixelShield in Docker (interactive)
# ================================================================

PYTHON    ?= python3
PIP       ?= pip3
PYTEST    ?= $(PYTHON) -m pytest
RUFF      ?= $(PYTHON) -m ruff
BANDIT    ?= $(PYTHON) -m bandit
PIP_AUDIT ?= $(PYTHON) -m pip_audit

IMAGE_NAME  = pixelshield
IMAGE_TAG   = latest
DEMO_IMAGE  = demo/sample.png

.PHONY: install test test-cov lint security bandit pip-audit secrets \
        all-checks clean demo demo-chacha demo-stego docker-build docker-run help

# ── Installation ────────────────────────────────────────────────

install:          ## Install Python dependencies
	$(PIP) install -r requirements.txt

install-dev:      ## Install with dev extras (editable)
	$(PIP) install -e ".[dev]"

# ── Testing ─────────────────────────────────────────────────────

test:             ## Run the full test suite
	$(PYTEST) tests/ -v --tb=short

test-cov:         ## Run tests with HTML coverage report
	$(PYTEST) tests/ -v --tb=short \
		--cov=. \
		--cov-report=term-missing \
		--cov-report=html:output/coverage \
		--cov-omit="tests/*,setup.py"
	@echo "Coverage report: output/coverage/index.html"

test-fast:        ## Run tests skipping slow integration tests
	$(PYTEST) tests/ -v --tb=short -m "not slow"

# ── Linting ─────────────────────────────────────────────────────

lint:             ## Run ruff linter
	$(RUFF) check . --output-format=full

lint-fix:         ## Auto-fix ruff lint issues
	$(RUFF) check . --fix

format:           ## Format code with ruff
	$(RUFF) format .

# ── Security ────────────────────────────────────────────────────

bandit:           ## Run bandit SAST scan
	$(BANDIT) -r . \
		--exclude ./tests,./output,./logs,./.github,./.venv \
		--severity-level medium \
		--confidence-level medium \
		-f txt

pip-audit:        ## Audit dependencies for known CVEs
	$(PIP_AUDIT) -r requirements.txt

secrets:          ## Scan for accidentally committed secrets
	$(PYTHON) -m detect_secrets scan \
		--exclude-files '\.git/.*' \
		--exclude-files 'output/.*' \
		--exclude-files 'logs/.*' \
		> /dev/null && echo "No secrets detected."

security: bandit pip-audit secrets  ## Run all security checks

# ── Full CI pipeline ────────────────────────────────────────────

all-checks: lint security test  ## Run lint + security + tests (mirrors CI)

# ── Demo ────────────────────────────────────────────────────────

demo:             ## Run a quick encrypt/decrypt demo on demo/sample.png
	@mkdir -p demo output
	@if [ ! -f $(DEMO_IMAGE) ]; then \
		$(PYTHON) -c "\
import numpy as np; \
from PIL import Image; \
rng = np.random.default_rng(0); \
arr = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8).astype('uint8'); \
Image.fromarray(arr, mode='RGB').save('$(DEMO_IMAGE)')"; \
		echo "Created demo image: $(DEMO_IMAGE)"; \
	fi
	@echo ""
	@echo "──────────────── Encrypt ────────────────"
	$(PYTHON) pixelshield.py encrypt $(DEMO_IMAGE) \
		--password "DemoPassword123!" \
		--shuffle --entropy --histogram \
		--out-dir output/ --verbose
	@echo ""
	@echo "──────────────── Decrypt ────────────────"
	$(PYTHON) pixelshield.py decrypt output/sample.psh \
		--password "DemoPassword123!" \
		--verify --out-dir output/ --verbose
	@echo ""
	@echo "──────────────── Files ──────────────────"
	@ls -lh output/sample* 2>/dev/null || true

demo-hybrid:      ## Run a hybrid RSA+AES demo (no password required)
	@mkdir -p demo output
	@if [ ! -f $(DEMO_IMAGE) ]; then \
		$(PYTHON) -c "\
import numpy as np; \
from PIL import Image; \
arr = np.random.randint(0,256,(128,128,3),dtype='uint8'); \
Image.fromarray(arr,'RGB').save('$(DEMO_IMAGE)')"; \
	fi
	$(PYTHON) pixelshield.py encrypt $(DEMO_IMAGE) \
		--algorithm hybrid --shuffle --entropy --out-dir output/
	$(PYTHON) pixelshield.py decrypt output/sample.psh \
		--rsa-key output/sample_private.pem --out-dir output/

demo-chacha:      ## Run a ChaCha20-Poly1305 encrypt/decrypt demo
	@mkdir -p demo output
	@if [ ! -f $(DEMO_IMAGE) ]; then \
		$(PYTHON) -c "\
import numpy as np; \
from PIL import Image; \
rng = np.random.default_rng(1); \
arr = rng.integers(0, 256, (128, 128, 3), dtype=np.uint8).astype('uint8'); \
Image.fromarray(arr, mode='RGB').save('$(DEMO_IMAGE)')"; \
	fi
	@echo ""
	@echo "──────────── ChaCha20-Poly1305 Encrypt ────────────"
	$(PYTHON) pixelshield.py encrypt $(DEMO_IMAGE) \
		--algorithm chacha20 \
		--password "DemoPassword123!" \
		--shuffle --entropy \
		--out-dir output/ --verbose
	@echo ""
	@echo "──────────── ChaCha20-Poly1305 Decrypt ────────────"
	$(PYTHON) pixelshield.py decrypt output/sample.psh \
		--password "DemoPassword123!" \
		--verify --out-dir output/ --verbose

demo-stego:       ## Run a steganography hide/reveal demo
	@mkdir -p demo output
	@if [ ! -f $(DEMO_IMAGE) ]; then \
		$(PYTHON) -c "\
import numpy as np; \
from PIL import Image; \
rng = np.random.default_rng(2); \
arr = rng.integers(0, 256, (256, 256, 3), dtype=np.uint8).astype('uint8'); \
Image.fromarray(arr, mode='RGB').save('$(DEMO_IMAGE)')"; \
	fi
	@echo ""
	@echo "────────────────── Stego Capacity ──────────────────"
	$(PYTHON) pixelshield.py stego capacity --carrier $(DEMO_IMAGE)
	@echo ""
	@echo "────────────────── Stego Hide ───────────────────────"
	$(PYTHON) pixelshield.py stego hide \
		--carrier $(DEMO_IMAGE) \
		--text "PixelShield steganography demo!" \
		--password "DemoPassword123!" \
		--output output/sample_stego.png
	@echo ""
	@echo "────────────────── Stego Reveal ─────────────────────"
	$(PYTHON) pixelshield.py stego reveal \
		--carrier output/sample_stego.png \
		--password "DemoPassword123!"

demo-batch:       ## Run batch encryption on the demo/ directory
	@mkdir -p demo
	@for i in 1 2 3; do \
		$(PYTHON) -c "\
import numpy as np; from PIL import Image; \
arr = np.random.randint(0,256,(64,64,3),dtype='uint8'); \
Image.fromarray(arr,'RGB').save('demo/image_$$i.png')"; \
	done
	$(PYTHON) pixelshield.py batch demo/ \
		--password "BatchDemo123!" --entropy --out-dir output/

# ── Docker ──────────────────────────────────────────────────────

docker-build:     ## Build the Docker image
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-run:       ## Run PixelShield in Docker (interactive)
	docker run --rm -it \
		-v $(PWD)/images:/app/images:ro \
		-v $(PWD)/output:/app/output \
		$(IMAGE_NAME):$(IMAGE_TAG) $(ARGS)

docker-compose-up:  ## Start with docker-compose
	docker compose up

# ── Cleanup ─────────────────────────────────────────────────────

clean:            ## Remove generated files (keep source)
	@rm -rf output/ logs/ .pytest_cache/ htmlcov/ .coverage demo/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@echo "Clean."

clean-all: clean  ## Also remove virtual environments
	@rm -rf .venv/ venv/ env/ *.egg-info/ dist/ build/

# ── Help ────────────────────────────────────────────────────────

help:             ## Show this help message
	@echo "PixelShield – Developer Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?##.*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

.DEFAULT_GOAL := help
