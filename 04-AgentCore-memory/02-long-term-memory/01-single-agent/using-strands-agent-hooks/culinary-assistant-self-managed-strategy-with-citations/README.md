# Self-Managed Memory Strategy를 사용한 요리 어시스턴트 (인용 포함)

이 샘플은 향상된 인용 추적 기능을 갖춘 Amazon Bedrock AgentCore의 self-managed memory strategy를 보여줍니다. 이 버전은 추출된 장기 메모리에 포괄적인 인용 정보를 추가하여 기본 요리 어시스턴트 예제를 확장합니다.

## 차이점

이 샘플은 추출된 메모리의 출처를 추적하는 인용 기능을 추가합니다:

### 인용 기능

1. **출처 추적**: 각 추출된 메모리에는 출처에 대한 메타데이터가 포함됩니다:
   - Session ID 및 Actor ID
   - 시작 및 종료 타임스탬프
   - 원본 단기 메모리 페이로드가 저장된 S3 URI
   - 추출 작업 ID

2. **인용 메타데이터**: 구조화된 인용 정보가 메모리 메타데이터에 저장됩니다:
   ```python
   citation_info = {
       'source_type': 'short_term_memory',  # 메모리 출처 타입
       'session_id': session_id,  # 세션 식별자
       'actor_id': actor_id,  # 액터 식별자
       'starting_timestamp': starting_timestamp,  # 메모리 추출 시작 시간
       'ending_timestamp': timestamp,  # 메모리 추출 종료 시간
       's3_uri': s3_location,  # S3 저장 위치
       's3_payload_location': s3_location,  # 원본 페이로드 S3 경로
       'extraction_job_id': job_id  # 추출 작업 고유 ID
   }
   ```

3. **사람이 읽을 수 있는 인용**: 각 메모리 콘텐츠에는 인용 텍스트가 추가됩니다:
   ```
   [Citation: Extracted from session {session_id}, actor {actor_id}, source: {s3_location}, job: {job_id}, timestamp: {timestamp}]
   ```

### 수정된 파일

#### `lambda_function.py`

주요 변경 사항은 `MemoryExtractor` 클래스에 있습니다:

- `extract_memories()` 메서드가 이제 `s3_location` 및 `job_id` 매개변수를 받습니다
- `_format_extracted_memories()` 메서드가 인용 정보를 구축하고 메모리 콘텐츠에 추가합니다
- 인용 정보를 추적하기 위한 향상된 로깅

**핵심 메서드**: `_format_extracted_memories` (97번째 줄)
이 메서드는 메타데이터 및 인용 정보와 함께 추출된 메모리를 포맷하여 장기 메모리에서 단기 메모리의 출처로 추적 가능한 링크를 생성합니다.

#### `agentcore_self_managed_memory_demo.ipynb`

인용 기능이 실제로 작동하는 모습을 보여주도록 업데이트되었으며, 추출된 메모리에 이제 출처 속성이 포함되는 방식을 보여줍니다.

## 사용 사례

이 인용 기능이 향상된 버전은 다음과 같은 경우에 특히 유용합니다:

1. **감사 추적**: 메모리가 어디에서 유래했는지에 대한 완전한 기록 유지
2. **디버깅**: 원본 대화 컨텍스트로 역추적
3. **규정 준수**: 데이터 계보 및 출처 속성에 대한 요구 사항 충족
4. **메모리 검증**: S3의 원본 출처와 메모리 콘텐츠를 검증할 수 있는 능력

## 사전 요구 사항

기본 요리 어시스턴트 예제와 동일합니다:
- Python 3.11+
- AWS 자격 증명 구성
- Claude model이 있는 Amazon Bedrock 액세스
- 필요한 AWS 서비스: Lambda, S3, SNS, SQS

## 설정

기본 요리 어시스턴트 예제와 동일한 설정 프로세스를 따르세요. 노트북이 다음을 안내합니다:

1. 인용 지원이 포함된 Lambda 함수 생성
2. 트리거 조건이 있는 메모리 전략 설정
3. 향상된 인용 기능 테스트

## 기본 샘플과의 비교

| 기능 | 기본 샘플 | 인용 포함 |
|---------|------------|----------------|
| 메모리 추출 | ✅ | ✅ |
| S3 페이로드 추적 | ❌ | ✅ |
| 출처 속성 | ❌ | ✅ |
| 작업 ID 추적 | ❌ | ✅ |
| 타임스탬프 컨텍스트 | ❌ | ✅ |
| 인용 메타데이터 | ❌ | ✅ |

## 문서

self-managed memory strategy에 대한 자세한 내용은 [Amazon Bedrock AgentCore 문서](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-self-managed-strategies.html)를 참조하세요.
