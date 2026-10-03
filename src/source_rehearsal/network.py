import json
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


class HttpClient:
    """Bounded, fixed-host downloads. Errors never expose request URLs or credentials."""

    def get(self, url: str) -> bytes:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            raise NetworkError("Download host or URL is unsupported.")
        request = Request(url, headers={"User-Agent": "SourceRehearsal/0.1"})
        try:
            with build_opener(NoRedirects()).open(request, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            raise NetworkError(
                f"Publisher/API returned HTTP {exc.code}. No data was loaded."
            ) from None
        except (URLError, OSError, TimeoutError):
            raise NetworkError(
                "Publisher/API is unavailable or timed out. Try again later."
            ) from None
        if len(raw) > MAX_BYTES:
            raise NetworkError("Response exceeded the 10 MB limit.")
        return raw

    def json(self, url: str):
        try:
            return json.loads(self.get(url))
        except (ValueError, UnicodeError) as exc:
            if isinstance(exc, NetworkError):
                raise
            raise NetworkError("Publisher/API did not return valid JSON.") from None
