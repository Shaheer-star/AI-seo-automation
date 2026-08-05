from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from utils.output_guard import repair_and_validate_output
import json
import re
import os


def clean_text(value):
    value = str(value or "").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def clean_tag(tag):
    tag = str(tag or "").lower().strip()
    tag = tag.replace("#", "")
    tag = re.sub(r"[^\w\s\-&]", "", tag)
    tag = re.sub(r"\s+", " ", tag).strip()
    return tag


def detect_video_category(title):
    title_lower = title.lower()

    music_words = [
        "song", "music", "official video", "lyrics", "lyric", "ost",
        "slowed", "reverb", "remix", "cover", "soundtrack", "audio",
        "love story", "ghazal", "qawwali", "naat", "singer", "album"
    ]

    if any(word in title_lower for word in music_words):
        return "Music/Song"

    film_words = ["trailer", "teaser", "movie", "film", "drama", "episode", "scene"]
    if any(word in title_lower for word in film_words):
        return "Entertainment/Film"

    education_words = ["tutorial", "course", "lecture", "learn", "explained", "how to"]
    if any(word in title_lower for word in education_words):
        return "Education/Tutorial"

    tech_words = ["python", "coding", "programming", "software", "app", "technology"]
    if any(word in title_lower for word in tech_words):
        return "Technology"

    return "General Entertainment"


def has_valid_groq_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key.startswith("gsk_") and len(key) > 30


def build_relevant_tags(title, author="", category="General Entertainment"):
    title = clean_text(title)
    author = clean_text(author)
    title_clean = clean_tag(title)
    author_clean = clean_tag(author)

    tags = []

    def add(tag):
        tag = clean_tag(tag)
        if tag and tag not in tags and len(tags) < 35:
            tags.append(tag)

    add(title_clean)

    if author_clean and author_clean != "unknown":
        add(author_clean)

    title_words = [
        clean_tag(word)
        for word in re.split(r"[\s\-\|\(\)\[\]:,/]+", title)
        if len(clean_tag(word)) > 2
    ]

    for word in title_words:
        add(word)

    if category == "Music/Song":
        related = [
            f"{title_clean} song",
            f"{title_clean} official video",
            f"{title_clean} music video",
            f"{title_clean} full song",
            f"{title_clean} lyrics",
            f"{title_clean} video song",
            f"{title_clean} soundtrack",
            "official song",
            "official music video",
            "music video",
            "video song",
            "full song",
            "lyrics",
            "lyrics video",
            "new song",
            "latest song",
            "trending song",
            "viral song",
            "popular song",
            "hit song",
            "love song",
            "romantic song",
            "sad song",
            "emotional song",
            "heart touching song",
            "slowed reverb",
            "soundtrack",
            "ost song",
            "youtube music",
            "pakistani song",
            "indian song",
            "bollywood song",
            "romantic music",
            "sad music",
            "trending music"
        ]
    elif category == "Entertainment/Film":
        related = [
            f"{title_clean} official",
            f"{title_clean} video",
            f"{title_clean} full video",
            f"{title_clean} scene",
            "official video",
            "entertainment video",
            "drama video",
            "film video",
            "movie scene",
            "trending video",
            "viral video",
            "popular video",
            "youtube video",
            "latest video"
        ]
    elif category == "Technology":
        related = [
            f"{title_clean} tutorial",
            f"{title_clean} explained",
            "technology",
            "tech video",
            "software",
            "ai tools",
            "tutorial",
            "how to",
            "programming",
            "coding",
            "learn tech",
            "tech guide"
        ]
    elif category == "Education/Tutorial":
        related = [
            f"{title_clean} tutorial",
            f"{title_clean} explained",
            "tutorial",
            "education",
            "learning",
            "lecture",
            "course",
            "how to",
            "step by step",
            "study",
            "guide"
        ]
    else:
        related = [
            f"{title_clean} video",
            f"{title_clean} youtube",
            "youtube video",
            "official video",
            "trending video",
            "viral video",
            "popular video",
            "latest video",
            "new video",
            "entertainment",
            "watch now",
            "full video"
        ]

    for tag in related:
        add(tag)

    while len(tags) < 35:
        add(f"{title_clean} {len(tags) + 1}")

    return tags[:35]


