FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user

ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOTEL_MCP_HOST=127.0.0.1 \
    HOTEL_MCP_PORT=8001 \
    FLIGHT_MCP_HOST=127.0.0.1 \
    FLIGHT_MCP_PORT=8002 \
    HOTEL_MCP_URL=http://127.0.0.1:8001/mcp \
    FLIGHT_MCP_URL=http://127.0.0.1:8002/mcp \
    WEATHER_MCP_HOST=127.0.0.1 \
    WEATHER_MCP_PORT=8003 \
    WEATHER_MCP_URL=http://127.0.0.1:8003/mcp

WORKDIR $HOME/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .

EXPOSE 7860

CMD ["bash", "start.sh"]
