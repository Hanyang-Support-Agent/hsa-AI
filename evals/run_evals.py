import json
import requests
import time
from typing import List, Dict, Any

# API Configuration
API_ENDPOINT = "http://localhost:8000/api/v1/inquiries/process"
TEST_DATA_PATH = "evals/tasks.json"

def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Test data file not found at: {file_path}")
        return []

def run_evaluation():
    tasks = load_test_cases(TEST_DATA_PATH)
    if not tasks:
        return

    print("=" * 60)
    print(f"🚀 hsa-AI Quality Evaluation Suite - Total: {len(tasks)} cases")
    print("=" * 60)

    summary = {"pass": 0, "fail": 0}

    for task in tasks:
        task_id = task.get("task_id", "N/A")
        print(f"\n[TestCase] {task_id}")
        
        # 1. 초기화 (에러 발생 시 undefined 방지)
        actual_response = None 
        
        try:
            # 2. API 요청 (타임아웃 30초로 넉넉히 설정)
            start_time = time.time()
            response = requests.post(API_ENDPOINT, json=task["input"], timeout=30)
            latency = round(time.time() - start_time, 2)
            
            # 3. JSON 파싱
            actual_response = response.json()
            
            # 4. 검증 로직
            expected_status = task["expected"].get("status")
            actual_status = actual_response.get("status")

            is_passed = (actual_status == expected_status)
            result_label = "✅ PASS" if is_passed else f"❌ FAIL (Expected: {expected_status}, Actual: {actual_status})"
            
            if is_passed: summary["pass"] += 1 
            else: summary["fail"] += 1

            print(f"Result: {result_label} | Latency: {latency}s")
            
            # 5. 데이터 안전하게 추출 (None 체크 강화)
            data_part = actual_response.get("data")
            if data_part:
                draft = data_part.get("draftAnswer") or "N/A (Needs Review)"
                reason = data_part.get("reason", "No reason provided")
                print(f"AI Response: {draft[:60]}...")
                print(f"Reason: {reason}")
            else:
                error_info = actual_response.get("error") or {}
                print(f"⚠️ Server Info: {error_info.get('message', 'No data field in response')}")

        except Exception as e:
            print(f"❌ Critical Error: {str(e)}")
            summary["fail"] += 1

        print("-" * 60)

    print(f"\n🏁 Evaluation Completed.")
    print(f"📊 Summary: PASS {summary['pass']} / FAIL {summary['fail']}")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()
