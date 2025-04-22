<script lang="ts">
	// get test users from server

	import type { PageProps } from './$types';
	import {  BACKEND_HOST  } from '$lib/api';
	import { browser } from '$app/environment';

	let { data }: PageProps = $props();

	let ws: WebSocket | undefined = undefined;
	let messages: HTMLPreElement
	let inp: string = $state("")

	if (browser) {
		ws = new WebSocket(
			`ws://${BACKEND_HOST}/ws/rooms/${data.currentRoom.id}?token=${data.token}&username=${data.username}`
		);

		ws.onopen = () => {
			console.log("Connected to WebSocket server");
		};

		ws.onerror = (e) => {
			console.log(e)
		};

		ws.onmessage = (event) => {
			const messagesDiv = document.getElementById("messages");
			const message = document.createElement("p");
			console.log("Received: ", event.data)
			message.textContent = "Received: " + JSON.stringify(event.data);
			messagesDiv?.appendChild(message);
		};

		ws.onerror = (error) => {
			console.error("WebSocket error:", error);
		};

		ws.onclose = () => {
			console.log("WebSocket connection closed");
		};

	}


	function sendMessage() {
		let value = inp;
		if (value?.trim() !== "") {
			let msg = {
				type: "text",
				message: value,
				sender: null
			}
			if (ws !== undefined) {
				ws.send(JSON.stringify(msg));
				console.log("Sent: ", value)
			} else {
				console.log("WebSocket not connected")
			}
		}
	}

</script>

<div>
	<a href="/{data.username}">&lt back</a>
	<h2>WebSocket Chat Test</h2>
	<pre id="messages" bind:this={messages}></pre>
	<input type="text" id="messageInput" placeholder="Type a message..." bind:value={inp}>
	<button id="sendButton" onclick={sendMessage}>Send</button>
</div>

<style>
	#messages { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: scroll; }
</style>
