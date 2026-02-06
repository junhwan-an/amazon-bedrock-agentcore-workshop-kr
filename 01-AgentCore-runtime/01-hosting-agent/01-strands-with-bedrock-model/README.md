# Amazon Bedrock AgentCore Runtime에서 Amazon Bedrock model을 사용하는 Strands Agent 호스팅

## 개요

이 튜토리얼에서는 Amazon Bedrock AgentCore Runtime을 사용하여 기존 agent를 호스팅하는 방법을 배웁니다.

Amazon Bedrock model을 사용하는 Strands Agent 예제에 중점을 둡니다. Amazon Bedrock model을 사용하는 LangGraph는 [여기](../02-langgraph-with-bedrock-model)를 확인하고,
OpenAI model을 사용하는 Strands Agent는 [여기](../03-strands-with-openai-model)를 확인하세요.


### 튜토리얼 세부사항

| 정보                | 세부사항                                                                          |
|:--------------------|:---------------------------------------------------------------------------------|
| 튜토리얼 유형       | 대화형                                                                            |
| Agent 유형          | 단일                                                                              |
| Agentic Framework   | Strands Agents                                                                   |
| LLM model           | Anthropic Claude Haiku 4.5                                                        |
| 튜토리얼 구성요소   | AgentCore Runtime에서 agent 호스팅. Strands Agent와 Amazon Bedrock Model 사용    |
| 튜토리얼 분야       | 범용                                                                              |
| 예제 복잡도         | 쉬움                                                                              |
| 사용된 SDK          | Amazon BedrockAgentCore Python SDK 및 boto3                                      |

### 튜토리얼 아키텍처

이 튜토리얼에서는 기존 agent를 AgentCore runtime에 배포하는 방법을 설명합니다.

시연 목적으로 Amazon Bedrock model을 사용하는 Strands Agent를 사용합니다.

예제에서는 `get_weather`와 `get_time` 두 가지 tool을 가진 매우 간단한 agent를 사용합니다.

<div style="text-align:left">
    <img src="images/architecture_runtime.png" width="100%"/>
</div>

### 튜토리얼 주요 기능

* Amazon Bedrock AgentCore Runtime에서 Agent 호스팅
* Amazon Bedrock model 사용
* Strands Agent 사용
