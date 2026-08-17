<script lang="ts">
	import { Chart, Label, Select } from 'flowbite-svelte';
	import type { NoiseSession, ProxyErrorResponse, SessionSummaryResponse } from '$lib/api/generated/types';
	import Card from '$lib/components/Card.svelte';
	import { escapeHtml } from '$lib/security/html.js';
	import Progressbar from '$lib/components/Progressbar.svelte';
	import Spinner from '$lib/components/Spinner.svelte';

	type ChartOptions = import('svelte').ComponentProps<typeof Chart>['options'];

	const { data } = $props();
	const { sessionsInfo } = data;

	// get date
	const permissibleHours = 1;
	const now = new Date();

	interface RecentSession {
		diff: number;
		isWithinAnHour: boolean;
	}

	function createTruthTable(sessions: NoiseSession[]): RecentSession[] {
		const recentTable: RecentSession[] = [];

		sessions.forEach((session) => {
			const sessionLastDate = session.endDate;
			const sessionLastTime = session.startTimes[session.startTimes.length - 1];

			const sessionDate = new Date(`${sessionLastDate} ${sessionLastTime}`);
			const diff = (Math.abs(now.getTime() - sessionDate.getTime()) / (60 * 60 * 1000))
			const isWithinAnHour = Math.round(diff) <= permissibleHours 
			recentTable.push({
				diff: diff * 60,
				isWithinAnHour: isWithinAnHour,
			});
		}
		)

		return recentTable;
	}

	const sessionsWithinAnHour = createTruthTable(sessionsInfo.sessions);

	// select latest date as default one
	let selected = $state(sessionsInfo.sessions?.[sessionsInfo.sessions.length - 1]?.sessionNumber ?? '');
	function listSessions() {
		const sessionChoices = sessionsInfo.sessions.map(session => ({
			value: session.sessionNumber,
			name: `${session.sessionNumber}: ${session.startDate} - ${session.endDate}`,
		}));

		return sessionChoices;
	}
	
	function fillMeanData(mean: number, length: number) {
		return Array(length).fill(mean)
	}

	function getTimeAndLevel(type: string, noiseLevels: number[], startTimes: string[]) {
		let time, level;
		if (type === "min") {
			level = Math.min(...noiseLevels);
		} else if (type === "max") {
			level = Math.max(...noiseLevels);
		}
		time = startTimes[noiseLevels.indexOf(level!)];
		return [time, level]
	}

	function buildOptions(noiseLevels: number[], meanNoise: number[], colorHex: string, startTimes: string[], descriptions: string[]): ChartOptions {
		return {
			chart: {
				height: '300px',
				width: '95%',
				type: 'line' as const,
				fontFamily: 'Inter, sans-serif',
				dropShadow: {
					enabled: false,
				},
				toolbar: {
					show: false,
				},
			},
			tooltip: {
				enabled: true,
				x: {
					show: true,
				},
				custom({
					series,
					seriesIndex,
					dataPointIndex,
				}: {
					series: number[][] | (number | null)[][];
					seriesIndex: number;
					dataPointIndex: number;
				}) {
					const description = descriptions[dataPointIndex];
					const time = startTimes[dataPointIndex];
					const point = series[seriesIndex]?.[dataPointIndex];
					const value = point === null || point === undefined ? 'No Data' : `${point} dBA`;

					return `
						<div class="p-2 text-sm">
							<p><strong>Time:</strong> ${escapeHtml(time)}</p>
							<p><strong>Level:</strong> ${escapeHtml(value)}</p>
							<p><strong>Description:</strong> ${escapeHtml(description)}</p>
						</div>
					`;
				},
			},
			dataLabels: {
				enabled: false,
			},
			stroke: {
				width: 2.5,
				curve: 'smooth',
			},
			grid: {
				show: true,
				strokeDashArray: 3,
			},
			series: [
				{
					name: 'dBA Level',
					data: noiseLevels,
					color: '#ffffff',
				},
				{
					name: 'mean',
					data: meanNoise,
					color: colorHex,
				}
			],
			legend: {
				show: false,
			},
			xaxis: {
				categories: startTimes,
				title: {
					text: 'Timeframes',
					style: {
						color: 'white',
					}
				},
				labels: {
					show: true,
					hideOverlappingLabels: true,
					rotate: -7,
					style: {
						fontFamily: 'Inter, sans-serif',
						cssClass: 'text-xs font-light fill-white',
					},
				},
				axisBorder: {
					show: true,
				},
				axisTicks: {
					show: false,
				},
			},
			yaxis: {
				show: true,
				title: {
					text: 'dBA Level',
					style: {
						color: 'white',
					}
				},
				labels: {
					style: {
						fontFamily: 'Inter, sans-serif',
						cssClass: 'text-xs font-light fill-white',
					},
				},
				axisBorder: {
					show: true,
				},
			},
		};
	}

	let isLoading = $state(false);
	let result = $state('');
	let summaryError = $state('');

	async function handleClick(sessionId: number) {
		isLoading = true;
		result = '';
		summaryError = '';

		try {
			const response = await fetch(`/api/session-summary/${encodeURIComponent(sessionId)}`);

			if (!response.ok) {
				const body = (await response.json().catch(() => null)) as ProxyErrorResponse | null;
				throw new Error(body?.error ?? 'Unable to summarize this session.');
			}

			result = (await response.json()) as SessionSummaryResponse;
		} catch (error) {
			summaryError =
				error instanceof Error ? error.message : 'Unable to summarize this session.';
		} finally {
			isLoading = false;
		}
	}

	const latDir = $derived(sessionsInfo.lat > 0 ? 'N' : 'S');
	const lonDir = $derived(sessionsInfo.lon > 0 ? 'E' : 'W');

	let levelDesc = $state('');
	let color = $state('');
	let colorHex = $state('');
	if (sessionsInfo.meanNoise < 60) {
		levelDesc = 'Quiet';
		color = 'quiet-green';
		colorHex = '#32cd32'
	} else if (sessionsInfo.meanNoise > 60 && sessionsInfo.meanNoise < 69) {
		levelDesc = 'Loud';
		color = 'loud-orange';
		colorHex = '#ff5f1f';
	} else {
		levelDesc = 'Very Loud';
		color = 'very-loud-red';
		colorHex = '#dc143c';
	}
