import assert from 'node:assert/strict';
import test from 'node:test';

import { escapeHtml } from './html.js';

test('escapeHtml prevents malicious values from becoming markup', () => {
	const malicious = `<img src=x onerror="globalThis.compromised=true">&'`;

	assert.equal(
		escapeHtml(malicious),
		'&lt;img src=x onerror=&quot;globalThis.compromised=true&quot;&gt;&amp;&#39;',
	);
	assert.equal(escapeHtml(null), '');
});
