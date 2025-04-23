<script lang="ts">
	let { data } = $props();
	import { Separator } from "$lib/components/ui/separator/index.js";
	import { Input } from "$lib/components/ui/input/index.js";
	import { Label } from "$lib/components/ui/label/index.js";
	import RoomListMember from "@/components/roomListMember.svelte";
</script>

<div class="w-full h-full flex items-center justify-center flex-col">
	<div class="min-w-[70%]">
		<div class="flex w-full justify-between">
			<div class="w-full flex items-center justify-start">
				<div class="grid w-full max-w-sm items-center gap-1.5">
					<Label for="email">Who do you want to chat with?</Label>
					<Input type="text" placeholder="Username" />
				</div>
			</div>
			<div>
				b
			</div>
		</div>
		<Separator />
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


<!--
-->

<a href="/">&lt back</a>
<h2>Hello { data.username }</h2>
<h2>Create Room</h2>

<div>
	<h2>Create A Private Room</h2>
	<span>Username: </span>
	<form method="POST" action="?/createRoom" >
		<input name="username" type="text" hidden={true} bind:value={data.username}>
		<input name="token" type="text" hidden={true} bind:value={data.token}>
		<input name="roomType" type="text" placeholder="Room Type" hidden={true} value="private">
		<input name="remoteUser" type="text" placeholder="User">
		<button type="submit">Create</button>
	</form>
</div>
<br>
<br>
<div>
	<h2>Create A Universal Room</h2>
	<form method="POST" action="?/createRoom">
		<input name="username" type="text" hidden={true} bind:value={data.username}>
		<input name="token" type="text" hidden={true} bind:value={data.token}>
		<input name="roomType" type="text" placeholder="Room Type" hidden={true} value="universal">
		<button type="submit">Create</button>
	</form>
</div>
<br>
<br>
<div class="flex w-1/2 justify-between"> 
	<div>
		<h3 class="text-xl">Private Rooms</h3>
		<div>
			{#each data.rooms.private as room }
				- <a href="/{data.username}/{room.id}">{room.id}</a> <br>
			{/each}
		</div>
	</div>
	<div>
		<h3 class="text-xl">Universal Rooms</h3>
		<div>
			{#each data.rooms.universal as room }
				- <a href="/{data.username}/{room.id}">{room.id}</a>
			{/each}
		</div>
	</div>
</div>















