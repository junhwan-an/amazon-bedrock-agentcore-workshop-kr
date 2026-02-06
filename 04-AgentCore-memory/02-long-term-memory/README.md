# AgentCore Memory: 장기 메모리 전략

## 개요

Amazon Bedrock AgentCore의 장기 메모리는 AI agent가 여러 대화와 세션에 걸쳐 지속적인 정보를 유지할 수 있도록 합니다. 즉각적인 컨텍스트에 초점을 맞추는 단기 메모리와 달리, 장기 메모리는 의미 있는 정보를 추출, 처리 및 저장하여 향후 상호작용에서 검색하고 적용할 수 있으며, 진정으로 개인화되고 지능적인 agent 경험을 만듭니다.

## 장기 메모리란?

장기 메모리는 다음을 제공합니다:

- **세션 간 지속성**: 개별 대화를 넘어 유지되는 정보
- **지능형 추출**: 중요한 사실, 선호도 및 패턴의 자동 식별 및 저장
- **의미론적 이해**: 자연어 검색을 가능하게 하는 벡터 기반 저장
- **개인화**: 맞춤형 경험을 가능하게 하는 사용자별 정보
- **지식 축적**: 시간이 지남에 따라 지속적인 학습 및 정보 구축

## 장기 메모리 전략 작동 방식

장기 메모리는 추출할 정보와 처리 방법을 정의하는 **Memory 전략**을 통해 작동합니다. 시스템은 백그라운드에서 자동으로 작동합니다:

### 처리 파이프라인

1. **대화 분석**: 저장된 대화가 구성된 전략에 따라 분석됩니다
2. **정보 추출**: 중요한 데이터(사실, 선호도, 요약)가 AI model을 사용하여 추출됩니다
3. **구조화된 저장**: 추출된 정보가 효율적인 검색을 위해 네임스페이스로 구성됩니다
4. **의미론적 인덱싱**: 정보가 자연어 검색 기능을 위해 벡터화됩니다
5. **통합**: 유사한 정보가 시간이 지남에 따라 병합되고 정제됩니다

**처리 시간**: 일반적으로 대화가 저장된 후 약 1분이 소요되며, 추가 코드가 필요하지 않습니다.

### 내부 작동 방식

- **AI 기반 추출**: foundation model을 사용하여 관련 정보를 이해하고 추출합니다
- **벡터 임베딩**: 유사성 기반 검색을 위한 의미론적 표현을 생성합니다
- **네임스페이스 구성**: 구성 가능한 경로와 같은 계층 구조를 사용하여 정보를 구조화합니다
- **자동 통합**: 중복을 방지하기 위해 유사한 정보를 병합하고 정제합니다
- **점진적 학습**: 대화 패턴을 기반으로 추출 품질을 지속적으로 개선합니다

## 장기 메모리 전략 유형

AgentCore Memory는 장기 정보 저장을 위한 네 가지 고유한 전략 유형을 지원합니다:

### 1. Semantic Memory 전략

벡터 임베딩을 사용하여 대화에서 추출한 사실 정보를 저장하여 유사성 검색을 수행합니다.

```python
{
    "semanticMemoryStrategy": {
        "name": "FactExtractor",
        "description": "Extracts and stores factual information",
        "namespaces": ["support/user/{actorId}/facts/"]  # {actorId}는 실제 사용자 ID로 자동 치환됨
    }
}
```

**최적 용도**: 제품 정보, 기술 세부 사항 또는 자연어 쿼리를 통해 검색해야 하는 모든 사실 데이터를 저장하는 경우.

### 2. Summary Memory 전략

긴 상호작용에 대한 컨텍스트를 보존하기 위해 대화 요약을 생성하고 유지합니다.

```python
{
    "summaryMemoryStrategy": {
        "name": "ConversationSummary",
        "description": "Maintains conversation summaries",
        "namespaces": ["support/summaries/{sessionId}/"]  # {sessionId}는 세션 ID로 자동 치환됨
    }
}
```

**최적 용도**: 후속 대화에서 컨텍스트를 제공하고 긴 상호작용에서 연속성을 유지하는 경우.

### 3. User Preference Memory 전략

상호작용을 개인화하기 위해 사용자별 선호도 및 설정을 추적합니다.

```python
{
    "userPreferenceMemoryStrategy": {
        "name": "UserPreferences",
        "description": "Captures user preferences and settings",
        "namespaces": ["support/user/{actorId}/preferences"/]  # 사용자별 선호도 저장 경로
    }
}
```

**최적 용도**: 커뮤니케이션 선호도, 제품 선호도 또는 모든 사용자별 설정을 저장하는 경우.

### 4. Custom Memory 전략

추출 및 통합을 위한 프롬프트 사용자 정의를 허용하여 특수한 사용 사례에 대한 유연성을 제공합니다.

```python
{
    "customMemoryStrategy": {
        "name": "CustomExtractor",
        "description": "Custom memory extraction logic",
        "namespaces": ["user/custom/{actorId}/"],
        "configuration": {
            "semanticOverride": { # Summary나 User Preferences도 override 가능
                "extraction": {
                    "appendToPrompt": "Extract specific information based on custom criteria",  # 추출 프롬프트 커스터마이징
                    "modelId": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
                },
                "consolidation": {
                    "appendToPrompt": "Consolidate extracted information in a specific format",  # 통합 프롬프트 커스터마이징
                    "modelId": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
                }
            }
        }
    }
}
```

