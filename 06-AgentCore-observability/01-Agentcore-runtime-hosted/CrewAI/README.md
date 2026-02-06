# Amazon Bedrock AgentCore Runtime과 Observability를 사용한 CrewAI Agent

이 튜토리얼은 [CrewAI](https://www.crewai.com/) 여행 agent를 Amazon Bedrock AgentCore Runtime에 배포하고 Amazon CloudWatch를 통해 observability를 구현하는 방법을 보여줍니다.

## 개요

AWS OpenTelemetry 계측과 Amazon CloudWatch 모니터링을 통한 포괄적인 observability와 함께 Amazon Bedrock model을 사용하여 CrewAI agent를 호스팅하는 방법을 배웁니다.

## 사전 요구사항

* Python 3.10+
* 적절한 권한으로 구성된 AWS 자격 증명
* Amazon Bedrock AgentCore SDK
* CrewAI 프레임워크
* Amazon CloudWatch 액세스
* Amazon CloudWatch에서 [transaction search](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Enable-TransactionSearch.html) 활성화

## 시작하기

1. 의존성 설치:
   ```bash
   pip install -r requirements.txt
   ```

2. Jupyter notebook 열기: `runtime-with-crewai-and-bedrock-models.ipynb`

3. 튜토리얼을 따라 진행:
   - 로컬에서 CrewAI agent 생성 및 테스트
   - AgentCore Runtime에 agent 배포
   - OpenTelemetry로 observability 활성화
   - CloudWatch에서 성능 모니터링

## 주요 기능

* 웹 검색 기능을 갖춘 CrewAI 여행 agent
* Amazon Bedrock model (Anthropic Claude Haiku 4.5)
* AgentCore Runtime 호스팅
* CloudWatch observability 및 추적

## 정리

튜토리얼 완료 후:
1. AgentCore Runtime 배포 제거
2. ECR 리포지토리 정리