<script lang="ts">
    let { color, level, noise, desc } = $props()
    let bgColor = $state("")
    let textColor = $state("")

    if (color == 'quiet-green') {
        bgColor = 'bg-quiet-green';
        textColor = 'text-quiet-green';
    } else if (color == 'loud-orange') {
        bgColor = 'bg-loud-orange';
        textColor = 'text-loud-orange';
    } else {
        bgColor = 'bg-very-loud-red'
        textColor = 'text-very-loud-red';
    }

    const noiseRanges = [
        { min: 0, max: 39, desc: "Silent Room or Library" },
        { min: 39, max: 49, desc: "Quiet Office or Residence" },
        { min: 49, max: 54, desc: "Refrigerator Hum" },
        { min: 54, max: 59, desc: "Household Appliance" },
        { min: 59, max: 64, desc: "Normal Indoor Sound" },
        { min: 64, max: 69, desc: "Moderate Traffic" },
        { min: 69, max: 74, desc: "TV Audio" },
        { min: 74, max: 79, desc: "Loud Indoor Sound" },
        { min: 79, max: 84, desc: "Busy Urban Noise" },
        { min: 84, max: 89, desc: "Truck" },
        { min: 89, max: 94, desc: "Outdoor Machinery" },
        { min: 94, max: 99, desc: "Motorcycle" },
        { min: 99, max: 104, desc: "Loud Vehicle" },
        { min: 104, max: 109, desc: "Concert" },
        { min: 109, max: 114, desc: "Night Club" },
        { min: 114, max: 124, desc: "Jet Engine" },
        { min: 124, max: 140, desc: "Jackhammer" },
        { min: 140, max: Infinity, desc: "Pain Threshold" }
    ];

    function getNoiseComparison(noise: number) {
        const found = noiseRanges.find(r => noise >= r.min && noise < r.max)
        return found ? found.desc : "Unknown"
    };

    let comparison = $derived(getNoiseComparison(noise))
</script>

<div class="flex justify-between mb-1 ">
  <span class="font-medium text-white text-md md:text-lg w-1/2 md:w-auto">Point is <span class="italic {textColor} text-md:font-semibold">{desc}</span> (similar to the noise of
    {#if 'aeiouAEIOU'.includes((comparison ?? '')[0] || '')}
        an
    {:else}
        a
    {/if}
     <span class="italic {textColor} font-semibold">{comparison}</span>)
  </span>
  <span class="font-medium text-white text-md md:text-lg">Mean dBA level: <span class="italic {textColor} font-semibold">{noise}</span></span>
</div>
<div class="w-full rounded-full h-4 md:h-5 bg-gray-700">
  <div class="{bgColor} h-4 md:h-5 rounded-full text-sm font-medium text-white flex items-center justify-center leading-none" style="width: {level}%">{noise} dBA</div>
</div>