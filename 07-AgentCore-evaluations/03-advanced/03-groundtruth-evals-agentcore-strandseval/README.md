# 오프라인 멀티 세션 Evaluation

AgentCore Observability의 과거 trace를 사용하여 배포된 AI agent 세션을 평가합니다. 이 도구는 agent의 observability 로그에서 trace를 가져와 Strands Evals 형식으로 변환하고, evaluation을 실행한 후 대시보드 상관관계를 위해 원본 trace ID와 함께 결과를 AgentCore Observability에 다시 기록합니다.

## 사용 사례

AgentCore Observability 계측이 적용된 AI agent가 배포되어 있을 때, 이 도구를 사용하면 다음을 수행할 수 있습니다:

- 과거 agent 상호작용에 대한 오프라인 evaluation 실행
- 업데이트된 rubric으로 낮은 점수를 받은 세션 재평가
- 기존 trace에 대해 새로운 evaluator 구성 테스트
- agent 출력을 ground truth(SME의 예상 응답)와 비교
- agent 변경 사항이 알려진 정상 동작을 손상시키지 않도록 회귀 테스트 수행
- AgentCore Observability 대시보드에서 원본 trace와 evaluation 결과 상관관계 분석

## 작동 방식

1. **Session Discovery**: 시간 범위 또는 기존 evaluation 점수로 agent 세션을 찾기 위해 AgentCore Observability 쿼리
2. **Trace Fetching**: CloudWatch Logs Insights를 사용하여 각 세션의 span 검색
3. **Format Conversion**: AgentCore Observability span을 Strands Evals Session 형식(tool 호출, agent 응답, trajectory)으로 매핑
4. **Evaluation**: 두 가지 접근 방식 중 하나를 사용하여 evaluator 실행:
   - **Rubric 기반**: 정의한 기준에 따라 점수 부여 (유연하고 정성적)
   - **Ground Truth**: 예상 출력과 비교 (참조 기반, 회귀 테스트)
5. **Result Logging**: 대시보드 상관관계를 위해 원본 trace ID와 함께 EMF 형식으로 evaluation 결과 전송

## Notebook 워크플로우

![Notebook Workflow](images/notebook_workflow.svg)

## Agent Evaluation 이해하기

Agent evaluation은 전통적인 소프트웨어 테스트를 넘어섭니다. 단위 테스트가 결정론적 출력을 검증하는 반면, agent는 정성적 평가가 필요한 가변적인 응답을 생성합니다. 체계적인 evaluation은 실패 패턴을 식별하고, 시간 경과에 따른 개선을 측정하며, prompt와 tool을 반복하면서 일관된 품질을 보장하는 데 도움이 됩니다.

### 두 가지 보완적 접근 방식

**AgentCore Evaluations**와 **Strands Evals**는 함께 작동하여 포괄적인 agent 품질 관리를 제공합니다:

| | AgentCore Evaluations | Strands Evals |
|---|---|---|
| **목적** | 지속적인 실시간 품질 모니터링 | 오프라인 배치 evaluation 및 실험 |
| **사용 사례** | 프로덕션 모니터링, 품질 저하 알림 | 테스트, 회귀 분석, rubric 개발 |
| **실행** | 완전 관리형, 실시간 상호작용 샘플링 | 온디맨드, 과거 trace에서 실행 |
| **내장 Evaluator** | 정확성, 유용성, tool 선택 정확도, 안전성, 목표 성공률, 컨텍스트 관련성 | 출력, trajectory, 유용성, 충실도, 목표 성공률, tool 정확도 |
| **커스텀 Evaluator** | 커스텀 prompt를 사용한 model 기반 점수 부여 | 코드 기반 또는 LLM 기반 evaluator |

**AgentCore Evaluations**는 실제 동작을 기반으로 agent 성능을 지속적으로 모니터링하는 완전 관리형 서비스입니다. 실시간 상호작용을 샘플링하고, 내장 또는 커스텀 evaluator에 대해 점수를 매기며, observability 인사이트와 함께 CloudWatch에서 결과를 시각화합니다. 만족도 감소 또는 정중함 점수 하락과 같이 품질 메트릭이 임계값 아래로 떨어질 때 알림을 설정하여 문제를 더 빠르게 감지하고 해결할 수 있습니다.

