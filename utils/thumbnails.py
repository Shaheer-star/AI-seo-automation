import hashlib
import os
import re
from io import BytesIO

from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
import requests

WIDTH, HEIGHT = 1280, 720

HF_IMAGE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "stabilityai/stable-diffusion-xl-base-1.0",
    "runwayml/stable-diffusion-v1-5",
]


def compact_text(value, max_chars=360):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_chars].rsplit(" ", 1)[0] if len(text) > max_chars else text


def build_seo_thumbnail_brief(metadata, results):
    metadata = metadata or {}
    results = results or {}
    seo = results.get("seo", {}) if isinstance(results, dict) else {}
    titles = seo.get("titles", []) if isinstance(seo, dict) else []
    tags = seo.get("tags", []) if isinstance(seo, dict) else []
    timestamps = seo.get("timestamps", []) if isinstance(seo, dict) else []

    title_angles = [
        compact_text(item.get("title", ""), 90)
        for item in titles[:4]
        if isinstance(item, dict) and item.get("title")
    ]
    timestamp_themes = [
        compact_text(item.get("description", ""), 60)
        for item in timestamps[:5]
        if isinstance(item, dict) and item.get("description")
    ]
    searchable_tags = [compact_text(tag, 34) for tag in tags[:12] if str(tag or "").strip()]

    brief_parts = [
        f"Original video title: {metadata.get('title', '')}",
        f"Creator: {metadata.get('author', '')}",
        f"Public video description: {compact_text(metadata.get('description', ''), 320)}",
        f"SEO content analysis: {compact_text(results.get('analysis', ''), 360)}",
        f"SEO description strategy: {compact_text(seo.get('description', ''), 420)}",
        f"SEO title angles: {' | '.join(title_angles)}",
        f"Search tags: {', '.join(searchable_tags)}",
        f"Timestamp themes: {' | '.join(timestamp_themes)}",
    ]
    return "\n".join(part for part in brief_parts if part.split(":", 1)[-1].strip())


def detect_video_type(video_title, video_context="", concept=None):
    concept = concept or {}
    content = " ".join(
        [
            str(video_title or ""),
            str(video_context or ""),
            str(concept.get("concept", "")),
            str(concept.get("focal_point", "")),
        ]
    ).lower()

    keyword_types = [
        ("music", ["song", "lyrics", "official video", "music", "album", "singer", "remix", "audio"]),
        ("education", ["reading", "academic", "study", "learn", "lesson", "tutorial", "explained", "course", "lecture", "exam"]),
        ("technology", ["python", "coding", "programming", "software", "app", "phone", "laptop", "ai ", "tech", "gadget"]),
        ("gaming", ["gameplay", "gaming", "walkthrough", "boss fight", "ranked", "game "]),
        ("travel", ["travel", "tour", "trip", "destination", "vlog", "city", "country", "explore"]),
        ("food", ["recipe", "cooking", "food", "bake", "meal", "kitchen", "restaurant"]),
        ("fitness", ["workout", "fitness", "gym", "exercise", "weight loss", "bodybuilding"]),
        ("business", ["business", "marketing", "seo", "money", "finance", "startup", "sales"]),
    ]

    for video_type, keywords in keyword_types:
        if any(keyword in content for keyword in keywords):
            return video_type

    return "general"


def get_type_guidance(video_type):
    return {
        "music": "Show a music-video-like performance, artist emotion, instrument, stage, or cinematic song scene. Do not show textbooks, apps, or office dashboards.",
        "education": "Show a real learning scene tied to the exact subject: student, teacher, book, notes, classroom, study pressure, or concept-specific props. Do not show music stages, random cyberpunk portraits, or unrelated products.",
        "technology": "Show the specific device, software-work context, coding setup, product interaction, or tech problem implied by the title. Keep screens believable and avoid fake unreadable UI as the main subject.",
        "gaming": "Show the game-like action, player stakes, battle reaction, controller, or gameplay atmosphere implied by the title. Keep it energetic and not like a business advertisement.",
        "travel": "Show the destination, journey moment, traveler, landscape, street, landmark, or real local atmosphere implied by the title.",
        "food": "Show the dish, cooking action, ingredients, kitchen craft, or restaurant moment implied by the title with appetizing realistic texture.",
        "fitness": "Show the exercise, athlete effort, gym environment, body movement, or fitness result implied by the title with realistic anatomy.",
        "business": "Show a realistic creator, entrepreneur, campaign, analytics decision, money workflow, or professional scene tied to the title instead of abstract sci-fi art.",
        "general": "Show the exact subject, action, place, and emotion implied by the title. Avoid generic faces or unrelated fantasy scenes.",
    }[video_type]


