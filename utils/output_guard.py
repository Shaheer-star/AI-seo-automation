import re


def detect_video_category(video_metadata, analysis_text=""):
    title = (video_metadata.get("title", "") or "").lower()
    text = (analysis_text or "").lower()
    combined = f"{title} {text}"

    music_keywords = ["song", "lyrics", "official video", "music", "album", "audio", "track", "remix"]
    education_keywords = ["tutorial", "how to", "learn", "explained", "lesson", "guide", "course"]
    tech_keywords = ["review", "unboxing", "comparison", "software", "app", "phone", "laptop", "tech"]
    gaming_keywords = ["gameplay", "walkthrough", "gaming", "live stream", "boss fight", "fps"]
    vlog_keywords = ["vlog", "daily life", "travel vlog", "day in my life"]

    if any(k in combined for k in music_keywords):
        return "music"
    if any(k in combined for k in education_keywords):
        return "education"
    if any(k in combined for k in tech_keywords):
        return "tech"
    if any(k in combined for k in gaming_keywords):
        return "gaming"
    if any(k in combined for k in vlog_keywords):
        return "vlog"

    return "general"


def get_category_tags(category, title):
    base = {
        "music": [
            "music", "song", "lyrics", "officialvideo", "newmusic", "artist", "track", "audio",
            "album", "musicvideo", "viral", "trendingmusic", "melody", "playlist", "beats",
            "remix", "liveperformance", "singer", "love song", "sad song", "romantic song",
            "pop", "desi music", "urdu song", "hindi song", "latest song", "hit song",
            "music lovers", "song release", "new track", "official audio", "top songs",
            "best music", "stream now", "listen now"
        ],
        "education": [
            "tutorial", "howto", "learn", "education", "guide", "explained", "training",
            "course", "lesson", "stepbystep", "tips", "beginner", "advanced", "skills",
            "study", "knowledge", "teaching", "learning", "concepts", "full guide",
            "complete tutorial", "easy explanation", "study material", "lecture", "practice",
            "examples", "student help", "teacher guide", "learning video", "exam prep",
            "academic help", "class tutorial", "subject guide", "learn fast", "explainer"
        ],
        "tech": [
            "tech", "review", "unboxing", "comparison", "gadgets", "software", "app", "device",
            "technology", "hands on", "features", "performance", "test", "camera test", "speed test",
            "tech review", "best tech", "buying guide", "smartphone", "laptop", "pc", "mobile",
            "latest tech", "new gadget", "product review", "tech news", "user experience",
            "setup guide", "tech tips", "pros and cons", "worth buying", "comparison video",
            "best product", "tech explained", "device review"
        ],
        "gaming": [
            "gaming", "gameplay", "walkthrough", "live stream", "boss fight", "mission", "fps",
            "multiplayer", "strategy", "pro gameplay", "gaming tips", "game review", "new game",
            "pc gaming", "mobile gaming", "console gaming", "rank push", "kills", "stream highlights",
            "funny moments", "epic moments", "game guide", "walkthrough part 1", "full gameplay",
            "gaming community", "best settings", "gaming tutorial", "competitive gaming", "match highlights",
            "win moments", "gaming clips", "game mechanics", "tips and tricks", "best loadout", "ranked match"
        ],
        "vlog": [
            "vlog", "daily vlog", "travel vlog", "lifestyle", "day in my life", "routine",
            "family vlog", "fun moments", "life update", "personal vlog", "trip", "journey",
            "memories", "explore", "weekend vlog", "adventure", "real life", "behind the scenes",
            "casual vlog", "happy moments", "life moments", "travel diary", "outing", "friends",
            "family time", "daily routine", "vlogger", "city tour", "food vlog", "event vlog",
            "cinematic vlog", "vacation vlog", "life story", "new experience", "fun day"
        ],
        "general": [
            "video", "trending", "viral", "popular", "interesting", "watch now", "must watch",
            "latest", "new upload", "youtube video", "best content", "top video", "discover",
            "content creator", "audience favorite", "recommended", "engaging", "creative",
            "featured", "best moments", "watch till end", "online video", "youtube content",
            "video update", "latest upload", "top trending", "viewer favorite", "new content",
            "share now", "support creator", "explore more", "must see", "hot topic", "viral clip", "youtube trending"
        ]
    }

    tags = base.get(category, base["general"])[:35]
    if title:
        title_words = [w.lower() for w in re.findall(r"\w+", title) if len(w) > 3]
        for w in title_words[:5]:
            if w not in tags and len(tags) < 35:
                tags.append(w)

    return tags[:35]


