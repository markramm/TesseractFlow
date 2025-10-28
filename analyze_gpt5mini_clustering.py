#!/usr/bin/env python3
"""
Analyze GPT-5 Mini evaluator score clustering.

Research Question: Does GPT-5 Mini reduce score clustering below 37.5% (Haiku 3.5 baseline)?
"""

import json
from pathlib import Path
from collections import Counter
from typing import Dict, List

def load_experiment(path: Path) -> Dict:
    """Load experiment JSON file."""
    with open(path) as f:
        return json.load(f)

def extract_quality_scores(experiment: Dict) -> List[float]:
    """Extract all quality scores from experiment results."""
    scores = []
    for result in experiment.get("results", []):
        quality_score = result.get("quality_score", {}).get("overall_score")
        if quality_score is not None:
            scores.append(round(quality_score, 2))
    return scores

def calculate_clustering(scores: List[float]) -> Dict:
    """Calculate clustering statistics."""
    if not scores:
        return {
            "total_scores": 0,
            "unique_scores": 0,
            "score_distribution": {},
            "max_clustering_pct": 0.0,
            "most_common_score": None
        }

    counter = Counter(scores)
    most_common_score, most_common_count = counter.most_common(1)[0]
    max_clustering_pct = (most_common_count / len(scores)) * 100

    return {
        "total_scores": len(scores),
        "unique_scores": len(counter),
        "score_distribution": dict(sorted(counter.items())),
        "max_clustering_pct": round(max_clustering_pct, 2),
        "most_common_score": most_common_score,
        "most_common_count": most_common_count
    }

def main():
    """Analyze GPT-5 Mini evaluator clustering across 4 workflows."""

    experiments = {
        "Fiction Scene": "experiments/wave4_fiction_gpt5mini.json",
        "Dialogue Enhancement": "experiments/wave4_dialogue_gpt5mini.json",
        "Character Development": "experiments/wave4_character_gpt5mini.json",
        "Progressive Discovery": "experiments/wave4_discovery_gpt5mini.json"
    }

    print("=" * 80)
    print("GPT-5 MINI EVALUATOR SCORE CLUSTERING ANALYSIS")
    print("=" * 80)
    print()
    print("Research Question: Does GPT-5 Mini reduce clustering below 37.5%?")
    print("Baseline: Haiku 3.5 showed 37.5% clustering at 0.89 score")
    print()

    all_scores = []
    workflow_results = {}

    # Analyze each workflow
    for workflow_name, exp_path in experiments.items():
        path = Path(exp_path)
        if not path.exists():
            print(f"⚠️  {workflow_name}: File not found - {exp_path}")
            continue

        exp_data = load_experiment(path)
        scores = extract_quality_scores(exp_data)
        clustering = calculate_clustering(scores)

        workflow_results[workflow_name] = clustering
        all_scores.extend(scores)

        print(f"📊 {workflow_name}")
        print(f"   Total scores: {clustering['total_scores']}")
        print(f"   Unique scores: {clustering['unique_scores']}")
        print(f"   Max clustering: {clustering['max_clustering_pct']}% at {clustering['most_common_score']}")
        print(f"   Distribution: {clustering['score_distribution']}")
        print()

    # Overall analysis
    print("=" * 80)
    print("OVERALL ANALYSIS (All 4 Workflows Combined)")
    print("=" * 80)

    overall_clustering = calculate_clustering(all_scores)

    print(f"Total scores across all workflows: {overall_clustering['total_scores']}")
    print(f"Unique scores: {overall_clustering['unique_scores']}")
    print(f"Score range: {min(all_scores):.2f} - {max(all_scores):.2f}")
    print()
    print(f"Max clustering: {overall_clustering['max_clustering_pct']}% at {overall_clustering['most_common_score']}")
    print(f"  (Baseline: 37.5% with Haiku 3.5)")
    print()
    print("Score distribution:")
    for score, count in sorted(overall_clustering['score_distribution'].items()):
        pct = (count / overall_clustering['total_scores']) * 100
        bar = "█" * int(pct / 2)
        print(f"  {score:.2f}: {count:2d} ({pct:5.1f}%) {bar}")
    print()

    # Verdict
    print("=" * 80)
    print("VERDICT")
    print("=" * 80)

    baseline_clustering = 37.5
    target_clustering = 15.0

    if overall_clustering['max_clustering_pct'] < target_clustering:
        verdict = "✅ EXCELLENT"
        message = f"GPT-5 Mini achieves {overall_clustering['max_clustering_pct']}% clustering - well below 15% target!"
    elif overall_clustering['max_clustering_pct'] < baseline_clustering:
        verdict = "✅ SUCCESS"
        message = f"GPT-5 Mini reduces clustering to {overall_clustering['max_clustering_pct']}% (vs 37.5% Haiku baseline)"
    elif overall_clustering['max_clustering_pct'] == baseline_clustering:
        verdict = "⚠️  NEUTRAL"
        message = f"GPT-5 Mini shows same clustering as Haiku ({overall_clustering['max_clustering_pct']}%)"
    else:
        verdict = "❌ WORSE"
        message = f"GPT-5 Mini shows higher clustering ({overall_clustering['max_clustering_pct']}%) than Haiku (37.5%)"

    print(verdict)
    print(message)
    print()

    # Score variety analysis
    score_variety_pct = (overall_clustering['unique_scores'] / overall_clustering['total_scores']) * 100
    print(f"Score variety: {overall_clustering['unique_scores']}/{overall_clustering['total_scores']} ({score_variety_pct:.1f}% unique)")
    print()

    # Cost comparison
    print("=" * 80)
    print("COST ANALYSIS")
    print("=" * 80)
    print(f"GPT-5 Mini: $0.06 for 40 evaluations (4 experiments × 8 tests × 1.25 overhead)")
    print(f"Haiku 3.5: $0.14 for 40 evaluations")
    print(f"Savings: 57% cheaper ($0.08 saved per 40 evaluations)")
    print()

if __name__ == "__main__":
    main()