def normalize_tags(tags, title, author="", category="General Entertainment"):
    banned_for_music = [
        "tech", "technology", "coding", "programming", "python", "java",
        "study", "education", "tutorial", "lecture", "course", "software",
        "machine learning", "ai tools", "productivity", "programmer"
    ]

    cleaned = []

    for tag in tags:
        tag = clean_tag(tag)
        if not tag:
            continue

        if category == "Music/Song":
            if any(bad == tag or bad in tag for bad in banned_for_music):
                continue

        if tag not in cleaned:
            cleaned.append(tag)

    fallback = build_relevant_tags(title, author, category)

    for tag in fallback:
        if tag not in cleaned:
            cleaned.append(tag)

    return cleaned[:35]


def generate_better_titles(title, category="General Entertainment"):
    title = clean_text(title)

    if category == "Music/Song":
        return [
            {"rank": 1, "title": title, "reason": "Original title with exact search match"},
            {"rank": 2, "title": f"{title} | Official Music Video", "reason": "Targets official music video searches"},
            {"rank": 3, "title": f"{title} Lyrics | Full Song", "reason": "Targets lyrics and full song searches"},
            {"rank": 4, "title": f"{title} - Heart Touching Song", "reason": "Emotional angle for music audience"},
            {"rank": 5, "title": f"{title} | Romantic Song", "reason": "Mood-based title for romantic searches"},
            {"rank": 6, "title": f"{title} | Trending Song", "reason": "Trend-based clickable title"},
            {"rank": 7, "title": f"{title} | Slowed + Reverb", "reason": "Popular music search format"}
        ]

    return [
        {"rank": 1, "title": title, "reason": "Original title with exact search relevance"},
        {"rank": 2, "title": f"{title} | Full Video", "reason": "Targets full video searches"},
        {"rank": 3, "title": f"{title} Explained", "reason": "Search-friendly explanation angle"},
        {"rank": 4, "title": f"Why {title} Is Trending", "reason": "Curiosity-based title"},
        {"rank": 5, "title": f"{title} - Must Watch", "reason": "Clickable entertainment angle"},
        {"rank": 6, "title": f"Best Moments from {title}", "reason": "Highlights-focused title"},
        {"rank": 7, "title": f"{title} | New Video", "reason": "General SEO title variation"}
    ]


def normalize_titles(titles, title, category):
    if not isinstance(titles, list):
        return generate_better_titles(title, category)

    final_titles = []
    seen = set()

    for item in titles:
        if not isinstance(item, dict):
            continue

        t = clean_text(item.get("title", ""))
        reason = clean_text(item.get("reason", "SEO friendly title"))

        if not t:
            continue

        key = t.lower()
        if key not in seen:
            seen.add(key)
            final_titles.append({
                "rank": len(final_titles) + 1,
                "title": t,
                "reason": reason
            })

    fallback_titles = generate_better_titles(title, category)

    for item in fallback_titles:
        key = item["title"].lower()
        if key not in seen:
            seen.add(key)
            item["rank"] = len(final_titles) + 1
            final_titles.append(item)

        if len(final_titles) >= 7:
            break

    return final_titles[:7]


def get_seo_output_parser():
    response_schemas = [
        ResponseSchema(
            name="tags",
            description="A list of exactly 35 highly relevant YouTube tags for this exact video"
        ),
        ResponseSchema(
            name="description",
            description="An SEO-optimized video description between 400-500 words"
        ),
        ResponseSchema(
            name="timestamps",
            description="A list of timestamp objects with 'time' and 'description' fields"
        ),
        ResponseSchema(
            name="titles",
            description="A list of exactly 7 unique title suggestion objects with 'rank', 'title', and 'reason' fields"
        )
    ]
    return StructuredOutputParser.from_response_schemas(response_schemas)


def get_thumbnail_output_parser():
    response_schemas = [
        ResponseSchema(
            name="thumbnail_concepts",
            description="A list of 4 thumbnail concept objects with concept, text_overlay, colors, focal_point, tone, composition"
        )
    ]
    return StructuredOutputParser.from_response_schemas(response_schemas)


