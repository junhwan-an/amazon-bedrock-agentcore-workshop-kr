# Amazon Bedrock AgentCore Runtime에서 Strands Agent와 Amazon Bedrock model을 사용한 스트리밍 응답

## 개요

이 튜토리얼에서는 기존 agent와 함께 Amazon Bedrock AgentCore Runtime을 사용하여 스트리밍 응답을 구현하는 방법을 배웁니다.

실시간 스트리밍 기능을 보여주는 Amazon Bedrock model을 사용하는 Strands Agent 예제에 중점을 둡니다.

### 튜토리얼 세부사항

| Information         | Details                                                                          |
|:--------------------|:---------------------------------------------------------------------------------|
| Tutorial type       | Conversational with Streaming                                                    |
| Agent type          | Single                                                                           |
| Agentic Framework   | Strands Agents                                                                   |
| LLM model           | Anthropic Claude Haiku 4.5                                                      |
| Tutorial components | Streaming responses with AgentCore Runtime. Using Strands Agent and Amazon Bedrock Model |
| Tutorial vertical   | Cross-vertical                                                                   |
| Example complexity  | Easy                                                                             |
| SDK used            | Amazon BedrockAgentCore Python SDK and boto3                                     |

### 튜토리얼 아키텍처

이 튜토리얼에서는 스트리밍 agent를 AgentCore runtime에 배포하는 방법을 설명합니다.

시연 목적으로 스트리밍 기능을 갖춘 Amazon Bedrock model을 사용하는 Strands Agent를 사용합니다.

예제에서는 `get_weather`, `get_time`, `calculator`라는 세 가지 tool을 가진 간단한 agent를 사용하지만, 실시간 스트리밍 응답 기능으로 향상되었습니다.

<div style="text-align:left">
    <img src="images/architecture_runtime.png" width="100%"/>
</div>

### 튜토리얼 주요 기능

* Amazon Bedrock AgentCore Runtime에서 스트리밍 응답 구현
* Server-Sent Events (SSE)를 사용한 실시간 부분 결과 전달
* 스트리밍 기능을 갖춘 Amazon Bedrock model 사용
* 비동기 스트리밍 지원을 갖춘 Strands Agent 사용
* 점진적 응답 표시로 향상된 사용자 경험
