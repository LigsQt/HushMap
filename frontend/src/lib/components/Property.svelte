<script>
	const props = $props();

	let dbClass = $state('');
	let dbText = $derived(props.val);
	if (props.attr === 'Mean dBA level')
		if (props.val === 0) {
			dbClass = 'text-black';
			dbText = 'No Data'
		}
		else if (props.val <= 60) {
			dbClass = 'text-quiet-green';
			dbText = `${props.val} dBA (Quiet)`;
		} else if (props.val > 60 && props.val < 69) {
			dbClass = 'text-loud-orange';
			dbText = `${props.val} dBA (Loud)`;
		} else {
			dbClass = 'text-very-loud-red';
			dbText = `${props.val} dBA (Very Loud)`;
		}
</script>

<div>
	<p>
		<span class="italic">{props.attr}</span>:
		{#if props.attr === 'Timeframe'}
			{@const [start, end] = props.val}
			<span class="font-semibold {dbClass}">{start} to {end}</span>
		{:else}
			<span class="font-semibold {dbClass}">{dbText}</span>
		{/if}
	</p>
</div>
