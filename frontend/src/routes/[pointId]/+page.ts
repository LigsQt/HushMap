import type { PointSessionsResponse, ProxyErrorResponse } from '$lib/api/generated/types';
import { error } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch, params }) => {
	const response = await fetch(`/api/getPointData/${encodeURIComponent(params.pointId)}`);

	if (!response.ok) {
		const body = (await response.json().catch(() => null)) as ProxyErrorResponse | null;
		error(response.status, body?.error ?? 'Unable to load point data.');
	}

	return {
		sessionsInfo: (await response.json()) as PointSessionsResponse,
	};
};
