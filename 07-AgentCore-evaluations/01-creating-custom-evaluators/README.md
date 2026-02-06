# Evaluator 생성하기

## 개요
이 튜토리얼에서는 AgentCore Evaluations의 내장 및 커스텀 메트릭에 대해 배웁니다.
각 유형을 언제 사용해야 하는지, 그리고 특정 요구사항에 맞춘 커스텀 evaluator를 생성하는 방법을 배웁니다.

## 학습 내용
- 내장 evaluator와 사용 사례 이해하기
- 특수한 요구사항을 위한 커스텀 evaluator 생성하기
- Agent에 적합한 평가 접근 방식 선택하기

## Evaluator 유형

### 내장 Evaluator
내장 evaluator는 Large Language Model(LLM)을 판단자로 사용하여 agent 성능을 평가하는 사전 구성된 evaluator입니다.

**주요 특징:**
- **사전 구성됨**: 신중하게 작성된 프롬프트 템플릿, 선택된 evaluator model, 표준화된 점수 기준이 포함되어 있습니다
- **즉시 사용 가능**: 추가 구성 없이 즉시 평가를 시작할 수 있습니다
- **일관성**: 고정된 구성으로 평가 전반에 걸쳐 신뢰성과 일관성을 보장합니다
- **포괄적**: 정확성, 유용성, 안전성을 포함한 13가지 중요한 평가 차원을 다룹니다

**내장 Evaluator를 사용해야 하는 경우:**
- 품질 평가를 빠르게 구현해야 할 때
- 팀이나 프로젝트 전반에 걸쳐 표준화된 평가 메트릭을 원할 때
- 평가 요구사항이 일반적인 품질 차원과 일치할 때
- 커스터마이징보다 일관성과 신뢰성을 우선시할 때


사용 사례에 따라 다음 내장 evaluator를 사용할 수 있습니다:
* 응답 품질 메트릭:
  * **Builtin.Correctness**: Agent 응답의 정보가 사실적으로 정확한지 평가합니다
  * **Builtin.Faithfulness**: 응답의 정보가 제공된 컨텍스트/소스에 의해 뒷받침되는지 평가합니다
  * **Builtin.Helpfulness**: 사용자 관점에서 agent 응답이 얼마나 유용하고 가치 있는지 평가합니다
  * **Builtin.ResponseRelevance**: 응답이 사용자의 질문을 적절하게 다루는지 평가합니다
  * **Builtin.Conciseness**: 응답이 핵심 정보를 누락하지 않으면서 적절하게 간결한지 평가합니다
  * **Builtin.Coherence**: 응답이 논리적으로 구조화되고 일관성이 있는지 평가합니다
  * **Builtin.InstructionFollowing**: Agent가 제공된 시스템 지침을 얼마나 잘 따르는지 측정합니다
  * **Builtin.Refusal**: Agent가 질문을 회피하거나 직접적으로 답변을 거부하는 경우를 감지합니다
* 작업 완료 메트릭:
  * **Builtin.GoalSuccessRate**: 대화가 사용자의 목표를 성공적으로 충족하는지 평가합니다
* Tool 레벨 메트릭:
  * **Builtin.ToolSelectionAccuracy**: Agent가 작업에 적합한 tool을 선택했는지 평가합니다
  * **Builtin.ToolParameterAccuracy**: Agent가 사용자 쿼리에서 파라미터를 얼마나 정확하게 추출하는지 평가합니다
* 안전성 메트릭:
  * **Builtin.Harmfulness**: 응답에 유해한 콘텐츠가 포함되어 있는지 평가합니다
  * **Builtin.Stereotyping**: 개인이나 그룹에 대한 일반화를 만드는 콘텐츠를 감지합니다

**참고:** 내장 evaluator 구성은 모든 사용자에게 평가 일관성과 신뢰성을 유지하기 위해 수정할 수 없지만, 내장 evaluator를 기반으로 자신만의 evaluator를 생성할 수 있습니다.

### 커스텀 Evaluator
커스텀 evaluator는 LLM을 기본 판단자로 활용하면서 평가 프로세스의 모든 측면을 정의할 수 있도록 최대한의 유연성을 제공합니다.

**커스터마이징 옵션:**
- **Evaluator model**: 평가 요구사항에 가장 적합한 LLM을 선택합니다
- **평가 프롬프트**: 사용 사례에 특화된 평가 지침을 작성합니다
- **점수 스키마**: 조직의 메트릭과 일치하는 점수 시스템을 설계합니다

**커스텀 Evaluator를 사용해야 하는 경우:**
- 도메인별 agent를 평가할 때 (예: 의료, 금융, 법률)
- 고유한 품질 표준이나 규정 준수 요구사항이 있을 때
- 조직의 KPI와 일치하는 특수한 점수 시스템이 필요할 때
- 내장 evaluator가 특정 평가 차원을 포착하지 못할 때

**사용 사례 예시:**
- HIPAA 규정 준수 평가가 필요한 의료 agent
- 규제 준수 점수가 필요한 금융 agent
- 브랜드별 품질 표준에 따라 평가되는 고객 서비스 agent
- 문제 해결 방법론에 따라 평가되는 기술 지원 agent

## 다음 단계
이 튜토리얼을 완료한 후 [Using On-demand Evaluation](../01-setting-evaluations)로 진행하여 이러한 evaluator를 agent trace에 적용하는 방법을 배우세요.
