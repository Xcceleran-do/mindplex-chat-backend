<script lang="ts">
	import { getOrCreatePrivateRoom, getUserByUsername } from '$lib/api';
	let { data } = $props();
</script>

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















