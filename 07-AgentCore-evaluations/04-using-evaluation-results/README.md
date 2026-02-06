# Evaluation Analyzer

**AI Agent Evaluation 분석을 며칠/몇 주에서 몇 분으로 단축하세요.**

<p align="center">
  <img src="assets/improvement_loop.svg" alt="Continuous improvement loop for AI agents" width="700">
</p>

## 문제점

AI Agent를 대규모로 평가하면 수백 개의 LLM-as-a-Judge 설명을 얻게 됩니다. 각 설명에는 점수가 부여된 이유에 대한 상세한 추론이 포함되어 있습니다. 사람이 이 모든 것을 읽고 패턴을 찾는 것은 불가능합니다.

## 기능

1. **로드** Evaluation JSON 파일을 로드합니다
2. **필터링** 낮은 점수의 Evaluation을 필터링합니다 (임계값 설정 가능)
3. **분석** AI를 사용하여 실패 패턴을 분석합니다
4. **생성** 구체적인 시스템 프롬프트 수정안을 생성합니다

## 결과물

- **상위 3개 문제점** LLM judge의 증거 인용과 함께 제공
- **변경 전/후 테이블** 정확한 프롬프트 변경 사항 표시
- **완전히 업데이트된 시스템 프롬프트** 복사-붙여넣기 가능한 형태로 제공

샘플 리포트는 [`example_agent_output.md`](example_agent_output.md)를 참조하세요.

## 빠른 시작

```bash
# 1. Install dependencies
# 필요한 Python 패키지 설치
pip install -r requirements.txt

# 2. Add your data
#    - Place evaluation JSONs in eval_data/
#      평가 결과 JSON 파일을 eval_data/ 디렉토리에 배치
#    - Edit system_prompt.txt with your agent's prompt
#      system_prompt.txt에 현재 agent의 시스템 프롬프트 입력

# 3. Run the notebook
# Jupyter 노트북 실행하여 분석 시작
jupyter notebook evaluation_analyzer.ipynb
```

## 요구사항

- Python 3.9+
- Amazon Bedrock에 대한 AWS 자격 증명 구성
- [Strands Evals](https://github.com/strands-agents/strands-evals) 또는 [AWS AgentCore](https://docs.aws.amazon.com/agentcore/)의 Evaluation 데이터

---

**전체 안내 및 문서는 [노트북을 열어보세요](evaluation_analyzer.ipynb).**
