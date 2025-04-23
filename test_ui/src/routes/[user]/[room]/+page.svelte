<script lang="ts">
	// get test users from server
	import type { Message } from '$lib/types';

	import type { PageProps } from './$types';
	import {  BACKEND_HOST  } from '$lib/api';
	import { browser } from '$app/environment';

	let { data }: PageProps = $props();

	let ws: WebSocket | undefined = undefined;
	let messages = $state(data.currentRoomMessages);
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
			let data = JSON.parse(JSON.parse(event.data));
			let msg = data?.message

			if (!msg) {
				console.error("Message is not recognized")
			} else if (msg.type === "text") {
				messages.push(msg.message)
			} else if (msg.type === "connected") {
				console.log("Websockket connection confirmed")
			} else if (msg.type === "sent_confirmation") {
				messages.push(msg.message)
			} else {
				console.error("Unknown message type:", msg)
			}
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
			} else {
				console.log("WebSocket not connected")
			}
		}
	}

</script>

<div>
	<a href="/{data.username}">&lt back</a>
	<h2>WebSocket Chat Test</h2>
	<div>
		{#each messages as message}
			<div>{JSON.stringify(message)}</div>
			<p>by: {message?.owner_id}</p>
			<p>{message?.text}</p>
			<p>{message?.created}</p>
			<span>-----------------</span>
		{/each}

	</div>
	<input type="text" id="messageInput" placeholder="Type a message..." bind:value={inp}>
	<button id="sendButton" onclick={sendMessage}>Send</button>
</div>

<style>
	#messages { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: scroll; }
</style>
