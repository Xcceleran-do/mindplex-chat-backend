<script lang="ts">
	import { Button } from "$lib/components/ui/button/index.js";
	import * as Card from "$lib/components/ui/card/index.js";
	import type { Room } from "$lib/types";

	let { username, room }: { username: string, room: Room } = $props();

</script>
 
<Card.Root class="w-[90%] border-none bg-muted mb-5 ml-5">
	<Card.Header>
		<Card.Title>Room {room.id}</Card.Title>
		<Card.Description>Created at {room.created}</Card.Description>
	</Card.Header>
	<Card.Footer class="flex justify-between mt-3">
		<a href="{username}/{room.id}">
			<Button variant="outline" class="bg-primary hover:bg-primary hover:opacity-50">Enter Room</Button>
		</a>
	</Card.Footer>
</Card.Root>
