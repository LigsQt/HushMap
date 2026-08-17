<script>
	import { is3d } from '$lib/state.svelte';
</script>

<label class="inline-flex cursor-pointer items-center">
	<input type="checkbox" bind:checked={is3d.state} value="" class="peer sr-only" />
	<div
		class="peer relative h-6 w-11 rounded-full bg-gray-200 peer-checked:bg-blue-600 peer-focus:ring-4 peer-focus:ring-blue-300 peer-focus:outline-none after:absolute after:start-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:border after:border-gray-300 after:bg-white after:transition-all after:content-[''] peer-checked:after:translate-x-full peer-checked:after:border-white rtl:peer-checked:after:-translate-x-full dark:border-gray-600 dark:bg-gray-700 dark:peer-checked:bg-blue-600 dark:peer-focus:ring-blue-800"
	></div>
	<span class="ms-3 text-sm font-medium text-white">3D Map</span>
</label>