def stable_image_seed(concept, video_title, variant=0, video_context=""):
    seed_source = "|".join(
        [
            str(video_title or ""),
            str(variant),
            str((concept or {}).get("concept", "")),
            str((concept or {}).get("focal_point", "")),
            str((concept or {}).get("composition", "")),
            compact_text(video_context, 500),
        ]
    )
    digest = hashlib.sha256(seed_source.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 2_147_483_647


def get_hf_image_models():
    preferred = compact_text(os.environ.get("HF_IMAGE_MODEL", ""), 120)
    models = [preferred] if preferred else []
    for model in HF_IMAGE_MODELS:
        if model not in models:
            models.append(model)
    return models


def generate_thumbnail_art(client, concept, video_title, platform="YouTube", variant=0, video_context=""):
    prompt = build_thumbnail_prompt(concept, video_title, platform, variant, video_context)
    seed = stable_image_seed(concept, video_title, variant, video_context)
    negative_prompt = (
        "duplicate composition, same image as another option, template, text, watermark, "
        "logo, fake interface, poster border, low quality, distorted face, distorted hands"
    )
    errors = []

    for model in get_hf_image_models():
        try:
            generated = client.text_to_image(
                prompt,
                model=model,
                width=1280,
                height=720,
                num_inference_steps=4,
                guidance_scale=3.5,
                seed=seed,
                negative_prompt=negative_prompt,
            )
            return prepare_generated_canvas(generated)
        except TypeError:
            try:
                generated = client.text_to_image(
                    prompt,
                    model=model,
                    width=1024,
                    height=576,
                    num_inference_steps=8,
                    seed=seed,
                )
                return prepare_generated_canvas(generated)
            except Exception as fallback_error:
                errors.append(f"{model}: {fallback_error}")
        except Exception as model_error:
            errors.append(f"{model}: {model_error}")

    raise RuntimeError(
        "Hugging Face image generation failed for all configured models. "
        "Check that HF_TOKEN is valid, your Hugging Face account has accepted any required model terms, "
        "and the model is available for Inference API. Last errors: "
        + " | ".join(errors[-3:])
    )


def generate_hd_thumbnail(
    concept,
    video_title,
    overlay_text="",
    platform="YouTube",
    variant=0,
    api_key=None,
    video_context="",
):
    if not api_key:
        raise ValueError("A free Hugging Face token is required for HD image generation.")

    client = InferenceClient(token=api_key, timeout=180, proxies={})
    canvas = generate_thumbnail_art(client, concept, video_title, platform, variant, video_context)
    return finish_generated_thumbnail(canvas, overlay_text, variant)


def get_variant_direction(variant):
    directions = [
        {
            "route": "emotional human-first visual route",
            "shot": "hero close-up with a human-scale focal subject and expressive realism",
            "composition": "cinematic asymmetrical framing, face or key subject large in frame, layered background depth",
            "lighting": "dramatic motivated light, realistic highlights, rich shadow detail",
            "energy": "emotionally magnetic and immediately clickable",
        },
        {
            "route": "location and story-world visual route",
            "shot": "story moment captured like a premium film still",
            "composition": "environmental wide shot with foreground action, middle-ground subject, and believable location detail",
            "lighting": "naturalistic atmospheric lighting with practical light sources",
            "energy": "immersive and suspenseful",
        },
        {
            "route": "object and evidence visual route",
            "shot": "high-end editorial product or object-focused visual when the topic allows it",
            "composition": "bold diagonal movement, tangible props, subject interacting with the topic instead of posing",
            "lighting": "crisp commercial lighting mixed with realistic scene light",
            "energy": "polished and high-value",
        },
        {
            "route": "action and stakes visual route",
            "shot": "decisive action or reaction moment with visible stakes",
            "composition": "dynamic perspective, strong foreground subject, natural motion cues, uncluttered visual hierarchy",
            "lighting": "contrast-rich realistic lighting with color separation",
            "energy": "urgent, attractive, and share-worthy",
        },
    ]
    return directions[variant % len(directions)]


def build_thumbnail_prompt(concept, video_title, platform, variant=0, video_context=""):
    colors = ", ".join(concept.get("colors") or [])
    direction = get_variant_direction(variant)
    video_type = detect_video_type(video_title, video_context, concept)
    context = compact_text(video_context) or "No extra description available; stay strictly grounded in the title."
    return f"""
Use case: ads-marketing
Asset type: professional {platform} thumbnail image
Primary request: Create a fresh photorealistic premium HD thumbnail image for this exact {video_type} video titled "{video_title}".
Video title to obey: "{video_title}"
Unique option route: Option {variant + 1} must use the {direction["route"]}. Make it visibly different from the other thumbnail options for this same video.
SEO thumbnail brief generated from the same analysis, SEO description, tags, titles, and timestamps:
"{context}"
Video-type relevance rule: {get_type_guidance(video_type)}
Scene/backdrop: {concept.get("concept", "high-impact relevant scene for the exact video topic")}
Subject: {concept.get("focal_point", "a clear main subject relevant to the video title")}
Style/medium: premium cinematic photography, lifelike realism, believable skin and materials, sharp eye-level subject detail, expensive campaign finish
Shot direction: {direction["shot"]}
Composition/framing: {direction["composition"]}; follow this concept composition too: {concept.get("composition", "clear realistic visual hierarchy")}
Lighting/mood: {direction["lighting"]}; {concept.get("tone", "confident, high-contrast, professional")}
Color palette: {colors or "balanced premium color contrast with natural skin and material tones"}
Materials/textures: realistic surfaces, cinematic depth, crisp foreground detail, subtle atmosphere, clean high-resolution finish
Audience effect: {direction["energy"]}
Constraints: generate a completely new image; make the first-glance topic match the title and SEO thumbnail brief; use a real scene, subject, props, place, audience promise, or action explicitly implied by the SEO brief; if the concept conflicts with the SEO brief, follow the SEO brief
Avoid: boxes, panels, card layouts, fake UI, template graphics, generic poster layout, copied YouTube screenshot, watermark, logos, border, labels, captions, readable text, gibberish writing, infographic arrows, cartoon clip art, plastic faces, deformed faces or hands, muddy blur, flat stock-photo posing
""".strip()


def prepare_generated_canvas(image):
    canvas = ImageOps.fit(
        image.convert("RGB"),
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5),
    )
    canvas = ImageEnhance.Color(canvas).enhance(1.08)
    canvas = ImageEnhance.Contrast(canvas).enhance(1.06)
    return canvas.filter(ImageFilter.UnsharpMask(radius=1.5, percent=125, threshold=2))


