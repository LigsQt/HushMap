import type { RequestHandler } from './$types';
import type { SessionSummaryResponse } from '$lib/api/generated/types';
import { createSlidingWindowRateLimiter } from '$lib/server/rate-limit.js';
import { env } from '$env/dynamic/private';
import { proxyBackendJson } from '$lib/server/backend';

const configuredSummaryLimit = Number.parseInt(env.SUMMARY_RATE_LIMIT_PER_MINUTE ?? '', 10);
const summaryLimit =
	Number.isSafeInteger(configuredSummaryLimit) && configuredSummaryLimit > 0
		? configuredSummaryLimit
		: 6;
const summaryLimiter = createSlidingWindowRateLimiter(summaryLimit);

export const GET: RequestHandler = ({ fetch, getClientAddress, params }) => {
	if (!summaryLimiter.allow(getClientAddress()))
		return Response.json({ error: 'Summary rate limit exceeded.' }, { status: 429 });

	return proxyBackendJson<SessionSummaryResponse>(
		fetch,
		`/session_info/${encodeURIComponent(params.sessionId)}`,
	);
};
