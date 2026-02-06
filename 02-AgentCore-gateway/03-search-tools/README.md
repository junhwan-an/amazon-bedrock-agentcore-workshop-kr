# Amazon Bedrock AgentCore Gateway - Semantic search

## 튜토리얼 아키텍처

Amazon Bedrock AgentCore Gateway는 agent와 상호작용해야 하는 tool 및 리소스 간의 통합 연결을 제공합니다. Gateway는 이 연결 계층에서 여러 역할을 수행합니다:

1. **Security Guard**: Gateway는 OAuth 인증을 관리하여 유효한 사용자/agent만 tool/리소스에 액세스할 수 있도록 보장합니다.
2. **Translator**: Gateway는 Model Context Protocol (MCP)과 같은 인기 있는 프로토콜을 사용하여 만들어진 agent 요청을 API 요청 및 Lambda 호출로 변환합니다. 이는 개발자가 서버를 호스팅하거나 프로토콜 통합, 버전 지원, 버전 패치 등을 관리할 필요가 없음을 의미합니다.
3. **Composer**: Gateway는 개발자가 여러 API, 함수 및 tool을 agent가 사용할 수 있는 단일 MCP 엔드포인트로 원활하게 결합할 수 있도록 합니다.
4. **Keychain**: Gateway는 올바른 tool과 함께 사용할 올바른 자격 증명의 주입을 처리하여 agent가 서로 다른 자격 증명 세트가 필요한 tool을 원활하게 활용할 수 있도록 보장합니다.
5. **Researcher**: Gateway는 agent가 모든 tool을 검색하여 특정 컨텍스트나 질문에 가장 적합한 tool만 찾을 수 있도록 합니다. 이를 통해 agent는 소수의 tool이 아닌 수천 개의 tool을 사용할 수 있습니다. 또한 agent의 LLM 프롬프트에 제공해야 하는 tool 세트를 최소화하여 지연 시간과 비용을 줄입니다.
6. **Infrastructure Manager**: Gateway는 완전히 서버리스이며 내장된 observability 및 감사 기능을 제공하여 개발자가 agent와 tool을 통합하기 위해 추가 인프라를 관리할 필요가 없습니다.

![How does it work](images/gw-arch-overview.png)

## AgentCore Gateway는 많은 수의 tool을 가진 MCP 서버의 문제를 해결하는 데 도움을 줍니다

일반적인 엔터프라이즈 환경에서 agent 빌더는 수백 또는 수천 개의 MCP tool을 가진 MCP 서버를 접하게 됩니다. 이러한 대량의 tool은 AI agent에게 낮은 tool 선택 정확도, 증가된 비용, 과도한 tool 메타데이터로 인한 높은 토큰 사용량으로 인한 높은 지연 시간 등의 문제를 야기합니다.
이는 agent를 타사 서비스(예: Zendesk, Salesforce, Slack, JIRA 등) 또는 기존 엔터프라이즈 REST 서비스에 연결할 때 발생할 수 있습니다. AgentCore Gateway는 tool 전반에 걸친 내장 semantic search를 제공하여 agent의 지연 시간, 비용 및 정확도를 개선하면서도 agent에게 필요한 tool을 제공합니다. 사용 사례, LLM model 및 agent 프레임워크에 따라 일반적인 MCP Server의 수백 개의 tool 전체 세트를 제공하는 것과 비교하여 관련 tool에 agent를 집중시킴으로써 최대 3배 더 나은 지연 시간을 확인할 수 있습니다.

![How does it work](images/gateway_tool_search.png)

## 튜토리얼 개요

이 튜토리얼에서는 다음 기능을 다룹니다:

- AWS Lambda 기반 대상을 사용하여 Amazon Bedrock AgentCore Gateway 생성
- AgentCore Gateway semantic search 사용
- Strands Agent를 사용하여 AgentCore Gateway search가 지연 시간을 개선하는 방법 보여주기

- [Amazon Bedrock AgentCore Gateway - Semantic search](./01-gateway-search.ipynb)
