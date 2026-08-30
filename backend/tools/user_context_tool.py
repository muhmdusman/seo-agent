from strands import tool

from services.oauth_service import OAuthService


def create_user_context_tool(db):

    oauth_service = OAuthService(db)

    @tool
    async def get_user_context(
        user_id: str,
    ) -> dict:
        """
        Return the Google credentials for a user.
        """

        credentials = await oauth_service.get_google_account(
            user_id=user_id,
        )

        if credentials is None:
            raise ValueError(
                "Google account not connected."
            )

        return {
            "user_id": user_id,
            "access_token": credentials.access_token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expires_at,
        }

    return get_user_context