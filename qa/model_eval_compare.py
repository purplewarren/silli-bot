#!/usr/bin/env python3
"""
Model Evaluation and Comparison Script
Compares different AI models against golden test data and generates reports
"""

import json
import time
import argparse
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import re

@dataclass
class ModelResult:
    model: str
    tips_count: int
    word_limit_compliance: bool
    latency_ms: float
    quality_score: float
    tips: List[str]
    rationale: str

@dataclass
class EvaluationMetrics:
    model: str
    avg_tips_count: float
    compliance_rate: float
    avg_latency_ms: float
    avg_quality_score: float
    total_tests: int
    successful_tests: int

class ModelEvaluator:
    def __init__(self, reasoner_url: str = "http://localhost:5001"):
        self.reasoner_url = reasoner_url
        self.models = ["llama3.2:1b", "llama3.2:3b", "gpt-oss:20b"]
        
    def load_golden_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load golden test data from eval directory"""
        golden_data = {}
        
        # Load golden data for each dyad
        for dyad in ["meal", "night", "tantrum"]:
            golden_file = Path(f"reasoner/eval/goldens_{dyad}.json")
            if golden_file.exists():
                with open(golden_file, 'r') as f:
                    golden_data[dyad] = json.load(f)
            else:
                print(f"⚠️  Warning: No golden data found for {dyad}")
                golden_data[dyad] = []
        
        return golden_data
    
    def calculate_quality_score(self, tips: List[str], rationale: str) -> float:
        """Calculate a simple heuristic quality score"""
        score = 0.0
        
        # Check for action verbs in tips
        action_verbs = ['try', 'use', 'take', 'make', 'do', 'start', 'stop', 'change', 'adjust', 'consider']
        for tip in tips:
            tip_lower = tip.lower()
            if any(verb in tip_lower for verb in action_verbs):
                score += 0.3
            
            # Check for hedging words (negative)
            hedging_words = ['maybe', 'perhaps', 'might', 'could', 'possibly', 'sometimes']
            if any(word in tip_lower for word in hedging_words):
                score -= 0.1
        
        # Check rationale length (should be concise)
        if 10 <= len(rationale) <= 140:
            score += 0.2
        elif len(rationale) > 140:
            score -= 0.1
        
        # Check for specific, actionable advice
        specific_words = ['specific', 'concrete', 'immediate', 'direct']
        if any(word in rationale.lower() for word in specific_words):
            score += 0.1
        
        # Normalize score to 0-1 range
        return max(0.0, min(1.0, score))
    
    def check_word_limit_compliance(self, tips: List[str]) -> bool:
        """Check if tips comply with word limit (≤25 words each)"""
        for tip in tips:
            word_count = len(tip.split())
            if word_count > 25:
                return False
        return True
    
    async def test_model(self, model: str, dyad: str, test_data: Dict[str, Any]) -> Optional[ModelResult]:
        """Test a single model with given data"""
        try:
            # Prepare request
            req = {
                "dyad": dyad,
                "features": test_data.get("features", {}),
                "context": test_data.get("context", {}),
                "metrics": test_data.get("metrics", {}),
                "history": test_data.get("history", [])
            }
            
            # Override model in reasoner (if supported)
            # Note: This would require reasoner to support model override
            # For now, we'll test with the currently configured model
            
            # Make request
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                timeout = aiohttp.ClientTimeout(total=120)  # 2 minutes timeout
                
                async with session.post(f"{self.reasoner_url}/v1/reason", json=req, timeout=timeout) as response:
                    end_time = time.time()
                    latency_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        result = await response.json()
                        tips = result.get("tips", [])
                        rationale = result.get("rationale", "")
                        model_used = result.get("model_used", "unknown")
                        
                        # Only process if the correct model was used
                        if model_used != model:
                            print(f"⚠️  Model {model} not used, got {model_used}")
                            return None
                        
                        # Calculate metrics
                        tips_count = len(tips)
                        word_limit_compliance = self.check_word_limit_compliance(tips)
                        quality_score = self.calculate_quality_score(tips, rationale)
                        
                        return ModelResult(
                            model=model,
                            tips_count=tips_count,
                            word_limit_compliance=word_limit_compliance,
                            latency_ms=latency_ms,
                            quality_score=quality_score,
                            tips=tips,
                            rationale=rationale
                        )
                    else:
                        print(f"❌ Error testing {model}: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error testing {model}: {e}")
            return None
    
    async def evaluate_model(self, model: str, golden_data: Dict[str, List[Dict[str, Any]]]) -> EvaluationMetrics:
        """Evaluate a model against all golden data"""
        print(f"🧪 Evaluating {model}...")
        
        results = []
        total_tests = 0
        successful_tests = 0
        
        for dyad, test_cases in golden_data.items():
            for i, test_case in enumerate(test_cases):
                total_tests += 1
                print(f"  Testing {dyad} case {i+1}/{len(test_cases)}...")
                
                result = await self.test_model(model, dyad, test_case)
                if result:
                    results.append(result)
                    successful_tests += 1
                
                # Small delay between requests
                await asyncio.sleep(1)
        
        if not results:
            return EvaluationMetrics(
                model=model,
                avg_tips_count=0.0,
                compliance_rate=0.0,
                avg_latency_ms=0.0,
                avg_quality_score=0.0,
                total_tests=total_tests,
                successful_tests=0
            )
        
        # Calculate averages
        avg_tips_count = sum(r.tips_count for r in results) / len(results)
        compliance_rate = sum(1 for r in results if r.word_limit_compliance) / len(results) * 100
        avg_latency_ms = sum(r.latency_ms for r in results) / len(results)
        avg_quality_score = sum(r.quality_score for r in results) / len(results)
        
        return EvaluationMetrics(
            model=model,
            avg_tips_count=avg_tips_count,
            compliance_rate=compliance_rate,
            avg_latency_ms=avg_latency_ms,
            avg_quality_score=avg_quality_score,
            total_tests=total_tests,
            successful_tests=successful_tests
        )
    
    def generate_report(self, metrics: List[EvaluationMetrics]) -> str:
        """Generate a comprehensive comparison report"""
        report_lines = []
        report_lines.append("# Model Comparison Report")
        report_lines.append("")
        report_lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Summary table
        report_lines.append("## Summary")
        report_lines.append("")
        report_lines.append("| Model | Success Rate | Avg Tips | Compliance | Avg Latency | Quality Score |")
        report_lines.append("|-------|-------------|----------|------------|-------------|---------------|")
        
        for metric in metrics:
            success_rate = (metric.successful_tests / metric.total_tests) * 100 if metric.total_tests > 0 else 0
            report_lines.append(
                f"| {metric.model} | {success_rate:.1f}% | {metric.avg_tips_count:.1f} | {metric.compliance_rate:.1f}% | {metric.avg_latency_ms:.0f}ms | {metric.avg_quality_score:.2f} |"
            )
        
        report_lines.append("")
        
        # Detailed analysis
        report_lines.append("## Detailed Analysis")
        report_lines.append("")
        
        for metric in metrics:
            report_lines.append(f"### {metric.model}")
            report_lines.append("")
            report_lines.append(f"- **Success Rate**: {metric.successful_tests}/{metric.total_tests} ({metric.successful_tests/metric.total_tests*100:.1f}%)")
            report_lines.append(f"- **Average Tips**: {metric.avg_tips_count:.1f}")
            report_lines.append(f"- **Word Limit Compliance**: {metric.compliance_rate:.1f}%")
            report_lines.append(f"- **Average Latency**: {metric.avg_latency_ms:.0f}ms")
            report_lines.append(f"- **Quality Score**: {metric.avg_quality_score:.2f}")
            report_lines.append("")
        
        # Recommendations
        report_lines.append("## Recommendations")
        report_lines.append("")
        
        # Find best model in each category
        best_latency = min(metrics, key=lambda m: m.avg_latency_ms)
        best_quality = max(metrics, key=lambda m: m.avg_quality_score)
        best_compliance = max(metrics, key=lambda m: m.compliance_rate)
        
        report_lines.append(f"- **Fastest Model**: {best_latency.model} ({best_latency.avg_latency_ms:.0f}ms)")
        report_lines.append(f"- **Highest Quality**: {best_quality.model} (score: {best_quality.avg_quality_score:.2f})")
        report_lines.append(f"- **Best Compliance**: {best_compliance.model} ({best_compliance.compliance_rate:.1f}%)")
        report_lines.append("")
        
        # Staging recommendation
        if any(m.model == "gpt-oss:20b" for m in metrics):
            gpt_20b = next(m for m in metrics if m.model == "gpt-oss:20b")
            if gpt_20b.successful_tests > 0:
                report_lines.append("### Staging Recommendation")
                report_lines.append("")
                report_lines.append("✅ **gpt-oss:20b is ready for staging**")
                report_lines.append(f"- Success rate: {gpt_20b.successful_tests/gpt_20b.total_tests*100:.1f}%")
                report_lines.append(f"- Quality score: {gpt_20b.avg_quality_score:.2f}")
                report_lines.append(f"- Average latency: {gpt_20b.avg_latency_ms:.0f}ms")
            else:
                report_lines.append("❌ **gpt-oss:20b failed all tests - investigate before staging**")
        else:
            report_lines.append("⚠️ **gpt-oss:20b not tested - cannot make staging recommendation**")
        
        return "\n".join(report_lines)

async def main():
    """Main evaluation function"""
    parser = argparse.ArgumentParser(description="Model Evaluation and Comparison")
    parser.add_argument("--reasoner-url", default="http://localhost:5001",
                       help="Reasoner service URL")
    parser.add_argument("--output", default="reports/model_comparison.md",
                       help="Output report file")
    args = parser.parse_args()
    
    # Create reports directory
    Path("reports").mkdir(exist_ok=True)
    
    # Initialize evaluator
    evaluator = ModelEvaluator(args.reasoner_url)
    
    # Load golden data
    print("📊 Loading golden test data...")
    golden_data = evaluator.load_golden_data()
    
    total_cases = sum(len(cases) for cases in golden_data.values())
    print(f"📋 Found {total_cases} test cases across {len(golden_data)} dyads")
    
    # Evaluate each model
    all_metrics = []
    for model in evaluator.models:
        metrics = await evaluator.evaluate_model(model, golden_data)
        all_metrics.append(metrics)
        print(f"✅ Completed evaluation of {model}")
    
    # Generate report
    print("📝 Generating report...")
    report = evaluator.generate_report(all_metrics)
    
    # Write report
    with open(args.output, 'w') as f:
        f.write(report)
    
    print(f"📄 Report written to {args.output}")
    
    # Print summary
    print("\n📊 Evaluation Summary:")
    for metric in all_metrics:
        success_rate = (metric.successful_tests / metric.total_tests) * 100 if metric.total_tests > 0 else 0
        print(f"  {metric.model}: {success_rate:.1f}% success, {metric.avg_latency_ms:.0f}ms avg, {metric.avg_quality_score:.2f} quality")

if __name__ == "__main__":
    asyncio.run(main())
