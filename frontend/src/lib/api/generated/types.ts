/**
 * Local API contract types matching the backend's current response field names.
 *
 * Replace this file with OpenAPI-generated output once backend generation is available.
 */

export interface NoisePointProperties {
	noOfSessions: number;
	meanNoiseLevel: number;
	brgy: string;
	city: string;
	isActive?: boolean;
}

export interface NoisePointFeature {
	type: 'Feature';
	id: number | string;
	geometry: {
		type: 'Point';
		coordinates: [number, number];
	};
	properties: NoisePointProperties;
}

export interface NoisePointsResponse {
	type: 'FeatureCollection';
	features: NoisePointFeature[];
}

export interface NoiseSession {
	sessionNumber: number;
	session_id: number;
	startDate: string;
	endDate: string;
	data: number[];
	startTimes: string[];
	descriptions: string[];
	meanNoiseSession: number;
}

export interface PointSessionsResponse {
	pointId: number | string;
	lat: number;
	lon: number;
	brgy: string;
	city: string;
	meanNoise: number;
	sessions: NoiseSession[];
}

export type SessionSummaryResponse = string;

export interface ProxyErrorResponse {
	error: string;
}
