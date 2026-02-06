# AgentCore Runtime에서 대용량 멀티모달 Payload 처리하기

## 개요

이 튜토리얼은 Amazon Bedrock AgentCore Runtime이 Excel 파일 및 이미지와 같은 멀티모달 콘텐츠를 포함하여 최대 100MB의 대용량 payload를 처리하는 방법을 보여줍니다. AgentCore Runtime은 풍부한 미디어 콘텐츠와 대규모 데이터셋을 원활하게 처리하도록 설계되었습니다.

### 튜토리얼 세부사항

| Information         | Details                                                      |
|:--------------------|:-------------------------------------------------------------|
| Tutorial type       | Large Payload & Multi-Modal Processing                       |
| Agent type          | Single                                                       |
| Agentic Framework   | Strands Agents                                               |
| LLM model           | Anthropic Claude Haiku 4.5                                    |
| Tutorial components | Large File Processing, Image Analysis, Excel Data Processing |
| Tutorial vertical   | Data Analysis & Multi-Modal AI                               |
| Example complexity  | Intermediate                                                 |
| SDK used            | Amazon BedrockAgentCore Python SDK                           |

### 주요 기능

* **대용량 Payload 지원**: 최대 100MB 크기의 파일 처리
* **멀티모달 처리**: Excel 파일, 이미지 및 텍스트를 동시에 처리
* **데이터 분석**: 구조화된 데이터 및 시각적 콘텐츠에서 인사이트 추출
* **Base64 인코딩**: JSON payload를 통한 바이너리 데이터의 안전한 전송
