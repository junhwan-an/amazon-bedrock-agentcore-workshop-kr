# Episodic Memory를 사용한 멀티 Agent 헬스케어 시스템

Episodic memory는 의미 있는 상호작용 조각을 캡처하여 중요한 순간을 식별하고 노이즈 없이 집중된 검색을 위해 간결하고 조직화된 레코드로 요약합니다.

Reflections는 에피소드를 분석하여 인사이트, 패턴, 결론을 도출하여 시스템이 이벤트가 왜 중요한지, 향후 동작에 어떻게 영향을 미쳐야 하는지 이해하도록 돕고, 경험을 실행 가능한 가이드로 전환합니다.

Amazon Bedrock AgentCore Memory를 사용한 **episodic memory를 활용한 멀티 agent 조정**을 보여주는 포괄적인 예제입니다. 이 튜토리얼은 AI agent가 과거 상호작용에서 학습하고 시간이 지남에 따라 의사 결정을 개선하는 방법을 보여줍니다.

## 개요

이 튜토리얼은 다음과 같은 헬스케어 어시스턴트 시스템을 보여줍니다:
- **Supervisor Agent**: 환자 질문을 전문 agent로 라우팅
- **Claims Agent**: 보험 청구 및 청구서 쿼리 처리
- **Demographics Agent**: 환자 인구통계 정보 관리
- **Medication Agent**: 약물 및 처방전 쿼리 처리

각 agent는 **memory branching**을 통해 격리된 단기 메모리를 유지하면서 **episodic memory 전략**을 통해 장기 인사이트를 공유합니다.

## 아키텍처
<div style="text-align:left">
    <img src="architecture.png" width="75%" />
</div>

## Memory 전략

### Episodic 

시스템은 다음과 같은 episodic memory 전략을 사용합니다:

**Extraction**: 대화 이벤트를 구조화된 에피소드로 변환
- Prompt: "Extract patient interactions with healthcare agents"
- Namespace: `healthcare/{actorId}/{sessionId}/`

**Consolidation**: 관련 에피소드 병합
- Prompt: "Consolidate healthcare conversations"

**Reflection**: 세션 간 인사이트 생성
- Prompt: "Generate insights from patient care patterns"
- Namespace: `healthcare/{actorId}/` (정확한 namespace 접두사)

### Memory Branching

각 agent는 자체 memory branch에서 작동합니다:
- `main`: Supervisor agent 라우팅 결정
- `claims_agent`: 보험 및 청구 대화
- `demographics_agent`: 환자 정보 업데이트
- `medication_agent`: 처방전 논의

**이점:**
- Agent들은 서로의 대화를 볼 수 없음
- 명확한 관심사 분리
- 모든 agent가 공유 장기 메모리에 기여
- 환자 수준 인사이트가 모든 상호작용에 걸쳐 있음

## 사전 요구 사항

### AWS Services
- **Amazon Bedrock**: Claude Sonnet 4 model 액세스 
- **Amazon Bedrock AgentCore Memory**: Episodic memory 전략용
- **Amazon HealthLake** (선택 사항): 환자 데이터가 있는 FHIR datastore
  - 설정 중 Synthea 데이터로 새 datastore 생성 가능
  - 또는 기존 datastore 사용

### IAM 권한
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",  // Bedrock 모델 호출 권한
        "bedrock:InvokeModelWithResponseStream"  // 스트리밍 응답 권한
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "healthlake:DescribeFHIRDatastore",  // Datastore 정보 조회
        "healthlake:CreateFHIRDatastore",  // Datastore 생성
        "healthlake:ReadResource",  // FHIR 리소스 읽기
        "healthlake:SearchWithGet"  // FHIR 리소스 검색
      ],
      "Resource": "*"
    }
  ]
}
```

### Python 환경
- Python 3.10+
- Jupyter Notebook 또는 JupyterLab

## 설치

1. 종속성 설치:
```bash
pip install -r requirements.txt
```

2. AWS 자격 증명 구성:
```bash
aws configure
```

## 사용법

### 빠른 시작

1. 노트북 열기:
```bash
jupyter notebook healthcare-data-assistant.ipynb
```

2. 셀을 순차적으로 실행:
   - **Step 1**: 환경 설정
   - **Step 2**: HealthLake Datastore 구성
   - **Step 3**: Episodic 전략을 사용한 장기 메모리용 tool로 Memory 생성
   - **Step 4**: 단기 메모리용 Branch 지원이 있는 Memory Hook Provider 생성
   - **Step 5**: Memory Branching을 사용한 멀티 Agent 헬스케어 아키텍처 생성
   - **Step 6**: 인터랙티브 채팅으로 테스트
   - **Step 7**: 헬스케어 memory branch 검사
   - **Step 8**: 장기 메모리 검증 (에피소드 및 reflections)

### 인터랙티브 입력

노트북은 다음을 요청합니다:
- **HealthLake datastore ID**: 기존 datastore 또는 Synthea 데이터로 새로 생성 (실제 환자 정보는 사용되지 않음)
- **HealthLake region**: HealthLake용 AWS 리전

### 시스템 테스트

인터랙티브 채팅 (Step 7)을 통해 다음을 수행할 수 있습니다:
- 보험 청구에 대해 질문
- 인구통계 정보 요청
- 약물 및 처방전 쿼리
- Supervisor 라우팅 실행 확인
- Memory branching 관찰

예제 질문:
```
You: What's the status of my insurance claim?
You: Can you tell me about my medications?
You: What's my current address on file?
```

채팅 세션을 종료하려면 `quit`, `exit` 또는 `q`를 입력하세요.

## Memory Browser 통합

노트북을 실행한 후 memory browser를 사용하여 메모리를 시각화할 수 있습니다:

1. 구성 요약에서 Memory ID를 기록
2. [Memory Browser](https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/01-tutorials/04-AgentCore-memory/03-advanced-patterns/04-memory-browser) 열기 - `http://localhost:8000`에서 memory 이벤트, 에피소드 및 reflections 시각화 및 탐색
3. Memory ID를 입력하여 탐색:
   - **단기 메모리**: Branch별 이벤트
   - **에피소드**: 세션 수준 통합 메모리
   - **Reflections**: 환자 수준 인사이트

