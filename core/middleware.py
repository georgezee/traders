from __future__ import annotations

from django.conf import settings


class AuthStateCookieMiddleware:
    """
    Keep a lightweight, non-HttpOnly cookie in sync with the user's
    authentication state so the SPA can detect whether server-side
    persistence is available.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cookie_name = getattr(settings, "AUTH_STATE_COOKIE_NAME", "traders_auth")
        self.cookie_max_age = getattr(
            settings, "AUTH_STATE_COOKIE_MAX_AGE", settings.SESSION_COOKIE_AGE
        )
        self.cookie_samesite = getattr(settings, "AUTH_STATE_COOKIE_SAMESITE", "Lax")
        self.cookie_secure = getattr(
            settings, "AUTH_STATE_COOKIE_SECURE", settings.SESSION_COOKIE_SECURE
        )

    def __call__(self, request):
        response = self.get_response(request)

        try:
            is_authenticated = bool(getattr(request, "user", None) and request.user.is_authenticated)
            cookie_value = request.COOKIES.get(self.cookie_name)

            if is_authenticated and cookie_value != "1":
                response.set_cookie(
                    self.cookie_name,
                    "1",
                    max_age=self.cookie_max_age,
                    secure=self.cookie_secure,
                    samesite=self.cookie_samesite,
                    httponly=False,
                    path="/",
                )
            elif not is_authenticated and cookie_value:
                response.delete_cookie(
                    self.cookie_name,
                    path="/",
                    samesite=self.cookie_samesite,
                )
        except Exception:
            # Fail silently – auth state cookies are a progressive enhancement.
            pass

        return response
