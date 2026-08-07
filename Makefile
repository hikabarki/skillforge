PY ?= python3
export PYTHONPATH := src
export PYTHONIOENCODING := utf-8

.PHONY: all harvest synth render eval test lint clean

all: harvest synth render eval

harvest:
	$(PY) -m skillforge.cli harvest --input fixtures/skills --out data/corpus/skills.jsonl

synth:
	$(PY) -m skillforge.cli synthesize --corpus data/corpus/skills.jsonl \
		--out data/trajectories/train.jsonl --distractors 6 --abstain-rate 0.25 --seed 20260807

render:
	$(PY) -m skillforge.cli render --trajectories data/trajectories/train.jsonl \
		--out data/trajectories/train.sft.jsonl --format chatml
	$(PY) -m skillforge.cli render --trajectories data/trajectories/dev.jsonl \
		--out data/trajectories/dev.sft.jsonl --format chatml

eval:
	$(PY) -m skillforge.cli baselines --trajectories data/trajectories/train.jsonl

test:
	$(PY) -m pytest -q

lint:
	ruff check src tests

clean:
	rm -f data/corpus/*.jsonl data/trajectories/*.jsonl data/reports/*.json
