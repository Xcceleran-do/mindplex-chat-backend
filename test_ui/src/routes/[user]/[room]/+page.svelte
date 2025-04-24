<script lang="ts">
	import * as Avatar from "$lib/components/ui/avatar/index.js";
	import * as Card from "$lib/components/ui/card/index.js"; 
	import * as Command from "$lib/components/ui/command/index.js";
	import * as Dialog from "$lib/components/ui/dialog/index.js";
	import * as Tooltip from "$lib/components/ui/tooltip/index.js";
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

	function cn(...inputs: ClassValue[]) {
		return twMerge(clsx(inputs));
	}


	const users = [
		{
			name: "Olivia Martin",
			email: "m@example.com",
		},
		{
			name: "Isabella Nguyen",
			email: "isabella.nguyen@email.com",
		},
		{
			name: "Emma Wilson",
			email: "emma@example.com",
		},
		{
			name: "Jackson Lee",
			email: "lee@example.com",
		},
		{
			name: "William Kim",
			email: "will@email.com",
		},
	] as const;

	type User = (typeof users)[number];

	let open = $state(false);
	let selectedUsers: User[] = $state([]);

	let messages = $state(data.currentRoomMessages);

	let input = $state("");
</script>

<a href="/{data.username}" class="absolute top-10 left-10">
	<CircleArrowLeft />
</a>


<div class="w-full flex items-center justify-center">
	<div class="w-full px-[400px] pt-20">
		<Card.Root class="w-full min-h-screen relative border-none rounded-none flex flex-col justify-between">
			<div>
				<Card.Header class="flex flex-row items-center mb-5">
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
				<Card.Content>
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
			</div>
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
		<Dialog.Root bind:open>
			<Dialog.Content class="gap-0 p-0 outline-none">
				<Dialog.Header class="px-4 pb-4 pt-5">
					<Dialog.Title>New message</Dialog.Title>
					<Dialog.Description>
						Invite a user to this thread. This will create a new group message.
					</Dialog.Description>
				</Dialog.Header>
				<Command.Root class="overflow-hidden rounded-t-none border-t bg-transparent">
					<Command.Input placeholder="Search user..." />
					<Command.List>
						<Command.Empty>No users found.</Command.Empty>
						<Command.Group class="p-2">
							{#each users as user}
								<Command.Item
									class="flex items-center px-2"
									onSelect={() => {
										if (selectedUsers.includes(user)) {
											selectedUsers = selectedUsers.filter(
												(selectedUser) => selectedUser !== user
											);
										} else {
											selectedUsers = [...users].filter((u) =>
												[...selectedUsers, user].includes(u)
											);
										}
									}}
								>
									<Avatar.Root>
										<Avatar.Fallback>{user.name[0]}</Avatar.Fallback>
									</Avatar.Root>
									<div class="ml-2">
										<p class="text-sm font-medium leading-none">
											{user.name}
										</p>
										<p class="text-muted-foreground text-sm">
											{user.email}
										</p>
									</div>
									{#if selectedUsers.includes(user)}
										<!--
<Check class="text-primary ml-auto flex h-5 w-5" />
-->
										<p>placholder...</p>
									{/if}
								</Command.Item>
							{/each}
						</Command.Group>
					</Command.List>
				</Command.Root>
				<Dialog.Footer class="flex items-center border-t p-4 sm:justify-between">
					{#if selectedUsers.length}
						<div class="flex -space-x-2 overflow-hidden">
							{#each selectedUsers as user}
								<Avatar.Root class="border-background inline-block border-2">
									<Avatar.Fallback>{user.name[0]}</Avatar.Fallback>
								</Avatar.Root>
							{/each}
						</div>
					{:else}
						<p class="text-muted-foreground text-sm">Select users to add to this thread.</p>
					{/if}
					<Button disabled={selectedUsers.length < 2} onclick={() => (open = false)}>
						Continue
					</Button>
				</Dialog.Footer>
			</Dialog.Content>
		</Dialog.Root>
	</div>
</div>