**최적 용도**: 표준 전략에 맞지 않는 특수한 추출 요구 사항이 있는 경우.

## 네임스페이스 이해

네임스페이스는 경로와 같은 구조를 사용하여 전략 내에서 메모리 레코드를 구성합니다. 동적으로 대체되는 변수를 포함할 수 있습니다:

- `support/facts/{sessionId}`: 세션별로 사실을 구성
- `user/{actorId}/preferences`: actor ID별로 사용자 선호도를 저장
- `meetings/{memoryId}/summaries/{sessionId}`: 메모리별로 요약을 그룹화

`{actorId}`, `{sessionId}`, `{memoryId}` 변수는 메모리를 저장하고 검색할 때 실제 값으로 자동으로 대체됩니다.

## 예시: 실제 작동 방식

사용자가 고객 지원 agent에게 다음과 같이 말한다고 가정해 봅시다: _"저는 채식주의자이고 이탈리아 요리를 정말 좋아합니다. 오후 6시 이후에는 전화하지 마세요."_

이 대화를 저장한 후, 구성된 전략이 자동으로:

**Semantic 전략**이 추출:

- "사용자는 채식주의자입니다"
- "사용자는 이탈리아 요리를 즐깁니다"

**User Preference 전략**이 캡처:

- "식단 선호도: 채식주의자"
- "요리 선호도: 이탈리아"
- "연락 선호도: 오후 6시 이후 전화 금지"

**Summary 전략**이 생성:

- "사용자가 식단 제한 및 연락 선호도에 대해 논의했습니다"

이 모든 것이 백그라운드에서 자동으로 발생합니다 - 대화를 저장하기만 하면 전략이 나머지를 처리합니다.

## 사용 가능한 샘플 노트북

장기 메모리 전략 구현을 학습하기 위한 실습 예제를 살펴보세요:

| Integration 방법          | 사용 사례            | 설명                                                                             | 노트북                                                                                                       | 아키텍처                                                                               |
| ------------------------- | ------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| Strands Agent Hooks       | Customer Support    | semantic 및 preference memory 전략을 갖춘 완전한 지원 시스템                  | [customer-support.ipynb](./01-single-agent/using-strands-agent-hooks/customer-support/customer-support.ipynb)  | [View](./01-single-agent/using-strands-agent-hooks/customer-support/architecture.png)      |
| Strands Agent Hooks       | Math Assistant      | 사용자 학습 선호도 및 진행 상황을 기억하는 수학 튜터 어시스턴트              | [math-assistant.ipynb](./01-single-agent/using-strands-agent-hooks/simple-math-assistant/math-assistant.ipynb) | [View](./01-single-agent/using-strands-agent-hooks/simple-math-assistant/architecture.png) |
| LangGraph Agent Hooks     | Nutrition Assistant | 개인화된 권장 사항을 위해 사용자 식단 선호도 및 건강 목표를 저장하는 영양 어드바이저 | [nutrition-assistant-with-user-preference-saving.ipynb](./01-single-agent/using-langgraph-agent-hooks/nutrition-assistant-with-user-preference-saving.ipynb) | [View](./01-single-agent/using-langgraph-agent-hooks/architecture.png) |
| Strands Agent Memory Tool | Culinary Assistant  | 식단 선호도 및 요리 스타일을 학습하는 음식 추천 agent            | [culinary-assistant.ipynb](./01-single-agent/using-strands-agent-memory-tool/culinary-assistant.ipynb)         | [View](./01-single-agent/using-strands-agent-memory-tool/architecture.png)                 |
| Multi-Agent               | Agent Collaboration | 장기 메모리 전략을 공유하고 활용하는 여러 agent가 있는 Travel Assistant | [travel-booking-assistant.ipynb](./02-multi-agent/with-strands-agent/travel-booking-assistant.ipynb)           | [View](./02-multi-agent/with-strands-agent/architecture.png)                               |

## 시작하기

1. 사용 사례와 일치하는 샘플을 선택하세요
2. 샘플 폴더로 이동하세요
3. 요구 사항을 설치하세요: `pip install -r requirements.txt`
4. Jupyter 노트북을 열고 단계별 구현을 따르세요

## 모범 사례

1. **전략 선택**: 사용 사례 요구 사항에 따라 적절한 전략을 선택하세요
2. **네임스페이스 설계**: 효율적인 정보 구성을 위해 네임스페이스 계층 구조를 계획하세요
3. **추출 튜닝**: 도메인별 정보에 대한 추출 프롬프트를 사용자 정의하세요
4. **성능 모니터링**: 메모리 추출 품질 및 검색 성능을 추적하세요
5. **개인정보 보호 고려 사항**: 적절한 데이터 보존 및 개인정보 보호 정책을 구현하세요

## 다음 단계

장기 메모리 전략을 마스터한 후 다음을 탐색하세요:

- 포괄적인 agent 경험을 위한 단기 및 장기 메모리 결합
- 고급 커스텀 전략 구성
- 멀티 에이전트 메모리 공유 패턴
- 프로덕션 배포 고려 사항
