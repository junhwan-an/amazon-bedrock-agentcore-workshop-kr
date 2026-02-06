"""
Amazon Bedrock AgentCore Identity를 위한 Authorization Code flow (3LO) 샘플 OAuth2 Callback Server

이 모듈은 AgentCore Identity를 위한 OAuth2 3-legged (3LO) 인증 플로우를 처리하는 로컬 콜백 서버를 구현합니다.
사용자의 브라우저, 외부 OAuth provider(Google, Github 등), 그리고 AgentCore Identity 서비스 간의 중개자 역할을 합니다.

주요 구성 요소:
- localhost:9090에서 실행되는 FastAPI 서버
- 외부 provider로부터의 OAuth2 콜백 리다이렉트 처리
- 사용자 토큰 저장 및 세션 완료 관리
- 준비 상태 확인을 위한 health check 엔드포인트 제공

사용 컨텍스트:
이 서버는 인증된 사용자를 대신하여 외부 리소스(Google Calendar, Github repos 등)에 접근해야 하는
AgentCore Runtime에서 실행되는 agent와 함께 사용됩니다. 일반적인 플로우는 다음과 같습니다:
1. Agent가 외부 리소스에 대한 접근을 요청
2. 사용자가 동의를 위해 OAuth provider로 리다이렉트됨
3. Provider가 이 콜백 서버로 다시 리다이렉트
4. 서버가 AgentCore Identity와 함께 인증 플로우를 완료
"""

import time
import uvicorn
import logging
import argparse
import requests
import json

from datetime import timedelta
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import HTMLResponse
from bedrock_agentcore.services.identity import IdentityClient, UserTokenIdentifier

# OAuth2 콜백 서버를 위한 설정 상수
OAUTH2_CALLBACK_SERVER_PORT = 9090  # 콜백 서버가 수신 대기하는 포트
PING_ENDPOINT = "/ping"  # Health check 엔드포인트
OAUTH2_CALLBACK_ENDPOINT = (
    "/oauth2/callback"  # provider 리다이렉트를 위한 OAuth2 콜백 엔드포인트
)
USER_IDENTIFIER_ENDPOINT = (
    "/userIdentifier/token"  # 사용자 토큰 식별자를 저장하는 엔드포인트
)

logger = logging.getLogger(__name__)


def _is_workshop_studio() -> bool:
    """
    SageMaker Workshop Studio 환경에서 실행 중인지 확인합니다.

    Returns:
        bool: Workshop Studio에서 실행 중이면 True, 그렇지 않으면 False
    """
    try:
        with open("/opt/ml/metadata/resource-metadata.json", "r") as file:
            json.load(file)
        return True
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def get_oauth2_callback_base_url() -> str:
    """
    외부 OAuth provider 리다이렉트(브라우저 접근 가능)를 위한 기본 URL을 가져옵니다.

    이것은 외부 OAuth provider(GitHub, Google 등)가 리다이렉트할 URL입니다.
    OAuth 세션 바인딩이 작동하려면 사용자의 브라우저가 이 URL에 접근할 수 있어야 합니다.

    환경 감지:
    - Workshop Studio: SageMaker 프록시 URL 반환 (https://domain.studio.sagemaker.aws/proxy/9090)
    - 로컬 개발: localhost URL 반환 (http://localhost:9090)

    Returns:
        str: OAuth 콜백을 위한 브라우저 접근 가능한 기본 URL

    사용법:
        이 URL은 다음 용도로 사용됩니다:
        1. Workload identity allowedResourceOauth2ReturnUrls 등록
        2. Agent decorator callback_url 파라미터
        3. 사용자의 브라우저가 콜백 서버에 도달해야 하는 모든 시나리오
    """
    if not _is_workshop_studio():
        base_url = f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}"
        logger.info(f"External OAuth callback base URL (local): {base_url}")
        return base_url

    try:
        import boto3

        with open("/opt/ml/metadata/resource-metadata.json", "r") as file:
            data = json.load(file)
            domain_id = data["DomainId"]
            space_name = data["SpaceName"]

        sagemaker_client = boto3.client("sagemaker")
        response = sagemaker_client.describe_space(
            DomainId=domain_id, SpaceName=space_name
        )
        base_url = response["Url"] + f"/proxy/{OAUTH2_CALLBACK_SERVER_PORT}"
        logger.info(f"External OAuth callback base URL (SageMaker): {base_url}")
        return base_url
    except Exception as e:
        logger.warning(
            f"Error getting SageMaker proxy URL: {e}. Falling back to localhost"
        )
        return f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}"


