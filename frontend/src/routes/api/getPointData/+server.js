import { proxyBackendJson } from '$lib/server/backend';

/** @type {import('./$types').RequestHandler} */
export function GET({ fetch }) {
	return proxyBackendJson(fetch, '/geojson/points');
}
