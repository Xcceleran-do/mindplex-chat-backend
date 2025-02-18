# A Backend Chat Service For the Mindplex Project

## Features

- Basic messaging capabilities
- Private chat
- Temporary universal group chat
- Message encryption
- User authoriaztion

## Usage

### Install

```
git clone https://github.com/arist76/telegram-chat-backend.git
cd telegram-chat-backend
pip install -r requirements.txt
fastapi run --host 0.0.0.0 --port 8000
```

### Create Rooms

Rooms are created by sending a POST request to `/rooms` with the room type. A room 
type can be private or universal. private rooms can only have one participant and
one owner and universal rooms don't need participants as they can be accessed by
anyone.


### Websocket

For live messaging you can use a websocket connection to `/ws/rooms/<room_id>/`.
you can send and expect to receive websocket connections using these types.

#### Message

A type for sending messages

```json
{
    "type": "text",
    "message": "Hello",
}
```

#### Response

Expect responses in this format 

```json
{
    "success": true,
    "error": null,
    "message": {
        "type": "text",
        "message": "Hello"
    }
}
```


## API Reference

see `/docs` for detailed swagger docs.
