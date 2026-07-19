---
title: TripWeaver
emoji: 🧳
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.20.0
app_file: app.py
python_version: "3.12"
pinned: false
---

# TripWeaver chat

Traveller facing chat interface for TripWeaver. It streams replies from the
TripWeaver backend and shows what each agent is doing while it works.

Set one secret on this Space:

- `BACKEND_URL` - the base URL of the deployed TripWeaver backend Space, for
  example `https://your-name-tripweaver-backend.hf.space`

The backend exposes the agents and the MCP servers. This Space holds no travel
logic of its own.
