# Suggested Commands

## Setup & Dependencies
- `uv python install 3.12`
- `uv venv --python 3.12`
- `source .venv/bin/activate`
- `uv sync`

## Running the Application
- **Default run**: `uv run main.py`
- **Server**: `uv run server.py` or `make serve`

## Testing & Quality
- **Test**: `make test` or `pytest`
- **Lint**: `make lint`
- **Format**: `make format`

## API Usage
- **Endpoint**: `POST /api/chat/stream`
- **Port**: Default 8000
