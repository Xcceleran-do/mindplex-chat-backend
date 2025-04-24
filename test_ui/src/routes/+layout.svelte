<script lang="ts">
	import '../app.css';
	let { children } = $props();
	import { ModeWatcher } from "mode-watcher";
	import Sun from "@lucide/svelte/icons/sun";
	import Moon from "@lucide/svelte/icons/moon";
	import { Button } from "$lib/components/ui/button/index.js";
	import { toggleMode } from "mode-watcher";
</script>

<div class="bg-background">
	<div class="w-screen h-[80px] flex items-center justify-between border-b-[1px] border-b-muted mb-10 px-40">
		<a href="/">
			<h4 class="scroll-m-20 text-xl font-semibold tracking-tight">Chat App</h4>
		</a>

		<Button onclick={toggleMode} variant="outline" size="icon" class="">
			<Sun
				class="h-[1.2rem] w-[1.2rem] rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0"
			/>
			<Moon
				class="absolute h-[1.2rem] w-[1.2rem] rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100"
			/>
			<span class="sr-only">Toggle theme</span>
		</Button>
	</div>
	<div class="w-screen min-h-screen">
		<ModeWatcher />
		{@render children()}
	</div>
</div>

