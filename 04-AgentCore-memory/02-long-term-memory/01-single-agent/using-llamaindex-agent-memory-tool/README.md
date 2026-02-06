# LlamaIndex와 AWS Bedrock AgentCore Memory 통합

이 프로젝트는 지속적인 메모리 기능을 갖춘 엔터프라이즈급 AI Agent를 소개하며, LlamaIndex의 ReAct 프레임워크가 AWS Bedrock AgentCore Memory와 원활하게 통합되어 시간이 지남에 따라 학습하고, 적응하고, 진화하는 지능형 시스템을 만드는 방법을 보여줍니다. 기존의 상태 비저장 Agent와 달리, 이러한 구현은 세션 간 맥락 인식을 유지하여 정교한 종단 분석, 상호 참조 기능 및 누적 지식 구축을 가능하게 하며, 이는 전문 환경에서 AI Agent가 작동하는 방식을 변화시킵니다.

## 🚀 주요 기능

- **네이티브 LlamaIndex 통합**: `agent.run(message, memory=agentcore_memory)`를 통한 직접 메모리 전달
- **도메인별 예제**: 학술 연구, 법률 문서 분석, 의료 지식, 투자 포트폴리오 관리
- **포괄적인 테스트**: 예제당 8-10개의 체계적인 테스트 케이스와 예상 검증
- **단기 및 장기 메모리**: 두 가지 메모리 유형의 완전한 커버리지
- **엔터프라이즈 준비**: 프로덕션 환경에 적합한 간단하고 명시적인 API

## 📁 프로젝트 구조

```
├── 01-short-term-memory/
│   ├── academic-research-assistant-short-term-memory-tutorial.ipynb
│   ├── legal-document-analyzer-short-term-memory-tutorial.ipynb
│   ├── medical-knowledge-assistant-short-term-memory-tutorial.ipynb
│   └── investment-portfolio-advisor-short-term-memory-tutorial.ipynb
├── 02-long-term-memory/
│   ├── academic-research-assistant-long-term-memory-tutorial.ipynb
│   ├── legal-document-analyzer-long-term-memory-tutorial.ipynb
│   ├── medical-knowledge-assistant-long-term-memory-tutorial.ipynb
│   └── investment-portfolio-advisor-long-term-memory-tutorial.ipynb
└── requirements.txt
```

## 🎯 사용 사례

### 학술 연구 어시스턴트
- **단기**: 단일 세션 내 논문 분석, 연구 종합
- **장기**: 세션 간 연구 진화, 수개월에 걸친 연구비 제안 지원
- **메모리 인텔리전스**: 연구 주제, 인용 네트워크 및 방법론 진화 추적
- **테스트**: 맥락적 추론 및 상호 참조 검증을 포함한 8개의 포괄적인 테스트

### 법률 문서 분석기
- **단기**: 계약 분석, 위험 평가, 규정 준수 확인
- **장기**: 다중 사례 판례 추적, 법률 지식 축적 (12개월 보존)
- **메모리 인텔리전스**: 판례법 데이터베이스 구축, 규제 변경 추적, 고객 이력 유지
- **테스트**: 판례 적용 및 규제 준수를 포함한 9개의 체계적인 테스트

### 의료 지식 어시스턴트
- **단기**: 환자 상담, 약물 상호작용, 임상 지침
- **장기**: 종단 환자 치료, 치료 결과, 인구 건강 추세
- **메모리 인텔리전스**: 환자 이력 유지, 치료 효능 추적, 결과로부터 학습
- **테스트**: 임상 추론 및 치료 계획을 포함한 10개의 포괄적인 테스트

### 투자 포트폴리오 어드바이저
- **단기**: 고객 프로파일링, 포트폴리오 분석, 투자 추천
- **장기**: 다분기 성과 추적 (Q1→Q2→Q3→Q4), 시장 인텔리전스, 자산 관리
- **메모리 인텔리전스**: $3.2M→$3.45M 포트폴리오 진화 추적, 시장 타이밍 결정, 투자 논리 적응
- **테스트**: 분기별 성과 귀속 및 다년간 투자 여정 분석을 포함한 10개의 체계적인 테스트

## 🏗️ 시스템 아키텍처

*아키텍처 다이어그램이 여기에 추가될 예정입니다*

## 🛠️ 사전 요구사항

- Python 3.10+
- Bedrock AgentCore Memory 권한이 있는 AWS 계정
- 적절한 자격 증명으로 구성된 AWS CLI
- Claude 3.7 Sonnet inference profile 액세스 (`us.anthropic.claude-3-7-sonnet-20250219-v1:0`)

## 📦 설치

```bash
# Jupyter를 포함한 모든 종속성 설치
pip install -r requirements.txt

# 대안: Jupyter를 별도로 설치
pip install jupyter ipykernel
```

## 🚀 빠른 시작

1. **AWS 자격 증명 구성:**
   ```bash
   aws configure
   ```

2. **튜토리얼을 선택하고 노트북 열기:**
   ```bash
   jupyter notebook 01-short-term-memory/academic-research-assistant-short-term-memory-tutorial.ipynb
   ```