def run_seo_analysis_with_langchain(video_url, video_metadata, language="English"):
    platform = video_metadata.get("platform", "YouTube")
    title = video_metadata.get("title", "Untitled Video")
    author = video_metadata.get("author", "Unknown")
    description = clean_text(video_metadata.get("description", ""))[:700]
    duration = video_metadata.get("duration", 0)
    category = detect_video_category(title)

    if not has_valid_groq_key():
        fallback_result = {
            "analysis": generate_fallback_analysis(title, platform, author, category, duration),
            "seo": generate_fallback_seo(title, platform, language, author, category),
            "thumbnails": generate_fallback_thumbnails(platform, language, title, category)["thumbnail_concepts"]
        }
        return repair_and_validate_output(fallback_result, video_metadata, language)

    minutes = duration // 60
    num_timestamps = min(15, max(5, int(minutes / 2))) if minutes > 0 else 5

    try:
        llm = ChatGroq(
            temperature=0.25,
            model_name="llama-3.1-8b-instant",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

        analysis_template = """
You are a YouTube content analyst.

Analyze this video using ONLY its metadata.

Video URL: {video_url}
Platform: {platform}
Title: "{title}"
Creator/Channel: "{author}"
Detected Category: {category}
Duration: {duration} seconds

Rules:
- Stay close to the actual title.
- Do NOT assume tech/study/tutorial content unless title clearly says that.
- If it is a song/music/lyrics/official video/love story/OST/remix, analyze it as Music/Song.
- Avoid unrelated assumptions.

Write:
1. Likely content summary
2. Main topic/category
3. Emotional tone
4. Target audience
5. Content style

Language: {language}
"""

        analysis_prompt = PromptTemplate(
            input_variables=["video_url", "platform", "title", "author", "category", "duration", "language"],
            template=analysis_template
        )

        analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt)

        analysis_result = analysis_chain.run(
            video_url=video_url,
            platform=platform,
            title=title,
            author=author,
            category=category,
            duration=duration,
            language=language
        )
    except Exception as exc:
        fallback_result = {
            "analysis": (
                f"{generate_fallback_analysis(title, platform, author, category, duration)}\n\n"
                f"AI connection note: Groq could not be reached ({exc}). "
                "These recommendations were generated locally from the video metadata."
            ),
            "seo": generate_fallback_seo(title, platform, language, author, category),
            "thumbnails": generate_fallback_thumbnails(platform, language, title, category)["thumbnail_concepts"]
        }
        return repair_and_validate_output(fallback_result, video_metadata, language)

    seo_parser = get_seo_output_parser()
    format_instructions = seo_parser.get_format_instructions()

    seo_template = """
You are a YouTube SEO expert.

Generate SEO data for this EXACT video only.

Video URL: {video_url}
Platform: {platform}
Title: "{title}"
Creator/Channel: "{author}"
Detected Category: {category}
Duration: {duration} seconds

Analysis:
{analysis}

VERY IMPORTANT TAG RULES:
1. Generate EXACTLY 35 tags.
2. Tags must be directly related to the video title, creator/channel, detected category, and likely search intent.
3. If category is Music/Song, all tags must be song/music related.
4. Do NOT include unrelated tags such as tech, coding, AI, study, tutorial, education, programming, software unless the title clearly proves it.
5. No fake trending topics.
6. Do not use # symbol.
7. Tags should be short and searchable.

TITLE RULES:
1. Generate EXACTLY 7 title suggestions.
2. Every title must have a different angle, not tiny wording changes.
3. Do NOT repeat the same title structure.
4. For Music/Song videos, use these different angles:
   - Exact/original SEO title
   - Official music video title
   - Lyrics/full song search title
   - Emotional title
   - Romantic/sad mood title
   - Trending/viral title
   - Short catchy title
5. Keep titles under 70 characters where possible.
6. Do NOT create tutorial/study/tech titles unless video is actually about that.

Generate:
1. EXACTLY 35 tags
2. SEO description of 400-500 words
3. Exactly {num_timestamps} timestamps
4. EXACTLY 7 unique SEO title suggestions

TIMESTAMP RULES:
1. All timestamp times must be inside the real video duration of {duration} seconds.
2. Never create timestamps after the video ends.
3. Use MM:SS for videos under 1 hour and HH:MM:SS only for videos over 1 hour.

{format_instructions}

Return only valid JSON.
Language: {language}
"""

    seo_prompt = PromptTemplate(
        input_variables=[
            "video_url", "platform", "title", "author", "category",
            "duration", "analysis", "num_timestamps", "language"
        ],
        partial_variables={"format_instructions": format_instructions},
        template=seo_template
    )

    seo_chain = LLMChain(llm=llm, prompt=seo_prompt)

    try:
        seo_result = seo_chain.run(
            video_url=video_url,
            platform=platform,
            title=title,
            author=author,
            category=category,
            duration=duration,
            analysis=analysis_result,
            num_timestamps=num_timestamps,
            language=language
        )

        seo_data = parse_langchain_output(seo_result)
        seo_data["tags"] = normalize_tags(
            seo_data.get("tags", []),
            title,
            author,
            category
        )
        seo_data["titles"] = normalize_titles(
            seo_data.get("titles", []),
            title,
            category
        )

    except Exception:
        seo_data = generate_fallback_seo(title, platform, language, author, category)

    thumbnail_parser = get_thumbnail_output_parser()
    thumbnail_format = thumbnail_parser.get_format_instructions()

    thumbnail_template = """
You are a YouTube thumbnail strategist.

Create 4 thumbnail concepts for this exact video.

Title: "{title}"
Creator: "{author}"
Detected Category: {category}
Public Video Description:
{description}
Analysis:
{analysis}

Rules:
- Concepts must match the video topic.
- Use the detected category, title, and public video description as hard relevance anchors.
- If Music/Song, focus on emotion, romance, sadness, cinematic mood, singer/album/video artwork vibe.
- If Education/Tutorial, show the real subject being learned, a student/teacher/story moment, and subject-specific props from the title.
- If Technology, show the exact device, software context, or tech action implied by the title.
- If a title is about reading, academics, study, or learning difficulty, show that education context and do not invent unrelated entertainment scenes.
- Do NOT suggest SEO robot, tech graphics, coding, dashboard, or AI visuals unless the video is actually tech-related.
- Text overlay must be 2-5 words, relevant to that exact concept and video type, and strong enough to place directly on the thumbnail.
- Do NOT use generic text such as "Watch Now", "New Video", or "Must Watch" unless the title itself requires it.
- Each concept must be visually different and suitable for a fresh photorealistic generated image.
- Make the 4 concepts use different visual strategies:
  1. close emotional hero subject or face when appropriate
  2. realistic story scene in a believable location
  3. topic-specific object, product, prop, or symbol integrated into a real scene
  4. action, reaction, or high-stakes moment with dynamic camera perspective
- Describe real subjects, environments, lighting, props, and camera framing.
- Avoid generic "bold thumbnail", text box, border, template, dashboard, collage, and stock-photo instructions.
- The visual should still work if no text is placed on top.

Return:
concept, text_overlay, colors, focal_point, tone, composition

{format_instructions}

Return only valid JSON.
Language: {language}
"""

    thumbnail_prompt = PromptTemplate(
        input_variables=["title", "author", "category", "description", "analysis", "language"],
        partial_variables={"format_instructions": thumbnail_format},
        template=thumbnail_template
    )

    thumbnail_chain = LLMChain(llm=llm, prompt=thumbnail_prompt)

    try:
        thumbnail_result = thumbnail_chain.run(
            title=title,
            author=author,
            category=category,
            description=description,
            analysis=analysis_result,
            language=language
        )
        thumbnail_data = parse_langchain_output(thumbnail_result)
    except Exception:
        thumbnail_data = generate_fallback_thumbnails(platform, language, title, category)

    if isinstance(thumbnail_data, dict) and "thumbnail_concepts" in thumbnail_data:
        thumbnail_data = thumbnail_data["thumbnail_concepts"]

    if not isinstance(thumbnail_data, list) or len(thumbnail_data) < 4:
        thumbnail_data = generate_fallback_thumbnails(platform, language, title, category)["thumbnail_concepts"]

    final_result = {
        "analysis": analysis_result,
        "seo": seo_data,
        "thumbnails": thumbnail_data[:4]
    }

    return repair_and_validate_output(final_result, video_metadata, language)


