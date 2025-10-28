#!/bin/bash
# Wave 4: Reasoning & Verbalized Sampling Experiments (n=5 replications)
# Run all 8 experiments with 5 replications each for statistical significance

source .env
export OPENROUTER_API_KEY

echo "=== WAVE 4: REASONING & VERBALIZED SAMPLING (n=5 replications) ==="
echo ""
echo "Testing framework-level reasoning and verbalized sampling integration"
echo "Models: DeepSeek R1 vs DeepSeek V3.2 Exp"
echo "Workflows: Fiction Scene, Dialogue, Character, Progressive Discovery"
echo "Replications: 5 per test configuration (40 tests per experiment)"
echo "Estimated cost: ~\$0.40-0.60 (with caching)"
echo "Estimated time: ~2-3 hours for all 8 experiments"
echo ""
echo "Launching 8 experiments in parallel..."
echo ""

# R1 Experiments (4)
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs.yaml \
  --output experiments/wave4_fiction_r1_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_fiction_r1_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs.yaml \
  --output experiments/wave4_dialogue_r1_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_dialogue_r1_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs.yaml \
  --output experiments/wave4_character_r1_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_character_r1_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs.yaml \
  --output experiments/wave4_discovery_r1_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_discovery_r1_n5.log &

# V3.2 Experiments (4)
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs_v32.yaml \
  --output experiments/wave4_fiction_v32_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_fiction_v32_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs_v32.yaml \
  --output experiments/wave4_dialogue_v32_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_dialogue_v32_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs_v32.yaml \
  --output experiments/wave4_character_v32_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_character_v32_n5.log &

.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs_v32.yaml \
  --output experiments/wave4_discovery_v32_n5.json \
  --replications 5 \
  --use-cache --record-cache 2>&1 | tee experiments/wave4_discovery_v32_n5.log &

echo ""
echo "✅ All 8 experiments launched in background"
echo ""
echo "Monitor progress with:"
echo "  watch -n 30 'ls -lh experiments/wave4_*_n5.json 2>/dev/null | tail -8'"
echo ""
echo "Check individual logs:"
echo "  tail -f experiments/wave4_fiction_r1_n5.log"
echo ""
echo "Wait for all to complete (2-3 hours), then run analysis:"
echo "  .venv/bin/tesseract analyze main-effects experiments/wave4_fiction_r1_n5.json"
echo ""
