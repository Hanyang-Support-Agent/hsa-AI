import json
import requests
import time
from typing import List, Dict, Any

# API Configuration
API_ENDPOINT = "http://localhost:8000/api/v1/inquiries/process"
TEST_DATA_PATH = "evals/tasks.json"

def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
    """
    지정된 경로에서 테스트 케이스 파일(JSON)을 로드합니다.
    
    Args:
        file_path (str): 테스트 데이터 파일의 상대 또는 절대 경로.
        
    Returns:
        List[Dict]: 로드된 테스트 케이스 리스트.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Test data file not found at: {file_path}")
        return []

def run_evaluation():
    """
    hsa-AI API 엔드포인트에 대한 자동화된 품질 검증을 수행합니다.
    각 테스트 케이스의 응답 규격 및 기대 결과(Expected Status)를 비교 분석합니다.
    """
    tasks = load_test_cases(TEST_DATA_PATH)
    if not tasks:
        return

    print("=" * 60)
    print(f"🚀 hsa-AI Quality Evaluation Suite - Total: {len(tasks)} cases")
    print("=" * 60)

    summary = {"pass": 0, "fail": 0}

    for task in tasks:
        task_id = task.get("task_id", "N/A")
        description = task.get("description", "No description")
        
        print(f"\n[TestCase] {task_id}")
        print(f"Description: {description}")

        # API Request Execution
        try:
            start_time = time.time()
            response = requests.post(API_ENDPOINT, json=task["input"], timeout=10)
            latency = round(time.time() - start_time, 2)
            
            actual_response = response.json()
            expected_status = task["expected"].get("status")
            actual_status = actual_response.get("status")

            # Validation Logic
            is_passed = (actual_status == expected_status)
            result_label = "✅ PASS" if is_passed else "❌ FAIL (Status Mismatch)"
            
            if is_passed: summary["pass"] += 1 
            else: summary["fail"] += 1

            print(f"Result: {result_label} | Latency: {latency}s")
            
            # AI Output Monitoring
            draft = actual_response.get("data", {}).get("draftAnswer", "None")
            print(f"AI Response: {draft[:60]}...")

        except Exception as e:
            print(f"❌ Critical Error: Failed to connect or parse response. ({e})")
            summary["fail"] += 1

        print("-" * 60)

    # Final Summary Report
    print(f"\n🏁 Evaluation Completed.")
    print(f"📊 Summary: PASS {summary['pass']} / FAIL {summary['fail']}")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()
