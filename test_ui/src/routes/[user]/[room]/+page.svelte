<script lang="ts">
	// get test users from server

	import type { PageProps } from './$types';
	import { getRooms, sendMessage, createSocket } from '$lib/api';

	let { data }: PageProps = $props();

	let user = $state(data.user);
	//let room = $state(data.remoteUser);
	//let room;
	//if (data.remoteUser) {
	//
	//}

	let messages: HTMLDivElement
	let inp: HTMLInputElement

</script>

<div>
	<h2>WebSocket Chat Test</h2>
	<h2>Hey {user?.username} you are chatting with</h2>
	<div id="messages" bind:this={messages}></div>
	<input type="text" id="messageInput" placeholder="Type a message..." bind:this={inp}>
	<button id="sendButton" onclick={sendMessage}>Send</button>
	<button onclick={createSocket}>Connect</button>
</div>

<style>
	#messages { border: 1px solid #ccc; padding: 10px; height: 200px; overflow-y: scroll; }
</style>
