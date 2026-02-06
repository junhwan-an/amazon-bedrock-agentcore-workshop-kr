from langgraph.graph import StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import argparse
import json
import operator
import math

app = BedrockAgentCoreApp()

# LangChain의 @tool 데코레이터로 calculator tool 생성
@tool
def calculator(expression: str) -> str:
    """
    Calculate the result of a mathematical expression.
    
    Args:
        expression: A mathematical expression as a string (e.g., "2 + 3 * 4", "sqrt(16)", "sin(pi/2)")
    
    Returns:
        The result of the calculation as a string
    """
    try:
        # eval() 함수에서 사용 가능한 안전한 함수들만 정의 (보안상 __builtins__ 비움)
        safe_dict = {
            "__builtins__": {},
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow,
            # Math functions
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10, "exp": math.exp,
            "pi": math.pi, "e": math.e,
            "ceil": math.ceil, "floor": math.floor,
            "degrees": math.degrees, "radians": math.radians,
            # Basic operators (for explicit use)
            "add": operator.add, "sub": operator.sub,
            "mul": operator.mul, "truediv": operator.truediv,
        }
        
        # 제한된 namespace에서 수식 평가
        result = eval(expression, safe_dict)
        return str(result)
        
    except ZeroDivisionError:
        return "Error: Division by zero"
    except ValueError as e:
        return f"Error: Invalid value - {str(e)}"
    except SyntaxError:
        return "Error: Invalid mathematical expression"
    except Exception as e:
        return f"Error: {str(e)}"

# 커스텀 weather tool 생성
@tool
def weather():
    """Get weather"""  # 평가용 더미 구현
    return "sunny"

# LangGraph를 사용하여 agent 정의
def create_agent():
    """Create and configure the LangGraph agent"""
    from langchain_aws import ChatBedrock
    
    # ChatBedrock LLM 초기화
    llm = ChatBedrock(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        model_kwargs={"temperature": 0.1}
    )
    
    # LLM에 tool 바인딩 (function calling 활성화)
    tools = [calculator, weather]
    llm_with_tools = llm.bind_tools(tools)
    
    # System message
    system_message = "You're a helpful assistant. You can do simple math calculation, and tell the weather."
    
    # LangGraph의 chatbot node 정의
    def chatbot(state: MessagesState):
        # 첫 메시지가 SystemMessage가 아니면 system message 추가
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_message)] + messages
        
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}
    
    # StateGraph 생성 (MessagesState는 messages 리스트를 자동 관리)
    graph_builder = StateGraph(MessagesState)
    
    # node 추가
    graph_builder.add_node("chatbot", chatbot)
    graph_builder.add_node("tools", ToolNode(tools))  # ToolNode는 tool 실행을 자동 처리
    
    # edge 추가 (tools_condition은 LLM이 tool을 호출했는지 자동 판단)
    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    graph_builder.add_edge("tools", "chatbot")  # tool 실행 후 다시 chatbot으로
    
    # entry point 설정
    graph_builder.set_entry_point("chatbot")
    
    # graph 컴파일하여 실행 가능한 agent 반환
    return graph_builder.compile()

# agent 초기화
agent = create_agent()

@app.entrypoint
def langgraph_bedrock(payload):
    """
    Invoke the agent with a payload
    """
    user_input = payload.get("prompt")
    
    # LangGraph invoke 형식에 맞게 HumanMessage로 변환
    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    
    # 최종 응답 메시지의 content 반환
    return response["messages"][-1].content

if __name__ == "__main__":
    app.run()