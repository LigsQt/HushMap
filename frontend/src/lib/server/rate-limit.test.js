import assert from 'node:assert/strict';
import test from 'node:test';

import { createSlidingWindowRateLimiter } from './rate-limit.js';

test('sliding window limiter bounds calls and evicts expired clients', () => {
	const limiter = createSlidingWindowRateLimiter(1, {
		windowMs: 100,
		maxBuckets: 2,
	});

	assert.equal(limiter.allow('client-a', 0), true);
	assert.equal(limiter.allow('client-a', 1), false);
	assert.equal(limiter.allow('client-b', 1), true);
	assert.equal(limiter.allow('client-c', 1), false);
	assert.equal(limiter.allow('client-c', 101), true);
});