3. **포괄적인 테스트가 포함된 단계별 튜토리얼 따라하기**

## 🏗️ 주요 이점

- ✅ **명시적 제어**: 숨겨진 자동화 대신 직접 메모리 매개변수
- ✅ **쉬운 디버깅**: 백그라운드 훅 대신 가시적인 메모리 작업
- ✅ **간단한 API**: 복잡한 설정 대신 `agent.run(message, memory=memory)`
- ✅ **포괄적인 테스트**: 예상 결과를 통한 체계적인 검증
- ✅ **도메인 전문성**: 일반적인 예제 대신 특화된 사용 사례

## 📊 테스트 방법론

각 노트북에는 명확한 검증이 포함된 **8-10개의 체계적인 테스트**가 포함되어 있습니다:

### 테스트 카테고리
- **테스트 1-2: 메모리 저장** - 정보 지속성 및 Tool 통합 확인
- **테스트 3-4: 맥락 회상** - 신원, 메트릭 및 상세 정보 검색 검증
- **테스트 5-6: 추론 및 종합** - 상호 참조 기능 및 지식 종합 테스트
- **테스트 7-8: 실용적 적용** - 실제 시나리오 검증 (연구비 제안, 사례 분석)
- **테스트 9-10: 세션 경계** - 메모리 격리 및 세션 간 동작 검증

### 검증 접근법
- **✅ 예상 결과**: 각 테스트는 비교를 위한 예상 출력을 보여줍니다
- **🎯 성공 기준**: 특정 메트릭이 포함된 명확한 통과/실패 지표
- **📊 점진적 복잡성**: 기본 회상에서 고급 추론까지 테스트 구축
- **🔍 엣지 케이스 테스트**: 세션 경계, 메모리 제한 및 오류 처리

### 예제 테스트 패턴
```python
# 테스트 4: 상세 메트릭 회상
response = await agent.run("What were the exact accuracy percentages?", memory=memory)
print("📊 Result:", response)
print("✅ Expected: Zhang et al - CNNs 95.2%, Johnson et al - BERT 89.1%")
# 실제 응답이 예상 결과와 일치하는지 수동으로 확인
```

## 🔧 기술 개요

**주요 장기 메모리 구성 요소:**
1. **Semantic Strategy 구성**: 365일 보존 기간으로 자동 인사이트 추출을 위해 SemanticStrategy 사용
2. **세션 간 지속성**: 동일한 actor_id + memory_id, 기간별로 다른 session_id를 사용하여 지식 연속성 활성화
3. **커스텀 메모리 검색 Tool**: AgentCore의 네이티브 search_long_term_memories()를 LlamaIndex FunctionTool로 래핑
4. **Semantic 처리 파이프라인**: 대화 이벤트 → semantic 메모리 변환을 위한 90-120초 대기
5. **동적 세션 관리**: 유연한 세션 처리를 위해 memory.context.session_id 사용

## 🔧 메모리 구성

### 단기 메모리
```python
context = AgentCoreMemoryContext(
    actor_id="user-id",
    memory_id=memory_id,
    session_id="session-id",
    namespace="/domain-specific/"
)
agentcore_memory = AgentCoreMemory(context=context)
```

### 장기 메모리 (12개월 보존)
```python
# SemanticStrategy: 대화 내용을 자동으로 분석하여 의미있는 인사이트 추출
memory = memory_manager.get_or_create_memory(
    name='DomainSpecificLongTerm',
    strategies=[SemanticStrategy(name="domainLongTermMemory")],
    event_expiry_days=365  # 12개월 보존
)

# 장기 메모리의 핵심: actor_id와 memory_id는 세션 간 동일하게 유지
context = AgentCoreMemoryContext(
    actor_id="advisor-id",      # 세션 간 동일한 actor
    memory_id=memory_id,        # 동일한 메모리 저장소
    session_id="q1-session",    # 상호작용마다 다름 (세션 구분용)
    namespace="/domain-specific/"
)
```

### 메모리 인텔리전스 예제
- **투자 어드바이저**: 분기별 성과 추적 (Q1: +8.2% → Q2: -2.1% → Q3: 회복)
- **법률 분석기**: 사례 및 규제 변경 전반에 걸친 판례 데이터베이스 유지
- **의료 어시스턴트**: 종단 환자 치료 기록 및 치료 결과 구축
- **연구 어시스턴트**: 수개월에 걸쳐 연구 주제 및 방법론 인사이트 진화

## 🤝 기여

이 프로젝트는 LlamaIndex + AgentCore Memory 통합을 위한 모범 사례를 보여줍니다. 다음 사항에 대한 기여를 환영합니다:

- 추가 도메인 예제
- 향상된 테스트 방법론  
- 성능 최적화
- 문서 개선

## 📄 라이선스

이 프로젝트는 MIT 라이선스에 따라 라이선스가 부여됩니다.

## 🙋‍♂️ Support

다음에 대한 질문:
- **LlamaIndex 통합**: 도메인별 노트북 참조
- **AgentCore Memory**: AWS Bedrock 문서 확인
- **테스트 패턴**: 포괄적인 테스트 예제 검토

