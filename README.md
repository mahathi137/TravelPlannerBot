# ✈️ TravelBot — Smart Travel Planner Agent

> A polished Flask-based travel planner that combines a clean Bootstrap interface with IBM watsonx.ai integration and a reliable demo mode fallback. It is designed for internship-style project submissions and focuses on practical travel planning features rather than flashy extras.

---

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [IBM Watsonx Setup](#ibm-watsonx-setup)
- [Customising the Agent](#customising-the-agent)
- [API Reference](#api-reference)
- [Deployment](#deployment)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Travel Chat** | Destination-aware chat responses that consider destination, trip length, travellers, budget, style, and preferences |
| 🗺️ **Itinerary Generator** | Personalised day-by-day travel itineraries with activities, restaurant suggestions, travel tips, and daily cost estimates |
| 💰 **Budget Planner** | Realistic trip cost estimation across accommodation, food, transport, sightseeing, and misc. categories |
| 🏨 **Destination Information** | Region details, best travel months, weather, attractions, food, transport, and hotel ranges |
| 🍽️ **Restaurant & Hotel Suggestions** | Practical local recommendations tailored to each destination |
| 🌤️ **Travel Tips** | Helpful planning advice for weather, packing, transport, and budgeting |
| 📄 **Trip Summary** | Downloadable itinerary summaries for convenient sharing |
| 🌙 **Dark Mode** | Clean light/dark theme with responsive Bootstrap layout |
| 🔒 **Demo Mode** | Runs without IBM credentials and clearly indicates when the app is using its local planning logic |

---

## 📁 Project Structure

```
TravelPlannerAgent/
├── app.py                    # Flask backend + Watsonx integration + AGENT_INSTRUCTIONS
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Your actual credentials (DO NOT COMMIT)
├── .gitignore                # Excludes .env, __pycache__, etc.
│
├── templates/
│   └── index.html            # Single-page frontend (Jinja2)
│
└── static/
    ├── css/
    │   └── style.css         # Custom styles + dark mode + animations
    └── js/
        └── app.js            # Frontend logic (Chat, Budget, Itinerary, Group Trip)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- IBM Cloud account (free tier available)
- IBM Watsonx.ai project

### 1. Clone & setup environment

```bash
git clone https://github.com/your-repo/travel-planner-agent.git
cd TravelPlannerAgent

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS / Linux)
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
# Copy the template
cp .env.example .env

# Edit .env and fill in your credentials
notepad .env         # Windows
nano .env            # macOS / Linux
```

Your `.env` should look like:

```env
IBM_API_KEY=your_actual_ibm_cloud_api_key
WATSONX_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=your_watsonx_project_url
FLASK_SECRET_KEY=any-random-secure-string
```

### 4. Run the application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

> **Demo Mode**: If API credentials are not configured, the app runs in demo mode with sample responses — perfect for UI testing.

---

## 🔑 IBM Watsonx Setup

### Step 1: Create IBM Cloud account
1. Go to [cloud.ibm.com](https://cloud.ibm.com) and sign up (free tier available)
2. Navigate to **Manage → Access (IAM) → API Keys**
3. Click **Create an IBM Cloud API key** and copy it

### Step 2: Create Watsonx.ai project
1. Go to [dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com)
2. Click **New Project → Create an empty project**
3. Copy the **Project ID** from project settings

### Step 3: Enable Watsonx.ai service
1. In your IBM Cloud account, go to **Catalog → AI / Machine Learning**
2. Add **Watson Machine Learning** service to your project
3. Ensure your region matches `WATSONX_URL` in `.env`

### Available Granite Models

| Model ID | Best For |
|---|---|
| `ibm/granite-3-8b-instruct` | Best quality (recommended) |
| `ibm/granite-3-2b-instruct` | Faster responses |
| `ibm/granite-13b-instruct-v2` | Older, widely available |

Change the model in `.env`:
```env
WATSONX_MODEL_ID=ibm/granite-3-8b-instruct
```

---

## 🎛️ Customising the Agent

All agent behaviour is controlled by the `AGENT_INSTRUCTIONS` dictionary at the **top of `app.py`** (lines 21–95). No AI knowledge required!

```python
AGENT_INSTRUCTIONS = {
    # ── Change the bot's name ────────────────────────────────────
    "name": "TravelBot",          # ← Change to "JourneyAI", "WanderlustBot", etc.

    # ── Set personality ─────────────────────────────────────────
    "persona": "You are TravelBot, an enthusiastic AI travel assistant...",

    # ── Change default travel style ──────────────────────────────
    "default_travel_style": "balanced",
    # Options: balanced | budget | luxury | adventure | family | solo | cultural

    # ── Toggle Indian destination focus ──────────────────────────
    "emphasise_indian_destinations": True,   # Set False for global destinations

    # ── Communication tone ───────────────────────────────────────
    "tone": "friendly_professional",
    "use_emojis": True,

    # ── Safety rules ─────────────────────────────────────────────
    "safety_rules": [
        "Always recommend checking official travel advisories...",
        # Add your own rules here
    ],
}
```

### Common Customisations

**Make it a luxury travel specialist:**
```python
"default_travel_style": "luxury",
"persona": "You are LuxuryTrailBot, an expert in high-end travel experiences...",
"emphasise_indian_destinations": False,
```

**Add a safety rule:**
```python
"safety_rules": [
    ...existing rules...,
    "Always remind travellers to check visa requirements for international destinations.",
]
```

**Change to a more formal tone:**
```python
"tone": "formal",
"use_emojis": False,
"language_style": "Use professional language with detailed travel insights.",
```

---

## 📡 API Reference

All endpoints accept/return JSON.

### `POST /api/chat`
Chat with the AI travel planning assistant.

**Request:**
```json
{
  "message": "Plan a 5-day trip to Goa for a couple on a budget",
  "history": [{"role": "user", "content": "..."}, ...],
  "profile": {
    "name": "Priya", "age": 28, "gender": "female",
    "nationality": "Indian", "travel_style": "budget",
    "goals": "beach relaxation", "budget": "₹2000/day"
  }
}
```

**Response:**
```json
{
  "response": "Here's a perfect 5-day Goa itinerary for couples on a budget...",
  "mode": "watsonx",
  "timestamp": "2025-01-15T10:30:00",
  "model": "ibm/granite-3-8b-instruct"
}
```

---

### `POST /api/budget`
Estimate trip budget.

**Request:**
```json
{ "destination": "Kerala", "days": 5, "travel_style": "balanced", "num_travellers": 2 }
```

**Response:**
```json
{
  "destination": "Kerala",
  "travel_style": "balanced",
  "days": 5,
  "num_travellers": 2,
  "daily_per_person": 4900,
  "total_per_person": 24500,
  "total_group": 49000,
  "breakdown": {
    "accommodation": 26950,
    "food": 15470,
    "transport": 12670,
    "sightseeing": 9850,
    "misc": 5635
  },
  "best_season": "September – March",
  "season_reason": "Post-monsoon greenery; pleasant temperatures for backwater cruises.",
  "currency": "INR",
  "destination_info": {
    "region": "South India",
    "top_attractions": ["Alleppey Backwaters", "Munnar Tea Gardens", "Thekkady Wildlife", "Kovalam Beach"],
    "hotel_range": "₹2,000–₹5,000/night"
  }
}
```

---

### `POST /api/itinerary`
Generate a personalised AI travel itinerary.

**Request:**
```json
{ "destination": "Rajasthan", "days": 7, "travel_style": "cultural", "profile": {...} }
```

**Response:**
```json
{ "itinerary": "**7-Day Rajasthan Heritage Tour...**", "mode": "watsonx" }
```

---

### `POST /api/group-trip`
Get group travel recommendations.

**Request:**
```json
{ "members": [{"name": "Raj", "age": 30, "gender": "male", "travel_style": "adventure", "goals": "trekking"}, ...] }
```

---

### `GET /api/health`
Check API and Watsonx connection status.

---

## 🚢 Deployment

### Option 1: Local (Development)

```bash
python app.py
```

### Option 2: Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Option 3: Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:
```bash
docker build -t travelbot .
docker run -p 5000:5000 --env-file .env travelbot
```

### Option 4: IBM Code Engine

```bash
# Install IBM Cloud CLI + Code Engine plugin first
ibmcloud ce project create --name travelbot-project
ibmcloud ce app create \
  --name travelbot \
  --image your-registry/travelbot:latest \
  --env-from-secret travelbot-secrets \
  --port 5000
```

### Option 5: Railway / Render / Fly.io

Set environment variables in the platform dashboard:
- `IBM_API_KEY`
- `WATSONX_PROJECT_ID`
- `WATSONX_URL`
- `FLASK_SECRET_KEY`

---
---

## 🛠️ Troubleshooting

| Issue | Solution |
|---|---|
| `IBM_API_KEY not set` | Copy `.env.example` to `.env` and fill in credentials |
| `401 Unauthorized` | Verify your IBM API Key is valid and active |
| `404 model not found` | Check `WATSONX_MODEL_ID` — use exact model ID from IBM catalog |
| `Import error: ibm_watsonx_ai` | Run `pip install ibm-watsonx-ai==1.5.14` |
| Charts not loading | Ensure internet access for CDN (Chart.js, Bootstrap) |
| Dark mode not saving | Enable localStorage in browser settings |

---

## 📝 License

MIT License — free for personal and commercial use.

---

*Built with ❤️ using IBM Watsonx.ai, Granite Models, Python Flask, and Bootstrap 5*
