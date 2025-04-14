<script>
	let { data } = $props();

</script>

<h2>Hello { data.user.username }</h2>
<h2>Chat with:</h2>

{#each data.allUsers as user}
	{#if user != data.user.username}
		<ol>
			<li>
				- <a href="/{data.user.username}/{user}/">{user}</a>
			</li>
		</ol>
	{/if}
{/each}
