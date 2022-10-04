PACKAGES := clinica test
POETRY ?= poetry
CONDA ?= conda
CONDA_ENV ?= "./env"

.PHONY: help
help: Makefile
	@echo "Commands:"
	@sed -n 's/^##//p' $<

## build			: Build the package.
.PHONY: build
build:
	@$(POETRY) build

.PHONY: clean.doc
clean.doc:
	@$(RM) -rf site

.PHONY: config.testpypi
config.testpypi:
	@$(POETRY) config repositories.testpypi https://test.pypi.org/legacy

## doc			: Build the documentation.
.PHONY: doc
doc: clean.doc 
	@$(POETRY) run mkdocs build

## env			: Bootstap an environment.
.PHONY: env
env: env.dev

.PHONY: env.conda
env.conda:
	@$(CONDA) env create -p $(CONDA_ENV)

.PHONY: env.dev
env.dev: install

.PHONY: env.doc
env.doc:
	@$(CONDA) env create -f docs/environment.yml -p $(CONDA_ENV)

## format			: Format the codebase.
.PHONY: format
format: install format.black format.isort

.PHONY: format.black
format.black:
	$(info Formatting code with black)
	@$(POETRY) run black --quiet $(PACKAGES)

.PHONY: format.isort
format.isort:
	$(info Formatting code with isort)
	@$(POETRY) run isort --quiet $(PACKAGES)

## install		: Install the project.
.PHONY: install
install:
	@$(POETRY) install

## lint			: Lint the codebase.
.PHONY: lint
lint: install lint.black lint.isort

.PHONY: lint.black
lint.black:
	$(info Linting code with black)
	@$(POETRY) run black --check --diff $(PACKAGES)

.PHONY: lint.isort
lint.isort:
	$(info Linting code with isort)
	@$(POETRY) run isort --check --diff $(PACKAGES)

## publish		: Publish the package to pypi.
.PHONY: publish
publish: publish.pypi

.PHONY: publish.pypi
publish.pypi: build
	@$(POETRY) publish

.PHONY: publish.testpypi
publish.testpypi: build config.testpypi
	@$(POETRY) publish --repository testpypi

.PHONY: test
test: install
	@$(POETRY) run python -m pytest -v test/unittests