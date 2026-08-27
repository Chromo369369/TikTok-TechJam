from __future__ import annotations

import json
import re
import sqlite3
from bisect import bisect_right
from collections import Counter
from pathlib import Path


TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "i", "in", "is", "it", "me", "my", "of", "on", "or", "please", "some",
    "that", "the", "this", "to", "want", "with", "would", "you", "looking",
}


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(f"{key} {item}" for key, item in value.items())
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value)


def _terms(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


def _phrase_regex(phrases: tuple[str, ...]) -> re.Pattern:
    ordered = sorted(phrases, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(p) for p in ordered) + r")\b", re.IGNORECASE)


MATERIALS = (
    "cotton", "polyester", "nylon", "leather", "wool", "spandex", "silk", "rayon",
    "fabric", "denim", "linen", "suede", "canvas", "mesh", "fleece", "acrylic",
    "cashmere", "velvet", "satin", "chiffon", "faux leather", "genuine leather",
)
COLORS = (
    "black", "white", "blue", "red", "pink", "green", "brown", "gray", "grey",
    "purple", "yellow", "orange", "beige", "navy", "gold", "silver", "tan",
    "multicolor", "maroon", "turquoise", "ivory", "khaki", "burgundy", "charcoal",
    "olive", "teal",
)
STYLE_PHRASES = (
    "slim fit", "regular fit", "relaxed fit", "athletic fit", "loose fit",
    "v neck", "crew neck", "round neck", "turtleneck", "long sleeve",
    "short sleeve", "sleeveless", "button down", "zip up", "pullover",
    "high waist", "low rise", "bootcut", "skinny", "straight leg", "wide leg",
    "a line", "fitted", "oversized",
)
USE_CASE_PHRASES = (
    "hiking", "running", "gym", "yoga", "workout", "outdoor", "work", "office",
    "formal", "casual", "wedding", "party", "beach", "travel", "winter",
    "summer", "athletic", "everyday", "school", "training", "cycling",
    "swimming", "camping",
)
FEATURE_PHRASES = (
    "waterproof", "water resistant", "breathable", "adjustable", "stretch",
    "lightweight", "padded", "reversible", "quick dry", "non slip",
    "moisture wicking", "pockets", "zipper", "elastic waist",
    "machine washable", "wrinkle resistant", "uv protection", "antimicrobial",
    "insulated", "reflective",
)
SIZE_STANDALONE_PHRASES = (
    "petite", "plus size", "wide width", "narrow width", "big and tall",
    "one size fits all", "tall length", "short length",
)
SIZE_CONTEXT_RE = re.compile(
    r"\bsizes?\b[^.;\n]{0,15}?\b(xxxl|xxl|xxs|xl|xs|s|m|l|\d{1,2})\b", re.IGNORECASE
)
BUDGET_DOLLAR_RE = re.compile(r"\$\s?(\d{1,5}(?:\.\d{1,2})?)")
BUDGET_WORD_RE = re.compile(
    r"(?:under|below|less than|around|about|budget(?:\s+of)?)\s+\$?\s?(\d{1,5}(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
BUDGET_CEILING_WORDS = ("under", "below", "less than", "<=", "at most", "no more than")

MATERIAL_RE = _phrase_regex(MATERIALS)
COLOR_RE = _phrase_regex(COLORS)
STYLE_RE = _phrase_regex(STYLE_PHRASES)
USE_CASE_RE = _phrase_regex(USE_CASE_PHRASES)
FEATURE_RE = _phrase_regex(FEATURE_PHRASES)
PHRASE_REGEX = {
    "material": MATERIAL_RE,
    "color": COLOR_RE,
    "style": STYLE_RE,
    "use_case": USE_CASE_RE,
    "feature": FEATURE_RE,
}

CATEGORY_GENERIC_WORDS = {"clothing", "shoes", "jewelry"}
BRAND_STOPWORDS = {"inc", "llc", "company", "brand", "store", "official", "the", "and", "co"}

ATTRS = ("category", "material", "color", "size", "style", "brand", "budget", "use_case", "feature")

TAG_TO_ATTR = {
    "fit": ("style", "size"),
    "comfort": ("feature", "material"),
    "durability": ("material", "feature"),
    "style": ("style",),
    "quality": ("feature", "material"),
    "price": ("budget",),
    "value": ("budget",),
    "color": ("color",),
    "material": ("material",),
    "size": ("size",),
    "brand": ("brand",),
}

NO_PREF_MARKERS = (
    "no preference", "don't have a preference", "dont have a preference",
    "doesn't matter", "does not matter", "any is fine", "anything works",
    "not particular", "use your judgment", "no particular preference",
    "not sure", "whatever works", "any will do", "no strong preference",
)
OVERRIDE_MARKERS = (
    "actually,", "actually i", "ignore my earlier", "ignore that",
    "ignore what i said", "instead of", "changed my mind", "never mind",
    "forget what i said", "scratch that", "on second thought", "to correct myself",
)

TEMPLATES = {
    "category": "Could you tell me more specifically what category or type of item you're looking for?",
    "material": "Do you have a material preference, like cotton, leather, or polyester?",
    "color": "Is there a particular color you'd like?",
    "size": "What size do you need?",
    "style": "Do you have a style or fit preference?",
    "brand": "Is there a brand you'd like me to stick to?",
    "budget": "What's your budget range for this?",
    "feature": "Are there any specific features that matter to you, like waterproof or adjustable?",
    "use_case": "What will you mainly use this for?",
    "other": "Is there anything else important about what you're looking for?",
}
DEFAULT_MESSAGE = "Here are my best matches so far based on everything you've told me."


def _is_generic_category_part(part: str) -> bool:
    words = [w for w in part.lower().replace("&", " ").split() if w]
    return bool(words) and all(w in CATEGORY_GENERIC_WORDS for w in words)


def _category_parts(categories: object) -> list[str]:
    parts: list[str] = []
    for value in categories or []:
        for part in str(value).split(","):
            part = part.strip()
            if part and not _is_generic_category_part(part):
                parts.append(part)
    return parts


def _canonical_category(categories: object) -> str:
    parts = _category_parts(categories)
    return " ".join(parts[-2:]).strip().lower() if parts else "product"


def _category_tokens(categories: object) -> set[str]:
    tokens: set[str] = set()
    for part in _category_parts(categories):
        tokens.update(_terms(part))
    return tokens


def _brand_tokens(store: str) -> set[str]:
    return {t for t in _terms(store) if len(t) >= 3 and t not in BRAND_STOPWORDS}


class Agent:
    """Adaptive clarification agent: for each un-asked attribute, scores
    expected-candidates-eliminated (Gini-Simpson impurity over the current
    hard-filtered pool) times a Bayesian-learned P(useful answer), and always
    surfaces the current top-10 best matches alongside the highest-value
    question.
    """

    def __init__(self, catalog_path: str | Path = "data/catalog.jsonl") -> None:
        self.catalog_path = Path(catalog_path)
        self.connection = sqlite3.connect(":memory:")
        self._sessions: dict[str, dict] = {}
        self._all_ids: set[str] = set()
        self._price: dict[str, float | None] = {}
        self._rating_number: dict[str, int] = {}
        self._average_rating: dict[str, float] = {}
        self._primary: dict[str, dict[str, object]] = {attr: {} for attr in ATTRS}
        self._value_index: dict[str, dict[object, set[str]]] = {attr: {} for attr in ATTRS}
        self._budget_edges: list[tuple[float, float]] = []
        self._popularity_sorted_ids: list[str] = []
        self._attr_alpha: dict[str, float] = {attr: 2.0 for attr in ATTRS + ("other",)}
        self._attr_beta: dict[str, float] = {attr: 2.0 for attr in ATTRS + ("other",)}
        self._build_index()

    # ------------------------------------------------------------------ #
    # Index construction
    # ------------------------------------------------------------------ #

    def _build_index(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            "CREATE VIRTUAL TABLE products USING fts5("
            "parent_asin UNINDEXED, title, categories, features, details, store, description, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        batch: list[tuple[str, str, str, str, str, str, str]] = []
        with self.catalog_path.open(encoding="utf-8") as handle:
            for line in handle:
                product = json.loads(line)
                asin = str(product["parent_asin"])
                self._all_ids.add(asin)

                title = _text(product.get("title"))
                features_raw = product.get("features") or []
                description_raw = product.get("description") or []
                details = product.get("details") or {}
                store = product.get("store")
                categories = product.get("categories") or []
                price = product.get("price")
                rating_number = product.get("rating_number")
                average_rating = product.get("average_rating")

                self._price[asin] = float(price) if isinstance(price, (int, float)) else None
                self._rating_number[asin] = int(rating_number) if isinstance(rating_number, (int, float)) else 0
                self._average_rating[asin] = float(average_rating) if isinstance(average_rating, (int, float)) else 0.0

                searchable = " ".join(
                    [title, _text(features_raw), _text(description_raw), _text(details), _text(store)]
                )
                normalized = searchable.replace("-", " ").lower()

                for attr, regex in PHRASE_REGEX.items():
                    self._assign_phrase_attr(attr, asin, regex, normalized)

                size_values = {m.lower() for m in SIZE_CONTEXT_RE.findall(normalized)}
                for phrase in SIZE_STANDALONE_PHRASES:
                    if phrase in normalized:
                        size_values.add(phrase)
                if size_values:
                    self._primary["size"][asin] = sorted(size_values)[0]
                    for value in size_values:
                        self._value_index["size"].setdefault(value, set()).add(asin)
                else:
                    self._primary["size"][asin] = "unknown"

                self._primary["category"][asin] = _canonical_category(categories)
                for token in _category_tokens(categories):
                    self._value_index["category"].setdefault(token, set()).add(asin)

                store_label = str(store).strip().lower() if store else None
                self._primary["brand"][asin] = store_label or "unknown"
                if store_label:
                    for token in _brand_tokens(str(store)):
                        self._value_index["brand"].setdefault(token, set()).add(asin)

                batch.append(
                    (
                        asin,
                        title,
                        _text(categories),
                        _text(features_raw),
                        _text(details),
                        _text(store),
                        _text(description_raw),
                    )
                )
                if len(batch) >= 1000:
                    cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
                    batch.clear()
        if batch:
            cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
        self.connection.commit()

        self._build_budget_bins()
        self._popularity_sorted_ids = sorted(
            self._all_ids,
            key=lambda a: (-(self._rating_number.get(a, 0)), -(self._average_rating.get(a, 0.0))),
        )

    def _assign_phrase_attr(self, attr: str, asin: str, regex: re.Pattern, normalized_text: str) -> None:
        values: list[str] = []
        seen: set[str] = set()
        for match in regex.findall(normalized_text):
            value = match.lower()
            if value not in seen:
                seen.add(value)
                values.append(value)
        if not values:
            self._primary[attr][asin] = "unknown"
            return
        self._primary[attr][asin] = values[0]
        for value in values:
            self._value_index[attr].setdefault(value, set()).add(asin)

    def _build_budget_bins(self, num_bins: int = 8) -> None:
        priced = sorted((a for a in self._all_ids if self._price[a] is not None), key=lambda a: self._price[a])
        n = len(priced)
        edges: list[tuple[float, float]] = []
        if n > 0:
            for i in range(num_bins):
                lo_idx = i * n // num_bins
                hi_idx = max((i + 1) * n // num_bins - 1, lo_idx)
                edges.append((self._price[priced[lo_idx]], self._price[priced[hi_idx]]))
        self._budget_edges = edges
        for asin in self._all_ids:
            price = self._price[asin]
            if price is None:
                self._primary["budget"][asin] = "unknown"
                continue
            idx = self._budget_bin_index(price)
            self._primary["budget"][asin] = idx
            self._value_index["budget"].setdefault(idx, set()).add(asin)

    def _budget_bin_index(self, price: float) -> int:
        highs = [hi for (_, hi) in self._budget_edges]
        idx = bisect_right(highs, price)
        return min(idx, len(self._budget_edges) - 1)

    def _extract_budget(self, text: str) -> tuple[list[int], float] | None:
        if not text or not self._budget_edges:
            return None
        lowered = text.lower()
        match = BUDGET_DOLLAR_RE.search(lowered) or BUDGET_WORD_RE.search(lowered)
        if not match:
            return None
        try:
            value = float(match.group(1))
        except (ValueError, IndexError):
            return None
        ceiling = any(word in lowered for word in BUDGET_CEILING_WORDS)
        bins: list[int] = []
        for idx, (lo, hi) in enumerate(self._budget_edges):
            if ceiling:
                if lo <= value:
                    bins.append(idx)
            else:
                span = max(hi - lo, 1.0)
                if lo - span <= value <= hi + span:
                    bins.append(idx)
        return (bins, value) if bins else None

    # ------------------------------------------------------------------ #
    # Session lifecycle
    # ------------------------------------------------------------------ #

    def reset(self, session_id: str, user_profile: dict) -> None:
        boosts: dict[str, float] = {}
        for tag in (user_profile or {}).get("preference_tags", []) or []:
            for attr in TAG_TO_ATTR.get(str(tag).lower(), ()):
                boosts[attr] = boosts.get(attr, 1.0) * 1.2
        self._sessions[session_id] = {
            "candidate_ids": None,  # None means "unfiltered / all products"
            "disclosed": {},
            "no_pref": set(),
            "asked_count": Counter(),
            "last_asked": None,
            "query_terms": [],
            "query_terms_set": set(),
            "turn": 0,
            "boosts": boosts,
        }

    def respond(self, session_id: str, user_message: str, turn: int, top_k: int) -> dict:
        if session_id not in self._sessions:
            raise RuntimeError("reset must be called before respond")
        state = self._sessions[session_id]
        state["turn"] = turn
        message_text = user_message or ""
        lowered = message_text.lower()
        normalized = lowered.replace("-", " ")

        if turn > 1 and any(marker in lowered for marker in OVERRIDE_MARKERS):
            state["candidate_ids"] = None
            state["disclosed"] = {}
            state["no_pref"] = set()
            state["asked_count"] = Counter()

        newly_matched: dict[str, set[object]] = {}
        filters: dict[str, set[str]] = {}

        for attr, regex in PHRASE_REGEX.items():
            found = {m.lower() for m in regex.findall(normalized)}
            if found:
                asins: set[str] = set()
                for value in found:
                    asins |= self._value_index[attr].get(value, set())
                if asins:
                    newly_matched[attr] = found
                    filters[attr] = asins

        size_found = {m.lower() for m in SIZE_CONTEXT_RE.findall(normalized)}
        for phrase in SIZE_STANDALONE_PHRASES:
            if phrase in normalized:
                size_found.add(phrase)
        if size_found:
            asins = set()
            for value in size_found:
                asins |= self._value_index["size"].get(value, set())
            if asins:
                newly_matched["size"] = size_found
                filters["size"] = asins

        cat_tokens = {t for t in _terms(message_text) if t in self._value_index["category"]}
        if cat_tokens:
            asins = set()
            for token in cat_tokens:
                asins |= self._value_index["category"].get(token, set())
            if asins:
                newly_matched["category"] = cat_tokens
                filters["category"] = asins

        brand_tokens = {t for t in _terms(message_text) if t in self._value_index["brand"]}
        if brand_tokens:
            asins = set()
            for token in brand_tokens:
                asins |= self._value_index["brand"].get(token, set())
            if asins:
                newly_matched["brand"] = brand_tokens
                filters["brand"] = asins

        budget_hit = self._extract_budget(message_text)
        if budget_hit:
            bins, _value = budget_hit
            asins = set()
            for idx in bins:
                asins |= self._value_index["budget"].get(idx, set())
            if asins:
                newly_matched["budget"] = {"budget"}
                filters["budget"] = asins

        cur = state["candidate_ids"]
        for attr, asins in filters.items():
            base = cur if cur is not None else self._all_ids
            updated = base & asins
            if updated:
                cur = updated
                state["disclosed"].setdefault(attr, set()).update(newly_matched.get(attr, set()))
        state["candidate_ids"] = cur

        no_pref_hit = any(marker in lowered for marker in NO_PREF_MARKERS)
        last_attr = state["last_asked"]
        if last_attr:
            if last_attr in newly_matched:
                self._attr_alpha[last_attr] += 1.0
            else:
                self._attr_beta[last_attr] += 1.0
                if no_pref_hit:
                    state["no_pref"].add(last_attr)

        for token in _terms(message_text):
            if token not in state["query_terms_set"]:
                state["query_terms_set"].add(token)
                state["query_terms"].append(token)
        if len(state["query_terms"]) > 60:
            dropped = state["query_terms"][: len(state["query_terms"]) - 60]
            state["query_terms"] = state["query_terms"][-60:]
            state["query_terms_set"] -= set(dropped)

        pool_ids = state["candidate_ids"]
        bm25_ids = self._bm25_order(state["query_terms"])
        recommendations = self._rank(pool_ids, bm25_ids, top_k)

        ask_attribute = self._choose_attribute(state, pool_ids, bm25_ids) if turn < 10 else None
        if ask_attribute:
            state["asked_count"][ask_attribute] += 1
            state["last_asked"] = ask_attribute
            message = TEMPLATES.get(ask_attribute, DEFAULT_MESSAGE)
        else:
            state["last_asked"] = None
            message = DEFAULT_MESSAGE

        return {
            "message": message,
            "ask_attribute": ask_attribute,
            "recommendations": [{"parent_asin": asin} for asin in recommendations],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
        }

    # ------------------------------------------------------------------ #
    # Retrieval and question scoring
    # ------------------------------------------------------------------ #

    def _bm25_order(self, terms: list[str], limit: int = 3000) -> list[str]:
        if not terms:
            return []
        expression = " OR ".join(f'"{term}"' for term in terms[-60:])
        rows = self.connection.execute(
            "SELECT parent_asin FROM products WHERE products MATCH ? "
            "ORDER BY bm25(products, 0.0, 6.0, 4.0, 2.5, 2.5, 1.5, 1.0) LIMIT ?",
            (expression, limit),
        ).fetchall()
        return [str(row[0]) for row in rows]

    def _rank(self, pool_ids: set[str] | None, bm25_ids: list[str], top_k: int) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for asin in bm25_ids:
            if (pool_ids is None or asin in pool_ids) and asin not in seen:
                seen.add(asin)
                result.append(asin)
                if len(result) >= top_k:
                    return result
        source = pool_ids if pool_ids is not None else self._all_ids
        for asin in self._popularity_sorted_ids:
            if asin in source and asin not in seen:
                seen.add(asin)
                result.append(asin)
                if len(result) >= top_k:
                    return result
        if len(result) < top_k:
            for asin in self._popularity_sorted_ids:
                if asin not in seen:
                    seen.add(asin)
                    result.append(asin)
                    if len(result) >= top_k:
                        break
        return result

    def _choose_attribute(self, state: dict, pool_ids: set[str] | None, bm25_ids: list[str]) -> str | None:
        if pool_ids is not None and len(pool_ids) > 2000 and bm25_ids:
            scoring_pool = pool_ids & set(bm25_ids)
            if len(scoring_pool) < 2:
                scoring_pool = pool_ids
        elif pool_ids is None:
            scoring_pool = set(bm25_ids) if bm25_ids else set(list(self._all_ids)[:2000])
        else:
            scoring_pool = pool_ids

        if len(scoring_pool) <= 1:
            return None

        best_attr: str | None = None
        best_score = 0.0
        for attr in ATTRS:
            if attr in state["no_pref"]:
                continue
            counts = Counter(self._primary[attr].get(a, "unknown") for a in scoring_pool)
            if len(counts) <= 1:
                continue
            if len(counts) > 12:
                common = counts.most_common(11)
                other = sum(counts.values()) - sum(c for _, c in common)
                counts = dict(common)
                if other > 0:
                    counts["__other__"] = other
            n = sum(counts.values())
            gini = 1.0 - sum((c / n) ** 2 for c in counts.values())
            elimination_value = n * gini
            p_useful = self._attr_alpha[attr] / (self._attr_alpha[attr] + self._attr_beta[attr])
            decay = 0.4 ** state["asked_count"][attr]
            boost = state["boosts"].get(attr, 1.0)
            score = elimination_value * p_useful * decay * boost
            if score > best_score:
                best_score = score
                best_attr = attr

        if "other" not in state["no_pref"] and state["asked_count"]["other"] == 0:
            n = len(scoring_pool)
            p_useful = self._attr_alpha["other"] / (self._attr_alpha["other"] + self._attr_beta["other"])
            score = (n * 0.3) * p_useful
            if score > best_score:
                best_score = score
                best_attr = "other"

        return best_attr if best_attr is not None and best_score > 1e-6 else None
