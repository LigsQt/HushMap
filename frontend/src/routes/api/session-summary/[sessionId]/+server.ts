import type { SessionSummaryResponse } from '$lib/api/generated/types';
import { proxyBackendJson } from '$lib/server/backend';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = ({ fetch, params }) =>
	proxyBackendJson<SessionSummaryResponse>(
		fetch,
		`/session_info/${encodeURIComponent(params.sessionId)}`,
	);
