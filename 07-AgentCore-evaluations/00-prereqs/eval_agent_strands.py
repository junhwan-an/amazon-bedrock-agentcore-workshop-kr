from strands import Agent, tool
from strands_tools import calculator  # strands 라이브러리의 계산기 tool
import argparse
import json
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from strands.models import BedrockModel

# Bedrock AgentCore 애플리케이션 초기화
app = BedrockAgentCoreApp()

# 커스텀 tool 생성
@tool
def weather():
    """ Get weather """
    return "sunny"  # 평가용 더미 데이터


model_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
model = BedrockModel(
    model_id=model_id,
)
# Strands Agent 생성 - calculator와 weather tool 사용 가능
agent = Agent(
    model=model,
    tools=[calculator, weather],
    system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather."
)

@app.entrypoint  # BedrockAgentCore의 진입점으로 등록
def strands_agent_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    print("사용자 입력:", user_input)
    response = agent(user_input)
    # Strands Agent 응답 구조에서 텍스트 추출
    return response.message['content'][0]['text']

if __name__ == "__main__":
    app.run()