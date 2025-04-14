
<script lang="ts">
	let { data } = $props();

</script>

<h2>Please select a user</h2>
<ol>
	{#each data.allUsers as user }
		<li>
			- <a href="/{user}">{user}</a>
		</li>
	{/each}
</ol>
