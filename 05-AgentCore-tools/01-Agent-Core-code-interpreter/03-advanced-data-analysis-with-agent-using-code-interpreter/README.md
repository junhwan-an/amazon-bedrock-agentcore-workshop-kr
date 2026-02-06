# Amazon AgentCore Bedrock Code Interpreter를 사용한 고급 데이터 분석 - 튜토리얼

## 개요

이 튜토리얼은 Python을 사용한 코드 실행을 통해 고급 데이터 분석을 수행하는 AI Agent를 생성하는 방법을 보여줍니다. Amazon Bedrock AgentCore Code Interpreter를 사용하여 LLM이 생성한 코드를 실행합니다.

이 튜토리얼은 AgentCore Bedrock Code Interpreter를 사용하여 다음을 수행하는 방법을 보여줍니다:

1. 샌드박스 환경 설정
2. 사용자 쿼리를 기반으로 코드를 생성하여 고급 데이터 분석을 수행하는 trands 및 langchain 기반 Agent 구성
3. Code Interpreter를 사용하여 샌드박스 환경에서 코드 실행
4. 결과를 사용자에게 다시 표시



### 튜토리얼 세부사항

| Information         | Details                                                                          |
|:--------------------|:---------------------------------------------------------------------------------|
| Tutorial type       | Conversational                                                                   |
| Agent type          | Single                                                                           |
| Agentic Framework   | Langchain & Strands Agents                                                       |
| LLM model           | Anthropic Claude Sonnet 3.5 & 3.7                                                |
| Tutorial components | AmazonBedrock AgentCore Code Interpreter                                                        |
| Tutorial vertical   | Cross-vertical                                                                   |
| Example complexity  | Easy                                                                             |
| SDK used            | Amazon BedrockAgentCore Python SDK and boto3                                     |


### 튜토리얼 아키텍처

코드 실행 샌드박스는 코드 인터프리터, 셸 및 파일 시스템을 갖춘 격리된 환경을 생성하여 Agent가 사용자 쿼리를 안전하게 처리할 수 있도록 합니다. Large Language Model이 Tool 선택을 지원한 후, 코드가 이 세션 내에서 실행되고, 합성을 위해 사용자 또는 Agent에게 반환됩니다.

<div style="text-align:left">
    <img src="images/code_interpreter.png" width="100%"/>
</div>
