.PHONY: ruff lint test

lint:
	uv run python -m mypy .

ruff:
	ruff check . --fix

test:
	uv run pytest -v

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"