def get_font(size):
    for font in [
        "impact.ttf", "Impact.ttf",
        "arialbd.ttf", "Arial Bold.ttf",
        "arial.ttf", "Arial.ttf",
        "DejaVuSans-Bold.ttf"
    ]:
        try:
            return ImageFont.truetype(font, size)
        except Exception:
            pass
    return ImageFont.load_default()


def load_video_thumbnail(url):
    try:
        session = requests.Session()
        session.trust_env = False
        r = session.get(url, timeout=12)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGB")
        return img.resize((WIDTH, HEIGHT))
    except Exception:
        return Image.new("RGB", (WIDTH, HEIGHT), (10, 15, 30))


def fit_text(draw, text, max_width, max_lines=2):
    text = str(text or "WATCH NOW").upper().strip()
    words = text.split()[:7]

    for size in range(96, 44, -4):
        font = get_font(size)
        lines = []
        line = ""

        for word in words:
            test = f"{line} {word}".strip()
            box = draw.textbbox((0, 0), test, font=font)
            if box[2] - box[0] <= max_width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word

        if line:
            lines.append(line)

        if len(lines) <= max_lines:
            return font, lines

    return get_font(48), [" ".join(words[:4])]


def text_block(draw, lines, x, y, font, main, accent):
    for idx, line in enumerate(lines):
        color = accent if idx == 0 else main
        draw.text(
            (x, y),
            line,
            font=font,
            fill=color,
            stroke_width=8,
            stroke_fill=(0, 0, 0)
        )
        box = draw.textbbox((x, y), line, font=font)
        y += box[3] - box[1] + 12


