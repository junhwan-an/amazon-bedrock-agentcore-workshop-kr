# AgentCore Runtime의 Runtime Context 및 Session 관리 이해하기

## 개요

이 튜토리얼에서는 Amazon Bedrock AgentCore Runtime의 runtime context 및 session 관리를 이해하고 작업하는 방법을 배웁니다. 이 예제는 AgentCore Runtime이 session을 처리하고, 여러 호출에 걸쳐 context를 유지하며, agent가 context 객체를 통해 runtime 정보에 액세스하는 방법을 보여줍니다.

Amazon Bedrock AgentCore Runtime은 각 사용자 상호작용에 대해 격리된 session을 제공하여, agent가 여러 호출에 걸쳐 context와 상태를 유지하면서 서로 다른 사용자 간의 완전한 보안 격리를 보장합니다.

### 튜토리얼 세부 정보

|정보| 세부사항|
|:--------------------|:---------------------------------------------------------------------------------|
| 튜토리얼 유형       | Context 및 Session 관리|
| Agent 유형          | Single         |
| Agentic Framework   | Strands Agents |
| LLM model           | Anthropic Claude Haiku 4.5 |
| 튜토리얼 구성요소 | Runtime Context, Session Management, AgentCore Runtime, Strands Agent and Amazon Bedrock Model |
| 튜토리얼 분야   | Cross-vertical                                                                   |
| 예제 복잡도  | Intermediate                                                                     |
| 사용된 SDK            | Amazon BedrockAgentCore Python SDK and boto3|

### 튜토리얼 아키텍처

이 튜토리얼에서는 Amazon Bedrock AgentCore Runtime이 session을 관리하고 agent에 context를 제공하는 방법을 살펴봅니다. 다음을 시연합니다:

1. **Session 연속성**: 동일한 session ID가 여러 호출에 걸쳐 context를 유지하는 방법
2. **Context 객체**: Agent가 context 매개변수를 통해 runtime 정보에 액세스하는 방법
3. **Session 격리**: 서로 다른 session ID가 완전히 격리된 환경을 생성하는 방법
4. **Payload 유연성**: Payload를 통해 agent에 커스텀 데이터를 전달하는 방법

시연 목적으로 이러한 session 관리 기능을 보여주는 Strands Agent를 사용합니다.

    
<div style="text-align:left">
    <img src="images/architecture_runtime.png" width="60%"/>
</div>

### 튜토리얼 주요 기능

* **Session 기반 Context 관리**: AgentCore Runtime이 session 내에서 context를 유지하는 방법 이해
* **Runtime Session 수명주기**: Session 생성, 유지 및 종료에 대해 학습
* **Context 객체 액세스**: Context 매개변수를 통해 session ID와 같은 runtime 정보 액세스
* **Session 격리**: 서로 다른 session이 완전한 격리를 제공하는 방법 시연
* **Payload 처리**: 커스텀 payload 구조를 통한 유연한 데이터 전달
* **호출 간 상태 유지**: 동일한 session 내에서 여러 호출에 걸쳐 agent 상태 유지
