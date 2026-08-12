"""Provider-plane authentication routes: password → challenge → TOTP → session.

HTTP only: parse, call the service, shape the response. These are the
unauthenticated and partially-authenticated routes, so no permission dependency
appears here — the challenge token *is* the partial credential, and the service
refuses everything else. No route in this file can return a session token without
a TOTP code having just been verified; there is no configuration that reduces the
two factors to one.
"""

from __future__ import annotations

from fastapi import APIRouter

from verity.modules.tenancy.schemas import (
    ChallengeResponse,
    LoginRequest,
    MfaConfirmRequest,
    MfaConfirmResponse,
    MfaEnrollRequest,
    MfaEnrollResponse,
    MfaVerifyRequest,
    SessionResponse,
)
from verity.modules.tenancy.service import provider_auth_service

router = APIRouter(prefix="/provider", tags=["provider auth"])


@router.post(
    "/login",
    response_model=ChallengeResponse,
    summary="Verify the password; answer with an MFA challenge, never a session",
)
async def login(body: LoginRequest) -> ChallengeResponse:
    challenge = await provider_auth_service.login(email=body.email, password=body.password)
    return ChallengeResponse(
        next_step=challenge.next_step,
        challenge_token=challenge.challenge_token,
        expires_at=challenge.expires_at,
    )


@router.post(
    "/mfa/verify",
    response_model=SessionResponse,
    summary="Exchange a challenge plus a TOTP or recovery code for a session",
)
async def verify_mfa(body: MfaVerifyRequest) -> SessionResponse:
    grant = await provider_auth_service.verify_mfa(
        challenge_token=body.challenge_token,
        code=body.code,
        recovery_code=body.recovery_code,
    )
    return SessionResponse(token=grant.token, expires_at=grant.expires_at)


@router.post(
    "/mfa/enroll",
    response_model=MfaEnrollResponse,
    summary="Start TOTP enrollment: mint the pending secret and provisioning URI",
)
async def enroll_mfa(body: MfaEnrollRequest) -> MfaEnrollResponse:
    start = await provider_auth_service.start_enrollment(challenge_token=body.challenge_token)
    return MfaEnrollResponse(secret=start.secret, otpauth_uri=start.otpauth_uri)


@router.post(
    "/mfa/confirm",
    response_model=MfaConfirmResponse,
    summary="Confirm enrollment with a code; receive the session and recovery codes",
)
async def confirm_mfa(body: MfaConfirmRequest) -> MfaConfirmResponse:
    grant = await provider_auth_service.confirm_enrollment(
        challenge_token=body.challenge_token, code=body.code
    )
    return MfaConfirmResponse(
        token=grant.token,
        expires_at=grant.expires_at,
        recovery_codes=grant.recovery_codes,
    )
