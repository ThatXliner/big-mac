.PHONY: check secrets catalog inventory
check:
	python3 -m unittest discover -s tests -v
	python3 scripts/validate.py
	bash -n scripts/bootstrap-macos.sh
secrets:
	python3 scripts/secret-scan.py
catalog:
	python3 scripts/catalog.py
inventory:
	python3 scripts/manage.py refresh
	python3 scripts/catalog.py