**⏱️ 참고**: 에피소드 및 reflection 생성은 대화 후 10-15분이 소요됩니다. 에피소드/reflections가 즉시 나타나지 않으면 나중에 다시 확인하세요.

## 주요 개념 시연

### 1. 멀티 Agent 조정
- 라우팅을 위한 Supervisor 패턴
- 도메인 전문 지식을 가진 전문 agent
- 실시간 데이터를 위한 동적 tool 사용

### 2. Memory Branching
- Agent별 격리된 대화
- Branch별 이벤트 저장
- 공유 세션 컨텍스트

### 3. Episodic Memory
- extraction, consolidation 및 reflection prompts
- 세션 수준 에피소드
- 환자 수준 reflections

### 4. HealthLake 통합
- 동적 FHIR 쿼리
- 실시간 환자 데이터 액세스
- 모든 데이터는 합성 데이터 (Synthea에서 생성) - 실제 환자 정보는 사용되지 않음

## 커스터마이징

### 새 Agent 추가

```python
@tool
def get_patient_allergies(patient_id: str = PATIENT_ID) -> dict:
    """Get patient allergies from HealthLake"""
    # HealthLake에서 환자의 알레르기 정보 조회
    return query_healthlake('AllergyIntolerance', {'patient': patient_id})

allergy_agent = Agent(
    model="global.anthropic.claude-sonnet-4-20250514-v1:0",
    system_prompt="You handle patient allergies. Use get_patient_allergies tool.",
    tools=[get_patient_allergies]  // 알레르기 조회 tool 등록
)
```

### 다른 Model 사용

agent 생성 시 `model` 매개변수 변경:
```python
Agent(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",  # 다른 모델 지정
    system_prompt="...",
    tools=[...]
)
```
## 추가 리소스

- [Episodic Memory 모범 사례](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/episodic-memory-strategy.html#memory-episodic-retrieve-episodes) - 에피소드를 검색하여 agentic 성능을 개선하는 방법 학습


## 문제 해결

### Branch 생성 오류
"Branch rootEventId is required when creating a branch" 오류가 표시되는 경우:
- **Jupyter 커널 재시작** (Kernel → Restart)
- **모든 셀을 처음부터 다시 실행**하여 수정된 `HealthcareMemoryHooks` 클래스 다시 로드
- 수정 사항은 전문 agent branch를 포크하기 전에 main branch에 초기 이벤트가 있는지 확인합니다

### Memory Hook 오류
"MemorySession.add_turns() got an unexpected keyword argument 'branch_name'" 오류가 표시되는 경우:
- 노트북이 캐시된/이전 코드를 사용하고 있음을 나타냅니다
- **커널을 재시작**하고 모든 셀을 다시 실행하여 API 수정 사항을 적용하세요
- 수정된 코드는 `branch={"name": branch_name}` 형식을 사용합니다

### Model을 사용할 수 없음
"serviceUnavailableException" 오류가 표시되는 경우 다음을 확인하세요:
- 글로벌 inference profile 사용: `global.anthropic.claude-sonnet-4-20250514-v1:0`
- 또는 해당 리전의 리전별 profile

### HealthLake 액세스 거부
IAM 권한에 다음이 포함되어 있는지 확인:
- `healthlake:DescribeFHIRDatastore`
- `healthlake:ReadResource`
- `healthlake:SearchWithGet`

### Memory 생성 실패
다음을 확인하세요:
- IAM 역할에 Bedrock invoke 권한이 있음


## 정리

튜토리얼을 완료한 후 지속적인 요금을 피하기 위해 리소스를 정리할 수 있습니다:

1. 노트북 끝에 있는 **Cleanup** 셀 실행
2. 다음을 삭제하라는 메시지가 표시됩니다:
   - **Memory**: AgentCore Memory 인스턴스
   - **HealthLake Datastore**: FHIR datastore (선택 사항)

각 리소스는 필요에 따라 독립적으로 삭제할 수 있습니다.

### 수동 정리

필요한 경우 리소스를 수동으로 삭제할 수도 있습니다:

```bash
# Memory 삭제
aws bedrock-agentcore-cp delete-memory --memory-id <MEMORY_ID> --region us-east-1

# HealthLake datastore 삭제
aws healthlake delete-fhir-datastore --datastore-id <DATASTORE_ID> --region <REGION>
```

## 더 알아보기

- [AgentCore Memory 문서](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory.html)
- [Strands Agents 가이드](https://strandsagents.com)
- [HealthLake FHIR API](https://docs.aws.amazon.com/healthlake/latest/devguide/working-with-FHIR-healthlake.html)
- [Memory Branching 패턴](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-memory-branching.html)


