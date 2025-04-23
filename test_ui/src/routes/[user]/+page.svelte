<script lang="ts">
	let { data } = $props();
	import { Separator } from "$lib/components/ui/separator/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import Button from "@/components/ui/button/button.svelte";
	import RoomListMember from "@/components/roomListMember.svelte";
	import CircleArrowLeft from "@lucide/svelte/icons/circle-arrow-left";
</script>

<a href="/" class="absolute top-10 left-10">
	<CircleArrowLeft />
</a>

<div class="w-full flex items-center justify-center flex-col">
	<div class="min-w-[70%] flex items-center justify-center flex-col">
		<div class="flex flex-col w-[70%] h-screen justify-center items-center -mb-52">

			<form method="POST" action="?/createRoom" class="w-full flex items-center justify-center" >
				<div class="grid w-full max-w-sm items-center gap-1.5">
					<input name="username" type="text" hidden={true} bind:value={data.username}>
					<input name="token" type="text" hidden={true} bind:value={data.token}>
					<input name="roomType" type="text" placeholder="Room Type" hidden={true} value="private">
					<Label for="email" class="font-bold mb-5">Create private room</Label>
					<Input name="remoteUser" type="text" placeholder="Username" class="h-12 w-full mb-3"/>
					<Button type="submit" variant="outline" class="bg-primary hover:bg-primary hover:opacity-50">Create Room</Button>
				</div>
			</form>

			<Separator orientation="horizontal" class="my-20"/>

			<form method="POST" action="?/createRoom" class="w-full flex items-end justify-center mt-10">
				<div class="grid w-full max-w-sm items-center gap-1.5">
					<input name="username" type="text" hidden={true} bind:value={data.username}>
					<input name="token" type="text" hidden={true} bind:value={data.token}>
					<input name="roomType" type="text" placeholder="Room Type" hidden={true} value="universal">
					<Label for="email" class="font-bold mb-2">Create universal room</Label>
					<Button type="submit" variant="outline" class="bg-primary hover:bg-primary hover:opacity-50">Create Room</Button>
				</div>
			</form>
		</div>

		<h2 class="scroll-m-20 border-b pb-2 text-3xl font-semibold tracking-tight transition-colors first:mt-0 my-20">Existing Rooms</h2>

		<div class="flex w-full justify-between">
			<div class="mt-10 w-1/2">
				{#if data.rooms.private.length === 0}
					<div class="w-full h-[100px] flex items-center justify-center">
						<h3 class="text-xl">No Universal Rooms</h3>
					</div>
				{:else}
					{#each data.rooms.private as room }
						<RoomListMember username={data.username} room={room}/>
					{/each}
				{/if}
			</div>
			<Separator orientation="vertical" />
			<div class="mt-10 w-1/2">
				{#if data.rooms.universal.length === 0}
					<div class="w-full h-[100px] flex items-center justify-center">
						<h3 class="text-xl">No Universal Rooms</h3>
					</div>
				{:else}
					{#each data.rooms.universal as room }
						<RoomListMember username={data.username} room={room}/>
					{/each}
				{/if}


			</div>
		</div>
	</div>
</div>

