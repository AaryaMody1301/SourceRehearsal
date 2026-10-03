import json
import sqlite3
import time
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
    parsed = urlsplit(link)
    if parsed.scheme != "https" or parsed.username or parsed.password:
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
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, at REAL, data TEXT)"
            )
            db.execute("CREATE TABLE IF NOT EXISTS attempts (at REAL)")

    def connection(self):
        return sqlite3.connect(self.cache, timeout=10)

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
                "num": 10,
            }
        )
        response = self.http.json(url)
        if not isinstance(response, dict) or response.get("error"):
            raise NetworkError(
                "SerpApi could not complete this search. Check your key and credits."
            )
        metadata = response.get("search_metadata", {})
        if not isinstance(metadata, dict) or metadata.get("status") != "Success":
            raise NetworkError(
                "SerpApi returned an incomplete search. No candidates were inferred."
            )
        # Persist and export only the necessary evidence, never full responses or API keys.
        organic = response.get("organic_results", [])
        if not isinstance(organic, list):
            raise NetworkError("SerpApi returned an unexpected search result schema.")
        data = {
            "query": query,
            "search_id": str(metadata.get("id", "")),
            "created_at": str(metadata.get("created_at", "")),
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

    def discover(self, contract: Contract) -> dict:
        candidates, evidence, errors = [], [], []
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
                if supported and supported not in seen:
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
        return {"candidates": candidates, "searches": evidence, "errors": errors}
