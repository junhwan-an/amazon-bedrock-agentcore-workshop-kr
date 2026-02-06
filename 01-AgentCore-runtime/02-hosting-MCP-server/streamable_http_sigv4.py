"""
StreamableHTTP Client Transport with AWS SigV4 Signing

This module extends the MCP StreamableHTTPTransport to add AWS SigV4 request signing
for authentication with MCP servers that authenticate using AWS IAM.
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
    """HTTPX Auth class that signs requests with AWS SigV4."""

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
        """Signs the request with SigV4 and adds the signature to the request headers."""

        headers = dict(request.headers)
        # 'connection' header는 SigV4 signature 계산에 포함되지 않으므로 제거 필요
        # 포함 시 서버 측 signature 검증 실패 발생
        headers.pop("connection", None)

        # botocore의 AWSRequest로 변환하여 SigV4 서명 준비
        aws_request = AWSRequest(
            method=request.method,
            url=str(request.url),
            data=request.content,
            headers=headers,
        )

        # AWS SigV4 서명을 request에 추가 (Authorization header 등)
        self.signer.add_auth(aws_request)

        # 서명된 header를 원본 httpx request에 병합
        request.headers.update(dict(aws_request.headers))

        yield request


class StreamableHTTPTransportWithSigV4(StreamableHTTPTransport):
    """
    Streamable HTTP client transport with AWS SigV4 signing support.

    This transport enables communication with MCP servers that authenticate using AWS IAM,
    such as servers behind a Lambda function URL or API Gateway.
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
        """Initialize the StreamableHTTP transport with SigV4 signing.

        Args:
            url: The endpoint URL.
            credentials: AWS credentials for signing.
            service: AWS service name (e.g., 'lambda').
            region: AWS region (e.g., 'us-east-1').
            headers: Optional headers to include in requests.
            timeout: HTTP timeout for regular operations.
            sse_read_timeout: Timeout for SSE read operations.
        """
        # 부모 클래스 초기화 시 SigV4 auth handler 전달
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
    Client transport for Streamable HTTP with SigV4 auth.

    This transport enables communication with MCP servers that authenticate using AWS IAM,
    such as servers behind a Lambda function URL or API Gateway.

    Yields:
        Tuple containing:
            - read_stream: Stream for reading messages from the server
            - write_stream: Stream for sending messages to the server
            - get_session_id_callback: Function to retrieve the current session ID
    """

    # MCP의 기본 streamablehttp_client에 SigV4 auth 추가하여 사용
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
