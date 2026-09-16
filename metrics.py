from prometheus_client import Counter

# 1. Metric: Total tokens consumed from Gemini
# Labels allow granular slicing by model and direction (prompt vs. completion)
GEMINI_TOKENS_TOTAL = Counter(
    "gemini_tokens_total",
    "Cumulative token consumption from Gemini API calls",
    ["model", "type"]  # type: "prompt" or "completion"
)

# 2. Metric: Cache efficiency tracking
# Labels record whether a request was served from memory or required network I/O
CACHE_EVENTS_TOTAL = Counter(
    "gemini_cache_events_total",
    "Evaluation count of cache lookups",
    ["status"]  # status: "hit" or "miss"
)

# Pre-initialize common labels so Prometheus scrapes show 0.0 instead of omitting the line
for status_label in ["hit", "miss"]:
    CACHE_EVENTS_TOTAL.labels(status=status_label)

for type_label in ["prompt", "completion"]:
    GEMINI_TOKENS_TOTAL.labels(model="gemini-3.6-flash", type=type_label)