def _get_internal_base_url() -> str:
    """
    내부 통신(notebook/Streamlit → 콜백 서버)을 위한 기본 URL을 가져옵니다.

    notebook/Streamlit과 OAuth2 콜백 서버가 동일한 환경(로컬 개발에서는 동일한 머신,
    SageMaker에서는 동일한 컨테이너)에서 실행되므로 항상 localhost입니다.

    Returns:
        str: 서버 간 통신을 위한 내부 기본 URL (항상 localhost)

    사용법:
        이 URL은 다음 용도로 사용됩니다:
        1. 사용자 토큰 저장 (POST /userIdentifier/token)
        2. Health check (GET /ping)
        3. 동일한 실행 환경 내의 모든 내부 통신
    """
    return f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}"


class OAuth2CallbackServer:
    """
    AgentCore Identity와 함께 3-legged OAuth 플로우를 처리하기 위한 OAuth2 Callback Server.

    이 서버는 사용자 인증 후 외부 OAuth provider(Google, Github 등)가 리다이렉트하는
    로컬 콜백 엔드포인트 역할을 합니다. AgentCore Identity 서비스와 조율하여
    OAuth 플로우의 완료를 관리합니다.

    서버는 다음을 유지합니다:
    - API 통신을 위한 AgentCore Identity 클라이언트
    - 세션 바인딩을 위한 사용자 토큰 식별자
    - 구성된 라우트가 있는 FastAPI 애플리케이션
    """

    def __init__(self, region: str):
        """
        OAuth2 콜백 서버를 초기화합니다.

        Args:
            region (str): AgentCore Identity 서비스가 배포된 AWS 리전
        """
        # 지정된 리전에 대한 AgentCore Identity 클라이언트 초기화
        self.identity_client = IdentityClient(region=region)

        # 사용자 토큰 식별자를 위한 저장소 - OAuth 세션을 특정 사용자에게 바인딩하는 데 사용됨
        # OAuth 플로우가 시작되기 전에 USER_IDENTIFIER_ENDPOINT를 통해 설정됨
        self.user_token_identifier = None

        # FastAPI 애플리케이션 인스턴스 생성
        self.app = FastAPI()

        # 모든 HTTP 라우트 구성
        self._setup_routes()

    def _setup_routes(self):
        """
        OAuth2 콜백 서버를 위한 FastAPI 라우트를 구성합니다.

        세 개의 엔드포인트를 설정합니다:
        1. POST /userIdentifier/token - 세션 바인딩을 위한 사용자 토큰 식별자 저장
        2. GET /ping - Health check 엔드포인트
        3. GET /oauth2/callback - provider 리다이렉트를 위한 OAuth2 콜백 핸들러
        """

        @self.app.post(USER_IDENTIFIER_ENDPOINT)
        async def _store_user_token(user_token_identifier_value: UserTokenIdentifier):
            """
            OAuth 세션 바인딩을 위한 사용자 토큰 식별자를 저장합니다.

            이 엔드포인트는 OAuth 플로우를 시작하기 전에 호출되어 다가오는 OAuth 세션을
            특정 사용자와 연결합니다. 사용자 토큰 식별자는 일반적으로 인바운드 인증의
            사용자 JWT 토큰에서 파생됩니다.

            Args:
                user_token_identifier_value: 사용자 식별 정보를 포함하는 UserTokenIdentifier 객체
            """
            self.user_token_identifier = user_token_identifier_value

        @self.app.get(PING_ENDPOINT)
        async def _handle_ping():
            """
            서버 준비 상태를 확인하기 위한 Health check 엔드포인트입니다.

            Returns:
                dict: 서버가 작동 중임을 나타내는 간단한 상태 응답
            """
            return {"status": "success"}

        @self.app.get(OAUTH2_CALLBACK_ENDPOINT)
        async def _handle_oauth2_callback(session_id: str):
            """
            외부 provider로부터의 OAuth2 콜백을 처리합니다.

            이것은 사용자 인증 후 외부 OAuth provider(Google, Github 등)가 리다이렉트하는
            핵심 엔드포인트입니다. session_id 파라미터를 받아 AgentCore Identity와 함께
            OAuth 플로우를 완료하는 데 사용합니다.

            OAuth 플로우 컨텍스트:
            1. 사용자가 AgentCore Identity에서 생성된 인증 URL을 클릭
            2. 사용자가 외부 provider(예: Google, Github)에서 접근 권한 부여
            3. Provider가 session_id와 함께 이 콜백으로 리다이렉트
            4. 이 핸들러가 AgentCore Identity를 호출하여 플로우를 완료

            Args:
                session_id (str): OAuth provider 리다이렉트의 세션 식별자

            Returns:
                dict: OAuth 플로우 완료를 나타내는 성공 메시지

            Raises:
                HTTPException: session_id가 누락되었거나 user_token_identifier가 설정되지 않은 경우
            """
            # session_id 파라미터가 존재하는지 검증
            if not session_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing session_id query parameter",
                )

            # 사용자 토큰 식별자가 이전에 저장되었는지 확인
            # OAuth 세션을 올바른 사용자에게 바인딩하는 데 필요함
            if not self.user_token_identifier:
                logger.error("No configured user token identifier")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal Server Error",
                )

            # AgentCore Identity 서비스를 호출하여 OAuth 플로우 완료
            # 이것은 OAuth 세션을 사용자와 연결하고 액세스 토큰을 검색함
            self.identity_client.complete_resource_token_auth(
                session_uri=session_id, user_identifier=self.user_token_identifier
            )

            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>OAuth2 Success</title>
                <style>
                    body {
                        margin: 0;
                        padding: 0;
                        height: 100vh;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        font-family: Arial, sans-serif;
                        background-color: #f5f5f5;
                    }
                    .container {
                        text-align: center;
                        padding: 2rem;
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
                    }
                    h1 {
                        color: #28a745;
                        margin: 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Completed OAuth2 3LO flow successfully</h1>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=200)

    def get_app(self) -> FastAPI:
        """
        구성된 FastAPI 애플리케이션 인스턴스를 가져옵니다.

        Returns:
            FastAPI: 모든 라우트가 설정된 구성된 애플리케이션
        """
        return self.app


