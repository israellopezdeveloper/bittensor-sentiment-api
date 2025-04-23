.PHONY: format lint test clean all

check:
	@echo "==========================="
	@echo "🐍 Checking the application"
	@echo "==========================="
	@cp .env.example .env
	@echo "  -------------------"
	@echo "  🧪 Running tests..."
	@echo "  -------------------"
	@poetry run pytest --no-header && echo "✅ Tests passed"
	@echo ""
	@echo "  -------------------------------"
	@echo "  🧪 Running security analysis..."
	@echo "  -------------------------------"
	@poetry run pip-audit \
    --ignore-vuln PYSEC-2022-42969 \
    --ignore-vuln GHSA-79v4-65xg-pq4g \
    --ignore-vuln GHSA-f96h-pmfr-66vw \
    && echo "✅ Security analysis passed"
	@echo -e "\n\n"

clean:
	@echo "=============="
	@echo "🧽 Cleaning up"
	@echo "=============="
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@rm -rf .mypy_cache docs .env docs
	@echo -e "USER_ID=$$(id -u)\nGROUP_ID=$$(id -g)" >> .env && \
    docker compose down -v && \
    rm -rf .env
	@echo -e "\n\n"

install:
	@echo "=========================="
	@echo "📦 Installing dependencies"
	@echo "=========================="
	@poetry lock && poetry install
	@echo -e "\n\n"

all: install format lint check

build: clean install
	@echo "==========================="
	@echo "📦 Building the application"
	@echo "==========================="
	@cp .env.example .env
	@echo -e "USER_ID=$$(id -u)\nGROUP_ID=$$(id -g)" >> .env && \
    docker compose build && \
    sed -i '/USER_ID=.*/d' .env && \
    sed -i '/GROUP_ID=.*/d' .env
	@echo -e "\n\n"

run: build
	@echo "=========================="
	@echo "🚀 Running the application"
	@echo "=========================="
	@echo -e "USER_ID=$$(id -u)\nGROUP_ID=$$(id -g)" >> .env && \
    docker compose up; \
    sed -i '/USER_ID=.*/d' .env && \
    sed -i '/GROUP_ID=.*/d' .env
	@echo -e "\n\n"

docs:
	@echo "============================="
	@echo "📚 Building the documentation"
	@echo "============================="
	@cp .env.example .env
	@poetry run pdoc ./app --output-dir docs
	@echo -e "\n\n"
