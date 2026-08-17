<script>
    const { title, value, icon, adtl = "" } = $props()

    let svg = $state("")
    if (icon == "dba") {
        svg = "icon-[solar--soundwave-circle-bold]"
    } else if (icon == "time") {
        svg = "icon-[solar--clock-circle-bold]"
    } else if (icon == "quiet") {
        svg = "icon-[solar--volume-small-bold-duotone]"
    } else if (icon == "loud") {
        svg = "icon-[solar--volume-loud-bold]"
    } else if (icon == "desc") {
        svg = "icon-[solar--notes-bold]"
    }
</script>

<div class="block min-w-1/4 p-4 border-2 rounded-lg shadow-sm bg-background-color border-gray-700">
    <div class="flex gap-1 items-center">
        <span class="{svg} text-normal"></span>
        <h5 class="text-sm tracking-tight text-gray-400">{title}</h5>
    </div>
        {#if adtl}
            <p class="text-2xl md:text-3xl font-bold text-white">{value} <span class="text-lg md:text-xl">({adtl})</span></p>
        {:else}
            <p class="text-2xl md:text-3xl font-bold text-white">{value}</p>
        {/if}
</div>
