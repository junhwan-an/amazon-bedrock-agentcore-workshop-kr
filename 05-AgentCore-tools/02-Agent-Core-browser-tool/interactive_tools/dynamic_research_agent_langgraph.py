"""
Bedrock-AgentCore Code Interpreter를 사용한 동적 연구 Agent
단순화된 아키텍처와 강력한 오류 처리 포함
"""

import asyncio
import json
import os
from typing import Dict, List, TypedDict, Optional, Any, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_aws import ChatBedrockConverse
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

console = Console()

# Agent 상태 정의
class AgentState(TypedDict):
    """적절한 어노테이션을 가진 연구 Agent의 상태"""
    messages: Annotated[List, "append"]  # LangGraph에서 메시지를 누적하기 위한 어노테이션
    research_query: str
    code_session_id: Optional[str]
    research_data: Dict[str, any]
    completed_tasks: List[str]
    errors: List[str]


class ResearchAgent:
    """간소화된 연구 Agent"""
    
    def __init__(self, region: str = "us-west-2", model: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"):
        self.region = region
        self.model = model
        self.llm = ChatBedrockConverse(
            model=model,
            region_name=region
        )
        
        console.print("[cyan]Initializing Bedrock-AgentCore Tools...[/cyan]")
        
        # Code Interpreter 세션 초기화 (샌드박스 환경 생성)
        self.code_client = CodeInterpreter(region)
        self.code_session_id = self.code_client.start()
        console.print(f"✅ Code Interpreter session: {self.code_session_id}")
        
        # 작업 환경 설정
        self._setup_working_environment()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        console.print("\n[yellow]Cleaning up...[/yellow]")
        if self.code_client:
            self.code_client.stop()
    
    def _setup_working_environment(self):
        """상세한 피드백과 함께 code interpreter에서 작업 환경 설정"""
        setup_code = """
import os
import sys
import matplotlib
matplotlib.use('Agg')  # 비인터랙티브 백엔드 사용

# 현재 작업 디렉토리 출력
print(f"Current working directory: {os.getcwd()}")
print(f"Python version: {sys.version}")

# 상세한 피드백과 함께 디렉토리 생성
try:
    os.makedirs('data', exist_ok=True)
    print("✓ Created 'data' directory")
    os.makedirs('visualizations', exist_ok=True)
    print("✓ Created 'visualizations' directory")
    os.makedirs('reports', exist_ok=True)
    print("✓ Created 'reports' directory")
    print("Environment setup complete.")
except Exception as e:
    print(f"Error creating directories: {e}")
    
# 파일 쓰기 테스트
try:
    with open('data/test_file.txt', 'w') as f:
        f.write('Test file writing capability')
    print("✓ Successfully tested file writing")
except Exception as e:
    print(f"Error writing test file: {e}")

# 확인을 위해 디렉토리 나열
print("\\nDirectory structure:")
for root, dirs, files in os.walk('.'):
    level = root.count(os.sep)
    indent = ' ' * 4 * level
    print(f"{indent}{os.path.basename(root) or '.'}/")
    for file in files:
        print(f"{indent}    {file}")
"""
        result = self.code_client.invoke("executeCode", {
            "code": setup_code,
            "language": "python",
            "clearContext": False
        })
        console.print(self._extract_output(result))
    
    def _refresh_file_list(self):
        """샌드박스에서 업데이트된 파일 목록 가져오기"""
        result = self.code_client.invoke("listFiles", {"path": ""})
        return self._extract_output(result).strip().split('\n') if self._extract_output(result).strip() else []
    
    def _extract_output(self, result: Dict) -> str:
        """코드 실행 결과에서 출력 추출"""
        # structuredContent 형식 처리 (stdout/stderr 분리)
        if "structuredContent" in result:
            stdout = result["structuredContent"].get("stdout", "")
            stderr = result["structuredContent"].get("stderr", "")
            return stdout + (f"\nSTDERR: {stderr}" if stderr else "")
        
        # content 배열 형식 처리
        output_parts = []
        if "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    output_parts.append(item.get("text", ""))
        return "\n".join(output_parts)
    
    def _extract_code_block(self, text: str) -> str:
        """마크다운 코드 블록을 포함할 수 있는 텍스트에서 코드 추출"""
        # ```python 형식의 코드 블록 추출
        if "```python" in text:
            start_idx = text.find("```python") + 9
            end_idx = text.find("```", start_idx)
            if end_idx != -1:
                return text[start_idx:end_idx].strip()
        # 언어 지정 없는 ``` 형식의 코드 블록 추출
        elif "```" in text:
            start_idx = text.find("```") + 3
            end_idx = text.find("```", start_idx)
            if end_idx != -1:
                return text[start_idx:end_idx].strip()
        
        # 코드 블록을 찾지 못하면 전체 텍스트 반환
        return text.strip()
    
    def execute_llm_generated_code(self, task_description: str, context: Dict = None) -> Dict[str, Any]:
        """작업을 위해 LLM이 코드를 생성하고 실행하도록 함"""
        console.print(f"\n[bold blue]🤖 LLM generating code for:[/bold blue] {task_description}")
        
        # 컨텍스트와 함께 프롬프트 구성
        prompt = f"""You are working in a Python code interpreter sandbox. 
Task: {task_description}

Available context:
{json.dumps(context, indent=2) if context else 'No previous context'}

Generate Python code to accomplish this task. Be specific and include:
- All necessary imports (pandas, numpy, matplotlib, seaborn, scikit-learn, etc. are available)
- Error handling with try/except blocks
- Clear output with print statements to show progress
- Ensure visualizations have proper titles, labels, and legends
- Save outputs to appropriate directories:
  * data/ - for CSV and JSON files
  * visualizations/ - for plots and charts
  * reports/ - for text reports

Return ONLY the Python code, no explanations."""
        
        # LLM에서 코드 생성
        response = self.llm.invoke([HumanMessage(content=prompt)])
        generated_code = self._extract_code_block(response.content)
        
        # 코드 미리보기 표시
        code_preview = generated_code[:300] + "..." if len(generated_code) > 300 else generated_code
        console.print(Syntax(code_preview, "python"))
        
        # Code Interpreter에서 코드 실행
        result = self.code_client.invoke("executeCode", {
            "code": generated_code,
            "language": "python",
            "clearContext": False  # 세션 컨텍스트 유지 (변수, import 등)
        })
        
        # 출력 추출
        output = self._extract_output(result)
        
        # 오류 확인
        has_error = result.get("isError", False)
        if has_error:
            console.print(f"[red]Execution error:[/red]\n{output}")
        else:
            console.print(f"[green]✅ Code executed successfully[/green]")
        
        # 업데이트된 파일 목록 가져오기
        files = self._refresh_file_list()
        
        return {
            "output": output,
            "error": has_error,
            "files": files
        }
    
    def create_workflow(self) -> StateGraph:
        """모든 단계를 시도하는 간단한 선형 워크플로우 생성"""
        workflow = StateGraph(AgentState)
        
        # 노드 추가 (각 노드는 연구의 한 단계)
        workflow.add_node("understand_query", self.understand_query)
        workflow.add_node("collect_data", self.collect_data)
        workflow.add_node("process_data", self.process_data)
        workflow.add_node("analyze_data", self.analyze_data)
        workflow.add_node("generate_insights", self.generate_insights)
        
        # 선형 플로우 설정 - 모든 단계를 순차적으로 실행
        workflow.set_entry_point("understand_query")
        workflow.add_edge("understand_query", "collect_data")
        workflow.add_edge("collect_data", "process_data")
        workflow.add_edge("process_data", "analyze_data")
        workflow.add_edge("analyze_data", "generate_insights")
        workflow.add_edge("generate_insights", END)
        
        return workflow.compile()
    
    def understand_query(self, state: AgentState) -> AgentState:
        """사용자가 연구하고자 하는 내용 이해"""
        console.print(f"\n[bold magenta]🎯 Understanding research query:[/bold magenta] {state['research_query']}")
        
        # LLM이 쿼리를 분석하도록 함
        prompt = f"""Analyze this research query: '{state['research_query']}'
        
Break it down into:
1. What specific data points need to be collected
2. What analysis techniques would be most appropriate
3. What insights are expected
4. What visualizations would be most informative

Respond in JSON format with the following structure:
{{
  "data_points": [],
  "analysis_techniques": [],
  "expected_insights": [],
  "recommended_visualizations": []
}}"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        understanding = response.content
        
        try:
            # JSON으로 파싱 시도
            json_understanding = json.loads(understanding)
            console.print("[green]Query analysis completed as structured JSON[/green]")
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 원본 텍스트 사용
            console.print("[yellow]Could not parse response as JSON. Using raw text.[/yellow]")
            json_understanding = {"raw_analysis": understanding}
        
        # 이해한 내용의 요약 표시
        console.print("[cyan]Query Understanding:[/cyan]")
        for key, value in json_understanding.items():
            if isinstance(value, list) and value:
                console.print(f"[cyan]• {key}:[/cyan] {', '.join(value[:3])}{'...' if len(value) > 3 else ''}")
            else:
                preview = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                console.print(f"[cyan]• {key}:[/cyan] {preview}")
        
        return {
            **state,
            "research_data": {"query_understanding": json_understanding},
            "completed_tasks": ["understand_query"],
            "errors": []
        }
    
    def collect_data(self, state: AgentState) -> AgentState:
        """연구 쿼리를 기반으로 데이터 수집"""
        console.print("\n[bold magenta]📊 Collecting data...[/bold magenta]")
        
        # 합성 데이터 생성 (실제 환경에서는 API 호출이나 데이터베이스 쿼리로 대체 가능)
        synthetic_data_code = """
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os
import matplotlib.pyplot as plt
import seaborn as sns

# 디렉토리가 존재하는지 확인
os.makedirs('data', exist_ok=True)
os.makedirs('visualizations', exist_ok=True)

# 랜덤 시드 설정 (재현 가능한 결과를 위해)
np.random.seed(42)

# 고객 ID
n_customers = 1000
customer_ids = [f'CUST{i:05d}' for i in range(n_customers)]

# 날짜 범위 - 최근 2년
end_date = datetime.now()
start_date = end_date - timedelta(days=730)
dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]

