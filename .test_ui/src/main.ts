const BACKEND_HOST = "localhost:8000"
const AUTH_BACKEND_HOST = "stagingauth.mindplex.ai"

const room_id = "be2f584262fd83ba"

const test_users = [
	{ username: "dave", password: "dave" },
	{ username: "tony", password: "tony" },
	{ username: "ivan", password: "ivan" },
]


async function auth_user(count = 1) {
	let user = test_users[count - 1]

	if (user === undefined) {
		throw new Error("No test user found")
	}

	let res = await fetch(`https://${AUTH_BACKEND_HOST}/realms/Mindplex/protocol/openid-connect/token`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			username: user.username,
			password: user.password,
			client_id: "mindplex",
			grant_type: "password",
			client_secret: "Dzkhw0zTnV6wgQ59Lsnqm5JaG4CreCAf",
			scope: "openid"
		})
	})

	let j = await res.json()
	let token = j.access_token

	return token as string
}

async function user_id() {
	let qp = new URLSearchParams(window.location.search)

	let user_id = qp.get("user_id")

	if (user_id) {
		return Number(user_id)
	} else {
		throw new Error("No user_id provided")
	}
}

const ws = new WebSocket(`ws://${BACKEND_HOST}/ws/rooms/${room_id}?token=${await auth_user(await user_id())}`); // Change to your WebSocket URL

ws.onopen = () => {
	console.log("Connected to WebSocket server");
};

ws.onerror = (e) => {
	console.log(e)
}

ws.onmessage = (event) => {
	const messagesDiv = document.getElementById("messages");
	const message = document.createElement("p");
	message.textContent = "Received: " + event.data;
	messagesDiv?.appendChild(message);
};

ws.onerror = (error) => {
	console.error("WebSocket error:", error);
};

ws.onclose = () => {
	console.log("WebSocket connection closed");
};

function sendMessage() {
	const input: HTMLInputElement | null = document.getElementById("messageInput");
	const message = input?.value;
	if (message?.trim() !== "") {
		ws.send(message as string);
		const messagesDiv = document.getElementById("messages");
		const sentMessage = document.createElement("p");
		sentMessage.textContent = "Sent: " + message;
		messagesDiv?.appendChild(sentMessage);
		(input as HTMLInputElement).value = "";
	}
}

const sendButton = document.getElementById("sendButton");
sendButton?.addEventListener("click", sendMessage);
