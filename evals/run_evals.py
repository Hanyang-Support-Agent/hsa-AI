import json
import requests
import time
from typing import List, Dict, Any

# API Configuration
# (나중에 백엔드 연동 시 이 주소 한 줄만 진짜 주소로 교체하시면 됩니다!)
API_ENDPOINT = "http://localhost:8000/api/v1/inquiries/process"
TEST_DATA_PATH = "evals/tasks.json"

def load_test_cases(file_path: str) -> List[Dict[str, Any]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Test data file not found at: {file_path}")
        return []

def verify_response_details(actual: Dict[str, Any], expected: Dict[str, Any]) -> List[str]:
    errors = []

    if actual.get("status") != expected.get("status"):
        errors.append(f"최상위 status 불일치 (기대치: {expected.get('status')}, 실제: {actual.get('status')})")

    actual_data = actual.get("data") or {}
    expected_data = expected.get("data") or {}

    if expected_data:
        core_fields = ["autoReplyAvailable", "needsAdminReview", "riskTags", "usedSources"]
        
        for field in core_fields:
            actual_val = actual_data.get(field)
            expected_val = expected_data.get(field)
            
            if isinstance(expected_val, list):
                if sorted(actual_val or []) != sorted(expected_val or []):
                    errors.append(f"data.{field} 불일치 (기대치: {expected_val}, 실제: {actual_val})")
            else:
                if actual_val != expected_val:
                    errors.append(f"data.{field} 불일치 (기대치: {expected_val}, 실제: {actual_val})")

    expected_error = expected.get("error")
    if expected_error:
        actual_error = actual.get("error") or {}
        if actual_error.get("code") != expected_error.get("code"):
            errors.append(f"error.code 불일치 (기대치: {expected_error.get('code')}, Referee: {actual_error.get('code')})")

    return errors

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
        
        actual_response = None 
        
        try:
            # 1. 실제 API 요청 및 응답 시간 계산 (정상화 완료)
            start_time = time.time()
            response = requests.post(API_ENDPOINT, json=task["input"], timeout=30)
            latency = round(time.time() - start_time, 2)
            actual_response = response.json()
            
            # 2. 정밀 확장 검증 로직 적용
            validation_errors = verify_response_details(actual_response, task["expected"])
            is_passed = (len(validation_errors) == 0)
            
            if is_passed:
                result_label = "✅ PASS"
                summary["pass"] += 1 
            else:
                result_label = "❌ FAIL"
                summary["fail"] += 1

            print(f"Result: {result_label} | Latency: {latency}s")
            
            if validation_errors:
                print("⚠️  Detail Errors:")
                for err in validation_errors:
                    print(f"   - {err}")
            
            # 3. 데이터 안전하게 추출 검증
            if isinstance(actual_response, dict):
                data_part = actual_response.get("data")
                if data_part and isinstance(data_part, dict):
                    draft = data_part.get("draftAnswer") or "N/A (Needs Review)"
                    reason = data_part.get("reason", "No reason provided")
                    print(f"AI Response: {str(draft)[:60]}...")
                    print(f"Reason: {reason}")
                else:
                    error_info = actual_response.get("error") or {}
                    if isinstance(error_info, dict):
                        print(f"⚠️ Server Info: {error_info.get('message', 'No data field in response')}")
                    else:
                        print(f"⚠️ Server Info: {error_info}")
            else:
                print(f"⚠️ Raw Server Response (Not JSON Object): {actual_response}")

        except Exception as e:
            # 주소가 틀려 404/JSON 파싱 에러가 나더라도 스크립트가 뻗지 않고 FAIL 처리 후 다음 테스크로 넘어가도록 방어
            print(f"❌ Critical Error: {str(e)}")
            summary["fail"] += 1

        print("-" * 60)

    print(f"\n🏁 Evaluation Completed.")
    print(f"📊 Summary: PASS {summary['pass']} / FAIL {summary['fail']}")
    print("=" * 60)

if __name__ == "__main__":
    run_evaluation()