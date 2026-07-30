from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from google.oauth2 import id_token
from google.auth.transport import requests

from core.config import settings
from schemas.google_oauth import GoogleTokenResponse
from schemas.google_user import GoogleUserInfo


class GoogleOAuthService:

    GOOGLE_AUTH_URL = (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )

    GOOGLE_TOKEN_URL = (
        "https://oauth2.googleapis.com/token"
    )


    SCOPES = [
        "openid",
        "email",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]


    def get_authorization_url(self):

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,

            "redirect_uri": settings.GOOGLE_REDIRECT_URI,

            "response_type": "code",

            "scope": " ".join(self.SCOPES),

            "access_type": "offline",

            "prommpt": "consent"

        }


        return (
            f"{self.GOOGLE_AUTH_URL}"
            f"?{urlencode(params)}"
        )



    async def exchange_code(
        self,
        code: str,
    ) -> GoogleTokenResponse:


        data = {

            "client_id":
                settings.GOOGLE_CLIENT_ID,


            "client_secret":
                settings.GOOGLE_CLIENT_SECRET,


            "code":
                code,


            "grant_type":
                "authorization_code",


            "redirect_uri":
                settings.GOOGLE_REDIRECT_URI,
        }



        async with httpx.AsyncClient() as client:

            response = await client.post(
                self.GOOGLE_TOKEN_URL,
                data=data,
            )


        response.raise_for_status()

        print("RAW GOOGLE TOKEN RESPONSE:")
        print(response.json())

        token_data = GoogleTokenResponse.model_validate(
            response.json()
        )


        token_data.expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                seconds=token_data.expires_in
            )
        )


        return token_data



    def verify_id_token(
    self,
    token: str,
) -> GoogleUserInfo:


        payload = id_token.verify_oauth2_token(
        token,
        requests.Request(),
        settings.GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=10
    )


        email = payload["email"]

        username = email.split("@")[0]


        return GoogleUserInfo(
        google_id=payload["sub"],

        email=email,

        username=username,

        email_verified=payload.get(
            "email_verified",
            False,
        ),
    )



google_oauth_service = GoogleOAuthService()