def clean_overlay_text(text):
    words = str(text or "").replace("\n", " ").strip().split()
    return " ".join(words[:6])


def get_relevant_overlay_text(concept, video_title, override_text=""):
    override = clean_overlay_text(override_text)
    if override:
        return override

    candidate = clean_overlay_text((concept or {}).get("text_overlay", ""))
    generic_overlays = {
        "",
        "watch now",
        "must watch",
        "new video",
        "thumbnail direction",
        "viral thumbnail",
        "modern thumbnail",
        "cinematic thumbnail",
        "premium thumbnail",
    }
    if candidate.lower() not in generic_overlays:
        return candidate

    words = re.findall(r"[A-Za-z0-9']+", str(video_title or ""))
    stop_words = {"official", "video", "youtube", "full", "episode", "the", "and", "with"}
    title_words = [word for word in words if word.lower() not in stop_words]
    return clean_overlay_text(" ".join(title_words[:5]) or "Featured Topic")


def overlay_editorial_title(img, text, variant=0):
    text = clean_overlay_text(text)
    if not text:
        return img

    layouts = [
        {"side": "left", "accent": (252, 184, 74), "x": 66, "y": 438, "stroke": 5},
        {"side": "right", "accent": (101, 214, 173), "x": 668, "y": 72, "stroke": 4},
        {"side": "left", "accent": (255, 120, 110), "x": 72, "y": 78, "stroke": 6},
        {"side": "right", "accent": (119, 196, 255), "x": 650, "y": 430, "stroke": 5},
    ]
    layout = layouts[variant % len(layouts)]
    overlay = add_side_gradient(img, layout["side"], (4, 8, 14), 145)
    draw = ImageDraw.Draw(overlay)

    x, y = layout["x"], layout["y"]
    panel_width = 520
    font, lines = fit_text(draw, text, panel_width, 2)
    line_y = y
    accent = layout["accent"]
    draw.line((x, y - 18, x + 138, y - 18), fill=accent, width=8)
    for line in lines:
        draw.text(
            (x + 5, line_y + 7),
            line,
            font=font,
            fill=(4, 8, 14),
            stroke_width=layout["stroke"] + 2,
            stroke_fill=(4, 8, 14),
        )
        draw.text(
            (x, line_y),
            line,
            font=font,
            fill=(255, 255, 255),
            stroke_width=layout["stroke"],
            stroke_fill=(4, 8, 14),
        )
        box = draw.textbbox((x, line_y), line, font=font)
        line_y += box[3] - box[1] + 8

    return overlay.convert("RGB")


def finish_generated_thumbnail(img, overlay_text="", variant=0):
    img = overlay_editorial_title(img, overlay_text, variant)
    return img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=2))


def badge(draw, label, x, y, color):
    font = get_font(30)
    box = draw.textbbox((0, 0), label, font=font)
    w = box[2] - box[0] + 48
    draw.rounded_rectangle((x, y, x + w, y + 58), 18, fill=color)
    draw.text(
        (x + 24, y + 10),
        label,
        font=font,
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0)
    )


def add_side_gradient(img, side="left", color=(0, 0, 0), alpha=180):
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    px = overlay.load()

    for x in range(WIDTH):
        if side == "left":
            strength = max(0, 1 - x / 780)
        else:
            strength = max(0, 1 - (WIDTH - x) / 780)

        a = int(alpha * strength)
        for y in range(HEIGHT):
            px[x, y] = (*color, a)

    return Image.alpha_composite(img.convert("RGBA"), overlay)


