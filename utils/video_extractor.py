
import html
import json
import os
import re
import requests
from urllib.parse import parse_qs, urlparse

try:
    from yt_dlp import YoutubeDL
except Exception:
    YoutubeDL = None

# here we are creating three types of functions(def)
# 1) id =  what's the id of video
# 2) metadata = “data about data” — it describes information about a video (like size, date, author, etc.).
# 3) from which platform we are fetching video


def public_get(url, **kwargs):
    session = requests.Session()
    session.trust_env = False
    return session.get(url, **kwargs)


def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    if not url:
        return None

    url = url.strip()

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # YouTube URL patterns
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/e/|youtube\.com/watch\?.*v=)([^&?#/]+)",
        r"youtube\.com/shorts/([^&?#/]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    # Fallback parsing
    parsed_url = urlparse(url)

    if "youtube.com" in parsed_url.netloc:
        if "watch" in parsed_url.path:
            query = parse_qs(parsed_url.query)
            if "v" in query:
                return query["v"][0]

        elif "/shorts/" in parsed_url.path:
            path_parts = parsed_url.path.split("/")
            for i, part in enumerate(path_parts):
                if part == "shorts" and i + 1 < len(path_parts):
                    return path_parts[i + 1]

    elif "youtu.be" in parsed_url.netloc:
        return parsed_url.path.strip("/")

    return None


def get_video_platform(url):
    """Determine the platform from the video URL."""
    if not url:
        return "Unknown"

    url = url.strip().lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "YouTube"
    elif "instagram.com" in url:
        return "Instagram"
    elif "linkedin.com" in url:
        return "LinkedIn"
    elif "facebook.com" in url or "fb.com" in url:
        return "Facebook"
    elif "tiktok.com" in url:
        return "TikTok"
    elif "twitter.com" in url or "x.com" in url:
        return "Twitter"
    else:
        return "Unknown"


def get_youtube_metadata(video_id):
    """Get metadata for a YouTube video with fallback mechanisms."""

    basic_metadata = {
        "title": f"YouTube Video ({video_id})",
        "description": "",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
        "duration": 0,
        "views": 0,
        "author": "YouTube Creator",
        "platform": "YouTube",
        "video_id": video_id,
        "metadata_status": "limited",
        "metadata_reason": ""
    }

    def apply_video_details(details):
        if not isinstance(details, dict):
            return

        if details.get("title"):
            basic_metadata["title"] = html.unescape(str(details["title"]))
            basic_metadata["metadata_status"] = "complete"

        if details.get("author"):
            basic_metadata["author"] = html.unescape(str(details["author"]))

        if details.get("shortDescription"):
            basic_metadata["description"] = html.unescape(str(details["shortDescription"]))

        if details.get("lengthSeconds"):
            try:
                basic_metadata["duration"] = int(details["lengthSeconds"])
            except (TypeError, ValueError):
                pass

        if details.get("viewCount"):
            try:
                basic_metadata["views"] = int(details["viewCount"])
            except (TypeError, ValueError):
                pass

        thumbnails = details.get("thumbnail", {}).get("thumbnails", [])
        if thumbnails:
            best_thumbnail = sorted(
                thumbnails,
                key=lambda item: item.get("width", 0),
                reverse=True
            )[0]
            if best_thumbnail.get("url"):
                basic_metadata["thumbnail_url"] = best_thumbnail["url"]

    def parse_iso_duration(value):
        if not value:
            return None

        match = re.fullmatch(
            r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
            value
        )
        if not match:
            return None

        parts = {key: int(val or 0) for key, val in match.groupdict().items()}
        return (
            parts["days"] * 86400
            + parts["hours"] * 3600
            + parts["minutes"] * 60
            + parts["seconds"]
        )

    def apply_ytdlp_info(info):
        if not isinstance(info, dict):
            return False

        if info.get("title"):
            basic_metadata["title"] = html.unescape(str(info["title"]))
            basic_metadata["metadata_status"] = "complete"

        if info.get("channel") or info.get("uploader"):
            basic_metadata["author"] = html.unescape(str(info.get("channel") or info.get("uploader")))

        if info.get("description"):
            basic_metadata["description"] = html.unescape(str(info["description"]))

        if info.get("duration"):
            try:
                basic_metadata["duration"] = int(info["duration"])
            except (TypeError, ValueError):
                pass

        if info.get("view_count"):
            try:
                basic_metadata["views"] = int(info["view_count"])
            except (TypeError, ValueError):
                pass

        thumbnail = info.get("thumbnail")
        thumbnails = info.get("thumbnails") or []
        if thumbnails:
            best = sorted(
                thumbnails,
                key=lambda item: (item.get("width") or 0) * (item.get("height") or 0),
                reverse=True,
            )[0]
            thumbnail = best.get("url") or thumbnail

        if thumbnail:
            basic_metadata["thumbnail_url"] = thumbnail

        return basic_metadata["metadata_status"] == "complete"

    try:
        api_key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("YOUTUBE_API")
        if api_key:
            api_url = "https://www.googleapis.com/youtube/v3/videos"
            api_response = public_get(
                api_url,
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": video_id,
                    "key": api_key,
                },
                timeout=15,
            )

            if api_response.status_code == 200:
                api_data = api_response.json()
                items = api_data.get("items", [])
                if items:
                    item = items[0]
                    snippet = item.get("snippet", {})
                    statistics = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})

                    if snippet.get("title"):
                        basic_metadata["title"] = html.unescape(snippet["title"])
                        basic_metadata["metadata_status"] = "complete"

                    if snippet.get("channelTitle"):
                        basic_metadata["author"] = html.unescape(snippet["channelTitle"])

                    if snippet.get("description"):
                        basic_metadata["description"] = html.unescape(snippet["description"])

                    thumbnails = snippet.get("thumbnails", {})
                    if thumbnails:
                        best = (
                            thumbnails.get("maxres")
                            or thumbnails.get("standard")
                            or thumbnails.get("high")
                            or thumbnails.get("medium")
                            or thumbnails.get("default")
                        )
                        if best and best.get("url"):
                            basic_metadata["thumbnail_url"] = best["url"]

                    if statistics.get("viewCount"):
                        basic_metadata["views"] = int(statistics["viewCount"])

                    parsed_duration = parse_iso_duration(content_details.get("duration"))
                    if parsed_duration:
                        basic_metadata["duration"] = parsed_duration

                    return basic_metadata

            basic_metadata["metadata_reason"] = (
                "YouTube Data API did not return a public video item for this ID."
            )
            print(f"YouTube API metadata lookup failed: {api_response.status_code} {api_response.text[:200]}")

    except Exception as e:
        basic_metadata["metadata_reason"] = "YouTube Data API request failed."
        print(f"YouTube API metadata lookup failed: {e}")

    if YoutubeDL is not None:
        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": True,
                "proxy": "",
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False,
                )
            if apply_ytdlp_info(info):
                return basic_metadata
        except Exception as e:
            basic_metadata["metadata_reason"] = f"yt-dlp could not access this video: {str(e).splitlines()[-1]}"
            print(f"yt-dlp metadata lookup failed: {e}")

    try:
        # Method 1: Scrape public HTML
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/96.0.4664.110 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9"
        }

        response = public_get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            html_content = response.text

            player_match = re.search(
                r"ytInitialPlayerResponse\s*=\s*({.+?});\s*(?:var\s+meta|</script>)",
                html_content
            )
            if player_match:
                try:
                    player_response = json.loads(player_match.group(1))
                    apply_video_details(player_response.get("videoDetails", {}))
                except Exception:
                    pass

            # Title
            title_match = re.search(
                r'<meta property="og:title" content="([^"]+)"',
                html_content
            )
            if title_match:
                basic_metadata["title"] = html.unescape(title_match.group(1))

            # Author
            author_match = re.search(
                r'<link itemprop="name"\s+content="([^"]+)"',
                html_content
            )
            if author_match:
                basic_metadata["author"] = html.unescape(author_match.group(1))

            # Description
            description_match = re.search(
                r'<meta property="og:description" content="([^"]+)"',
                html_content
            )
            if description_match:
                basic_metadata["description"] = html.unescape(description_match.group(1))

            # Duration
            duration_match = re.search(r'"lengthSeconds":"(\d+)"', html_content)
            if duration_match:
                try:
                    basic_metadata["duration"] = int(duration_match.group(1))
                except ValueError:
                    pass

            # Views
            views_match = re.search(r'"viewCount":"(\d+)"', html_content)
            if views_match:
                try:
                    basic_metadata["views"] = int(views_match.group(1))
                except ValueError:
                    pass

            # Thumbnail
            thumbnail_match = re.search(
                r'<meta property="og:image" content="([^"]+)"',
                html_content
            )
            if thumbnail_match:
                basic_metadata["thumbnail_url"] = thumbnail_match.group(1)

            approx_duration_match = re.search(r'"approxDurationMs":"(\d+)"', html_content)
            if approx_duration_match:
                try:
                    basic_metadata["duration"] = int(approx_duration_match.group(1)) // 1000
                except ValueError:
                    pass

        # Method 2: oEmbed fallback
        try:
            oembed_url = (
                f"https://www.youtube.com/oembed?"
                f"url=https://www.youtube.com/watch?v={video_id}&format=json"
            )
            oembed_response = public_get(oembed_url, timeout=15)

            if oembed_response.status_code == 200:
                oembed_data = oembed_response.json()

                if oembed_data.get("title"):
                    basic_metadata["title"] = oembed_data["title"]

                if oembed_data.get("author_name"):
                    basic_metadata["author"] = oembed_data["author_name"]

                if oembed_data.get("thumbnail_url"):
                    basic_metadata["thumbnail_url"] = oembed_data["thumbnail_url"]

        except Exception:
            pass

        # Method 3: public metadata fallback for duration and views.
        # This endpoint mirrors public YouTube metadata without requiring an API key.
        try:
            public_api_url = (
                "https://yt.lemnoslife.com/videos"
                f"?part=snippet,statistics,contentDetails&id={video_id}"
            )
            api_response = public_get(public_api_url, timeout=15)

            if api_response.status_code == 200:
                api_data = api_response.json()
                items = api_data.get("items", [])
                if items:
                    item = items[0]
                    snippet = item.get("snippet", {})
                    statistics = item.get("statistics", {})
                    content_details = item.get("contentDetails", {})

                    if snippet.get("title"):
                        basic_metadata["title"] = html.unescape(snippet["title"])
                        basic_metadata["metadata_status"] = "complete"

                    if snippet.get("channelTitle"):
                        basic_metadata["author"] = html.unescape(snippet["channelTitle"])

                    if snippet.get("description"):
                        basic_metadata["description"] = html.unescape(snippet["description"])

                    thumbnails = snippet.get("thumbnails", {})
                    if thumbnails:
                        best = (
                            thumbnails.get("maxres")
                            or thumbnails.get("standard")
                            or thumbnails.get("high")
                            or thumbnails.get("medium")
                            or thumbnails.get("default")
                        )
                        if best and best.get("url"):
                            basic_metadata["thumbnail_url"] = best["url"]

                    if statistics.get("viewCount"):
                        basic_metadata["views"] = int(statistics["viewCount"])

                    parsed_duration = parse_iso_duration(content_details.get("duration"))
                    if parsed_duration:
                        basic_metadata["duration"] = parsed_duration

        except Exception:
            pass

    except Exception as e:
        print(f"Error extracting YouTube metadata: {e}")

    return basic_metadata


def get_video_metadata(url):
    """Get video metadata based on the platform."""
    if not url:
        raise ValueError("Please enter a video URL")

    platform = get_video_platform(url)

    if platform == "YouTube":
        video_id = extract_video_id(url)

        if not video_id:
            raise ValueError(
                "Could not extract video ID from URL. Please use a standard YouTube URL."
            )

        return get_youtube_metadata(video_id)

    return {
        "title": f"Video on {platform}",
        "description": "",
        "thumbnail_url": f"https://via.placeholder.com/1280x720.png?text={platform}",
        "duration": 0,
        "views": 0,
        "author": f"{platform} Creator",
        "platform": platform,
        "video_id": "unknown",
        "metadata_status": "limited",
        "metadata_reason": "Only basic metadata is available for this platform."
    }
