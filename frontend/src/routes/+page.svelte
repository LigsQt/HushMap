<script lang="ts">
	import {
		FillExtrusionLayer,
		FullScreenControl,
		GeoJSONSource,
		GlobeControl,
		MapLibre,
		Marker,
		NavigationControl,
		Popup,
		ScaleControl,
	} from 'svelte-maplibre-gl';
	import Circle from '$lib/components/Circle.svelte';
	import { is3d } from '$lib/state.svelte';
	import Legend from '$lib/components/Legend.svelte';
	import Property from '$lib/components/Property.svelte';

	// for server load
	const { data } = $props();

	const OFFSET = 23;
	const popupOffset = {
		top: [0, OFFSET] as [number, number],
		bottom: [0, -OFFSET] as [number, number],
		left: [OFFSET + 12, 0] as [number, number],
		right: [-OFFSET - 12, 0] as [number, number],
		center: [0, 0] as [number, number],
		'top-left': [OFFSET, OFFSET] as [number, number],
		'top-right': [-OFFSET, OFFSET] as [number, number],
		'bottom-left': [OFFSET, -OFFSET] as [number, number],
		'bottom-right': [-OFFSET, -OFFSET] as [number, number],
	};
</script>

<!-- lightMap: style="https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json" -->
<!-- darkMap: style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json" -->
<!-- openStreetMap: style="https://roblabs.com/xyz-raster-sources/styles/openstreetmap.json" -->

<div class="relative w-full h-full">
	<MapLibre
		class="h-full"
		style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
		zoom={15.3}
		center={{ lng: 121.068, lat: 14.6539 }}
	>
		<NavigationControl />
		<GlobeControl />
		<ScaleControl />
		<FullScreenControl position="top-left" />
		<div class="absolute z-10 left-3 bottom-10">
			<Legend />
		</div>

		<GeoJSONSource data={data.points}>
			{#each data.points.features as feature (feature.id)}
				<Marker lnglat={feature.geometry.coordinates} >
					{#snippet content()}
						{@const dbaRounded = Math.round(Number(feature.properties.meanNoiseLevel))}
							<div class={feature.properties.isActive ? "breathe" : ""}>
								{#if feature.properties.noOfSessions === 0}
									<Circle color="red-900" dbaLevel={0} />
								{:else if Number(feature.properties.meanNoiseLevel) <= 60}
									<Circle color="quiet-green" dbaLevel={dbaRounded} />
								{:else if Number(feature.properties.meanNoiseLevel) > 60 && Number(feature.properties.meanNoiseLevel) < 69}
									<Circle color="loud-orange" dbaLevel={dbaRounded} />
								{:else}
									<Circle color="very-loud-red" dbaLevel={dbaRounded} />
								{/if}
							</div>
					{/snippet}
					<Popup class="maplibre-popup-content" offset={popupOffset}>
						<Property attr="Barangay" val={feature.properties.brgy} />
						<Property attr="City" val={feature.properties.city} />
						<Property attr="Number of sessions" val={feature.properties.noOfSessions} />
						<Property attr="Mean dBA level" val={feature.properties.meanNoiseLevel} />
						<span class="italic">Graph</span>:
						<a href="/{feature.id}" target="_blank" class="italic underline"
							>Click here for more info!</a
						>
					</Popup>
				</Marker>
			{/each}
		</GeoJSONSource>

		{#if is3d.state}
			<FillExtrusionLayer
				source="carto"
				sourceLayer="building"
				minzoom={14}
				filter={['!=', ['get', 'hide_3d'], true]}
				paint={{
					'fill-extrusion-color': [
						'interpolate',
						['linear'],
						['get', 'render_height'],
						0,
						'#aaccbb',
						200,
						'royalblue',
						400,
						'purple',
					],
					'fill-extrusion-height': [
						'interpolate',
						['linear'],
						['zoom'],
						14,
						0,
						15,
						['get', 'render_height'],
					],
					'fill-extrusion-base': [
						'case',
						['>=', ['get', 'zoom'], 14],
						['get', 'render_min_height'],
						0,
					],
				}}
			/>
		{/if}
	</MapLibre>
</div>

<style>
@keyframes breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.25);
    opacity: 0.75;
  }
}

.breathe {
  animation: breathe 1.5s ease-in-out infinite;
}
</style>