# 구매 데이터 생성 - 고객당 여러 구매
purchases = []
for cust_id in customer_ids:
    # 랜덤 구매 횟수 (포아송 분포 사용)
    n_purchases = np.random.poisson(3)  
    for _ in range(n_purchases):
        purchase_date = np.random.choice(dates)
        # 최근 몇 개월 동안 구매 확률이 더 높음
        days_ago = (end_date - purchase_date).days
        if days_ago > 365 and random.random() < 0.5:
            continue  # 일부 오래된 구매 건너뛰기
            
        purchases.append({
            'customer_id': cust_id,
            'purchase_date': purchase_date,
            'product_category': np.random.choice(['Electronics', 'Clothing', 'Home', 'Books', 'Beauty', 'Food', 'Sports']),
            'amount': round(np.random.gamma(shape=2, scale=25), 2),
            'satisfaction_score': np.random.choice(range(1, 11), p=[0.01, 0.02, 0.03, 0.05, 0.09, 0.15, 0.25, 0.2, 0.1, 0.1]),
            'delivery_days': np.random.choice(range(1, 10)),
            'is_return': np.random.choice([0, 1], p=[0.95, 0.05])
        })

# DataFrame으로 변환
df = pd.DataFrame(purchases)

# 더 많은 특성 추가
df['is_repeat_purchase'] = df.groupby('customer_id')['purchase_date'].rank(method='first') > 1
df['is_repeat_purchase'] = df['is_repeat_purchase'].astype(int)

