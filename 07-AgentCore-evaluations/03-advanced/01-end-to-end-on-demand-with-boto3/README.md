# AgentCore Evaluation 유틸리티

CloudWatch 추적 데이터를 추출하고 AgentCore Evaluation DataPlane API를 사용하여 agent 세션을 평가하는 Python 유틸리티입니다.

## 설치

```bash
pip install -r requirements.txt
```

## 구성

CloudWatch Logs 및 AgentCore Evaluation API에 대한 액세스 권한이 있는 AWS 자격 증명을 구성합니다:

```bash
aws configure
```

또는 환경 변수를 설정합니다:

```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"
```

## 사용법

```python
from utils import EvaluationClient

# 클라이언트 초기화
client = EvaluationClient(region="us-east-1")

# 세션 평가 실행
results = client.evaluate_session(
    session_id="your-session-id",
    evaluator_ids=["Builtin.Helpfulness"],  # 내장 평가자 ID 목록
    agent_id="your-agent-id",
    region="us-east-1"
)

# 평가 결과 출력
for result in results.results:
    print(f"{result.evaluator_name}: {result.value} - {result.label}")
    print(f"Explanation: {result.explanation}")
```

## 다중 Evaluator 지원

단일 호출로 여러 evaluator를 사용하여 평가합니다:

```python
results = client.evaluate_session(
    session_id="session-id",
    evaluator_ids=["Builtin.Helpfulness", "Builtin.Accuracy", "Builtin.Harmfulness"],  # 여러 평가자를 동시에 사용
    agent_id="agent-id",
    region="us-east-1"
)
```

## 자동 저장 및 메타데이터

입력/출력 파일을 저장하고 실험을 추적합니다:

```python
results = client.evaluate_session(
    session_id="session-id",
    evaluator_ids=["Builtin.Helpfulness"],
    agent_id="agent-id",
    region="us-east-1",
    auto_save_input=True,   # evaluation_input/ 디렉토리에 입력 데이터 저장
    auto_save_output=True,  # evaluation_output/ 디렉토리에 결과 저장
    auto_create_dashboard=True,  # 로컬에서 사용 가능한 HTML 대시보드용 데이터 생성
    metadata={  # 실험 추적을 위한 임의의 메타데이터 전달 가능
        "experiment": "baseline",
        "description": "Initial evaluation run"
    }
)
```

입력 파일에는 정확한 재생을 위해 API로 전송된 span만 포함됩니다. 출력 파일에는 메타데이터가 포함된 전체 결과가 포함됩니다.

## 구현 세부 사항

이 유틸리티는 OpenTelemetry span 및 런타임 로그에 대해 CloudWatch Logs를 쿼리하고, 관련 데이터(gen_ai 속성 및 대화 로그)를 필터링한 다음 evaluation API에 제출합니다. 기본 조회 기간은 7일이며 평가당 최대 1000개 항목입니다.
