# AgentCore Runtime에서 MCP server 호스팅하기

## 개요

이 세션에서는 Amazon Bedrock AgentCore Runtime에서 MCP tool을 호스팅하는 방법을 다룹니다.

Amazon Bedrock AgentCore Python SDK를 사용하여 agent 함수를 Amazon Bedrock AgentCore와 호환되는 MCP server로 래핑합니다.
이를 통해 MCP server의 세부 사항은 SDK가 처리하므로 agent의 핵심 기능에 집중할 수 있습니다.

Amazon Bedrock AgentCore Python SDK는 agent 또는 tool 코드를 AgentCore Runtime에서 실행할 수 있도록 준비합니다.

코드를 AgentCore 표준화된 HTTP protocol 또는 MCP protocol 계약으로 변환하여 전통적인 요청/응답 패턴을 위한 직접 REST API 엔드포인트 통신(HTTP protocol) 또는 tool 및 agent server를 위한 Model Context Protocol(MCP Protocol)을 가능하게 합니다.

tool을 호스팅할 때, Amazon Bedrock AgentCore Python SDK는 [session isolation]https://modelcontextprotocol.io/specification/2025-06-18/basic/transports#session-management을 위한 `MCP-Session-Id` 헤더와 함께 [Stateless Streamable HTTP] 전송 프로토콜을 구현합니다. server는 플랫폼에서 생성된 Mcp-Session-Id 헤더를 거부하지 않도록 stateless 작업을 지원해야 합니다.
MCP server는 포트 `8000`에서 호스팅되며 하나의 호출 경로인 `mcp-POST`를 제공합니다. 이 상호작용 엔드포인트는 MCP RPC 메시지를 수신하고 tool의 기능을 통해 처리합니다. application/json과 text/event-stream을 응답 content-type으로 모두 지원합니다.

AgentCore protocol을 MCP로 설정하면, AgentCore Runtime은 MCP server 컨테이너가 `0.0.0.0:8000/mcp` 경로에 있을 것으로 예상합니다. 이는 대부분의 공식 MCP server SDK에서 지원하는 기본 경로입니다.

AgentCore Runtime은 기본적으로 session-isolation을 제공하고 헤더가 없는 모든 요청에 자동으로 Mcp-Session-Id 헤더를 추가하므로 stateless streamable-http server를 호스팅해야 합니다. 이를 통해 MCP client는 동일한 Bedrock AgentCore Runtime session ID에 대한 연결 연속성을 가질 수 있습니다.

`InvokeAgentRuntime` API의 Payload는 완전히 pass through되므로 MCP와 같은 프로토콜의 RPC 메시지를 쉽게 프록시할 수 있습니다.

이 튜토리얼에서 배울 내용:

* tool을 사용하여 MCP server를 생성하는 방법
* 로컬에서 server를 테스트하는 방법
* AWS에 server를 배포하는 방법
* 배포된 server를 호출하는 방법

### 튜토리얼 세부 정보

| 정보                | 세부 사항                                                 |
|:--------------------|:----------------------------------------------------------|
| 튜토리얼 유형       | Tool 호스팅                                               |
| Tool 유형           | MCP server                                                |
| 튜토리얼 구성 요소  | AgentCore Runtime에서 tool 호스팅. MCP server 생성        |
| 튜토리얼 분야       | 범용                                                      |
| 예제 복잡도         | 쉬움                                                      |
| 사용된 SDK          | Amazon BedrockAgentCore Python SDK 및 MCP Client          |

### 튜토리얼 아키텍처
이 튜토리얼에서는 기존 MCP server를 AgentCore runtime에 배포하는 방법을 설명합니다.

시연 목적으로 3개의 tool(`add_numbers`, `multiply_numbers`, `greet_users`)을 가진 매우 간단한 MCP server를 사용합니다.

![MCP architecture](images/hosting_mcp_server.png)

### 튜토리얼 주요 기능

* MCP Server 호스팅