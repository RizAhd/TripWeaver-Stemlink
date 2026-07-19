import json
import os
from typing import AsyncIterator, Dict, List

import gradio as gr
import httpx

import cards
from theme import HEAD, TripWeaverTheme

def backend_url() -> str:
    url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


BACKEND_URL = backend_url()
STREAM_URL = BACKEND_URL + "/chat/stream"

REQUEST_TIMEOUT = httpx.Timeout(180.0, connect=90.0)

EMPTY_RESULTS = {"hotel_results": [], "flight_results": [], "bookings": []}

CSS = """
.gradio-container {max-width: 980px !important; width: 100% !important; margin-left: auto !important; margin-right: auto !important;}

#tripweaver-header {padding: 22px 4px 10px 4px; border-bottom: 1px solid #e2ded4;}
#tripweaver-header h1 {
  font-family: 'Fraunces', Georgia, serif;
  font-weight: 600;
  font-size: 2.1rem;
  letter-spacing: -0.015em;
  margin: 0 0 4px 0;
  color: #12212e;
}
#tripweaver-header p {margin: 0; color: #5b6b7a; font-size: 0.95rem;}

#tripweaver-chat {border: none; background: transparent;}

.tw-empty {max-width: 420px; margin: 0 auto; text-align: center; padding: 8px 16px;}
.tw-empty-mark {
  width: 46px; height: 46px; margin: 0 auto 16px auto;
  border-radius: 13px; background: #0e7c86; color: #f6f3ec;
  font-family: 'Fraunces', Georgia, serif; font-weight: 600;
  font-size: 1.05rem; line-height: 46px; letter-spacing: 0.02em;
}
.tw-empty h2 {
  font-family: 'Fraunces', Georgia, serif; font-weight: 600;
  font-size: 1.35rem; color: #12212e; margin: 0 0 8px 0;
}
.tw-empty p {color: #5b6b7a; font-size: 0.93rem; line-height: 1.55; margin: 0;}

.gradio-container .dataset {border: none !important; background: transparent !important; padding: 0 !important;}
.gradio-container .dataset button,
.gradio-container .dataset .gallery-item {
  border: 1px solid #e2ded4 !important;
  background: #ffffff !important;
  border-radius: 999px !important;
  padding: 7px 15px !important;
  font-size: 0.86rem !important;
  color: #12212e !important;
  box-shadow: none !important;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.gradio-container .dataset button:hover,
.gradio-container .dataset .gallery-item:hover {
  border-color: #0e7c86 !important;
  background: #f6f3ec !important;
}

@media (max-width: 640px) {
  .gradio-container {padding: 0 10px !important;}
  #tripweaver-header {padding-top: 14px;}
  #tripweaver-header h1 {font-size: 1.55rem;}
  #tripweaver-header p {font-size: 0.88rem;}
  .tw-empty h2 {font-size: 1.15rem;}
}
"""


def plain_history(history: List[dict]) -> List[Dict[str, str]]:
    turns = []
    for message in history or []:
        if not isinstance(message, dict):
            continue
        if (message.get("metadata") or {}).get("title"):
            continue
        role = message.get("role")
        content = message.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content:
            turns.append({"role": role, "content": content})
    return turns


async def stream_events(message: str, history: List[dict], results: dict) -> AsyncIterator[dict]:
    payload = {
        "message": message,
        "history": plain_history(history),
        "hotel_results": results.get("hotel_results", []),
        "flight_results": results.get("flight_results", []),
        "bookings": results.get("bookings", []),
    }

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        async with client.stream("POST", STREAM_URL, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    yield json.loads(line[6:])


def panel(label: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "metadata": {"title": label, "status": "pending"},
    }


def settle(panels: List[dict]) -> None:
    for item in panels:
        item["metadata"]["status"] = "done"


def rendered(panels: List[dict], reply: str) -> List[dict]:
    if reply:
        return panels + [{"role": "assistant", "content": reply}]
    return list(panels)


async def respond(message: str, history: List[dict], results: dict):
    results = results or dict(EMPTY_RESULTS)
    panels: List[dict] = []
    reply = ""

    try:
        async for event in stream_events(message, history, results):
            kind = event.get("type")

            if kind == "activity":
                settle(panels)
                panels.append(panel(event.get("label", event.get("state", "Working..."))))

            elif kind == "tool":
                if panels:
                    panels[-1]["metadata"]["log"] = "%s %s" % (
                        event.get("name", "tool"),
                        event.get("status", "").lower(),
                    )

            elif kind == "token":
                reply += event.get("text", "")

            elif kind == "results":
                results = {
                    "hotel_results": event.get("hotel_results", []),
                    "flight_results": event.get("flight_results", []),
                    "bookings": event.get("bookings", []),
                }

            elif kind == "error":
                reply = event.get("message", "Something went wrong. Please try again.")

            yield rendered(panels, reply), results, cards.render(results)

    except httpx.HTTPStatusError as exc:
        settle(panels)
        if exc.response.status_code == 404:
            message = (
                "The travel planner is not answering at %s. Check that BACKEND_URL "
                "points at the deployed backend." % BACKEND_URL
            )
        else:
            message = "The travel planner returned an error (%s). Please try again." % exc.response.status_code
        yield rendered(panels, message), results, cards.render(results)
        return
    except httpx.RequestError:
        settle(panels)
        yield rendered(panels, "I cannot reach the travel planner right now. Please try again shortly."), results, cards.render(results)
        return

    settle(panels)
    if not reply:
        reply = "I did not get a reply from the travel planner. Please try again."
    yield rendered(panels, reply), results, cards.render(results)


EMPTY_STATE = """
<div class="tw-empty">
  <div class="tw-empty-mark">TW</div>
  <h2>Where are you going?</h2>
  <p>Ask for hotels in a city or flights between two airports, and I will
  search live availability and book on your behalf.</p>
</div>
"""

STARTERS = [
    ["Show me hotels in Tokyo", None],
    ["Find flights from NRT to ICN", None],
    ["Book the first one for me", None],
    ["What is the best season to visit Japan?", None],
]


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="TripWeaver") as demo:
        gr.Markdown(
            "# TripWeaver\nPlan flights and hotels in one conversation.",
            elem_id="tripweaver-header",
        )

        results_state = gr.State(dict(EMPTY_RESULTS))

        chatbot = gr.Chatbot(
            height="60vh",
            show_label=False,
            placeholder=EMPTY_STATE,
            layout="panel",
            buttons=["copy"],
            avatar_images=(None, "assets/mark.svg"),
            elem_id="tripweaver-chat",
        )

        results_panel = gr.HTML(
            value="",
            css_template=cards.CARD_CSS,
            apply_default_css=False,
            elem_id="tripweaver-results",
        )

        gr.ChatInterface(
            fn=respond,
            chatbot=chatbot,
            additional_inputs=[results_state],
            additional_outputs=[results_state, results_panel],
            examples=STARTERS,
            api_name="chat",
        )

    return demo


if __name__ == "__main__":
    build_demo().launch(
        theme=TripWeaverTheme(),
        css=CSS,
        head=HEAD,
        footer_links=[],
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
    )
