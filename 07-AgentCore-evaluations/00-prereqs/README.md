# 사전 요구사항: 샘플 Agent 생성

## 개요

Agent를 평가하기 전에 평가할 Agent가 필요합니다. 이 튜토리얼에서는 나머지 평가 튜토리얼에서 사용할 두 개의 샘플 Agent를 설정합니다: 하나는 [Strands Agents SDK](https://strandsagents.com/)를 사용하고 다른 하나는 [LangGraph](https://www.langchain.com/langgraph)를 사용합니다.

## Agent
생성된 Agent는 본질적으로 동일하며, AgentCore의 "모든 프레임워크" 제안을 보여주기 위해 두 가지 다른 프레임워크를 사용합니다.

생성된 Agent는 두 가지 주요 기능을 가지고 있습니다:

**코드 실행**
- AgentCore Code Interpreter를 사용하여 Python 코드 실행
- 수학 계산 및 데이터 분석 처리

**메모리**
- 사용자 사실 및 선호도 저장
- 개인화된 응답을 위한 관련 컨텍스트 검색

두 Agent 모두 Amazon Bedrock의 Anthropic Claude Haiku 4.5를 LLM 모델로 사용하지만, AgentCore를 사용하면 원하는 모델을 사용할 수 있습니다.

아키텍처는 다음과 같습니다:

![Architecture](../images/agent_architecture.png)

## 사전 요구사항
Agent를 배포하기 전에 필요한 사항:
* Python 3.10+
* AWS 액세스


## 다음 단계
이제 필요한 모든 사전 요구사항이 준비되었으므로 개별 평가 튜토리얼을 진행해 보겠습니다:

- **[Tutorial 01](../01-creating-custom-evaluators)**: 커스텀 evaluator 생성
- **[Tutorial 02](../02-running-evaluations)**: 온디맨드 및 온라인 evaluation 실행
- **[Tutorial 03](../03-advanced)**: 고급 기술 및 대시보드