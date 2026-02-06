# Amazon Bedrock AgentCore Runtime과 Observability를 사용한 LlamaIndex Agent

이 튜토리얼은 [LlamaIndex agent](https://developers.llamaindex.ai/python/framework/use_cases/agents/)를 포괄적인 observability 및 텔레메트리 수집과 함께 Amazon Bedrock AgentCore Runtime에 배포하는 방법을 보여줍니다.

## 개요

다음 내용을 학습합니다:
- 산술 도구를 사용하는 LlamaIndex FunctionAgent 생성
- 자동 observability와 함께 AgentCore Runtime에 agent 배포
- agent 워크플로우, tool 호출, LLM 상호작용을 포함한 상세한 텔레메트리 데이터 캡처
- Amazon CloudWatch GenAI Observability 대시보드에서 추적 및 메트릭 확인

## 구축할 내용

다음 기능을 가진 LlamaIndex 산술 agent:
- function tool을 사용한 덧셈 및 곱셈 연산 수행
- 내장된 확장성을 갖춘 Amazon Bedrock AgentCore Runtime에서 실행
- 포괄적인 observability 데이터 자동 생성
- 상세한 추적 정보가 포함된 CloudWatch 대시보드를 통한 모니터링

## 주요 기능

- **LlamaIndex 통합**: 비동기 워크플로우를 사용하는 LlamaIndex FunctionAgent 활용
- **자동 Observability**: LlamaIndex OpenTelemetry 계측을 통한 내장 텔레메트리 수집
- **CloudWatch 통합**: GenAI Observability 대시보드에서 agent 성능 확인

## 사전 요구사항

- 적절한 권한을 가진 AWS 계정
- Amazon Bedrock model 액세스 (Claude Haiku)
- Python 3.10+
- AWS 자격 증명 구성
- Amazon CloudWatch에서 [transaction search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html) 활성화

## 빠른 시작

1. 종속성 설치:
   ```bash
   pip install -r requirements.txt
   ```

2. 노트북 실행:
   ```bash
   jupyter notebook runtime_with_llamaindex_and_bedrock_models.ipynb
   ```

3. observability와 함께 agent를 배포하기 위한 단계별 튜토리얼 따라하기

## 아키텍처

튜토리얼에서 다루는 내용:
- LlamaIndex 계측을 사용한 로컬 개발 및 테스트
- 자동 observability를 갖춘 AgentCore Runtime 배포
- 추적 분석을 위한 CloudWatch 대시보드 액세스
- 향상된 텔레메트리를 위한 수동 span 생성

## 파일

- `runtime_with_llamaindex_and_bedrock_models.ipynb` - 메인 튜토리얼 노트북
- `requirements.txt` - LlamaIndex observability를 포함한 Python 종속성
- `README.md` - 이 문서

## Observability 기능

- **Agent 워크플로우 추적**: LlamaIndex FunctionAgent의 완전한 실행 흐름
- **Tool 호출 모니터링**: 산술 함수 호출 추적
- **LLM 상호작용 추적**: 입력/출력 추적을 포함한 Bedrock model 호출

## 다음 단계

이 튜토리얼을 완료한 후 다음을 수행할 수 있습니다:
- LlamaIndex agent에 더 복잡한 tool 및 워크플로우 추가
- 상세한 observability를 갖춘 멀티 에이전트 아키텍처 구현
- 추적 데이터를 기반으로 커스텀 알림 및 모니터링 설정
- 완전한 가시성을 갖춘 프로덕션 워크로드를 위한 agent 확장