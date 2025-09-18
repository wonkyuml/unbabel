# Unbabel - Continuous Automatic Translation Broadcasting App

A lightweight web application that receives a live audio stream from a single speaker, converts speech to text in real time, translates that text to a target language using an LLM, and broadcasts the translated transcript to many viewers with minimal latency.

## Features

- Live audio capture and streaming (browser-based, no PyAudio required)
- Real-time speech-to-text using Deepgram
- Translation using OpenAI GPT-4o
- Broadcasting to multiple viewers
- Low latency (<3s end-to-end)
- Scalable to thousands of viewers

## How it works

- The broadcaster page captures microphone audio using the browser `MediaRecorder` API and encodes it as `audio/webm;codecs=opus` at 16 kHz mono.
- Encoded audio chunks are sent over a WebSocket to the server at `/ws/stream/{room_id}`.
- The server forwards the binary audio frames directly to Deepgram Live Transcription.
- As transcripts arrive from Deepgram, the server translates them with OpenAI and broadcasts caption messages to all viewers connected to `/ws/view/{room_id}`.

Notes:
- Audio capture is entirely in the browser. There is no server-side microphone capture and no need for PyAudio.
- A small HTTPS middleware adapts links for Cloud Run so assets load over HTTPS when deployed.

## Setup

1. Clone this repository
2. Create a `.env` file with your API keys (see `.env.example`)
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
REDIS_URL=redis://localhost:6379
```

Notes:
- Redis is not required for the MVP; state is stored in-memory. The `REDIS_URL` is provided for future/production use.
- `PORT` is honored automatically on Cloud Run. You can also set `HOST`, `PORT`, and `DEBUG` if needed.
- Default translation is Korean -> English; adjust language defaults in `app/config.py`.

## Project Structure

```
unbabel/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application
│   ├── config.py              # Configuration settings
│   ├── middleware.py          # HTTPS adjustments for Cloud Run
│   ├── routes/                # API routes
│   │   ├── __init__.py
│   │   ├── broadcast.py       # Broadcaster WebSocket: /ws/stream/{room_id}
│   │   ├── viewer.py          # Viewer WebSocket: /ws/view/{room_id}
│   │   └── pages.py           # Web page routes
│   ├── services/              # Business logic
│   │   ├── __init__.py
│   │   ├── stt.py             # Speech-to-text (Deepgram Live)
│   │   ├── translation.py     # Translation (OpenAI GPT-4o)
│   │   └── broadcast.py       # Broadcasting helper
│   ├── models/
│   │   ├── __init__.py
│   │   └── messages.py        # Message schemas
│   └── utils/
│       ├── __init__.py
│       ├── websocket.py       # WebSocket helpers
│       └── state.py           # In-memory room state (MVP)
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── broadcaster.js
│       └── viewer.js
├── templates/
│   ├── base.html
│   ├── base_with_protocol.html
│   ├── index.html
│   ├── broadcast.html
│   └── view.html
├── .env                       # Environment variables (not in repo)
├── .env.example               # Example environment variables
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
```

## Usage

1. Start the app and open the homepage.
2. Click "Start Broadcast" to create a new room and open the broadcaster page.
3. On the broadcaster page, click "Start" to grant mic permission and begin streaming.
4. Share the viewer link on that page; viewers see original and translated captions live.

### WebSocket endpoints

- Broadcaster audio stream: `ws://<host>/ws/stream/{room_id}`
- Viewer captions: `ws://<host>/ws/view/{room_id}`

## Deployment to Google Cloud Run

This application can be easily deployed to Google Cloud Run using the provided deployment script.

### Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed
- [Docker](https://docs.docker.com/get-docker/) installed
- A Google Cloud Platform account with billing enabled
- A Google Cloud project created

### Deployment Steps

1. Make the deployment script executable:
   ```
   chmod +x deploy-to-cloud-run.sh
   ```

2. Edit the script to set your Google Cloud project ID:
   ```bash
   # Configuration
   PROJECT_ID="your-gcp-project-id"  # Replace with your GCP project ID
   ```

3. Create your `.env.yaml` file from the template:
   ```
   cp .env.yaml.template .env.yaml
   ```

4. Edit the `.env.yaml` file to add your API keys and configuration.

5. Run the deployment script:
   ```
   ./deploy-to-cloud-run.sh
   ```

6. The script will build and deploy your application to Google Cloud Run and provide you with a URL when complete.

### Scaling Configuration

The deployment script includes default scaling settings that you can modify:

- `MIN_INSTANCES`: Minimum number of instances (default: 1)
- `MAX_INSTANCES`: Maximum number of instances (default: 10)
- `MEMORY`: Memory allocation per instance (default: 512Mi)
- `CPU`: CPU allocation per instance (default: 1)
- `CONCURRENCY`: Maximum concurrent requests per instance (default: 80)

Edit these values in the script based on your expected traffic and requirements.

## License

MIT
