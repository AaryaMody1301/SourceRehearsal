import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import MAX_BYTES

HOSTS = frozenset({"serpapi.com", "api.worldbank.org", "ourworldindata.org"})


class NetworkError(ValueError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def reject_nonfinite(value):
    raise ValueError("JSON contains a non-finite number.")


class HttpClient:
    """Bounded, fixed-host downloads. Errors never expose request URLs or credentials."""

    def get(self, url: str) -> bytes:
        try:
            parsed = urlsplit(url)
            supported = (
                parsed.scheme == "https"
                and parsed.hostname in HOSTS
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 443)
            )
        except ValueError:
            supported = False
        if not supported:
            raise NetworkError("Download host or URL is unsupported.")
        request = Request(url, headers={"User-Agent": "SourceRehearsal/0.1"})
        try:
            with build_opener(NoRedirects()).open(request, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            raise NetworkError(
                f"Publisher/API returned HTTP {exc.code}. No data was loaded."
            ) from None
        except (URLError, OSError, HTTPException):
            raise NetworkError(
                "Publisher/API is unavailable or timed out. Try again later."
            ) from None
        if len(raw) > MAX_BYTES:
            raise NetworkError("Response exceeded the 10 MB limit.")
        return raw

    def json(self, url: str):
        try:
            return json.loads(self.get(url), parse_constant=reject_nonfinite)
        except (ValueError, UnicodeError) as exc:
            if isinstance(exc, NetworkError):
                raise
            raise NetworkError("Publisher/API did not return valid JSON.") from None
