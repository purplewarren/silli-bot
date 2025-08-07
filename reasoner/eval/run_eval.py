#!/usr/bin/env python3
"""
Evaluation harness for reasoner output quality
Tests constraint compliance and generates performance report
"""

import json
import time
import requests
import sys
from typing import Dict, List, Any, Tuple
from pathlib import Path

class ReasonerEvaluator:
    """Evaluates reasoner output quality against golden test cases"""
    
    def __init__(self, reasoner_url: str = "http://localhost:5001"):
        self.reasoner_url = reasoner_url
        self.results = []
        
    def load_golden_cases(self, dyad: str) -> List[Dict[str, Any]]:
        """Load golden test cases for a dyad"""
        golden_file = Path(__file__).parent / f"goldens_{dyad}.json"
        
        if not golden_file.exists():
            raise FileNotFoundError(f"Golden file not found: {golden_file}")
        
        with open(golden_file, 'r') as f:
            return json.load(f)
    
    def check_forbidden_terms(self, text: str) -> bool:
        """Check if text contains forbidden terms"""
        forbidden_terms = [
            'fuck', 'shit', 'damn', 'bitch', 'ass', 'piss', 'cock', 'dick', 'pussy',
            'cunt', 'whore', 'slut', 'bastard', 'motherfucker', 'fucker', 'shitty',
            'fucking', 'shitting', 'damned', 'asshole', 'dumbass', 'jackass'
        ]
        
        text_lower = text.lower()
        return any(term in text_lower for term in forbidden_terms)
    
    def evaluate_response(self, response: Dict[str, Any], golden: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a single response against golden expectations"""
        tips = response.get('tips', [])
        rationale = response.get('rationale', '')
        response_time = response.get('response_time', 0)
        
        # Check tip count
        tip_count_valid = 1 <= len(tips) <= golden['expect']['tips_max']
        
        # Check tip word limits
        tip_words_valid = True
        for tip in tips:
            word_count = len(tip.split())
            if word_count > golden['expect']['max_words_per_tip']:
                tip_words_valid = False
                break
        
        # Check rationale length
        rationale_valid = len(rationale) <= 140
        
        # Check for forbidden terms
        no_forbidden_terms = True
        for tip in tips:
            if self.check_forbidden_terms(tip):
                no_forbidden_terms = False
                break
        if self.check_forbidden_terms(rationale):
            no_forbidden_terms = False
        
        # Overall pass/fail
        passed = tip_count_valid and tip_words_valid and rationale_valid and no_forbidden_terms
        
        return {
            'passed': passed,
            'tip_count_valid': tip_count_valid,
            'tip_words_valid': tip_words_valid,
            'rationale_valid': rationale_valid,
            'no_forbidden_terms': no_forbidden_terms,
            'response_time': response_time,
            'tips': tips,
            'rationale': rationale,
            'tip_count': len(tips),
            'rationale_length': len(rationale)
        }
    
    def run_evaluation(self, dyad: str) -> Tuple[List[Dict[str, Any]], float]:
        """Run evaluation for a dyad"""
        print(f"🧪 Evaluating {dyad} dyad...")
        
        golden_cases = self.load_golden_cases(dyad)
        results = []
        total_time = 0
        
        for i, golden in enumerate(golden_cases, 1):
            print(f"  Test {i}/{len(golden_cases)}...", end=" ")
            
            # Prepare request
            request_data = {
                'dyad': dyad,
                'features': golden['features'],
                'context': golden['context'],
                'metrics': golden.get('metrics', {}),
                'history': []
            }
            
            try:
                # Send request to reasoner
                start_time = time.time()
                response = requests.post(
                    f"{self.reasoner_url}/v1/reason",
                    json=request_data,
                    timeout=30
                )
                request_time = time.time() - start_time
                
                if response.status_code == 200:
                    response_data = response.json()
                    response_data['response_time'] = request_time
                    
                    # Evaluate response
                    eval_result = self.evaluate_response(response_data, golden)
                    eval_result['test_case'] = i
                    eval_result['dyad'] = dyad
                    eval_result['golden'] = golden
                    
                    results.append(eval_result)
                    total_time += request_time
                    
                    status = "✅ PASS" if eval_result['passed'] else "❌ FAIL"
                    print(f"{status} ({request_time:.2f}s)")
                    
                else:
                    print(f"❌ HTTP {response.status_code}")
                    results.append({
                        'passed': False,
                        'test_case': i,
                        'dyad': dyad,
                        'error': f"HTTP {response.status_code}",
                        'response_time': request_time
                    })
                    
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                results.append({
                    'passed': False,
                    'test_case': i,
                    'dyad': dyad,
                    'error': str(e),
                    'response_time': 0
                })
        
        return results, total_time
    
    def generate_report(self, all_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate Markdown evaluation report"""
        report = []
        report.append("# Reasoner Evaluation Report")
        report.append("")
        
        total_tests = 0
        total_passed = 0
        total_time = 0
        
        for dyad, results in all_results.items():
            passed = sum(1 for r in results if r.get('passed', False))
            total = len(results)
            avg_time = sum(r.get('response_time', 0) for r in results) / total if total > 0 else 0
            
            total_tests += total
            total_passed += passed
            total_time += sum(r.get('response_time', 0) for r in results)
            
            pass_rate = (passed / total) * 100 if total > 0 else 0
            
            report.append(f"## {dyad.title()} Dyad")
            report.append("")
            report.append(f"- **Tests**: {total}")
            report.append(f"- **Passed**: {passed}")
            report.append(f"- **Pass Rate**: {pass_rate:.1f}%")
            report.append(f"- **Avg Latency**: {avg_time:.2f}s")
            report.append("")
            
            # Detailed results
            report.append("### Detailed Results")
            report.append("")
            report.append("| Test | Status | Tips | Rationale | Latency |")
            report.append("|------|--------|------|-----------|---------|")
            
            for result in results:
                test_num = result.get('test_case', '?')
                status = "✅ PASS" if result.get('passed', False) else "❌ FAIL"
                tip_count = result.get('tip_count', 0)
                rationale_len = result.get('rationale_length', 0)
                latency = result.get('response_time', 0)
                
                report.append(f"| {test_num} | {status} | {tip_count} | {rationale_len} chars | {latency:.2f}s |")
            
            report.append("")
            
            # Failure analysis
            failures = [r for r in results if not r.get('passed', False)]
            if failures:
                report.append("### Failures")
                report.append("")
                for failure in failures:
                    test_num = failure.get('test_case', '?')
                    report.append(f"**Test {test_num}**:")
                    
                    if not failure.get('tip_count_valid', True):
                        report.append("- ❌ Invalid tip count")
                    if not failure.get('tip_words_valid', True):
                        report.append("- ❌ Tip exceeds word limit")
                    if not failure.get('rationale_valid', True):
                        report.append("- ❌ Rationale exceeds character limit")
                    if not failure.get('no_forbidden_terms', True):
                        report.append("- ❌ Contains forbidden terms")
                    if 'error' in failure:
                        report.append(f"- ❌ Error: {failure['error']}")
                    
                    report.append("")
        
        # Overall summary
        overall_pass_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        overall_avg_time = total_time / total_tests if total_tests > 0 else 0
        
        report.append("## Overall Summary")
        report.append("")
        report.append(f"- **Total Tests**: {total_tests}")
        report.append(f"- **Total Passed**: {total_passed}")
        report.append(f"- **Overall Pass Rate**: {overall_pass_rate:.1f}%")
        report.append(f"- **Overall Avg Latency**: {overall_avg_time:.2f}s")
        report.append("")
        
        if overall_pass_rate >= 90:
            report.append("🎉 **EVALUATION PASSED** - Pass rate ≥ 90%")
        else:
            report.append("❌ **EVALUATION FAILED** - Pass rate < 90%")
        
        return "\n".join(report)
    
    def run_all_evaluations(self) -> bool:
        """Run evaluations for all dyads"""
        print("🚀 Starting Reasoner Evaluation")
        print("=" * 40)
        
        all_results = {}
        dyads = ['tantrum', 'meal', 'night']
        
        for dyad in dyads:
            try:
                results, _ = self.run_evaluation(dyad)
                all_results[dyad] = results
            except Exception as e:
                print(f"❌ Failed to evaluate {dyad}: {e}")
                return False
        
        # Generate and print report
        report = self.generate_report(all_results)
        print("\n" + "=" * 40)
        print("📊 EVALUATION REPORT")
        print("=" * 40)
        print(report)
        
        # Calculate overall pass rate
        total_tests = sum(len(results) for results in all_results.values())
        total_passed = sum(
            sum(1 for r in results if r.get('passed', False))
            for results in all_results.values()
        )
        
        overall_pass_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 Overall Pass Rate: {overall_pass_rate:.1f}%")
        
        return overall_pass_rate >= 90

def main():
    """Main evaluation entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate reasoner output quality")
    parser.add_argument(
        "--reasoner-url",
        default="http://localhost:5001",
        help="Reasoner service URL (default: http://localhost:5001)"
    )
    
    args = parser.parse_args()
    
    evaluator = ReasonerEvaluator(args.reasoner_url)
    
    try:
        success = evaluator.run_all_evaluations()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Evaluation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Evaluation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 