</script>

<div class="bg-background-color flex min-w-full flex-col px-4 pt-2 text-white">
	<div class="border-b pb-2">
		<h2 class="text-2xl md:text-3xl font-bold mb-2">
			This point is in <span class="italic">{sessionsInfo.brgy}, {sessionsInfo.city}</span>.
		</h2>
		<div class="mb-2">
			<Progressbar {color} level={String((sessionsInfo.meanNoise / 1.40).toFixed(2))} noise={sessionsInfo.meanNoise} desc={levelDesc} />
		</div>
		<p class="">
			Latitude and Longitude: [{sessionsInfo.lat.toFixed(2)}°{latDir}, {sessionsInfo.lon.toFixed(
				2,
			)}°{lonDir}]
		</p>
	</div>

	<Label class="text-md mt-2 w-full md:w-1/4 mb-2">
		<p class="mb-1 text-white">Select date (session)</p>
		<Select
			items={listSessions()}
			bind:value={selected}
			class="rounded-lg px-2 py-2 bg-header-color text-white outline-[0.5px]"
		/>
	</Label>

	<div class="flex flex-col justify-center text-white gap-2 md:gap-4 pb-6">
		{#each sessionsInfo.sessions as session (session.sessionNumber)}
			{#if selected === session.sessionNumber}
				<h4 class="text-xl font-semibold text-center">
					{#if session.startDate === session.endDate}
						Session {session.sessionNumber}: {session.startDate}
					{:else}
						Session {session.sessionNumber}: {session.startDate} - {session.endDate}
					{/if}
				</h4>
				<Chart
					class="w-full border-2 px-4 border-gray-700"
					options={buildOptions(session.data, fillMeanData(session.meanNoiseSession, session.data.length), colorHex, session.startTimes, session.descriptions)}
				/>
				<div class="flex items-center justify-center flex-col">
					{#if result}
						<p class="border-3 px-2 border-gray-700 py-2">{result}</p>
					{:else if summaryError}
						<div class="flex flex-col items-center gap-2">
							<p role="alert" class="border-2 border-red-700 px-2 py-2">{summaryError}</p>
							<button
								type="button"
								class="rounded-full border-2 border-header-color px-6 py-2 hover:bg-gray-700"
								onclick={() => handleClick(session.session_id)}
							>
								Retry summary
							</button>
						</div>
					{:else}
						{#if isLoading}
							<Spinner />
							<p class="mt-2">Summarizing insights...</p>
						{:else}
							<button type="button" class="mt-2 md:mt-0 animate-bounce border-2 rounded-full border-header-color py-3 px-8 cursor-pointer hover:bg-gray-700" onclick={() => handleClick(session.session_id)}>Summarize insights with <span class="italic text-lg">✨AI✨</span>?</button>
						{/if}
					{/if}
				</div>
				<div class="grid grid-cols-1 md:grid-cols-4 gap-2 justify-center">
					<Card title={"Session's Mean dBA Level"} value={`${session.meanNoiseSession} dBA`} icon="dba" />
					<Card title={"Timeframe"} value={`${session.startTimes[0]} - ${session.startTimes[session.startTimes.length - 1]}`} icon="time" />
					<Card title={"Quietest Time"} value={getTimeAndLevel("min", session.data, session.startTimes)[0]} adtl={String(getTimeAndLevel("min", session.data, session.startTimes)[1]) + ' dBA'} icon="quiet" />
					<Card title={"Loudest Time"} value={getTimeAndLevel("max", session.data, session.startTimes)[0]} adtl={String(getTimeAndLevel("max", session.data, session.startTimes)[1]) + ' dBA'} icon="loud" />
				</div>
				<div class="grid grid-cols-1 md:grid-cols-3 gap-2 justify-center">
					{#if sessionsWithinAnHour[session.sessionNumber - 1]?.isWithinAnHour}
						<Card title="Time (Most Recent)" value={`${session.startTimes[session.startTimes.length - 1]}`} adtl={Math.round(sessionsWithinAnHour[session.sessionNumber - 1]?.diff ?? 0) + ' minute/s ago'} icon="time" />
						<Card title="dBA Level (Most Recent)" value={`${session.data[session.data.length - 1]} dBA`} icon="dba" />
						<Card title="Description (Most Recent)" value={session.descriptions[session.descriptions.length - 1]} icon="desc" />
					{/if}
				</div>
			{/if}
		{/each}
	</div>
</div>