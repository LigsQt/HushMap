import { proxyBackendJson } from '$lib/server/backend';

/** @type {import('./$types').RequestHandler} */
export function GET({ fetch, params }) {
	return proxyBackendJson(fetch, `/points/${encodeURIComponent(params.pointId)}`);
}
