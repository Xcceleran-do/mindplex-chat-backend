<h2>WebSocket Chat Test</h2>
<div id="messages" bind:this={messages}></div>
<input type="text" id="messageInput" placeholder="Type a message..." bind:this={inp}>
<button id="sendButton" onclick={sendMessage}>Send</button>
<button onclick={create_socket}>Connect</button>

<script lang="ts">
	// get test users from server

	import type { PageProps } from './$types';
	import { browser } from '$app/environment';

	let { data }: PageProps = $props();

	let user = data.user;

	

	const BACKEND_HOST = "localhost"

	const room_id = "87e6efa27a10c41b"

	let messages: HTMLDivElement

	let inp: HTMLInputElement


	function create_socket() {
		
		if (browser) {

			const ws = new WebSocket(`ws://${BACKEND_HOST}/ws/rooms/${room_id}?token=${user.token}&username=dave`); // Change to your WebSocket URL

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

			return ws
		}

	}

	const ws: WebSocket =  create_socket()

	function sendMessage() {
		const value = (inp as HTMLInputElement).value
		console.log(value)
		if (value?.trim() !== "") {
			let msg = {
				type: "text",
				message: value,
				sender: null
			}
			console.log("Ws: ", ws)
			ws.send(JSON.stringify(msg));
			const sentMessage = document.createElement("p");
			sentMessage.textContent = "Sent: " + value;
			messages?.appendChild(sentMessage);
			(inp as HTMLInputElement).value = "";
		}
	}
	
</script>

<style>
	#messages { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: scroll; }
</style>
