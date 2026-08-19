ARCH := $(shell uname -m)

ifeq ($(ARCH),arm64)
	PLATFORM := linux/arm64
else
	PLATFORM := linux/amd64
endif

HOST_PATH := $(shell pwd)
IMAGE_NAME := restaurant-analytics-data-platform
APP_DIR := /app

DATA_FILES := \
	data/raw/restaurants.parquet \
	data/raw/users.parquet \
	data/raw/bookings.parquet \
	data/raw/payments.parquet

.PHONY: build run test generate-data clean clean-all docs docs-generate docs-serve check-data


# =========================
# BUILD
# =========================

build:
	docker build \
		--platform $(PLATFORM) \
		-t $(IMAGE_NAME) .


# =========================
# DATA
# =========================

check-data:
	@echo "Checking input data..."
	@missing=0; \
	for f in $(DATA_FILES); do \
		if [ ! -f $$f ]; then \
			echo " - missing: $$f"; \
			missing=1; \
		fi; \
	done; \
	if [ $$missing -eq 0 ]; then \
		echo "Input data found, skipping generation"; \
	else \
		echo "Input data not found, generating synthetic datasets..."; \
		docker run --rm \
			-v "$$(pwd)/data:$(APP_DIR)/data" \
			$(IMAGE_NAME) \
			python $(APP_DIR)/scripts/generate_input_data.py; \
	fi


generate-data: build
	docker run --rm \
		-v "$$(pwd)/data:$(APP_DIR)/data" \
		$(IMAGE_NAME) \
		python $(APP_DIR)/scripts/generate_input_data.py


# =========================
# PIPELINE
# =========================

run: build check-data
	docker run --rm \
		-e HOST_PATH="$(HOST_PATH)" \
		-v "$$(pwd)/data:$(APP_DIR)/data" \
		-v "$$(pwd)/exports:$(APP_DIR)/exports" \
		-v "$$(pwd)/logs:$(APP_DIR)/logs" \
		-v "$$(pwd)/.duckdb:$(APP_DIR)/.duckdb" \
		$(IMAGE_NAME) \
		$(APP_DIR)/scripts/run.sh


# =========================
# TEST
# =========================

test: build
	docker run --rm \
		-v "$$(pwd)/data:$(APP_DIR)/data" \
		-v "$$(pwd)/exports:$(APP_DIR)/exports" \
		-v "$$(pwd)/logs:$(APP_DIR)/logs" \
		-v "$$(pwd)/.duckdb:$(APP_DIR)/.duckdb" \
		$(IMAGE_NAME) \
		$(APP_DIR)/scripts/test.sh


# =========================
# DBT DOCS
# =========================

docs-generate: build
	docker run --rm \
		-v "$$(pwd)/data:$(APP_DIR)/data" \
		-v "$$(pwd)/exports:$(APP_DIR)/exports" \
		-v "$$(pwd)/logs:$(APP_DIR)/logs" \
		-v "$$(pwd)/.duckdb:$(APP_DIR)/.duckdb" \
		-v "$$(pwd)/target:$(APP_DIR)/target" \
		$(IMAGE_NAME) \
		dbt docs generate


docs-serve: build
	docker run --rm \
		-p 8080:8080 \
		-v "$$(pwd)/data:$(APP_DIR)/data" \
		-v "$$(pwd)/exports:$(APP_DIR)/exports" \
		-v "$$(pwd)/logs:$(APP_DIR)/logs" \
		-v "$$(pwd)/.duckdb:$(APP_DIR)/.duckdb" \
		-v "$$(pwd)/target:$(APP_DIR)/target" \
		$(IMAGE_NAME) \
		dbt docs serve --host 0.0.0.0


docs: docs-generate docs-serve


# =========================
# CLEANUP
# =========================

clean:
	@echo "Cleaning generated outputs..."

	rm -rf exports/cleaned/*
	rm -rf exports/marts/*
	rm -f exports/reports/summary_report.md

	touch exports/cleaned/.gitkeep
	touch exports/marts/.gitkeep
	touch exports/reports/.gitkeep

	rm -rf logs/*
	touch logs/.gitkeep

	rm -f .duckdb/*.duckdb
	touch .duckdb/.gitkeep

	rm -rf target/

	@echo "Clean completed"


clean-all: clean
	@echo "Cleaning generated input data..."

	rm -f data/raw/*.parquet
	touch data/raw/.gitkeep

	@echo "Full clean completed"