**Strands Evals**는 여러 evaluation 유형, 멀티턴 대화를 위한 동적 시뮬레이터, OpenTelemetry를 통한 trace 기반 evaluation, 자동화된 실험 생성, 그리고 모든 라이브러리의 커스텀 evaluator를 지원하는 확장 가능한 아키텍처를 제공하는 포괄적인 evaluation 프레임워크입니다. 전체 기능은 [Strands Evals 문서](https://strandsagents.com/latest/documentation/docs/user-guide/evals-sdk/quickstart/)를 참조하세요.

### 이 프로젝트

이 프로젝트는 **AgentCore Observability**에서 수집한 trace의 **오프라인 evaluation을 위해 Strands Evals**를 사용하며, 두 가지 일반적인 패턴을 보여줍니다:

- **Output Quality**: agent의 응답이 사용자의 요청을 올바르고 완전하게 처리하는가? 생성 방법에 관계없이 최종 답변을 평가합니다.

- **Trajectory Quality**: agent가 tool을 효과적으로 사용했는가? agent가 적절한 tool을 선택하고, 효율적으로 사용하며, 논리적인 순서를 따랐는지 평가합니다.

결과는 원본 trace ID와 함께 AgentCore Observability에 다시 기록되어 AgentCore Evaluations 결과와 함께 대시보드에서 상관관계를 분석할 수 있습니다.

## Strands Evals 개념

이 도구는 AI agent를 위한 범용 evaluation 프레임워크인 [Strands Evals](https://github.com/strands-agents/strands-evals)를 사용합니다. Strands Evals는 LLM을 심사위원으로 사용하여 사람이 정의한 기준에 따라 agent 동작을 점수화합니다. 이 프레임워크는 설명과 함께 0.0에서 1.0 척도로 품질을 정량화하여 agent 응답의 고유한 가변성을 처리합니다.

**핵심 인사이트**: Agent는 "정확한" 또는 "부정확한" 답변을 생성하지 않습니다—더 나은 또는 더 나쁜 응답을 생성합니다. Strands Evals는 주관적인 품질 평가를 측정 가능하고 일관된 메트릭으로 전환합니다.

핵심 개념을 이해하면 evaluation을 효과적으로 커스터마이즈하는 데 도움이 됩니다.

**Session**: 잠재적으로 여러 번의 왕복 교환을 포함하는 완전한 사용자 대화를 나타냅니다. AgentCore Observability에서 session은 `session.id`로 관련 상호작용을 그룹화합니다.

**Trace**: 단일 사용자 요청과 해당 요청을 이행하기 위해 수행된 모든 tool 호출을 포함한 agent의 완전한 응답입니다. 각 trace에는 AgentCore Observability와 상관관계가 있는 고유한 `trace_id`가 있습니다.

**Case**: 입력(사용자 prompt), 실제 출력(agent 응답) 및 메타데이터(trace_id, tool trajectory)를 포함하는 evaluation을 위한 테스트 케이스입니다. Case는 evaluator가 점수를 매기는 대상입니다.

**Experiment**: 하나 이상의 evaluator와 쌍을 이루는 case 모음입니다. experiment를 실행하면 각 case에 대한 점수와 설명이 생성됩니다.

## Evaluation 접근 방식

Strands Evals는 여러 evaluation 접근 방식을 지원하는 확장 가능한 LLM 기반 evaluation 프레임워크입니다. 정확한 문자열 매칭 대신 LLM을 심사위원으로 사용하여 agent 출력을 점수화합니다. 이 프레임워크는 유연성을 위해 설계되었으며 거의 모든 evaluation 유형을 구현할 수 있습니다.

**두 가지 기본 evaluation 접근 방식:**

| 접근 방식 | 설명 | 사용 시기 |
|----------|-------------|----------|
| **Rubric 기반** | 정의한 기준에 따라 LLM이 심사 | 유연하고 정성적인 평가를 원할 때 |
| **Ground Truth** | 알려진 정답과 비교 | 측정할 예상 출력이 있을 때 |

이 프로젝트는 별도의 notebook에서 두 가지 접근 방식을 모두 보여줍니다.

### Rubric 기반 Evaluation (Notebook 02)

rubric에서 evaluation 기준을 정의하면 LLM이 기준에 따라 각 응답을 심사합니다. 이 접근 방식은 응답이 다양할 수 있지만 여전히 다른 방식으로 "좋을" 수 있을 때 이상적입니다.

**OutputEvaluator**: agent 응답의 품질을 평가합니다. 좋은 응답을 만드는 요소(관련성, 정확성, 완전성)를 설명하는 rubric을 제공하면 evaluator가 LLM을 사용하여 설명과 함께 0.0에서 1.0까지 출력을 점수화합니다.

**TrajectoryEvaluator**: agent가 tool을 사용한 방법을 평가합니다. 좋은 tool 사용 패턴(적절한 선택, 효율성, 논리적 순서)을 설명하는 rubric을 제공하면 evaluator가 0.0에서 1.0까지 tool trajectory를 점수화합니다.

### Ground Truth Evaluation (Notebook 03)

실제 agent 출력을 미리 정의된 예상 응답과 비교합니다. 이 접근 방식은 회귀 테스트, 벤치마킹 및 알려진 정답이 있는 경우에 이상적입니다.

evaluator는 실제와 예상을 비교하고 agent의 출력이 Subject Matter Expert(SME)가 정의한 올바른 응답과 얼마나 잘 일치하는지 점수를 매깁니다. 자세한 내용은 [Ground Truth Evaluation](#ground-truth-evaluation) 섹션을 참조하세요.

### 확장성

Strands Evals 프레임워크는 이 프로젝트가 보여주는 것 이상의 커스텀 evaluator를 지원합니다. 점수 부여 기준으로 표현할 수 있는 모든 evaluation—사실 정확성, 안전성, 도메인별 품질 검사, 규정 준수 요구 사항—은 LLM-as-judge 접근 방식을 사용하여 구현할 수 있습니다.

**Rubric 작동 방식**: rubric은 agent의 출력과 함께 LLM에 전송됩니다. LLM은 심사위원 역할을 하여 기준을 적용하여 점수와 설명을 생성합니다. 명확한 점수 부여 지침이 있는 잘 작성된 rubric은 더 일관된 evaluation을 생성합니다.

## Ground Truth Evaluation

Ground truth evaluation은 agent 출력을 미리 정의된 예상 응답과 비교합니다. 이는 특정 쿼리에 대해 알려진 정답이 있고 agent가 이와 얼마나 가깝게 일치하는지 측정하려는 경우에 유용합니다.

![Ground Truth Flow](images/ground_truth_flow.svg)

**핵심 개념:**
- **session_id**: 단일 사용자 세션의 모든 trace를 그룹화
- **trace_id**: 세션 내 각 개별 상호작용(사용자 prompt + agent 응답)을 식별

**두 파일 접근 방식**: ground truth notebook은 동일한 `session_id`를 공유하는 두 개의 파일을 사용합니다:

1. **Trace 파일** (`demo_traces.json`): CloudWatch의 실제 agent 출력 포함
   ```json
   {
     "session_id": "5B467129-E54A-4F70-908D-CB31818004B5",
     "traces": [
       {
         "trace_id": "693cb6c4e931",
         "user_prompt": "What is the best route for a NZ road trip?",
         "actual_output": "Based on the search results...",
         "actual_trajectory": ["web_search"]
       },
       {
         "trace_id": "693cb6fa87aa",
         "user_prompt": "Should I visit North or South Island?",
         "actual_output": "Here's how the islands compare...",
         "actual_trajectory": ["web_search"]
       }
     ]
   }
   ```

2. **Ground truth 파일** (`demo_ground_truth.json`): SME가 생성한 예상 출력
   ```json
   {
     "session_id": "5B467129-E54A-4F70-908D-CB31818004B5",
     "ground_truth": [
       {
         "trace_id": "693cb6c4e931",
         "expected_output": "Response should mention Milford Road, Southern Scenic Route...",
         "expected_trajectory": ["web_search"]
       },
       {
         "trace_id": "693cb6fa87aa",
         "expected_output": "Response should compare both islands...",
         "expected_trajectory": ["web_search"]
       }
     ]
   }
   ```

**작동 방식:**
1. Notebook이 CloudWatch에서 trace를 가져옴 (또는 데모 파일 로드)
2. SME가 각 `trace_id`에 대한 예상 출력으로 ground truth 파일 생성
3. Notebook이 `trace_id`로 병합하여 실제와 예상을 쌍으로 연결
4. Evaluator가 각 쌍에 점수 부여

**데모 모드**: 자체 CloudWatch 데이터에 연결하기 전에 제공된 예제 파일을 사용하여 테스트하려면 `USE_DEMO_MODE = True`로 실행하세요.

## 데이터 흐름

Evaluation 파이프라인은 AgentCore Observability trace를 점수가 매겨진 결과로 변환합니다:

![Evaluation Pipeline](images/evaluation_pipeline.svg)

## 프로젝트 구조

```
01_session_discovery.ipynb        - Notebook 1: 세션 발견
02_multi_session_analysis.ipynb   - Notebook 2: 커스텀 rubric으로 평가
03_ground_truth_evaluation.ipynb  - Notebook 3: ground truth에 대해 평가
demo_traces.json                  - 예제 trace 데이터 (데모 모드용)
demo_ground_truth.json            - 예제 ground truth 기대값 (데모 모드용)
config.py                         - 중앙 집중식 구성
requirements.txt                  - Python 종속성
utils/
  __init__.py                     - 모듈 내보내기
  cloudwatch_client.py            - CloudWatch Logs Insights 쿼리 클라이언트
  constants.py                    - 상수 및 evaluator 구성
  evaluation_cloudwatch_logger.py - 원본 trace ID를 보존하는 EMF 로거
  models.py                       - 데이터 모델 (Span, TraceData, SessionInfo)
  session_mapper.py               - AgentCore Observability span을 Strands Evals Session으로 매핑
```

## 빠른 시작

### 1. 구성

AWS 설정으로 `config.py`를 편집하세요:

```python
AWS_REGION = "us-east-1"
AWS_ACCOUNT_ID = "123456789012"
SOURCE_LOG_GROUP = "your-agent-log-group"
EVAL_RESULTS_LOG_GROUP = "your-eval-log-group"
EVALUATION_CONFIG_ID = "your-evaluation-config-id"
SERVICE_NAME = "your-service-name"
```

### 2. 세션 발견

`01_session_discovery.ipynb` 실행:
- 시간 기반 발견(시간 창의 모든 세션) 또는 점수 기반 발견(evaluation 점수별 세션) 선택
- 발견된 세션 미리보기
- evaluation notebook을 위해 JSON으로 저장

### 3. 세션 평가 (하나의 경로 선택)

**옵션 A: 커스텀 Rubric** - `02_multi_session_analysis.ipynb` 실행:
- 발견된 세션 로드 (또는 커스텀 세션 ID 제공)
- 사용 사례에 맞게 evaluator rubric 커스터마이즈
- evaluation 실행 및 결과 보기
- 결과는 원본 trace ID와 함께 AgentCore Observability에 기록됨

**옵션 B: Ground Truth** - `03_ground_truth_evaluation.ipynb` 실행:
- agent 출력을 미리 정의된 예상 응답과 비교
- 평가할 알려진 정답이 있을 때 유용
- 예제 파일(`demo_traces.json`, `demo_ground_truth.json`)을 사용한 데모 모드 지원
- `trace_id`로 trace와 ground truth 병합

## 구성 참조

모든 설정은 `config.py`에 있습니다. 값을 직접 편집하세요.

| 변수 | 설명 |
|----------|-------------|
| `AWS_REGION` | AWS 리전 (예: us-east-1) |
| `AWS_ACCOUNT_ID` | AWS 계정 ID |
| `SOURCE_LOG_GROUP` | AgentCore Observability 로그 그룹 이름 |
| `EVAL_RESULTS_LOG_GROUP` | Evaluation 결과 로그 그룹 이름 |
| `EVALUATION_CONFIG_ID` | AgentCore Observability evaluation 구성 ID |
| `SERVICE_NAME` | CloudWatch 로깅을 위한 서비스 이름 |
| `EVALUATOR_NAME` | 점수 기반 발견을 위한 evaluator 이름 |
| `LOOKBACK_HOURS` | 세션을 찾기 위해 되돌아볼 시간 (기본값: 72) |
| `MAX_SESSIONS` | 발견할 최대 세션 수 (기본값: 100) |
| `MIN_SCORE` / `MAX_SCORE` | 점수 기반 발견을 위한 점수 필터 |
| `MAX_CASES_PER_SESSION` | 세션당 평가할 최대 trace 수 (기본값: 10) |

## 커스터마이징

### Evaluator Rubric

분석 notebook에서 평가 기준에 맞게 rubric을 커스터마이즈하세요:

```python
output_rubric = """
다음을 기반으로 agent의 응답을 평가하세요:
1. 관련성: 사용자의 질문을 다루는가?
2. 정확성: 정보가 정확한가?
...
"""
```

### Evaluator 이름

CloudWatch 메트릭을 위한 커스텀 evaluator 이름 설정:

```python
OUTPUT_EVALUATOR_NAME = "Custom.YourOutputEvaluator"
TRAJECTORY_EVALUATOR_NAME = "Custom.YourTrajectoryEvaluator"
```

### Evaluation Config ID

AgentCore Observability evaluation 구성과 일치하도록 `config.py`에서 evaluation config ID를 설정하세요:

```python
EVALUATION_CONFIG_ID = "your-evaluation-config-id"
```

## 요구 사항

- Python 3.9+
- CloudWatch Logs 액세스 권한이 있는 AWS 자격 증명
- `strands-evals` 패키지
- `boto3`
