import { env } from '$env/dynamic/private';
import { json, type RequestEvent } from '@sveltejs/kit';

const DEFAULT_TIMEOUT_MS = 15_000;

type ServerFetch = RequestEvent['fetch'];

export class BackendError extends Error {
	override readonly cause?: unknown;

	constructor(
		message: string,
		readonly status: number,
		cause?: unknown,
	) {
		super(message);
		this.name = 'BackendError';
		this.cause = cause;
	}
}

function getBackendUrl(): string {
	const backendUrl = env.BACKEND_URL?.trim();

	if (!backendUrl) {
		throw new BackendError('The backend service is not configured.', 503);
	}

	return backendUrl.replace(/\/+$/, '');
}

async function getErrorMessage(response: Response): Promise<string> {
	const fallback = `The backend returned HTTP ${response.status}.`;

	try {
		const body: unknown = await response.json();

		if (typeof body === 'string' && body) return body;
		if (body && typeof body === 'object') {
			const detail = 'detail' in body ? body.detail : undefined;
			if (typeof detail === 'string' && detail) return detail;

			const error = 'error' in body ? body.error : undefined;
			if (typeof error === 'string' && error) return error;
		}
	} catch {
		return fallback;
	}

	return fallback;
}

export async function requestBackendJson<T>(
	fetch: ServerFetch,
	path: `/${string}`,
	init: RequestInit = {},
): Promise<T> {
	const timeoutSignal = AbortSignal.timeout(DEFAULT_TIMEOUT_MS);

	try {
		const response = await fetch(`${getBackendUrl()}${path}`, {
			...init,
			headers: {
				accept: 'application/json',
				...init.headers,
			},
			signal: timeoutSignal,
		});

		if (!response.ok) {
			throw new BackendError(await getErrorMessage(response), response.status);
		}

		return (await response.json()) as T;
	} catch (error) {
		if (error instanceof BackendError) throw error;
		if (error instanceof DOMException && error.name === 'TimeoutError') {
			throw new BackendError('The backend request timed out.', 504, error);
		}

		throw new BackendError('The backend service could not be reached.', 502, error);
	}
}

export async function proxyBackendJson<T>(
	fetch: ServerFetch,
	path: `/${string}`,
	init?: RequestInit,
): Promise<Response> {
	try {
		return json(await requestBackendJson<T>(fetch, path, init));
	} catch (error) {
		const backendError =
			error instanceof BackendError
				? error
				: new BackendError('An unexpected backend proxy error occurred.', 502, error);

		return json({ error: backendError.message }, { status: backendError.status });
	}
}
