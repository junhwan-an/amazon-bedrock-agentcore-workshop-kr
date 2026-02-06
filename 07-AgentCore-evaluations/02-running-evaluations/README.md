# Evaluation 실행하기

## 개요

이 튜토리얼에서는 AgentCore Evaluations를 사용하여 on-demand 및 online evaluation 접근 방식을 통해 agent의 성능을 평가하는 방법을 배웁니다. 내장 및 커스텀 evaluator를 적용하여 agent 상호작용을 분석하고 대규모로 품질을 모니터링합니다.

## 학습 내용

- 특정 상호작용에 대한 타겟 평가를 위한 on-demand evaluation 실행
- 지속적인 프로덕션 모니터링을 위한 online evaluation 설정
- Evaluation 결과를 분석하여 agent 품질 개선
- AgentCore Observability trace를 evaluation의 입력으로 사용

## 사전 요구사항

이 튜토리얼을 시작하기 전에 다음을 완료해야 합니다:
- [Tutorial 00: Prerequisites](../00-prereqs) 완료 - 샘플 agent 생성 (Strands 및/또는 LangGraph)
- [Tutorial 01: Creating Custom Evaluators](../01-creating-custom-evaluators) 완료 - 커스텀 evaluator 생성
- Observability가 활성화된 AgentCore Runtime에 agent 배포
- AgentCore Observability에서 trace가 포함된 세션을 최소 하나 이상 생성

## Evaluation 유형

### On-demand Evaluations

On-demand evaluation은 선택한 span, trace 또는 세션 세트를 직접 분석하여 특정 agent 상호작용을 평가하는 유연한 방법을 제공합니다.

**주요 특징:**
- **타겟 평가**: span, trace 또는 세션 ID를 제공하여 특정 상호작용 평가
- **동기 실행**: evaluation 요청에 대한 즉각적인 결과 획득
- **유연한 범위**: 단일 span, 완전한 trace 또는 전체 세션 평가
- **조사 도구**: 특정 고객 상호작용 분석 또는 수정 사항 검증에 완벽

**On-demand Evaluations 사용 시기:**
- 특정 고객 상호작용 또는 보고된 문제 조사
- 식별된 문제에 대한 수정 사항 검증
- 품질 개선을 위한 과거 데이터 분석
- 프로덕션에 배포하기 전에 evaluator 테스트
- 엣지 케이스에 대한 심층 분석 수행

**작동 방식:**

![On-demand Evaluations](../images/on_demand_evaluations.png)

1. Agent가 AgentCore Observability에서 trace 생성
2. Trace가 세션에 매핑되고 CloudWatch Log 그룹에 저장
3. 평가할 특정 세션 또는 trace 선택
4. 적용할 evaluator(내장 또는 커스텀) 지정
5. AgentCore Evaluations가 선택한 trace를 처리하고 상세한 결과 반환

### Online Evaluations

Online evaluation은 실시간 트래픽을 기반으로 프로덕션 환경에서 배포된 agent의 지속적인 품질 모니터링을 가능하게 합니다.

**주요 특징:**
- **지속적인 모니터링**: 상호작용이 발생할 때 agent 성능을 자동으로 평가
- **샘플링 기반**: 백분율 기반 샘플링 또는 조건부 필터 구성
- **실시간 인사이트**: 품질 추세를 추적하고 조기에 회귀 감지
- **프로덕션 준비**: 최소한의 성능 영향으로 확장 가능하도록 설계

**Online Evaluations 사용 시기:**
- 프로덕션 agent 성능을 지속적으로 모니터링
- 사용자에게 영향을 미치기 전에 품질 회귀 감지
- 대규모 사용자 상호작용 패턴 식별
- 시간 경과에 따른 일관된 agent 성능 유지
- 다양한 agent 구성에 대한 A/B 테스트

**작동 방식:**

![Online Evaluations](../images/online_evaluations.png)

1. Agent가 AgentCore Observability에서 trace 생성
2. 다음을 지정하는 online evaluation 구성 생성:
   - 데이터 소스 (CloudWatch log 그룹 또는 AgentCore Runtime 엔드포인트)
   - 샘플링 비율 (예: 모든 세션의 10% 평가)
   - 적용할 evaluator (내장 및/또는 커스텀)
3. AgentCore Evaluations가 규칙에 따라 들어오는 trace를 지속적으로 처리
4. 결과가 대시보드 시각화 및 분석을 위해 CloudWatch로 출력
5. 집계된 점수를 모니터링하고, 추세를 추적하며, 낮은 점수의 세션 조사

## AgentCore Observability 통합

두 evaluation 유형 모두 **AgentCore Observability**에 의존하여 OpenTelemetry (OTEL) trace를 통해 agent 동작을 캡처합니다.

**Observability 작동 방식:**

![Observability Traces](../images/observability_traces.png)

AgentCore는 **AWS Distro for OpenTelemetry (ADOT)**에 의존하여 다양한 agent 프레임워크에서 여러 유형의 OTEL trace를 계측합니다:

**AgentCore Runtime 호스팅 agent의 경우** (이 튜토리얼의 agent와 같이):
- 최소한의 구성으로 자동 계측
- `requirements.txt`에 `aws-opentelemetry-distro`만 포함
- AgentCore Runtime이 OTEL 구성을 자동으로 처리
- Trace가 CloudWatch GenAI Observability Dashboard에 표시

**Non-Runtime agent의 경우:**
- 환경 변수를 구성하여 텔레메트리를 CloudWatch로 전달
- OpenTelemetry 계측으로 agent 실행
- 자세한 내용은 [AgentCore Observability 문서](../../06-AgentCore-observability) 참조

## 튜토리얼 구조

이 튜토리얼은 AgentCore의 프레임워크 독립적 기능을 보여주기 위해 **Strands Agents** 및 **LangGraph** 프레임워크 모두에 대한 예제를 제공합니다:

### [01-strands](01-strands/)
Strands Agents SDK를 사용한 예제:
- **01-on-demand-eval.ipynb**: 특정 trace에 대한 타겟 evaluation 실행
- **02-online-eval.ipynb**: 지속적인 프로덕션 모니터링 설정

### [02-langgraph](02-langgraph/)
LangGraph 프레임워크를 사용한 예제:
- **01-on-demand-eval.ipynb**: 특정 trace에 대한 타겟 evaluation 실행
- **02-online-eval.ipynb**: 지속적인 프로덕션 모니터링 설정

두 구현 모두 동일한 evaluation 개념을 보여주고 동등한 결과를 생성하여 AgentCore Evaluations가 다양한 agent 프레임워크에서 일관되게 작동하는 방식을 보여줍니다.

## 다음 단계

이 튜토리얼을 완료한 후:
- [Tutorial 03: Advanced](../03-advanced)로 진행하여 다음을 포함한 고급 기능 탐색:
  - boto3 SDK를 사용하여 on-demand evaluation을 위한 CloudWatch 로그 쿼리
  - 다양한 agent 구성으로 실험을 시각화하는 로컬 대시보드 생성
  - Online evaluation을 위한 고급 필터링 및 샘플링 전략
