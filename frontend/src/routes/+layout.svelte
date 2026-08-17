<script lang="ts">
	import '../app.css';
	import { page } from '$app/state';
	import Header from '$lib/components/Header.svelte';

	let currentPath = page.url.pathname

	const { children } = $props();
</script>

<div class="grid min-h-screen grid-rows-[auto_1fr]">
	{#if currentPath !== "/"}
		<header class="bg-header-color flex justify-between px-4 pt-2 py-3 text-center shadow-xl md:px-8"> <a class="flex w-8 aspect-square items-center gap-2" href="/">
				<img src="/logo.svg" alt="HushMap's logo" />
				<h1 class="text-3xl font-bold text-white">HushMap</h1>
			</a>
		</header>
	{:else}
		<Header />
	{/if}

	{@render children()}
</div>
