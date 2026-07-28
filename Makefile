SHELL := /bin/bash

PYTHON_BIN ?= /opt/homebrew/bin/python3.11
VENV := .venv-p22
PY := $(VENV)/bin/python
RUFF := $(VENV)/bin/ruff
GENERATED := reports/generated
NOTEBOOK_DIR := notebooks/implementation
LEGACY_NOTEBOOK := $(NOTEBOOK_DIR)/01_tasic_evidence_boundary.ipynb
SYNTHETIC_NOTEBOOKS := $(filter-out $(LEGACY_NOTEBOOK),$(sort $(wildcard $(NOTEBOOK_DIR)/*.ipynb)))
SCALE_NOTEBOOK := notebooks/scale/11_scale_benchmark.ipynb
LINT_PATHS := src tests scripts
KERNEL_ROOT := $(CURDIR)/$(GENERATED)/jupyter
KERNEL_DIR := $(KERNEL_ROOT)/kernels/python3

export UV_PROJECT_ENVIRONMENT := $(VENV)

.PHONY: setup plan-status plan-check lint test-fast test-all verify-step \
        notebook-kernel notebook-check notebook-check-legacy scale-check \
        verify-fast verify clean-generated

setup:
	uv sync --python $(PYTHON_BIN) --extra dev

plan-status:
	$(PY) scripts/plan_guard.py status

plan-check:
	@test -n "$(STEP)" || { echo "STEP=CNN required"; exit 2; }
	@test -n "$(PHASE)" || { echo "PHASE=worktree|staged|committed required"; exit 2; }
	$(PY) scripts/plan_guard.py check --step $(STEP) --phase $(PHASE)

lint:
	$(RUFF) check $(LINT_PATHS)
	$(RUFF) format --check $(LINT_PATHS)

test-fast:
	$(PY) -m pytest -q -m "not slow"

test-all:
	$(PY) -m pytest -q

verify-step:
	@test -n "$(STEP)" || { echo "STEP=CNN required"; exit 2; }
	$(PY) scripts/plan_guard.py check --step $(STEP) --phase worktree
	$(MAKE) lint
	$(MAKE) test-fast

# Notebooks execute against .venv-p22, not any user-level kernel. The kernelspec
# is generated under the ignored reports/generated tree so no global state is needed.
notebook-kernel:
	@mkdir -p $(KERNEL_DIR)
	@printf '{\n  "argv": ["%s", "-m", "ipykernel_launcher", "-f", "{connection_file}"],\n  "display_name": "P22 (.venv-p22)",\n  "language": "python"\n}\n' \
	  "$(CURDIR)/$(PY)" > $(KERNEL_DIR)/kernel.json

notebook-check: notebook-kernel
	@mkdir -p $(GENERATED)/notebooks
	@if [ -z "$(SYNTHETIC_NOTEBOOKS)" ]; then \
	  echo "notebook-check: no synthetic notebooks present yet"; \
	else \
	  JUPYTER_PATH=$(KERNEL_ROOT) PYTHONDONTWRITEBYTECODE=1 $(PY) -m jupyter nbconvert --to notebook --execute \
	    --ExecutePreprocessor.timeout=1800 \
	    --ExecutePreprocessor.startup_timeout=300 \
	    --output-dir $(GENERATED)/notebooks $(SYNTHETIC_NOTEBOOKS); \
	fi

notebook-check-legacy: notebook-kernel
	@mkdir -p $(GENERATED)/notebooks
	@if [ -f $(LEGACY_NOTEBOOK) ]; then \
	  JUPYTER_PATH=$(KERNEL_ROOT) PYTHONDONTWRITEBYTECODE=1 $(PY) -m jupyter nbconvert --to notebook --execute \
	    --ExecutePreprocessor.timeout=1800 \
	    --ExecutePreprocessor.startup_timeout=300 \
	    --output-dir $(GENERATED)/notebooks $(LEGACY_NOTEBOOK); \
	else \
	  echo "notebook-check-legacy: legacy notebook not present yet"; \
	fi

scale-check: notebook-kernel
	@mkdir -p $(GENERATED)/scale-notebooks
	@JUPYTER_PATH=$(KERNEL_ROOT) PYTHONDONTWRITEBYTECODE=1 $(PY) -m jupyter nbconvert --to notebook --execute \
		--ExecutePreprocessor.timeout=1800 \
		--ExecutePreprocessor.startup_timeout=300 \
		--output-dir $(GENERATED)/scale-notebooks $(SCALE_NOTEBOOK)

verify-fast: lint test-fast plan-status

verify: verify-fast test-all notebook-check notebook-check-legacy
	@if [ -f scripts/verify_repository.py ]; then \
	  $(PY) scripts/verify_repository.py; \
	else \
	  echo "verify: scripts/verify_repository.py not present yet (added in C12)"; \
	fi

clean-generated:
	rm -rf $(GENERATED)
