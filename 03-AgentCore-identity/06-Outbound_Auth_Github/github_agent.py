import os

import json
import asyncio

from typing import Optional
import httpx
from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token

# 환경 설정
os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"
os.environ["OTEL_PYTHON_EXCLUDED_URLS"] = "/ping,/invocations"

# 앱 초기화
app = BedrockAgentCoreApp()


class StreamingQueue:
    """비동기 streaming을 위한 queue 클래스"""
    def __init__(self):
        self.finished = False
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def finish(self):
        self.finished = True
        await self.queue.put(None)  # stream 종료 신호

    async def stream(self):
        while True:
            item = await self.queue.get()
            if item is None and self.finished:
                break
            yield item


queue = StreamingQueue()


async def on_auth_url(url: str):
    """OAuth 인증 URL이 생성되면 호출되는 콜백 함수"""
    app.logger.info(f"Authorization url: {url}")
    await queue.put(f"Authorization url: {url}")


@tool
def inspect_github_repos() -> str:
    """Inspect and list the user's private GitHub repositories.

    Returns:
        str: A JSON string containing the list of repositories and their details
    """

    # tool 시그니처 도출 시 access_token 파라미터를 고려하지 않도록 중첩 함수를 사용
    # requires_access_token 데코레이터가 OAuth 인증을 처리하고 access_token을 주입
    @requires_access_token(
        provider_name="github-provider",
        scopes=["repo", "read:user"],  # GitHub API 접근 권한 범위
        auth_flow="USER_FEDERATION",  # 사용자 인증 위임 방식
        on_auth_url=on_auth_url,  # 인증 URL 생성 시 호출되는 콜백
        force_authentication=False,
        callback_url=os.environ["CALLBACK_URL"],  # OAuth 리다이렉트 URL
    )
    def inspect_github_repos_tool(access_token: Optional[str] = None) -> str:
        """Inspect and list the user's private GitHub repositories.

        Returns:
            str: A JSON string containing the list of repositories and their details,
                or an authentication required message.
        """
        github_access_token = access_token

        # 토큰이 없으면 인증 필요 메시지 반환
        if not github_access_token:
            return json.dumps(
                {
                    "auth_required": True,
                    "message": "GitHub authentication is required. Please wait while we set up the authorization.",
                    "events": [],
                }
            )

        app.logger.info(f"Using GitHub access token: {github_access_token[:10]}...")

        headers = {"Authorization": f"Bearer {github_access_token}"}

        try:
            with httpx.Client() as client:
                # 사용자 정보 가져오기
                user_response = client.get(
                    "https://api.github.com/user", headers=headers
                )
                user_response.raise_for_status()
                username = user_response.json().get("login", "Unknown")
                app.logger.info(f"✅ User: {username}")

                # 사용자의 repository 검색
                repos_response = client.get(
                    f"https://api.github.com/search/repositories?q=user:{username}",
                    headers=headers,
                )
                repos_response.raise_for_status()
                repos_data = repos_response.json()
                app.logger.info(
                    f"✅ Found {len(repos_data.get('items', []))} repositories"
                )

                repos = repos_data.get("items", [])
                if not repos:
                    return f"No repositories found for {username}."

                # repository 정보 포맷팅
                response_lines = [f"GitHub repositories for {username}:\n"]

                for repo in repos:
                    repo_line = f"📁 {repo['name']}"
                    if repo.get("language"):
                        repo_line += f" ({repo['language']})"
                    repo_line += f" - ⭐ {repo['stargazers_count']}"
                    response_lines.append(repo_line)

                    if repo.get("description"):
                        response_lines.append(f"   {repo['description']}")
                    response_lines.append("")  # 간격을 위한 빈 줄

                return "\n".join(response_lines)

        except httpx.HTTPStatusError as e:
            return f"GitHub API error: {e.response.status_code} - {e.response.text}"
        except Exception as e:
            return f"Error fetching GitHub repositories: {str(e)}"

    return inspect_github_repos_tool()


# Agent를 tool과 선호하는 model로 초기화
agent = Agent(
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=[inspect_github_repos],
    system_prompt="""You are a GitHub assistant. Use the inspect_github_repos tool to fetch private repositories data.
    The inspect_github_repos tool handles token exchange and proper authentication with the GitHub API 
    to obtain private information for the user.""",
)


async def agent_task(user_message: str):
    try:
        await queue.put("Begin agent execution")

        # agent를 비동기로 호출하여 응답 생성
        response = await agent.invoke_async(user_message)

        await queue.put(response.message)
        await queue.put("End agent execution")
    except Exception as e:
        await queue.put(f"Error: {str(e)}")
    finally:
        await queue.finish()


@app.entrypoint
async def agent_invocation(payload):
    user_message = payload.get(
        "prompt",
        "No prompt found in input, please guide customer to create a json payload with prompt key",
    )

    # agent task를 백그라운드에서 실행
    task = asyncio.create_task(agent_task(user_message))

    # streaming 응답을 반환하면서 task가 동시에 실행되도록 함
    async def stream_with_task():
        # queue에서 결과를 받아 실시간으로 stream
        async for item in queue.stream():
            yield item

        # task 완료 대기
        await task

    return stream_with_task()


if __name__ == "__main__":
    app.run()
