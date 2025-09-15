#!/usr/bin/env python3
# This script generates an RSA key pair and creates a signed JWT (token)
# using FastMCP's Bearer auth utility

from fastmcp.server.auth.providers.bearer import RSAKeyPair

key_pair = RSAKeyPair.generate()
print(key_pair.public_key)

token = key_pair.create_token(
    subject="dev-user",
    issuer="local-auth",
    audience="fastmcp-tools",
    scopes=["read", "write"],
    expires_in_seconds=10 * 365 * 24 * 60 * 60,  # 10 years
)
print(token)