def get_oauth2_callback_url() -> str:
    """
    외부 provider(브라우저 접근 가능)를 위한 전체 OAuth2 콜백 URL을 생성합니다.

    이 URL은 workload identity에 등록되며 OAuth 인증 후 사용자의 브라우저를 리다이렉트하기 위해
    AgentCore에서 사용됩니다. 사용자의 브라우저에서 접근 가능해야 합니다.

    환경 인식 동작:
    - 로컬 개발: http://localhost:9090/oauth2/callback 반환
    - SageMaker Studio: https://domain.studio.sagemaker.aws/proxy/9090/oauth2/callback 반환

    Returns:
        str: 엔드포인트 경로가 포함된 완전한 브라우저 접근 가능 콜백 URL

    사용법:
        이 URL은 다음 경우에 사용됩니다:
        1. workload identity에서 allowedResourceOauth2ReturnUrls 등록
        2. @requires_access_token decorator에 callback_url 전달
        3. AgentCore가 브라우저를 콜백으로 리다이렉트해야 하는 모든 시나리오
    """
    base_url = get_oauth2_callback_base_url()
    return f"{base_url}{OAUTH2_CALLBACK_ENDPOINT}"


def store_token_in_oauth2_callback_server(user_token_value: str):
    """
    실행 중인 OAuth2 콜백 서버에 사용자 토큰 식별자를 저장합니다(내부 통신).

    이 함수는 OAuth 플로우를 시작하기 전에 사용자의 토큰 식별자를 저장하기 위해
    콜백 서버에 POST 요청을 보냅니다. 토큰 식별자는 OAuth 세션을 특정 사용자에게
    바인딩하는 데 사용됩니다.

    동일한 실행 환경(동일한 머신 또는 동일한 컨테이너) 내에서 서버 간 통신이므로
    내부 기본 URL(항상 localhost)을 사용합니다.

    Args:
        user_token_value (str): OAuth 플로우에서 사용자를 식별하는 데 사용되는
                               사용자 토큰(일반적으로 Cognito의 JWT 액세스 토큰)

    사용 컨텍스트:
        OAuth 플로우를 시작하기 전에 호출되어 콜백 서버가 OAuth 세션이 어느 사용자에게
        속하는지 알 수 있도록 합니다. 이는 다중 사용자 시나리오에서 적절한 세션 바인딩을
        위해 중요합니다.

    예시:
        # OAuth가 필요한 agent를 호출하기 전에
        bearer_token = reauthenticate_user(client_id)
        store_token_in_oauth2_callback_server(bearer_token)
    """
    if user_token_value:
        base_url = _get_internal_base_url()
        requests.post(
            f"{base_url}{USER_IDENTIFIER_ENDPOINT}",
            json={"user_token": user_token_value},
            timeout=2,
        )
    else:
        logger.error("Ignoring: invalid user_token provided...")


