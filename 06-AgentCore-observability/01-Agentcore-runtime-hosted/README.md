# Bedrock AgentCore Runtime Agent를 위한 Amazon CloudWatch의 AgentCore Observability

이 리포지토리는 Amazon OpenTelemetry Python Instrumentation과 Amazon CloudWatch를 사용하여 Amazon Bedrock AgentCore Runtime에서 호스팅되는 Strands, CrewAI, LlamaIndex agent에 대한 AgentCore Observability를 보여주는 예제를 포함합니다. Observability는 개발자가 통합 운영 대시보드를 통해 프로덕션 환경에서 agent 성능을 추적, 디버그 및 모니터링하는 데 도움을 줍니다. OpenTelemetry 호환 텔레메트리 지원과 agent 워크플로우의 각 단계에 대한 상세한 시각화를 통해 Amazon CloudWatch GenAI Observability는 개발자가 agent 동작에 대한 가시성을 쉽게 확보하고 대규모로 품질 표준을 유지할 수 있도록 합니다.

## Framework 예제

### Strands Agents
[Strands](https://strandsagents.com/latest/)는 model 기반 agentic 개발에 중점을 두고 복잡한 워크플로우를 가진 LLM 애플리케이션을 구축하기 위한 프레임워크를 제공합니다.

**위치**: `Strands Agents/`
- 튜토리얼: `runtime_with_strands_and_bedrock_models.ipynb`
- 기능: Amazon Bedrock model과 함께 날씨 및 계산기 도구

### CrewAI
[CrewAI](https://www.crewai.com/)는 역할 기반 agent 오케스트레이션을 통한 멀티 에이전트 협업을 가능하게 합니다.

**위치**: `CrewAI/`
- 튜토리얼: `runtime-with-crewai-and-bedrock-models.ipynb`
- 기능: 협업 agent 패턴

### LlamaIndex
[LlamaIndex](https://www.llamaindex.ai/)는 고급 검색 및 추론 기능을 갖춘 LLM 애플리케이션을 위한 데이터 프레임워크를 제공합니다.

**위치**: `LlamaIndex/`
- 튜토리얼: `runtime_with_llamaindex_and_bedrock_models.ipynb`
- 기능: 산술 도구와 포괄적인 observability를 갖춘 FunctionAgent

## 시작하기

각 프레임워크 폴더에는 다음이 포함되어 있습니다:
- AgentCore Runtime deployment와 CloudWatch observability를 보여주는 Jupyter 노트북
- 필요한 종속성을 나열하는 requirements.txt 파일
- 프레임워크별 지침이 포함된 README.md

## 사용법

1. 탐색하려는 프레임워크의 디렉토리로 이동합니다
2. 요구사항을 설치합니다: `pip install -r requirements.txt`
3. AWS 자격 증명을 구성합니다
4. Jupyter 노트북을 열고 실행합니다

## 주요 기능

- **자동 Observability**: agent가 AgentCore Runtime에서 실행될 때 내장된 텔레메트리 수집
- **CloudWatch 통합**: GenAI Observability 대시보드에서 추적 및 메트릭 확인
- **Framework 유연성**: 여러 agentic 프레임워크 지원

## 정리

예제를 완료한 후:

1. AgentCore Runtime deployment를 제거합니다
2. 생성된 ECR 리포지토리를 정리합니다
3. 더 이상 필요하지 않은 경우 CloudWatch 로그 그룹을 삭제합니다