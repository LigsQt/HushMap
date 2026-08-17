<script>
	const { color, dbaLevel } = $props();

	let tbColor = $state("");
	if (color === 'quiet-green') tbColor = "text-quiet-green border-quiet-green"
	else if (color === 'loud-orange') tbColor = "text-loud-orange border-loud-orange"
	else if (color === 'very-loud-red') tbColor = "text-very-loud-red border-very-loud-red"
	else tbColor = `text-gray-300 border-gray-300`
</script>

<div
	class="{tbColor} center flex size-10 cursor-pointer flex-col items-center justify-center gap-0 rounded-full border-2 bg-header-color"
>
	{#if color === 'quiet-green'}
		<span class="icon-[solar--volume-small-linear] size-xl"></span>
	{:else if color === 'loud-orange'}
		<span class="icon-[solar--volume-loud-linear]"></span>
	{:else if color === 'very-loud-red'}
		<span class="icon-[solar--volume-loud-bold]"></span>
	{:else}
		<span class="icon-[solar--muted-bold]"></span>
	{/if}

	{#if dbaLevel === 0}
		<p class="text-xs">N/A</p>
	{:else}
		<p class="text-xs">{dbaLevel}</p>
	{/if}

</div>

<style>
	span {
		width: 24px;
		height: 24px;
	}
</style>