def parse_langchain_output(output_text):
    try:
        return json.loads(output_text)
    except Exception:
        pass

    patterns = [
        r"```json\s*([\s\S]*?)\s*```",
        r"```\s*([\s\S]*?)\s*```"
    ]

    for pattern in patterns:
        match = re.search(pattern, output_text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

    start = output_text.find("{")
    end = output_text.rfind("}") + 1

    if start >= 0 and end > start:
        try:
            return json.loads(output_text[start:end])
        except Exception:
            pass

    raise ValueError("Could not parse output as JSON")


def generate_fallback_analysis(title, platform, author, category, duration):
    title = clean_text(title) or "this video"
    author = clean_text(author) or "the creator"
    minutes = duration // 60 if duration else 0
    duration_text = f"about {minutes} minute(s)" if minutes else "an unknown length"

    return (
        f"'{title}' is a {platform} video by {author}. Based on the available metadata, "
        f"the likely category is {category} and the video is {duration_text}. "
        "The SEO strategy should stay tightly connected to the exact title, creator name, "
        "viewer search intent, and platform context. The strongest optimization angles are "
        "clear searchable titles, relevant tags, a description that repeats the core topic "
        "naturally, and timestamps that make the content easier to scan."
    )


def ensure_35_tags(tags, llm, title, platform, language):
    return normalize_tags(tags, title, "", detect_video_category(title))


def generate_fallback_seo(title, platform, language, author="", category=None):
    if category is None:
        category = detect_video_category(title)

    tags = build_relevant_tags(title, author, category)

    if category == "Music/Song":
        description = (
            f"Enjoy '{title}', a music-focused {platform} video created for fans who love emotional, romantic, "
            f"and memorable songs. This video is ideal for listeners searching for the official video, music video, "
            f"lyrics, full song, trending song, or heart-touching soundtrack experience.\n\n"
            f"With its emotional tone and engaging presentation, this video is suitable for viewers who enjoy love songs, "
            f"sad songs, romantic music, and trending music content. Listen carefully, feel the mood, and share it with "
            f"friends who enjoy meaningful music.\n\n"
            f"Like, comment, share, and subscribe for more music videos and related content."
        )
    else:
        description = (
            f"This {platform} video titled '{title}' is designed for viewers interested in this topic. "
            f"Watch the full video for the main highlights, important moments, and useful takeaways.\n\n"
            f"Like, comment, share, and subscribe for more related videos."
        )

    return {
        "tags": tags,
        "description": description,
        "timestamps": [
            {"time": "00:00", "description": "Opening"},
            {"time": "01:00", "description": "Main section begins"},
            {"time": "02:00", "description": "Key moment"},
            {"time": "03:00", "description": "Highlight section"},
            {"time": "04:00", "description": "Closing"}
        ],
        "titles": generate_better_titles(title, category)
    }


def generate_fallback_thumbnails(platform, language, title="Video", category="General Entertainment"):
    if category == "Music/Song":
        return {
            "thumbnail_concepts": [
                {
                    "concept": "Photoreal artist close-up during an emotional performance with cinematic stage light and visible expression",
                    "text_overlay": title[:30],
                    "colors": ["#000000", "#FFD166", "#EF233C"],
                    "focal_point": "Main emotional scene or artist visual",
                    "tone": "cinematic emotional romantic",
                    "composition": "Tight asymmetric portrait with light falloff and a real performance environment"
                },
                {
                    "concept": "Romantic film-still scene between performers in a believable night location with soft practical lights",
                    "text_overlay": "Official Video",
                    "colors": ["#2B0A1E", "#FFB6C1", "#FFFFFF"],
                    "focal_point": "Romantic or emotional video frame",
                    "tone": "romantic soft heartfelt",
                    "composition": "Wide story moment with layered foreground and intimate eye-line"
                },
                {
                    "concept": "Moody rain-lit music scene with a solitary subject, realistic atmosphere, and cinematic blue reflections",
                    "text_overlay": "Heart Touching",
                    "colors": ["#111827", "#60A5FA", "#FFFFFF"],
                    "focal_point": "Sad or emotional visual moment",
                    "tone": "sad emotional deep",
                    "composition": "Environmental portrait with deep background perspective and emotional isolation"
                },
                {
                    "concept": "Energetic live-performance moment with motion, crowd light, and a dynamic camera angle",
                    "text_overlay": "Trending Song",
                    "colors": ["#FF1744", "#FFEB3B", "#000000"],
                    "focal_point": "Main music video artwork",
                    "tone": "viral energetic emotional",
                    "composition": "Action-led frame with strong subject scale and natural color contrast"
                }
            ]
        }

    return {
        "thumbnail_concepts": [
            {
                "concept": "Photoreal hero image of the topic's main subject in a believable real scene with premium cinematic detail",
                "text_overlay": title[:30],
                "colors": ["#000000", "#FFFFFF", "#FF1744"],
                "focal_point": "Main subject from video",
                "tone": "professional engaging",
                "composition": "Close asymmetric subject framing with strong depth and natural negative space"
            },
            {
                "concept": "Realistic story moment that shows the topic happening in a specific location with expressive stakes",
                "text_overlay": "Watch Now",
                "colors": ["#000000", "#00E5FF", "#FFFFFF"],
                "focal_point": "Central visual subject",
                "tone": "bold engaging",
                "composition": "Wide cinematic scene with foreground action and layered background"
            },
            {
                "concept": "Editorial object or product-focused scene with tangible props and premium realistic lighting",
                "text_overlay": "Must Watch",
                "colors": ["#111827", "#FACC15", "#FFFFFF"],
                "focal_point": "Important scene from video",
                "tone": "cinematic dramatic",
                "composition": "Object-led composition with diagonal movement and scene context"
            },
            {
                "concept": "Dynamic action or reaction scene with a strong camera perspective and realistic motion cues",
                "text_overlay": "New Video",
                "colors": ["#0D47A1", "#FFFFFF", "#42A5F5"],
                "focal_point": "Main topic visual",
                "tone": "clean modern",
                "composition": "High-energy foreground subject with clean hierarchy and believable environment"
            }
        ]
    }
