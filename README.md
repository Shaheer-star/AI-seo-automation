<div align="center">

  <img src="assets/logo.png" alt="Video SEO Optimizer Logo" width="120" />

  # Multi-Model AI Video SEO Optimizer and Thumbnail Studio

  <p>
    <strong>BS Computer Science Final Year Project</strong><br/>
    An AI-powered Streamlit application for video SEO analysis, metadata optimization, and HD thumbnail generation.
  </p>

  <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&pause=900&color=38BDF8&center=true&vCenter=true&width=900&lines=Autonomous+Video+SEO+Assistant;LangChain+%2B+Groq+Multi-Agent+Workflow;YouTube+Metadata+Extraction+with+yt-dlp+Fallback;AI+Thumbnail+Studio+with+Hugging+Face;Built+as+a+BSCS+Final+Year+Project" alt="Animated project summary" />

  <br/><br/>

  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Streamlit-1.45.1-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/LangChain-Agentic_AI-1C3C3C?style=for-the-badge" alt="LangChain" />
  <img src="https://img.shields.io/badge/Groq-LLaMA_3-F55036?style=for-the-badge" alt="Groq" />
  <img src="https://img.shields.io/badge/Hugging_Face-Image_AI-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face" />

</div>

---

## Overview

**Multi-Model AI Video SEO Optimizer and Thumbnail Studio** is a Project built for creators, marketers, and students who want to improve the discoverability of online videos. The system accepts a video URL, extracts available metadata, analyzes the content context, and generates SEO-friendly recommendations such as tags, titles, descriptions, timestamps, and thumbnail concepts.

The project combines a Streamlit user interface with AI-assisted SEO generation, platform metadata extraction, structured output validation, and optional AI image generation for 1280 x 720 thumbnail assets.

---

## Core Features

| Feature | What It Does | Main Files |
| --- | --- | --- |
| Video metadata extraction | Extracts title, description, duration, views, channel name, thumbnail URL, and platform information. Uses YouTube Data API when available and `yt-dlp` fallback when needed. | `utils/video_extractor.py` |
| Multi-agent SEO generation | Uses LangChain and Groq to generate SEO recommendations from video metadata and content context. | `utils/seo_agents.py` |
| SEO scoring and analysis | Evaluates keywords, descriptions, tags, titles, and optimization quality. | `analysis_functions.py` |
| Output guardrails | Repairs and validates model responses so the UI receives clean structured data. | `utils/output_guard.py` |
| Thumbnail Studio | Builds thumbnail briefs, generates AI images through Hugging Face, overlays text, and exports images. | `utils/thumbnails.py` |
| Streamlit interface | Provides the complete interactive dashboard, sidebar API configuration, analysis results, and download buttons. | `app.py` |

---

## System Architecture

```mermaid
flowchart TD
    A[User enters video URL or topic] --> B[Streamlit app.py]
    B --> C[Video metadata extractor]
    C --> D{API keys available?}
    D -->|YouTube API| E[Fetch official public metadata]
    D -->|No YouTube key or fallback needed| F[yt-dlp metadata extraction]
    E --> G[LangChain + Groq SEO agents]
    F --> G
    G --> H[Output guard validation]
    H --> I[SEO recommendations]
    H --> J[Thumbnail brief builder]
    J --> K[Hugging Face image generation]
    K --> L[HD thumbnail compositor]
    I --> M[Interactive Streamlit results]
    L --> M
    M --> N[Download descriptions, tags, timestamps, and thumbnails]
```

---

## AI Workflow

```mermaid
sequenceDiagram
    participant User
    participant UI as Streamlit UI
    participant Extractor as Metadata Extractor
    participant Agent as SEO Agent Pipeline
    participant Guard as Output Guardrails
    participant Thumb as Thumbnail Studio

    User->>UI: Submit video URL or topic
    UI->>Extractor: Request metadata
    Extractor-->>UI: Return title, duration, views, author, description
    UI->>Agent: Send metadata and language preference
    Agent-->>Guard: Return generated SEO JSON
    Guard-->>UI: Return repaired and validated recommendations
    UI->>Thumb: Build thumbnail prompt and overlay text
    Thumb-->>UI: Return HD thumbnail options
    UI-->>User: Display SEO package and download assets
```

---

## Repository Structure

```text
video-seo-optimizer/
|-- app.py
|-- analysis_functions.py
|-- requirements.txt
|-- README.md
|-- .env.example
|-- .gitignore
|-- assets/
|   `-- logo.png
`-- utils/
    |-- __init__.py
    |-- output_guard.py
    |-- seo_agents.py
    |-- thumbnails.py
    `-- video_extractor.py
