.PHONY: install run debug clean lint lint-strict visual

MAP ?= maps/easy/01_linear_path.txt

install:
	pip install -r requirements.txt

run:
	python3 main.py $(MAP)

visual:
	python3 main.py $(MAP) --visual

debug:
	python3 -m pdb main.py $(MAP)

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict