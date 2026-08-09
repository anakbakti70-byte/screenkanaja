.PHONY: install run test
install:
	pip install -r apps/backend/requirements.txt
run:
	python apps/backend/app/main.py
