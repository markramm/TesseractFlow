#!/bin/bash
# Wave 4: Reasoning & Verbalized Sampling Experiments
# Launch all 8 experiments in parallel

source .env
export OPENROUTER_API_KEY

echo "=== WAVE 4: REASONING & VERBALIZED SAMPLING EXPERIMENTS ==="
echo ""
echo "Testing framework-level reasoning and verbalized sampling integration"
echo "Models: DeepSeek R1 vs DeepSeek V3.2 Exp"
echo "Workflows: Fiction Scene, Dialogue, Character, Progressive Discovery"
echo "Estimated cost: ~\$0.10-0.15 (with caching)"
echo "Estimated time: ~30-40 minutes"
echo ""
echo "Launching 8 experiments in parallel..."
echo ""

# R1 Experiments
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs.yaml --output experiments/wave4_fiction_r1.json --use-cache --record-cache 2>&1 | tee experiments/wave4_fiction_r1.log &
.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs.yaml --output experiments/wave4_dialogue_r1.json --use-cache --record-cache 2>&1 | tee experiments/wave4_dialogue_r1.log &
.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs.yaml --output experiments/wave4_character_r1.json --use-cache --record-cache 2>&1 | tee experiments/wave4_character_r1.log &
.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs.yaml --output experiments/wave4_discovery_r1.json --use-cache --record-cache 2>&1 | tee experiments/wave4_discovery_r1.log &

# V3.2 Experiments
.venv/bin/tesseract experiment run experiments/wave4_fiction_reasoning_vs_v32.yaml --output experiments/wave4_fiction_v32.json --use-cache --record-cache 2>&1 | tee experiments/wave4_fiction_v32.log &
.venv/bin/tesseract experiment run experiments/wave4_dialogue_reasoning_vs_v32.yaml --output experiments/wave4_dialogue_v32.json --use-cache --record-cache 2>&1 | tee experiments/wave4_dialogue_v32.log &
.venv/bin/tesseract experiment run experiments/wave4_character_reasoning_vs_v32.yaml --output experiments/wave4_character_v32.json --use-cache --record-cache 2>&1 | tee experiments/wave4_character_v32.log &
.venv/bin/tesseract experiment run experiments/wave4_discovery_reasoning_vs_v32.yaml --output experiments/wave4_discovery_v32.json --use-cache --record-cache 2>&1 | tee experiments/wave4_discovery_v32.log &

echo "✅ All 8 experiments launched in background"
echo ""
echo "Monitor with:"
echo "  watch -n 10 'ls -lh experiments/wave4_*.json 2>/dev/null | tail -8'"
echo ""
echo "Check logs:"
echo "  tail -f experiments/wave4_fiction_r1.log"
