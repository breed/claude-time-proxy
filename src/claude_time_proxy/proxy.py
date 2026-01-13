"""HTTP proxy logic for forwarding requests to Claude API."""

import httpx
from fastapi import Request, Response


async def proxy_request(
    request: Request,
    target_base_url: str,
    api_key: str,
    path: str,
) -> Response:
    """
    Proxy an incoming request to the Claude API.

    Args:
        request: The incoming FastAPI request.
        target_base_url: The base URL of the Claude API.
        api_key: The Anthropic API key to use.
        path: The API path to forward to.

    Returns:
        The proxied response.
    """
    # Build target URL
    target_url = f"{target_base_url}/{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    # Get request body
    body = await request.body()

    # Build headers, replacing/adding the API key
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    headers["x-api-key"] = api_key

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Check if this is a streaming request
        is_streaming = b'"stream":true' in body or b'"stream": true' in body

        if is_streaming:
            # For streaming requests, we need to stream the response back
            async with client.stream(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            ) as upstream_response:
                # Collect response headers
                response_headers = dict(upstream_response.headers)
                response_headers.pop("content-length", None)
                response_headers.pop("transfer-encoding", None)

                # Stream the response
                content = b""
                async for chunk in upstream_response.aiter_bytes():
                    content += chunk

                return Response(
                    content=content,
                    status_code=upstream_response.status_code,
                    headers=response_headers,
                    media_type=upstream_response.headers.get("content-type"),
                )
        else:
            # Non-streaming request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

            response_headers = dict(response.headers)
            response_headers.pop("content-length", None)
            response_headers.pop("transfer-encoding", None)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )
