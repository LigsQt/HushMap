import type { NoisePointsResponse, ProxyErrorResponse } from '$lib/api/generated/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/api/getPointData');

	if (!response.ok) {
		const body = (await response.json().catch(() => null)) as ProxyErrorResponse | null;
		error(response.status, body?.error ?? 'Unable to load map points.');
	}

	return {
		points: (await response.json()) as NoisePointsResponse,
	};
};
