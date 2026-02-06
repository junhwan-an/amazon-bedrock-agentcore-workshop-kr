import os
import datetime
import json
import asyncio

from typing import Optional

from strands import Agent, tool
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.identity.auth import requires_access_token
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 환경 설정
os.environ["STRANDS_OTEL_ENABLE_CONSOLE_EXPORT"] = "true"
os.environ["OTEL_PYTHON_EXCLUDED_URLS"] = "/ping,/invocations"

# Google Calendar API에 필요한 OAuth2 scope
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# app 초기화
app = BedrockAgentCoreApp()


class StreamingQueue:
    """비동기 스트리밍을 위한 큐 - agent 실행 중 실시간으로 메시지를 전달"""
    def __init__(self):
        self.finished = False
        self.queue = asyncio.Queue()

    async def put(self, item):
        await self.queue.put(item)

    async def finish(self):
        self.finished = True
        await self.queue.put(None)  # 스트림 종료 신호

    async def stream(self):
        while True:
            item = await self.queue.get()
            if item is None and self.finished:
                break
            yield item


queue = StreamingQueue()


async def on_auth_url(url: str):
    """OAuth 인증 URL이 생성되면 호출되는 콜백 - 사용자에게 인증 URL 전달"""
    app.logger.info(f"Authorization url: {url}")
    await queue.put(f"Authorization url: {url}")


@tool(
    name="Get_calendar_events_today",
    description="Retrieves the calendar events for the day from your Google Calendar",
)
async def get_calendar():
    # requires_access_token 데코레이터: OAuth 토큰 자동 관리 및 인증 플로우 처리
    @requires_access_token(
        provider_name="google-cal-provider",
        scopes=SCOPES,
        auth_flow="USER_FEDERATION",  # 3-legged OAuth 플로우
        on_auth_url=on_auth_url,
        force_authentication=True,
        callback_url=os.environ["CALLBACK_URL"],
    )
    async def get_calendar_events_today(access_token: Optional[str] = "") -> str:
        google_access_token = access_token
        # 이미 토큰이 있는지 확인
        if not google_access_token:
            app.logger.info("Missing access token")
            return json.dumps(
                {
                    "auth_required": True,
                    "message": "Google Calendar authentication is required. Please wait while we set up the authorization.",
                    "events": [],
                }
            )

        # 제공된 access token으로 credentials 생성
        creds = Credentials(token=google_access_token, scopes=SCOPES)
        try:
            # Google Calendar API 서비스 객체 생성
            service = build("calendar", "v3", credentials=creds)
            # Calendar API 호출
            today_start = datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            # 고정된 Time Zone을 사용합니다. 실제 애플리케이션에서는
            # agent와 상호작용하는 사용자로부터 파생됩니다
            tz = "00:00"
            today_end = today_start.replace(hour=23, minute=59, second=59)
            # RFC3339 형식의 시간 문자열 생성
            time_min = today_start.strftime(f"%Y-%m-%dT00:00:00-{tz}")
            time_max = today_end.strftime(f"%Y-%m-%dT23:59:59-{tz}")

            # 오늘 하루의 이벤트만 조회
            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,  # 반복 이벤트를 개별 인스턴스로 확장
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                return json.dumps({"events": []})  # 빈 events 배열을 JSON으로 반환

            return json.dumps({"events": events})  # events를 객체로 감싸서 반환
        except HttpError as error:
            error_message = str(error)
            return json.dumps({"error": error_message, "events": []})
        except Exception as e:
            error_message = str(e)
            return json.dumps({"error": error_message, "events": []})

    app.logger.info("Run tool")
    try:
        return await get_calendar_events_today()
    except Exception as e:
        app.logger.info(e)


# tool과 선호하는 model로 agent 초기화
agent = Agent(
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    tools=[get_calendar],
)


async def agent_task(user_message: str):
    """Agent 실행을 별도 task로 분리 - 스트리밍과 병렬 처리"""
    try:
        await queue.put("Begin agent execution")

        # 먼저 agent를 호출하여 인증이 필요한지 확인
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

    # agent task 생성 및 시작 (백그라운드에서 실행)
    task = asyncio.create_task(agent_task(user_message))
    app.logger.info(os.environ["CALLBACK_URL"])

    # stream을 반환하되, task가 동시에 실행되도록 보장
    async def stream_with_task():
        # 결과가 들어오는 대로 stream (agent task와 병렬 실행)
        async for item in queue.stream():
            yield item

        # task가 완료되도록 보장
        await task

    return stream_with_task()


if __name__ == "__main__":
    app.logger.info("Starting")
    app.run()