```

This GitHub-ready folder intentionally excludes:

- `.env` real secrets
- `.venv` virtual environment
- `.git` local repository history
- `.agents` workspace files
- `.streamlit` runtime files
- `__pycache__` Python cache
- zip archives and generated output files

---

## Technology Stack

| Layer | Tools and Libraries |
| --- | --- |
| Frontend | Streamlit |
| AI orchestration | LangChain |
| LLM provider | Groq API |
| Optional OpenAI fallback module | OpenAI Python SDK |
| Thumbnail generation | Hugging Face Inference API, Pillow |
| Metadata extraction | YouTube Data API v3, yt-dlp, requests |
| Data handling | pandas, numpy, pydantic |
| Environment management | python-dotenv |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/video-seo-optimizer.git
cd video-seo-optimizer
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file from the example file.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux or macOS:

```bash
cp .env.example .env
```

Then add your own API keys:

```env
GROQ_API_KEY=your_groq_api_key_here
HF_TOKEN=your_hugging_face_token_here
YOUTUBE_API_KEY=your_youtube_data_api_key_here
```

### 5. Run the application

```bash
streamlit run app.py
```

Open the local app in your browser:

```text
http://localhost:8501
```

---

## API Keys

| Key | Required | Purpose |
| --- | --- | --- |
| `GROQ_API_KEY` | Recommended | Powers the main LangChain SEO agent workflow. |
| `HF_TOKEN` | Required for AI thumbnails | Generates HD thumbnail artwork through Hugging Face. |
| `YOUTUBE_API_KEY` | Optional | Improves metadata accuracy using the official YouTube Data API. |
| `OPENAI_API_KEY` | Optional | Used only by the optional `analysis_functions.py` OpenAI path. |

Never commit the real `.env` file to GitHub. This repository includes `.env.example` only.

---

## How to Use

1. Start the Streamlit app.
2. Enter a YouTube video URL or supported video topic.
3. Add API keys in the sidebar or in your local `.env` file.
4. Run the SEO analysis.
5. Review generated titles, tags, descriptions, timestamps, and SEO insights.
6. Generate thumbnail concepts and HD thumbnail images if a Hugging Face token is configured.
7. Download individual thumbnails or export all generated thumbnail options as a zip file.

---

## Output Examples

The app can generate:

- Search-optimized titles
- 35 relevant tags or hashtags
- Long-form SEO descriptions
- Video chapter timestamps
- SEO score and improvement suggestions
- Thumbnail concepts with color direction, focal point, tone, and composition
- 1280 x 720 thumbnail images with overlay text

---

## Academic Relevance

This project demonstrates practical implementation of several Computer Science concepts:

- Natural Language Processing
- Prompt engineering
- Agentic AI workflow design
- API integration
- Web application development
- Data validation and repair
- Multimedia metadata extraction
- Generative AI image processing
- Human-computer interaction through Streamlit

---

## Final Year Project Details

| Field | Detail |
| --- | --- |
| Degree | BS Computer Science |
| Project Type | Final Year Project |
| Domain | Artificial Intelligence, SEO Automation, Web Development |
| Application Type | AI-powered Streamlit web app |
| Main Objective | Automate video SEO recommendations and thumbnail generation |

---

## GitHub Upload Checklist

Before uploading, confirm that your repository contains only these useful files:

- `app.py`
- `analysis_functions.py`
- `requirements.txt`
- `README.md`
- `.env.example`
- `.gitignore`
- `assets/logo.png`
- `utils/*.py`

Do not upload:

- `.env`
- `.venv/`
- `__pycache__/`
- `.git/`
- zip files
- generated thumbnails containing private/client data
- local logs or temporary files

---

## Useful Git Commands

Run these commands from inside the `video-seo-optimizer` folder:

```bash
git init
git add .
git commit -m "Initial commit: AI video SEO optimizer"
git branch -M main
git remote add origin https://github.com/your-username/video-seo-optimizer.git
git push -u origin main
```

---

## Future Enhancements

- Add user authentication for saved SEO projects
- Add database storage for analysis history
- Add support for TikTok, Instagram Reels, and Facebook videos
- Add competitor keyword comparison
- Add automated PDF export for SEO reports
- Add thumbnail A/B testing score prediction
- Deploy on Streamlit Community Cloud or Hugging Face Spaces

---

<div align="center">

  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:0EA5E9,100:22C55E&height=120&section=footer&text=AI%20Video%20SEO%20Optimizer&fontColor=ffffff&fontSize=28&animation=twinkling" alt="Animated footer" />

  <strong>Built as a BS Computer Science Final Year Project</strong>

</div>
