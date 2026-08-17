/**
 * Creates a process-local sliding-window limiter with bounded client state.
 *
 * @param {number} limit
 * @param {{ windowMs?: number; maxBuckets?: number }} [options]
 */
export function createSlidingWindowRateLimiter(limit, options = {}) {
	const windowMs = options.windowMs ?? 60_000;
	const maxBuckets = options.maxBuckets ?? 10_000;
	if (limit < 1 || windowMs < 1 || maxBuckets < 1)
		throw new Error('Rate limiter settings must be positive.');

	/** @type {Map<string, number[]>} */
	const hits = new Map();

	/**
	 * @param {number} now
	 */
	function pruneExpired(now) {
		const cutoff = now - windowMs;
		for (const [key, timestamps] of hits) {
			const recent = timestamps.filter((timestamp) => timestamp >= cutoff);
			if (recent.length === 0)
				hits.delete(key);
			else
				hits.set(key, recent);
		}
	}

	/**
	 * @param {string} key
	 * @param {number} [now]
	 */
	function allow(key, now = Date.now()) {
		if (!hits.has(key) && hits.size >= maxBuckets)
			pruneExpired(now);
		if (!hits.has(key) && hits.size >= maxBuckets)
			return false;

		const cutoff = now - windowMs;
		const recent = (hits.get(key) ?? []).filter((timestamp) => timestamp >= cutoff);
		if (recent.length >= limit) {
			hits.set(key, recent);
			return false;
		}

		recent.push(now);
		hits.set(key, recent);
		return true;
	}

	return { allow };
}