def style_viral(base, text):
    base = ImageEnhance.Color(base).enhance(1.45)
    base = ImageEnhance.Contrast(base).enhance(1.35)
    img = add_side_gradient(base, "left", (0, 0, 0), 210)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, 26, HEIGHT), fill=(255, 30, 60))
    draw.rectangle((26, 0, 42, HEIGHT), fill=(255, 230, 0))
    badge(draw, "MUST WATCH", 70, 70, (255, 30, 60))

    font, lines = fit_text(draw, text, 650, 3)
    text_block(draw, lines, 70, 230, font, (255, 255, 255), (255, 230, 0))

    return img.convert("RGB")


def style_cinematic(base, text):
    base = ImageEnhance.Color(base).enhance(1.15)
    base = ImageEnhance.Contrast(base).enhance(1.45)
    img = base.convert("RGBA")

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (15, 5, 0, 85))
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, WIDTH, 85), fill=(0, 0, 0, 230))
    draw.rectangle((0, HEIGHT - 95, WIDTH, HEIGHT), fill=(0, 0, 0, 230))
    draw.rectangle((0, 430, WIDTH, HEIGHT), fill=(0, 0, 0, 130))

    badge(draw, "CINEMATIC", 70, 110, (220, 35, 35))
    font, lines = fit_text(draw, text, 1080, 2)
    text_block(draw, lines, 70, 485, font, (255, 255, 255), (255, 190, 35))

    return img.convert("RGB")


def style_neon(base, text):
    base = ImageEnhance.Color(base).enhance(1.25)
    base = ImageEnhance.Contrast(base).enhance(1.3)
    img = add_side_gradient(base, "right", (0, 20, 45), 210)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        (535, 90, 1210, 625),
        35,
        fill=(0, 0, 0, 150),
        outline=(0, 230, 255),
        width=5
    )
    badge(draw, "AI OPTIMIZED", 575, 125, (0, 130, 255))

    font, lines = fit_text(draw, text, 560, 3)
    text_block(draw, lines, 575, 245, font, (255, 255, 255), (0, 230, 255))

    return img.convert("RGB")


def style_premium(base, text):
    base = ImageEnhance.Color(base).enhance(1.05)
    base = ImageEnhance.Contrast(base).enhance(1.2)
    blurred = base.filter(ImageFilter.GaussianBlur(5)).convert("RGBA")
    draw = ImageDraw.Draw(blurred)

    draw.rounded_rectangle(
        (95, 105, 1185, 610),
        35,
        fill=(255, 255, 255, 230)
    )
    draw.rectangle((95, 105, 1185, 205), fill=(13, 71, 161))

    header = get_font(38)
    draw.text((135, 135), "PROFESSIONAL SEO THUMBNAIL", font=header, fill=(255, 255, 255))

    font, lines = fit_text(draw, text, 950, 2)
    y = 285
    for line in lines:
        draw.text(
            (135, y),
            line,
            font=font,
            fill=(13, 71, 161),
            stroke_width=2,
            stroke_fill=(255, 255, 255)
        )
        box = draw.textbbox((135, y), line, font=font)
        y += box[3] - box[1] + 12

    badge(draw, "RANK HIGHER", 135, 520, (13, 71, 161))
    return blurred.convert("RGB")


def create_thumbnail_preview(concept, video_title, base_image_url=None, variant=0):
    text = concept.get("text_overlay") or video_title or "WATCH NOW"
    base = load_video_thumbnail(base_image_url)

    styles = [
        style_viral,
        style_neon,
        style_cinematic,
        style_premium
    ]

    img = styles[variant % 4](base, text)

    draw = ImageDraw.Draw(img)
    font = get_font(22)
    draw.text(
        (WIDTH - 270, HEIGHT - 38),
        "Video SEO Optimizer",
        font=font,
        fill=(255, 255, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0)
    )

    return img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
