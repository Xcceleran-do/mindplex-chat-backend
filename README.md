# Mindplex Chat Backend

This is the backend for the Mindplex Chat application. It provides a RESTful API for managing chat rooms and users, as well as a WebSocket interface for real-time communication.

## Features

- Private and group chat rooms
- User authentication and authorization
- Message encryption
- Real-time messaging with WebSockets
- Kafka integration for message queuing
- Celery for background tasks

## Getting Started

### Prerequisites

- Docker
- Docker Compose
- Python 3.9+
- pip

### Installation

1.  Clone the repository:

    ```bash
    git clone https://github.com/arist76/telegram-chat-backend.git
    ```

2.  Navigate to the project directory:

    ```bash
    cd telegram-chat-backend
    ```

3.  Create a `.env` file from the `.env.example` file and update it with your environment variables.

4.  Build and run the application with Docker Compose:

    ```bash
    docker-compose up -d
    ```

The application will be available at `http://localhost:9010`.

### Running the Tests

To run the tests, you can use the following command:

```bash
docker-compose exec web pytest
```

## API Reference

The API is documented with Swagger UI. You can access it at `http://localhost:9010/docs`.

### Authentication

Authentication is handled via JWT. You need to provide a valid JWT in the `Authorization` header and the username in the `X-Username` header. You can get the Authorization token from the mindplex servers.

### WebSockets

The WebSocket interface is available at `/ws/rooms/{room_id}/`. You can send and receive messages in the following format:

**Send:**

```json
{
    "type": "text",
    "message": "Hello, world!"
}
```

**Receive:**

```json
{
    "success": true,
    "error": null,
    "message": {
        "type": "text",
        "message": "Hello, world!"
    }
}
```

### Server-Sent Events (SSE)

**Note:** The SSE feature is currently under construction.
