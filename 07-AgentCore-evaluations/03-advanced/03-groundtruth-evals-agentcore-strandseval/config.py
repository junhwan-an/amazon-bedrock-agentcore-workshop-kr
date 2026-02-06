"""멀티 세션 평가를 위한 설정.

아래 값들을 AWS 환경과 선호도에 맞게 수정하세요.
"""

import os
from typing import Optional


# =============================================================================
# AWS 설정
# =============================================================================
AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "YOUR_AWS_ACCOUNT_ID"


# =============================================================================
# CloudWatch Log Groups
# =============================================================================

# Agent의 OTEL 트레이스가 저장되는 소스 로그 그룹
SOURCE_LOG_GROUP = "your-source-log-group"

# Evaluation 결과 로그 그룹 (점수 기반 검색 및 결과 로깅용). 아직 생성하지 않았다면 Online Evaluator를 설정하여 생성하세요
# 이것은 /aws/bedrock-agentcore/evaluations/results/ 접두사가 없는 로그 그룹 이름입니다
EVAL_RESULTS_LOG_GROUP = "your-evaluation-log-group"

# Evaluation 결과 로그 그룹의 전체 경로 (위에서 자동 구성됨)
EVAL_RESULTS_LOG_GROUP_FULL = f"/aws/bedrock-agentcore/evaluations/results/{EVAL_RESULTS_LOG_GROUP}"


# =============================================================================
# Evaluation 설정
# =============================================================================

# AgentCore의 Online Evaluation Config ID. 오프라인 평가 결과를
# AgentCore 대시보드와 연관시키는 데 사용됩니다. AgentCore 콘솔의 Online Evaluations에서
# 찾거나 CloudWatch 로그 그룹 이름에서 찾을 수 있습니다 (마지막 대시 뒤의 접미사).
# 예시: 로그 그룹이 "MyAgent-Evaluation-5MB8aF5rLE"인 경우, config ID는 "MyAgent-Evaluation-5MB8aF5rLE"입니다
# 대시보드 시각화를 위해 결과를 CloudWatch에 다시 로깅하려는 경우에만 필요합니다.
EVALUATION_CONFIG_ID = "your-evaluation-config-id"

# 점수 기반 검색을 위한 Evaluator 이름. 기존 평가 결과의 evaluator 이름과
# 일치해야 합니다 (예: "Builtin.Correctness" 또는 "Custom.MyEvaluator")
EVALUATOR_NAME = "Builtin.YourEvaluatorName"

# AgentCore Observability 대시보드에 표시되는 Agent의 서비스 이름.
# CloudWatch > Log groups > agent의 로그 그룹에서 service.name 속성을 확인하세요.
SERVICE_NAME = "your-service-name"


# =============================================================================
# 시간 범위 설정
# =============================================================================

# 세션과 트레이스를 검색할 과거 시간 범위 (시간 단위)
LOOKBACK_HOURS = 72


# =============================================================================
# 세션 검색 설정
# =============================================================================

# 검색할 최대 세션 수
MAX_SESSIONS = 100

# 점수 기반 검색을 위한 점수 임계값 (필터링을 비활성화하려면 None으로 설정)
MIN_SCORE: Optional[float] = None
MAX_SCORE: Optional[float] = 0.5


# =============================================================================
# 처리 설정
# =============================================================================

# 세션당 평가할 최대 케이스 수 (모두 평가하려면 None으로 설정)
MAX_CASES_PER_SESSION: Optional[int] = 10


# =============================================================================
# 파일 경로
# =============================================================================

# 세션 검색 결과를 위한 출력 파일 경로
DISCOVERED_SESSIONS_PATH = "discovered_sessions.json"

# 멀티 세션 평가 결과를 위한 출력 파일 경로
RESULTS_JSON_PATH = "multi_session_results.json"


# =============================================================================
# 헬퍼 함수
# =============================================================================

def setup_cloudwatch_environment() -> None:
    """CloudWatch 로깅을 위한 환경 변수를 설정합니다."""
    os.environ["AWS_REGION"] = AWS_REGION
    os.environ["AWS_DEFAULT_REGION"] = AWS_REGION
    os.environ["AWS_ACCOUNT_ID"] = AWS_ACCOUNT_ID
    os.environ["EVALUATION_RESULTS_LOG_GROUP"] = EVAL_RESULTS_LOG_GROUP
    os.environ["OTEL_RESOURCE_ATTRIBUTES"] = f"service.name={SERVICE_NAME}"
