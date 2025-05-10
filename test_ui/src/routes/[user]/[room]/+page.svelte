<script lang="ts">
	import * as Avatar from "$lib/components/ui/avatar/index.js";
	import * as Card from "$lib/components/ui/card/index.js"; 
	import { Button } from "@/components/ui/button";
	import { Input } from "@/components/ui/input";
	import Send from "@lucide/svelte/icons/send";
	import CircleArrowLeft from "@lucide/svelte/icons/circle-arrow-left";
	import { browser } from "$app/environment";
	import { twMerge } from "tailwind-merge";
	import { clsx } from "clsx";
	import type { ClassValue } from "clsx";
	import {  BACKEND_HOST  } from '$lib/api';

	let { data } = $props();

	let ws: WebSocket | undefined = undefined;

	let useSse = true;
	
	if (useSse) {
		if (browser) {
			console.log("Using SSE");
			let eventSource = new EventSource(
				`http://localhost:9010/sse/${data.currentRoom.id}?token=${data.token}&username=${data.username}`,
			)

			eventSource.onmessage = (event) => {
				console.log("New message!!!")
				console.log(event.data)
			}
			console.log("is connected: ", eventSource.readyState === EventSource.OPEN);
		}

	} else {
		if (browser) {
			ws = new WebSocket(
				`ws://localhost:9010/ws/rooms/${data.currentRoom.id}?token=${data.token}&username=${data.username}`
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
	}


	function cn(...inputs: ClassValue[]) {
		return twMerge(clsx(inputs));
	}

	let messages = $state(data.currentRoomMessages);

	let input = $state("");
</script>

<a href="/{data.username}" class="absolute top-10 left-10">
	<CircleArrowLeft />
</a>

<div class="w-full flex items-center justify-center">
	<div class="w-full px-[250px] h-screen overflow-hidden -mt-[80px] pt-[80px]">
		<Card.Root class="w-full h-full relative rounded-none flex flex-col justify-between border-y-0 border-x-2 border-x-muted px-32">
			<Card.Header class="flex flex-row items-center my-5 h-[5vh]">
				<div class="flex items-center space-x-4">
					<Avatar.Root>
						<Avatar.Fallback>
							{data.username.charAt(0).toUpperCase()}{data.username.charAt(1).toUpperCase()}
						</Avatar.Fallback>
					</Avatar.Root>
					<div>
						<p class="text-sm font-medium leading-none">Chat with 
							{#each data.currentRoomParticipants as participant}
								{participant.remote_id}, 
							{/each}
						</p>
						<p class="text-muted-foreground text-sm">Room id: {data.currentRoom.id}</p>
					</div>
				</div>
			</Card.Header>
			<Card.Content class="w-full overflow-scroll">
				<div class="space-y-4 px-10">
					{#each messages as message}
						<div
							class={cn(
								"flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
								message.owner_id === data.user.id
									? "bg-primary text-primary-foreground ml-auto"
									: "bg-muted"
							)}
						>
							{message.text}
						</div>
					{/each}
				</div>
			</Card.Content>
			<Card.Footer class="w-full">
				<form
					onsubmit={(event) => {
						event.preventDefault();
						if (input.length === 0) return;
						let msg = {
							type: "text",
							message: input,
							sender: null
						}
						if (ws !== undefined) {
							ws.send(JSON.stringify(msg));
						} else {
							console.log("WebSocket not connected")
						}
						input = "";
					}}
					class="flex w-full items-center space-x-2"
				>
					<Input
						id="message"
						placeholder="Type your message..."
						class="flex-1 h-14"
						autocomplete="off"
						bind:value={input}
					/>
					<Button type="submit" size="icon" disabled={input.length === 0}>
						<Send  class="h-4 w-4" />
						<span class="sr-only">Send</span>
					</Button>
				</form>
			</Card.Footer>
		</Card.Root>
	</div>
</div>
