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


def queries(contract: Contract) -> list[str]:
    scope = " ".join(contract.countries)
    return [
        f"population total annual {scope} {contract.start_year} {contract.end_year} dataset",
        "site:data.worldbank.org/indicator/SP.POP.TOTL population total",
        "site:ourworldindata.org/grapher/population-unwpp population estimates data",
    ]


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

    def search(self, query: str) -> dict:
        if not self.api_key:
            raise NetworkError("Configure a SerpApi key to run live discovery.")
        key = sha256(("google/en/" + query).encode()).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            cached = db.execute("SELECT at, data FROM cache WHERE key=?", [key]).fetchone()
            if cached and time.time() - cached[0] < 24 * 60 * 60:
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
        data = {
            "query": query,
            "search_id": str(metadata.get("id", "")),
            "created_at": str(metadata.get("created_at", "")),
            "organic_results_state": str(information.get("organic_results_state", ""))[:200]
            if isinstance(information, dict)
            else "",
            "organic_results": [
                {k: str(item.get(k, ""))[:2000] for k in ("title", "link", "snippet")}
                for item in organic[:20]
                if isinstance(item, dict)
            ],
        }
        with self.connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO cache VALUES (?, ?, ?)",
                [key, time.time(), json.dumps(data)],
            )
        return {**data, "cached": False}

    def discover(self, contract: Contract, exclude_url: str = "") -> dict:
        candidates, evidence, errors, diagnostics = [], [], [], []
        excluded = recognize(exclude_url)
        seen = set()
        for query in queries(contract):
            try:
                result = self.search(query)
            except NetworkError as exc:
                errors.append({"query": query, "error": str(exc)})
                continue
            evidence.append(result)
            for row in result["organic_results"]:
                supported = recognize(row["link"])
                if not supported:
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
                    {"query": query, "title": row["title"], "url": row["link"], "reason": reason}
                )
        return {
            "candidates": candidates,
            "searches": evidence,
            "errors": errors,
            "diagnostics": diagnostics,
            "local_budget": self.usage(),
        }
