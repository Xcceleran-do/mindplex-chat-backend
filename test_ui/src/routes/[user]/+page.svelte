<script lang="ts">
	let { data } = $props();
	import { Separator } from "$lib/components/ui/separator/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import Button from "@/components/ui/button/button.svelte";
	import RoomListMember from "@/components/roomListMember.svelte";
</script>


<div class="w-full flex items-center justify-center flex-col relative">
	<!--
	<a href="/" class="absolute top-2 left-[300px]">
		<CircleArrowLeft />
	</a>
	-->
	<div class="min-w-[70%] flex items-center justify-center flex-col mt-32 mb-32">
		<div class="justify-center items-center">
			<div class="flex flex-col h-[80%] rounded-xl border-b-1 border-b-muted py-20 border-[1px] border-muted w-[500px]">
				<form method="POST" action="?/createRoom" class="flex items-center justify-center" >
					<div class="grid w-full max-w-sm items-center gap-1.5">
						<input name="username" type="text" hidden={true} bind:value={data.username}>
						<input name="token" type="text" hidden={true} bind:value={data.token}>
						<input name="roomType" type="text" placeholder="Room Type" hidden={true} value="private">
						<Label for="email" class="font-bold mb-5">Create private room</Label>
						<Input name="remoteUser" type="text" placeholder="Username" class="h-12 w-full mb-3"/>
						<Button type="submit" variant="outline" class="bg-primary hover:bg-primary hover:opacity-50">Create Room</Button>
					</div>
				</form>

				<div class="my-10"></div>

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
		</div>

		<h2 class="scroll-m-20 pb-2 text-3xl font-semibold tracking-tight transition-colors first:mt-0 my-20">Existing Rooms</h2>

		<div class="flex w-full justify-between">
			<div class="mt-10 w-1/2">
				{#if data.rooms.private.length === 0}
					<div class="w-full h-[100px] flex items-center justify-center">
						<h3 class="text-xl">No Private Rooms</h3>
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

