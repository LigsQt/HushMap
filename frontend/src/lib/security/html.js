/**
 * Escapes a value for insertion into an HTML text context.
 *
 * @param {unknown} value
 * @returns {string}
 */
export function escapeHtml(value) {
	return String(value ?? '')
		.replaceAll('&', '&amp;')
		.replaceAll('<', '&lt;')
		.replaceAll('>', '&gt;')
		.replaceAll('"', '&quot;')
		.replaceAll("'", '&#39;');
}
