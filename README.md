# TripWeaver

TripWeaver is a multi agent travel planning assistant. A traveller describes
what they need in plain language, a graph of specialist agents works out what
is being asked, and the right specialist gathers real hotel or flight data and
answers. The agents never talk to a travel provider directly. Every external
call goes through an MCP server, so a provider can be replaced without touching
agent code.

## Live demo

- Frontend: https://tripweaver-frontend-lg5y.onrender.com
- Backend: https://tripweaver-backend-xjpr.onrender.com

Both run on Render's free tier, which puts an instance to sleep after fifteen
minutes without traffic. The first request after a quiet period takes about a
minute while the instance wakes up. Open both links a few minutes before a
demonstration and they will respond immediately.

## Architecture

```
Gradio chat  --SSE-->  FastAPI  -->  LangGraph  -->  MCP client
                                                          |
                                        +-----------------+-----------------+
                                        |                                   |
                                  hotel MCP server                  flight MCP server
                                        |                                   |
                                        +------------> Convex travel API <---+
```

| Component | Responsibility |
|---|---|
| `frontend/app.py` | Chat interface. Streams the reply and shows agent activity. Holds no travel logic. |
| `main.py` | FastAPI endpoints. Builds the graph at startup and streams its execution. |
| `agents/graph.py` | The LangGraph topology and the intent routing. |
| `agents/nodes.py` | Router, the specialist agents, and the tool call lifecycle. |
| `agents/mcp_client.py` | Loads the MCP tools once at startup, one server at a time. |
| `mcp_servers/` | Two MCP servers and the single HTTP client that knows the travel provider. |

The graph routes on intent rather than running a fixed path:

```
START -> router -+-> hotel_agent  <-> hotel_tools
                 +-> flight_agent <-> flight_tools
                 +-> general_qa
                 +-> ambiguous
```

## Prerequisites

- Python 3.12
- An OpenAI API key

## Environment variables

Copy `.env.example` to `.env` and fill in the values. Nothing here is committed.

| Name | Purpose | Example |
|---|---|---|
| `OPENAI_API_KEY` | Key for the chat model | `sk-proj-...` |
| `OPENAI_MODEL` | Model name | `gpt-4o-mini` |
| `CONVEX_BASE_URL` | Travel provider the MCP servers call | `https://standing-fish-574.convex.site` |
| `HOTEL_MCP_URL` | Where the backend reaches the hotel MCP server | `http://127.0.0.1:8001/mcp` |
| `FLIGHT_MCP_URL` | Where the backend reaches the flight MCP server | `http://127.0.0.1:8002/mcp` |
| `BACKEND_URL` | Frontend only. Base URL of the backend | `http://127.0.0.1:8000` |

## Running it locally

Install the dependencies:

```
python -m venv tripweaver
tripweaver\Scripts\pip install -r requirements.txt
tripweaver\Scripts\pip install -r frontend\requirements.txt
```

Then start four processes, each in its own terminal:

```
python -m mcp_servers.hotel_server
python -m mcp_servers.flight_server
python -m uvicorn main:app --port 8000
python frontend\app.py
```

The chat interface opens on http://127.0.0.1:7860 and talks to the backend on
port 8000.

## MCP server guide

Two MCP servers run as their own processes and speak streamable HTTP. Each one
exposes its capabilities as MCP tools, and the tool docstrings are what the
model reads when it decides which tool to call.

| Server | Port | Tools |
|---|---|---|
| `mcp_servers/hotel_server.py` | 8001 | `list_hotels`, `search_hotels`, `book_hotel` |
| `mcp_servers/flight_server.py` | 8002 | `list_flights`, `search_flights`, `book_flight` |

Every tool answers with the same envelope, so the agent can always tell the
difference between a service that failed and a search that found nothing:

```
{"ok": true,  "hotels": [...]}
{"ok": true,  "booking": {"bookingReference": "HT35961762", "status": "confirmed"}}
{"ok": false, "error": "The travel service did not respond in time."}
```

Errors from the provider are rewritten before they leave the MCP server, so an
internal validation message never reaches the traveller.

To check a server by hand while it is running:

```
curl http://127.0.0.1:8001/mcp
```

### Swapping the travel provider

`mcp_servers/convex_client.py` is the only file that knows which provider is in
use. Point it somewhere else, or rewrite the six functions in it, and the
agents keep working unchanged. After such a change `git diff --stat agents/`
stays empty, which is the point of putting MCP between the two.

Adding a new capability is the same story. Add a function to a server, decorate
it with `@mcp.tool()`, give it a docstring, and the agent picks it up the next
time the backend starts. No node, edge, or prompt has to change.

## Deploying

Both services are described in `render.yaml`, so Render creates them together
from one blueprint rather than being configured by hand.

1. Sign in to Render and connect this GitHub repository. No card is needed for
   the free plan.
2. Go to Blueprints and create a new blueprint instance from this repository.
   Render reads `render.yaml` and offers both services.
3. Supply `OPENAI_API_KEY` when prompted. The model name and the travel
   provider URL are already in the blueprint.
4. Apply. The backend builds from the Dockerfile, the frontend installs from
   `frontend/requirements.txt`.
5. Once the backend is live, copy its address into the frontend's `BACKEND_URL`
   variable and redeploy the frontend.

Step five is manual because a service address is only known after its first
deploy, and Render's own service reference resolves to an internal name that
the public internet cannot reach.

The backend container runs the two MCP servers alongside the API on loopback
ports, so they are reachable by the agents and never exposed publicly.

Check the backend with `curl https://<your-backend>.onrender.com/health`, which
answers `{"status": "ok"}`.

## User guide

Ask for what you want in plain language. Some examples:

- `What is the best season to visit Japan?` goes to the general agent.
- `Show me hotels in Tokyo` returns a numbered list of real availability.
- `Find flights from NRT to ICN` returns matching flights.
- `Book the second one for Riflan Mohamed, riflan@example.com, double room, 2026-11-02 to 2026-11-05`
  books by position from the list you were just shown.
- `Book a hotel in Tokyo` makes the agent ask for the details it still needs
  instead of guessing them.

While the assistant works, a panel appears for each stage and settles once that
stage finishes:

| Panel | Meaning |
|---|---|
| Understanding your request | The graph is deciding which specialist to use |
| Searching hotel suggestions | A search tool is running |
| Booking hotel | A booking tool is running |
| Asking for a missing detail | The agent needs something before it can act |

If a travel service is unavailable the assistant says so plainly and the other
specialist keeps working.
