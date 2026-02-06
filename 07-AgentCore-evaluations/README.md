# 개요

Amazon Bedrock AgentCore Evaluations는 실제 상호작용을 기반으로 agent의 품질을 최적화하는 데 도움을 줍니다.

## 주요 기능

AgentCore Observability가 agent 상태에 대한 운영 인사이트를 제공하는 반면, AgentCore Evaluations는 agent 의사결정 품질과 성능 결과에 중점을 둡니다.

온디맨드 및 온라인 evaluation 기능과 함께 내장 및 커스텀 evaluator를 제공합니다.

### 내장 및 커스텀 Evaluator

AgentCore Evaluations는 정확성, 유용성, 안전성과 같은 중요한 차원에 대한 13개의 내장 evaluator와 비즈니스별 요구사항에 맞는 커스텀 evaluator를 생성할 수 있는 기능을 제공합니다.

온디맨드 evaluations API를 사용하여 개발 및 배포 중에 agent를 테스트하거나, 온라인 evaluations API를 사용하여 프로덕션 agent를 모니터링할 수 있습니다.

### 온디맨드 Evaluations

개별 trace에 대해 내장 및 커스텀 메트릭을 사용하여 동기식 온디맨드 evaluation을 실행합니다.

시스템은 OpenTelemetry (OTEL) trace를 사용하여 점수를 매기고 다음을 포함하는 응답을 반환합니다:
- 점수 값
- 점수에 대한 설명
- 토큰 사용량

온라인 Evaluations

프로덕션 환경에서는 각 trace를 수동으로 평가하지 않고도 모든 상호작용에 대한 지속적인 성능 모니터링이 필요합니다. 통계적 샘플만으로도 의미 있는 성능 메트릭을 생성하기에 충분한 경우가 많습니다.

AgentCore Evaluations의 온라인 기능은 자동 샘플링 및 evaluation을 가능하게 합니다:

- 샘플 크기 및 trace 선택 기준 정의
- evaluation 메트릭 선택 (내장 또는 커스텀)
- AgentCore Evaluations가 나머지를 처리하여 대규모로 agent를 모니터링하는 데 필요한 성능 데이터를 생성합니다

## 튜토리얼 개요

이 튜토리얼에서는 다음 기능을 다룹니다:
- [사전 요구사항](00-prereqs): evaluation 튜토리얼에서 사용할 샘플 agent 생성
- [커스텀 evaluator 생성](01-creating-custom-evaluators): 내장 및 커스텀 메트릭에 대해 알아보고 agent를 평가하기 위한 커스텀 메트릭 생성
- [온디맨드 및 온라인 evaluations 사용](02-running-evaluations): 온디맨드 및 온라인 evaluations를 사용하여 대규모로 agent를 구축, 최적화 및 모니터링하는 방법 학습
- [고급](03-advanced): boto3 SDK를 사용하여 온디맨드 evaluation을 위한 Amazon CloudWatch 로그 쿼리 및 다양한 agent 구성으로 실험을 시각화하기 위한 로컬 대시보드 생성을 포함한 고급 기능 탐색