def wait_for_oauth2_server_to_be_ready(
    duration: timedelta = timedelta(seconds=40),
) -> bool:
    """
    OAuth2 콜백 서버가 준비되고 응답할 때까지 대기합니다(내부 통신).

    이 함수는 서버가 성공적으로 응답하거나 타임아웃에 도달할 때까지 서버의
    health check 엔드포인트를 폴링합니다. OAuth 플로우를 시작하기 전에
    서버가 준비되었는지 확인하는 것이 필수적입니다.

    동일한 실행 환경(동일한 머신 또는 동일한 컨테이너) 내에서 서버 간 통신이므로
    내부 기본 URL(항상 localhost)을 사용합니다.

    Args:
        duration (timedelta): 서버 준비를 위해 대기할 최대 시간
                             기본값은 40초

    Returns:
        bool: 타임아웃 내에 서버가 준비되면 True, 그렇지 않으면 False

    사용 컨텍스트:
        OAuth2 콜백 서버 프로세스를 시작한 후 호출되어 OAuth 플로우를 트리거할 수 있는
        agent 호출을 진행하기 전에 콜백을 처리할 준비가 되었는지 확인합니다.

    예시:
        # 서버 프로세스 시작
        server_process = subprocess.Popen([...])

        # 준비 상태 대기
        if wait_for_oauth2_server_to_be_ready():
            # OAuth 지원 작업 진행
            invoke_agent()
        else:
            # 서버 시작 실패 처리
            server_process.terminate()
    """
    logger.info("Waiting for OAuth2 callback server to be ready...")
    base_url = _get_internal_base_url()
    timeout_in_seconds = duration.seconds

    start_time = time.time()
    while time.time() - start_time < timeout_in_seconds:
        try:
            # 서버의 health check 엔드포인트에 ping
            response = requests.get(
                f"{base_url}{PING_ENDPOINT}",
                timeout=2,
            )
            if response.status_code == status.HTTP_200_OK:
                logger.info("OAuth2 callback server is ready!")
                return True
        except requests.exceptions.RequestException:
            # 서버가 아직 준비되지 않음, 계속 대기
            pass

        time.sleep(2)
        elapsed = int(time.time() - start_time)

        # 여전히 대기 중임을 표시하기 위해 10초마다 진행 상황 로깅
        if elapsed % 10 == 0 and elapsed > 0:
            logger.info(f"Still waiting... ({elapsed}/{timeout_in_seconds}s)")

    logger.error(
        f"Timeout: OAuth2 callback server not ready after {timeout_in_seconds} seconds"
    )
    return False


def main():
    """
    OAuth2 콜백 서버를 독립 실행형 애플리케이션으로 실행하기 위한 메인 진입점입니다.

    명령줄 인수를 파싱하고 uvicorn을 사용하여 FastAPI 서버를 시작합니다.
    서버는 지정된 AWS 리전에 대한 OAuth2 콜백을 처리합니다.

    환경 인식 호스트 바인딩:
    - 로컬 개발: 127.0.0.1에 바인딩 (보안을 위해 localhost만)
    - SageMaker Studio: 0.0.0.0에 바인딩 (프록시가 서버에 도달할 수 있도록 허용)

    명령줄 사용법:
        python oauth2_callback_server.py --region us-east-1

    서버는 수동으로 종료될 때까지 실행되며 지정된 리전의 모든 AgentCore agent에 대한
    OAuth2 콜백을 처리합니다.
    """
    parser = argparse.ArgumentParser(description="OAuth2 Callback Server")
    parser.add_argument(
        "-r", "--region", type=str, required=True, help="AWS Region (e.g. us-east-1)"
    )

    args = parser.parse_args()
    oauth2_callback_server = OAuth2CallbackServer(region=args.region)

    # 환경에 따라 호스트 바인딩 결정
    # SageMaker에서는 프록시가 서버에 도달할 수 있도록 0.0.0.0에 바인딩
    # 로컬 개발에서는 보안을 위해 127.0.0.1에 바인딩
    host = "0.0.0.0" if _is_workshop_studio() else "127.0.0.1"
    base_url = get_oauth2_callback_base_url()

    logger.info(
        f"Starting OAuth2 callback server on {host}:{OAUTH2_CALLBACK_SERVER_PORT}"
    )
    logger.info(f"External callback URL: {base_url}{OAUTH2_CALLBACK_ENDPOINT}")

    # uvicorn을 사용하여 FastAPI 서버 시작
    uvicorn.run(
        oauth2_callback_server.get_app(),
        host=host,
        port=OAUTH2_CALLBACK_SERVER_PORT,
    )


if __name__ == "__main__":
    main()
