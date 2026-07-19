# TripWeaver chat

Traveller facing chat interface for TripWeaver. It streams replies from the
TripWeaver backend and shows what each agent is doing while it works.

This folder is deployed as its own Render service, defined in `render.yaml` at
the repository root. It reads one variable:

- `BACKEND_URL` the base address of the deployed TripWeaver backend

The backend holds the agents and the MCP servers. This service has no travel
logic of its own.