def _parse_timestamp_seconds(value):
    value = str(value or "").strip()
    match = re.match(r"^(\d{1,2}:)?\d{1,2}:\d{2}$", value)
    if not match:
        return None

    parts = [int(part) for part in value.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        hours = 0
    else:
        hours, minutes, seconds = parts

    if seconds >= 60 or minutes >= 60:
        return None

    return hours * 3600 + minutes * 60 + seconds


def _format_timestamp(seconds):
    seconds = max(0, int(seconds))
    hours, remaining = divmod(seconds, 3600)
    minutes, seconds = divmod(remaining, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


def _fallback_timestamps(duration):
    count = 5 if duration <= 900 else 7
    last_start = max(duration - 1, 0)
    step = max(duration // count, 1)
    normalized = []

    for i in range(count):
        sec = min(i * step, last_start)
        normalized.append({
            "time": _format_timestamp(sec),
            "description": f"Segment {i + 1}"
        })

    return normalized


def normalize_timestamps(timestamps, duration):
    try:
        duration = int(duration or 0)
    except (TypeError, ValueError):
        duration = 0

    if duration <= 0:
        duration = 300

    if not isinstance(timestamps, list):
        return _fallback_timestamps(duration)

    max_timestamp = max(duration - 1, 0)
    normalized = []
    seen_seconds = set()

    for index, item in enumerate(timestamps):
        if not isinstance(item, dict):
            continue

        seconds = _parse_timestamp_seconds(item.get("time"))
        if seconds is None:
            continue

        seconds = min(seconds, max_timestamp)
        if seconds in seen_seconds:
            continue

        description = str(item.get("description") or "").strip()
        normalized.append({
            "time": _format_timestamp(seconds),
            "description": description or f"Segment {index + 1}"
        })
        seen_seconds.add(seconds)

    normalized.sort(key=lambda item: _parse_timestamp_seconds(item["time"]) or 0)

    if len(normalized) < 3:
        return _fallback_timestamps(duration)

    return normalized


def enforce_language(results, language):
    if language.lower() != "english":
        if "analysis" in results and isinstance(results["analysis"], str):
            results["analysis"] = f"[{language}] {results['analysis']}"
    return results


def improve_thumbnail_concepts(thumbnails, category, title):
    if not isinstance(thumbnails, list) or not thumbnails:
        thumbnails = []

    while len(thumbnails) < 4:
        thumbnails.append({})

    category_defaults = {
        "music": (
            "Photoreal emotional artist close-up in a believable performance scene",
            "Official Lyrics",
            ["#FF0050", "#111111", "#FFFFFF"]
        ),
        "education": (
            "Real learning moment with a specific concept shown through subject, props, and environment",
            "Learn Fast",
            ["#005BFF", "#FFFFFF", "#FFC107"]
        ),
        "tech": (
            "Premium product-in-use scene with realistic materials and focused camera detail",
            "Worth It?",
            ["#00C2FF", "#111111", "#FFFFFF"]
        ),
        "gaming": (
            "Immersive action scene with dynamic perspective and high-stakes reaction",
            "Epic Win",
            ["#FF3D00", "#000000", "#FFFFFF"]
        ),
        "vlog": (
            "Candid lifestyle story moment in a real location with cinematic depth",
            "A New Day",
            ["#FFB300", "#FFFFFF", "#333333"]
        ),
        "general": (
            "Photoreal topic-specific hero scene with a clear subject and believable stakes",
            "Must Watch",
            ["#FF0000", "#FFFFFF", "#000000"]
        )
    }

    concept, overlay, colors = category_defaults.get(category, category_defaults["general"])

    repaired = []
    for item in thumbnails[:4]:
        repaired.append({
            "concept": item.get("concept") or concept,
            "text_overlay": item.get("text_overlay") or overlay,
            "colors": item.get("colors") or colors,
            "focal_point": item.get("focal_point") or title or "Main subject",
            "tone": item.get("tone") or category,
            "composition": item.get("composition") or "Cinematic subject framing with realistic depth and no template graphics"
        })

    return repaired


def repair_and_validate_output(results, video_metadata, language="English"):
    if not isinstance(results, dict):
        results = {}

    analysis = results.get("analysis", "")
    seo = results.get("seo", {})
    thumbnails = results.get("thumbnails", [])

    if not isinstance(seo, dict):
        seo = {}

    category = detect_video_category(video_metadata, analysis)
    title = video_metadata.get("title", "")
    duration = video_metadata.get("duration", 300)

    tags = seo.get("tags", [])
    if not isinstance(tags, list) or len(tags) != 35:
        tags = get_category_tags(category, title)

    description = seo.get("description", "")
    if not description:
        description = (
            f"This {category} video about {title} is optimized for better "
            f"discoverability and audience engagement."
        )

    timestamps = normalize_timestamps(seo.get("timestamps", []), duration)

    titles = seo.get("titles", [])
    if not isinstance(titles, list) or len(titles) < 5:
        titles = [
            {"rank": 1, "title": title or "Optimized Video Title", "reason": "Original or base title"},
            {"rank": 2, "title": f"{title} | Complete Guide", "reason": "SEO-rich variant"},
            {"rank": 3, "title": f"Best of {title}", "reason": "Higher CTR style"},
            {"rank": 4, "title": f"{title} Explained", "reason": "Clear and searchable"},
            {"rank": 5, "title": f"Watch This: {title}", "reason": "Engagement style"},
        ]

    thumbnails = improve_thumbnail_concepts(thumbnails, category, title)

    repaired = {
        "analysis": analysis or f"This is a {category} video about {title}.",
        "seo": {
            "tags": tags[:35],
            "description": description,
            "timestamps": timestamps,
            "titles": titles[:5]
        },
        "thumbnails": thumbnails
    }

    repaired = enforce_language(repaired, language)
    return repaired
