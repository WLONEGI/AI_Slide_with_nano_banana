# AI Slide Generator - Frontend

Next.js frontend for the AI Slide Generator Prototype.
Provides a Dual-Pane interface (Chat + Preview) for building presentations.

## Prerequisites

- Node.js v20+
- npm

## Setup

1.  **Install Dependencies**:
    ```bash
    npm install
    ```

## Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Configuration

The frontend reads `NEXT_PUBLIC_API_URL` for backend routing (default: `http://localhost:8000`).

## Key Components

-   **ChatPane**: Left side of the screen. Handles user chat input and displays AI conversation history. Communicates with `/api/style`, `/api/plan`, and `/api/edit-slide`.
-   **PreviewPane**: Right side. Displays a carousel of generated slide images. Handles generation requests (`/api/generate-slide`) for each slide and PDF Export (`/api/assemble`).

## Features

-   **Dual-Pane UI**: Chat and Preview side-by-side.
-   **Live Generation**: Slides are generated asynchronously using Gemini + image generation.
-   **PDF Export**: Combines generated images into a single PDF download.
