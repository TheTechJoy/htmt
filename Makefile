# HTMT tasks. Run `make` for the list. Uses .venv/ when `make setup` has created it.

PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: help setup setup-dev test validate convert build check schema

help:
	@echo "make setup                    create .venv and install lxml (needed to validate)"
	@echo "make validate [FILES=...]     validate .htmt files or folders (default: examples)"
	@echo "make convert IN=x.vtt OUT=x.htmt   convert VTT, SRT, TXT or ASR JSON to HTMT"
	@echo "make test                     run the self-test suite"
	@echo "make build                    rebuild index.html from src/, the schema and examples"
	@echo "make check                    test + confirm index.html is up to date"
	@echo "make setup-dev / make schema  maintainers: regenerate htmt-1.0.rng from htmt-1.0.rnc"

setup:
	python3 -m venv .venv
	.venv/bin/pip install --require-virtualenv -r requirements.txt

setup-dev: setup
	.venv/bin/pip install --require-virtualenv -r requirements-dev.txt

FILES ?= examples
validate:
	$(PYTHON) tools/validate.py $(FILES)

convert:
	@test -n "$(IN)" || (echo "usage: make convert IN=input.vtt OUT=output.htmt" && exit 2)
	$(PYTHON) tools/to_htmt.py "$(IN)" $(if $(OUT),-o "$(OUT)")

test:
	$(PYTHON) tools/test.py

build:
	$(PYTHON) tools/build.py

check: test
	$(PYTHON) tools/build.py --check

schema:
	$(PYTHON) tools/make_rng.py