# 고객 생애 가치 계산
customer_stats = df.groupby('customer_id').agg(
    total_spent=('amount', 'sum'),
    avg_satisfaction=('satisfaction_score', 'mean'),
    purchase_count=('purchase_date', 'count')
).reset_index()

# 데이터 파일 저장
df.to_csv('data/research_data.csv', index=False)
customer_stats.to_csv('data/customer_stats.csv', index=False)

# 간단한 시각화 생성
plt.figure(figsize=(10, 6))
sns.histplot(df['satisfaction_score'], kde=True, bins=10)
plt.title('Distribution of Customer Satisfaction Scores')
plt.xlabel('Satisfaction Score')
plt.ylabel('Count')
plt.savefig('visualizations/satisfaction_distribution.png', dpi=300)

print(f"Created dataset with {len(df)} purchases from {n_customers} customers")
print(f"Data saved to data/research_data.csv")
print(f"Customer stats saved to data/customer_stats.csv")
print(f"Basic visualization saved to visualizations/satisfaction_distribution.png")
print("\\nFirst 5 rows of data:")
print(df.head())
print("\\nSummary statistics:")
print(df.describe())
"""
        
        # 데이터 생성 코드를 직접 실행
        result = self.code_client.invoke("executeCode", {
            "code": synthetic_data_code,
            "language": "python",
            "clearContext": False
        })
        
        output = self._extract_output(result)
        console.print(output)
        
        # 오류가 있는지 확인
        errors = state["errors"]
        if result.get("isError", False):
            errors.append("Error generating synthetic data")
        
        return {
            **state,
            "research_data": {
                **state["research_data"],
                "data_collection_output": output
            },
            "completed_tasks": state["completed_tasks"] + ["collect_data"],
            "errors": errors
        }
    
    def process_data(self, state: AgentState) -> AgentState:
        """수집된 데이터 처리 및 정제"""
        console.print("\n[bold magenta]🔧 Processing data...[/bold magenta]")
        
        # LLM이 데이터 처리 코드 생성
        result = self.execute_llm_generated_code(
            "Load data/research_data.csv and perform thorough data processing: "
            "1. Handle missing values "
            "2. Remove outliers or cap extreme values "
            "3. Create summary statistics and distributions "
            "4. Add derived features useful for the analysis "
            "5. Create visualizations showing data quality "
            "6. Save processed data as data/processed_data.csv "
            "7. Save summary statistics as data/summary_stats.json",
            context=state["research_data"]
        )
        
        # 오류가 있는지 확인
        errors = state["errors"]
        if result["error"]:
            errors.append("Error processing data")
        
        return {
            **state,
            "research_data": {
                **state["research_data"],
                "processing_output": result["output"],
                "available_files": result["files"]
            },
            "completed_tasks": state["completed_tasks"] + ["process_data"],
            "errors": errors
        }
    
    def analyze_data(self, state: AgentState) -> AgentState:
        """처리된 데이터에 대한 분석 수행"""
        console.print("\n[bold magenta]📈 Analyzing data...[/bold magenta]")
        
        # 사용할 최적의 데이터 파일 찾기 (처리된 데이터 우선)
        available_files = state["research_data"].get("available_files", [])
        data_file = 'data/processed_data.csv' if 'data/processed_data.csv' in available_files else 'data/research_data.csv'
        
        # 분석을 안내할 이해 내용 가져오기
        understanding = state["research_data"].get("query_understanding", {})
        
        # LLM이 연구 쿼리를 기반으로 분석 코드 생성
        result = self.execute_llm_generated_code(
            f"Load {data_file} and perform comprehensive analysis for: {state['research_query']}. "
            "Your analysis should include: "
            "1. Trend analysis over time for satisfaction metrics "
            "2. Correlation analysis between satisfaction and repeat purchases "
            "3. Customer segmentation based on behavior patterns "
            "4. Feature importance for factors driving repeat purchases "
            "5. Create visualizations saved to the visualizations/ directory "
            "6. Save analysis results as data/analysis_results.json",
            context={
                "query": state["research_query"],
                "understanding": understanding,
                "available_files": state["research_data"].get("available_files", [])
            }
        )
        
        # 오류가 있는지 확인
        errors = state["errors"]
        if result["error"]:
            errors.append("Error analyzing data")
        
        return {
            **state,
            "research_data": {
                **state["research_data"],
                "analysis_output": result["output"],
                "available_files": result["files"]
            },
            "completed_tasks": state["completed_tasks"] + ["analyze_data"],
            "errors": errors
        }
    
    def generate_insights(self, state: AgentState) -> AgentState:
        """이전 단계의 성공 여부와 관계없이 인사이트가 포함된 최종 보고서 생성"""
        console.print("\n[bold magenta]💡 Generating insights and report...[/bold magenta]")
        
        # 사용 가능한 파일 목록 가져오기
        available_files = state["research_data"].get("available_files", [])
        if not available_files:
            available_files = self._refresh_file_list()
            
        # 특정 파일 유형 필터링
        data_files = [f for f in available_files if f.endswith('.csv') or f.endswith('.json')]
        viz_files = [f for f in available_files if f.endswith(('.png', '.jpg', '.jpeg', '.svg'))]
        
        # 사용 가능한 경우 분석 결과 로드
        analysis_data = {}
        if 'data/analysis_results.json' in available_files:
            try:
                result = self.code_client.invoke("readFiles", {"paths": ["data/analysis_results.json"]})
                analysis_content = self._extract_output(result)
                analysis_data = json.loads(analysis_content) if analysis_content else {}
            except Exception:
                console.print("[yellow]Could not load analysis results[/yellow]")
        
        # LLM으로 직접 보고서 생성
        prompt = f"""Create a comprehensive markdown research report for: {state['research_query']}

