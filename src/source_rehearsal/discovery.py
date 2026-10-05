import json
import sqlite3
import time
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .models import Contract
from .network import HttpClient, NetworkError


@dataclass(frozen=True)
class Candidate:
    publisher: str
    source_url: str
    title: str
    query: str
    search_id: str
    slug: str = ""
    cached: bool = False


def recognize(link: str) -> tuple[str, str] | None:
    try:
        parsed = urlsplit(link)
        if (
            parsed.scheme != "https"
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            return None
    except ValueError:
        return None
    if parsed.hostname == "data.worldbank.org" and parsed.path.rstrip("/") == (
        "/indicator/SP.POP.TOTL"
    ):
        return "World Bank", ""
    if parsed.hostname == "ourworldindata.org" and parsed.path.rstrip("/") in (
        "/grapher/population-unwpp",
        "/grapher/population-unwpp.csv",
    ):
        return "Our World in Data", "population-unwpp"
    return None


def queries(exclude_url: str = "") -> list[str]:
    # Dataset pages span countries/years; validate the selected scope after download.
    choices = [
        '"total population" annual country dataset',
        'site:data.worldbank.org "Population, total" "SP.POP.TOTL"',
        "site:ourworldindata.org/grapher population",
    ]
    baseline = recognize(exclude_url)
    if baseline:
        # Spend all three attempts on alternatives, rather than a baseline-only query.
        index = 1 if baseline[0] == "World Bank" else 2
        choices[index] = (
            'site:ourworldindata.org "population-unwpp"'
            if index == 1
            else '"SP.POP.TOTL" population dataset'
        )
    return choices


class SearchClient:
    def __init__(self, api_key: str, cache: Path, http=None, budget: int = 200):
        self.api_key = api_key.strip()
        self.cache = Path(cache)
        self.http = http or HttpClient()
        self.budget = budget
        try:
            self.cache.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            raise NetworkError(
                "Local search cache folder is unavailable or not writable."
            ) from None
        with self.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, at REAL, data TEXT)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS attempts (at REAL)")

    @contextmanager
    def connection(self):
        try:
            with closing(sqlite3.connect(self.cache, timeout=10)) as db, db:
                yield db
        except sqlite3.Error:
            raise NetworkError(
                "Local search cache is unavailable or invalid. Check the .cache folder."
            ) from None

    def usage(self) -> dict:
        with self.connection() as db:
            used = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        return {"attempts": used, "limit": self.budget, "remaining": max(0, self.budget - used)}

    def search(self, query: str, *, refresh: bool = False) -> dict:
        if not self.api_key:
            raise NetworkError("Configure a SerpApi key to run live discovery.")
        key = sha256(("google/en/v2/" + query).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            cached = db.execute("SELECT at, data FROM cache WHERE key=?", [key]).fetchone()
            if not refresh and cached and time.time() - cached[0] < 24 * 60 * 60:
                return {**json.loads(cached[1]), "cached": True}
            used = db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            if used >= self.budget:
                raise NetworkError(
                    "Local search budget reached. Review your account's remaining credits."
                )
            db.execute("INSERT INTO attempts VALUES (?)", [time.time()])
        url = "https://serpapi.com/search.json?" + urlencode(
            {
                "engine": "google",
                "q": query,
                "api_key": self.api_key,
                "hl": "en",
                **({"no_cache": "true"} if refresh else {}),
            }
        )
        response = self.http.json(url)
        if not isinstance(response, dict):
            raise NetworkError(
                "SerpApi could not complete this search. Check your key and credits."
            )
        metadata = response.get("search_metadata", {})
        information = response.get("search_information", {})
        empty = (
            isinstance(information, dict)
            and information.get("organic_results_state") == "Fully empty"
            and not response.get("organic_results")
        )
        if response.get("error") and not empty:
            raise NetworkError(
                "SerpApi could not complete this search. Check your key and credits."
            )
        if not isinstance(metadata, dict) or metadata.get("status") != "Success":
            raise NetworkError(
                "SerpApi returned an incomplete search. No candidates were inferred."
            )
        if not isinstance(metadata.get("id"), str) or not metadata["id"].strip():
            raise NetworkError("SerpApi search evidence is missing a valid search ID.")
        # Persist and export only the necessary evidence, never full responses or API keys.
        organic = response.get("organic_results", [])
        if not isinstance(organic, list):
            raise NetworkError("SerpApi returned an unexpected search result schema.")
        parameters = response.get("search_parameters", {})
        parameters = parameters if isinstance(parameters, dict) else {}
        returned_query = parameters.get("q")
        returned_query = (
            returned_query.replace(self.api_key, "[redacted]")[:2000]
            if isinstance(returned_query, str)
            else None
        )
        data = {
            "engine": "google",
            "returned_engine": parameters.get("engine")
            if parameters.get("engine") == "google"
            else None,
            "returned_language": parameters.get("hl") if parameters.get("hl") == "en" else None,
            "query_displayed": str(information.get("query_displayed", "")).replace(
                self.api_key, "[redacted]"
            )[:2000]
            if isinstance(information, dict)
            else "",
            "returned_query": returned_query,
            "query_matches_request": returned_query == query
            if returned_query is not None
            else None,
            "query": query,
            "search_id": str(metadata.get("id", "")),
            "created_at": str(metadata.get("created_at", "")),
            "organic_results_state": str(information.get("organic_results_state", ""))[:200]
            if isinstance(information, dict)
            else "",
            "organic_results": [
                {
                    **{
                        k: str(item.get(k, "")).replace(self.api_key, "[redacted]")[:2000]
                        for k in ("title", "link", "snippet")
                    },
                    "position": index,
                }
                for index, item in enumerate(organic[:20], start=1)
                if isinstance(item, dict)
            ],
        }
        with self.connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                [key, time.time(), json.dumps(data)],
            )
        return {**data, "cached": False}

    def discover(self, contract: Contract, exclude_url: str = "", *, refresh: bool = False) -> dict:
        candidates, evidence, errors, diagnostics = [], [], [], []
        excluded = recognize(exclude_url)
        seen = set()
        for query in queries(exclude_url):
            try:
                result = self.search(query, refresh=refresh)
            except NetworkError as exc:
                errors.append({"query": query, "error": str(exc)})
                continue
            evidence.append(result)
            for row in result["organic_results"]:
                supported = recognize(row["link"])
                if result.get("query_matches_request") is False:
                    reason = "Returned query differs from request; result withheld"
                elif not supported:
                    reason = "Unsupported source or indicator"
                elif supported == excluded:
                    reason = "Baseline source excluded"
                elif supported in seen:
                    reason = "Duplicate source"
                else:
                    reason = "Downloadable candidate; metadata review required"
                    publisher, slug = supported
                    seen.add(supported)
                    candidates.append(
                        asdict(
                            Candidate(
                                publisher,
                                row["link"],
                                row["title"],
                                query,
                                result["search_id"],
                                slug,
                                result["cached"],
                            )
                        )
                    )
                diagnostics.append(
                    {
                        "query": query,
                        "search_id": result["search_id"],
                        "position": row["position"],
                        "title": row["title"],
                        "url": row["link"],
                        "reason": reason,
                    }
                )
        return {
            "candidates": candidates,
            "searches": evidence,
            "errors": errors,
            "diagnostics": diagnostics,
            "local_budget": self.usage(),
        }
