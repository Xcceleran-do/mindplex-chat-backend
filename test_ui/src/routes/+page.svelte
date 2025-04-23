
<script lang="ts">
	let { data } = $props();
  import * as Avatar from "$lib/components/ui/avatar/index.js";
</script>

<div class="w-full h-full flex items-center justify-center flex-col">
	<h1 class="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl mb-20">
	Please select a user to login as
	</h1>
	<div class="flex items-center justify-between">
			{#each data.allUsers as user }
				<a href="/{user}" class="w-[250px] flex items-center justify-center flex-col mx-5 rounded-xl bg-primary py-10">
					<Avatar.Root>
						<Avatar.Fallback class="bg-primary-foreground text-primary">{user.charAt(0).toUpperCase()}{user.charAt(1).toUpperCase()}</Avatar.Fallback>
					</Avatar.Root>
					<h3 class="mt-8 scroll-m-20 text-2xl font-semibold tracking-tight">
						{user.toUpperCase()}
					</h3>
				</a>
			{/each}
	</div>

</div>