Available data files: {data_files}
Available visualizations: {viz_files}
Completed research steps: {state['completed_tasks']}
Analysis results: {json.dumps(analysis_data, indent=2)[:1000] if analysis_data else 'Not available'}

The report should include:
1. Executive summary
2. Key findings with supporting data
3. Methodology section
4. Analysis of factors driving customer satisfaction
5. Analysis of factors driving repeat purchases
6. Actionable recommendations for businesses
7. References to any visualizations using markdown image syntax: ![description](filename)

Format as a complete professional markdown document with proper headings, bullet points, and formatting.
"""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        report_content = response.content
        
        # 보고서를 파일로 저장
        try:
            save_result = self.code_client.invoke("executeCode", {
                "code": f"import os\nos.makedirs('reports', exist_ok=True)\nwith open('reports/final_report.md', 'w') as f:\n    f.write('''{report_content}''')\nprint('Report saved successfully to reports/final_report.md')",
                "language": "python"
            })
            console.print(self._extract_output(save_result))
        except Exception as e:
            console.print(f"[yellow]Could not save report file: {e}[/yellow]")
        
        # 보고서 표시
        console.print("\n[bold green]📄 Final Report:[/bold green]")
        console.print("="*60)
        
        try:
            # Markdown 렌더링 시도
            md = Markdown(report_content[:5000] + ("..." if len(report_content) > 5000 else ""))
            console.print(md)
        except Exception:
            # Markdown 렌더링이 실패하면 일반 텍스트로 대체
            console.print(report_content[:2000] + "..." if len(report_content) > 2000 else report_content)
        
        console.print("="*60)
        
        # 보고서와 함께 업데이트된 상태 반환
        return {
            **state,
            "messages": state["messages"] + [AIMessage(content=report_content)],
            "research_data": {
                **state["research_data"],
                "final_report": report_content
            },
            "completed_tasks": state["completed_tasks"] + ["generate_insights"]
        }


async def run_research(query: str):
    """LLM이 생성한 코드로 연구 실행"""
    console.print(Panel(
        f"[bold cyan]🚀 Dynamic Research Agent[/bold cyan]\n\n"
        f"Research Query: {query}\n\n"
        "[dim]Using Bedrock-AgentCore Code Interpreter with LLM-generated code[/dim]",
        border_style="blue"
    ))
    
    # Context manager로 리소스 자동 정리
    with ResearchAgent() as agent:
        workflow = agent.create_workflow()
        
        initial_state = {
            "messages": [HumanMessage(content=query)],
            "research_query": query,
            "code_session_id": agent.code_session_id,
            "research_data": {},
            "completed_tasks": [],
            "errors": []
        }
        
        # 워크플로우 비동기 실행
        final_state = await workflow.ainvoke(initial_state)
        
        # 연구 중 생성된 모든 파일 나열
        console.print("\n[bold]Files created during research:[/bold]")
        files = agent._refresh_file_list()
        for file in files:
            if file.endswith(('/')):
                console.print(f"[blue]📁 {file}[/blue]")
            elif file.endswith(('.png', '.jpg', '.jpeg', '.svg')):
                console.print(f"[magenta]🖼️ {file}[/magenta]")
            elif file.endswith(('.csv', '.json')):
                console.print(f"[yellow]📊 {file}[/yellow]")
            elif file.endswith(('.md', '.txt')):
                console.print(f"[green]📝 {file}[/green]")
            else:
                console.print(f"📄 {file}")
        
        console.print(f"\n[bold green]✅ Research completed with {len(final_state['completed_tasks'])} tasks![/bold green]")
        console.print(f"Completed: {', '.join(final_state['completed_tasks'])}")
        
        if final_state.get("errors"):
            console.print(f"[red]⚠️ {len(final_state['errors'])} errors encountered[/red]")
            for error in final_state["errors"]:
                console.print(f"[red]- {error}[/red]")


if __name__ == "__main__":
    import sys
    
    # 명령줄에서 쿼리를 가져오거나 기본값 사용
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Analyze customer satisfaction trends in e-commerce and identify factors that drive repeat purchases"
    
    asyncio.run(run_research(query))