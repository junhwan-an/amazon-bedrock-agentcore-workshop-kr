# Strands Agent로 Evaluation 실행하기

## 개요

이 튜토리얼은 [Strands Agents SDK](https://strandsagents.com/)를 사용하여 구축된 agent와 함께 AgentCore Evaluations를 사용하는 방법을 보여줍니다. 내장 및 커스텀 evaluator를 사용하여 Strands agent의 성능을 평가하고 모니터링하기 위해 on-demand 및 online evaluation을 실행하는 방법을 배웁니다.

## 학습 내용

- 특정 Strands agent trace에 대한 on-demand evaluation 실행
- Strands agent의 지속적인 모니터링을 위한 online evaluation 설정
- AgentCore Starter Toolkit을 사용한 evaluation 관리
- agent 품질 개선을 위한 evaluation 결과 분석

## 사전 요구사항

이 튜토리얼을 시작하기 전에 다음을 확인하세요:
- [Tutorial 00: Prerequisites](../../00-prereqs)를 완료하고 Strands agent(`eval_agent_strands.py`)를 생성했는지 확인
- [Tutorial 01: Creating Custom Evaluators](../../01-creating-custom-evaluators)를 완료하고 커스텀 evaluator를 생성했는지 확인
- AgentCore Runtime에 Strands agent가 배포되어 있는지 확인
- agent를 호출하여 trace가 포함된 세션을 하나 이상 생성했는지 확인
- Python 3.10+ 설치
- 적절한 권한으로 AWS 자격 증명 구성

## 튜토리얼 구조

### [01-on-demand-eval.ipynb](01-on-demand-eval.ipynb)

**튜토리얼 유형:** on-demand evaluator(내장 및 커스텀)를 사용한 Strands agent 평가

**학습 내용:**
- 배포된 Strands agent에서 세션 및 trace 정보를 검색하는 방법
- Starter Toolkit을 사용하여 AgentCore Evaluations 클라이언트 초기화
- 특정 trace 또는 세션에 대한 on-demand evaluation 실행
- 내장 evaluator(예: `Builtin.Correctness`, `Builtin.Helpfulness`) 및 커스텀 evaluator 모두 사용
- 점수, 설명 및 토큰 사용량을 포함한 evaluation 결과 해석

**주요 개념:**
- **타겟 평가**: 세션 또는 trace ID를 제공하여 특정 상호작용 평가
- **동기 실행**: evaluation 요청에 대한 즉각적인 결과 획득
- **유연한 Evaluator 선택**: 동일한 trace에 여러 evaluator 적용
- **조사 도구**: 특정 상호작용 분석 또는 수정 사항 검증에 적합

### [02-online-eval.ipynb](02-online-eval.ipynb)

**튜토리얼 유형:** online evaluator(내장 및 커스텀)를 사용한 Strands agent 평가

**학습 내용:**
- Strands agent에 대한 online evaluation 구성 생성
- 샘플링 비율 및 필터링 규칙 구성
- 내장 및 커스텀 evaluator를 사용한 지속적인 evaluation 설정
- CloudWatch 대시보드에서 evaluation 결과 모니터링
- online evaluation 구성 관리(활성화, 비활성화, 업데이트, 삭제)

**주요 개념:**
- **지속적인 모니터링**: 상호작용이 발생할 때 agent 성능을 자동으로 평가
- **샘플링 기반**: 백분율 기반 샘플링 구성(예: 세션의 10% 평가)
- **실시간 인사이트**: 품질 추세 추적 및 조기 회귀 감지
- **프로덕션 준비**: 최소한의 성능 영향으로 확장 가능하도록 설계

## Strands Agent 아키텍처

이 튜토리얼에서 사용되는 Strands agent는 다음을 포함합니다:

**코드 실행 기능:**
- AgentCore Code Interpreter를 사용하여 Python 코드 실행
- 수학 계산 및 데이터 분석 처리

**Memory 통합:**
- 사용자 사실 및 선호도 저장
- 개인화된 응답을 위한 관련 컨텍스트 검색

**Model:**
- Amazon Bedrock의 Anthropic Claude Haiku 4.5

**Observability:**
- AgentCore Runtime을 통한 자동 OTEL 계측
- CloudWatch GenAI Observability Dashboard에서 사용 가능한 trace

## Strands Agent와 Evaluation이 작동하는 방식

1. **Agent 호출**: Strands agent가 사용자 요청을 처리
2. **Trace 생성**: AgentCore Observability가 OTEL trace를 자동으로 캡처
3. **Trace 저장**: trace가 CloudWatch Log 그룹에 저장
4. **Evaluation**:
   - **On-demand**: 평가할 특정 세션/trace를 선택
   - **Online**: AgentCore가 구성에 따라 자동으로 샘플링 및 평가
5. **결과 분석**: CloudWatch에서 점수, 설명 및 추세 확인

## AgentCore Starter Toolkit 사용

두 노트북 모두 **AgentCore Starter Toolkit**을 사용하여 evaluation 워크플로를 단순화합니다:

```python
from bedrock_agentcore_starter_toolkit import Evaluations

# Evaluations 클라이언트 초기화
evaluations = Evaluations()

# On-demand evaluation: 특정 세션에 대해 즉시 평가 실행
result = evaluations.evaluate_session(
    session_id="your-session-id",
    evaluator_ids=["Builtin.Correctness", "your-custom-evaluator-id"]  # 내장 및 커스텀 evaluator 조합 가능
)

# Online evaluation: 지속적인 모니터링을 위한 자동 평가 설정
config = evaluations.create_online_evaluation(
    config_name="your-config-name",
    sampling_percentage=100,  # 100%의 세션을 평가 (프로덕션에서는 낮은 비율 권장)
    evaluator_ids=["Builtin.Helpfulness", "your-custom-evaluator-id"]
)
```

## 예상 결과

이 튜토리얼을 완료하면 다음을 수행할 수 있습니다:
- on-demand evaluation을 사용하여 특정 Strands agent 상호작용 평가
- 프로덕션 Strands agent에 대한 지속적인 품질 모니터링 설정
- evaluation 결과를 분석하여 개선 영역 식별
- 내장 및 커스텀 evaluator를 효과적으로 사용
- 시간 경과에 따른 agent 품질 추세 모니터링

## 다음 단계

이 Strands 관련 튜토리얼을 완료한 후:
- [LangGraph 예제](../02-langgraph/)를 탐색하여 다양한 프레임워크에서 evaluation이 작동하는 방식 확인
- 고급 evaluation 기술을 위해 [Tutorial 03: Advanced](../../03-advanced)로 진행
- CloudWatch GenAI Observability Dashboard에서 evaluation 결과 검토

