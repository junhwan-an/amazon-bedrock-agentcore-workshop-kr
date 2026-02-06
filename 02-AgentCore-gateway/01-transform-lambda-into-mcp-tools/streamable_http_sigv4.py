"""
AWS SigV4 서명을 사용하는 StreamableHTTP Client Transport

이 모듈은 MCP StreamableHTTPTransport를 확장하여 AWS IAM을 사용하여 인증하는
MCP 서버와의 인증을 위한 AWS SigV4 요청 서명을 추가합니다.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Generator

import httpx
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
from mcp.client.streamable_http import (
    GetSessionIdCallback,
    StreamableHTTPTransport,
    streamablehttp_client,
)
from mcp.shared._httpx_utils import McpHttpClientFactory, create_mcp_http_client
from mcp.shared.message import SessionMessage


class SigV4HTTPXAuth(httpx.Auth):
    """AWS SigV4로 요청에 서명하는 HTTPX Auth 클래스."""

    def __init__(
        self,
        credentials: Credentials,
        service: str,
        region: str,
    ):
        self.credentials = credentials
        self.service = service
        self.region = region
        self.signer = SigV4Auth(credentials, service, region)

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        """SigV4로 요청에 서명하고 요청 헤더에 서명을 추가합니다."""

        # AWS 요청 생성
        headers = dict(request.headers)
        # 'connection' 헤더는 서버 측 서명 계산에 포함되지 않으므로
        # 클라이언트 측에서도 제거해야 서명 불일치 방지
        headers.pop("connection", None)

        # botocore의 AWSRequest 객체로 변환
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )

        # SigV4 서명을 Authorization 헤더에 추가
        self.signer.add_auth(aws_request)

        # 서명된 헤더를 원본 httpx 요청에 병합
        request.headers.update(dict(aws_request.headers))

        yield request


class StreamableHTTPTransportWithSigV4(StreamableHTTPTransport):
    """
    AWS SigV4 서명을 지원하는 Streamable HTTP client transport.

    이 transport는 Lambda 함수 URL 또는 API Gateway 뒤에 있는 서버와 같이
    AWS IAM을 사용하여 인증하는 MCP 서버와의 통신을 가능하게 합니다.
    """

    def __init__(
        self,
        url: str,
        credentials: Credentials,
        service: str,
        region: str,
        headers: dict[str, str] | None = None,
        timeout: float | timedelta = 30,
        sse_read_timeout: float | timedelta = 60 * 5,
    ) -> None:
        """SigV4 서명을 사용하는 StreamableHTTP transport를 초기화합니다.

        Args:
            url: 엔드포인트 URL.
            credentials: 서명을 위한 AWS 자격 증명.
            service: AWS 서비스 이름 (예: 'lambda').
            region: AWS 리전 (예: 'us-east-1').
            headers: 요청에 포함할 선택적 헤더.
            timeout: 일반 작업에 대한 HTTP 타임아웃.
            sse_read_timeout: SSE(Server-Sent Events) 읽기 작업에 대한 타임아웃.
        """
        # 부모 클래스에 SigV4 auth handler 전달
        super().__init__(
            url=url,
            headers=headers,
            timeout=timeout,
            sse_read_timeout=sse_read_timeout,
            auth=SigV4HTTPXAuth(credentials, service, region),
        )

        self.credentials = credentials
        self.service = service
        self.region = region


@asynccontextmanager
async def streamablehttp_client_with_sigv4(
    url: str,
    credentials: Credentials,
    service: str,
    region: str,
    headers: dict[str, str] | None = None,
    timeout: float | timedelta = 30,
    sse_read_timeout: float | timedelta = 60 * 5,
    terminate_on_close: bool = True,
    httpx_client_factory: McpHttpClientFactory = create_mcp_http_client,
) -> AsyncGenerator[
    tuple[
        MemoryObjectReceiveStream[SessionMessage | Exception],
        MemoryObjectSendStream[SessionMessage],
        GetSessionIdCallback,
    ],
    None,
]:
    """
    SigV4 인증을 사용하는 Streamable HTTP용 Client transport.

    이 transport는 Lambda 함수 URL 또는 API Gateway 뒤에 있는 서버와 같이
    AWS IAM을 사용하여 인증하는 MCP 서버와의 통신을 가능하게 합니다.

    Yields:
        다음을 포함하는 튜플:
            - read_stream: 서버로부터 메시지를 읽기 위한 스트림
            - write_stream: 서버로 메시지를 보내기 위한 스트림
            - get_session_id_callback: 현재 세션 ID를 검색하는 함수
    """

    async with streamablehttp_client(
        url=url,
        headers=headers,
        timeout=timeout,
        sse_read_timeout=sse_read_timeout,
        terminate_on_close=terminate_on_close,
        httpx_client_factory=httpx_client_factory,
        auth=SigV4HTTPXAuth(credentials, service, region),
    ) as result:
        yield result
