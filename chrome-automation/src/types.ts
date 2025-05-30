/**
 * Chrome DevTools Protocol 관련 타입 정의
 */

export interface ChromeTab {
	id: string;
	title: string;
	type: string;
	url: string;
	webSocketDebuggerUrl: string;
	devtoolsFrontendUrl?: string;
	faviconUrl?: string;
	thumbnailUrl?: string;
}

export interface ChromeVersion {
	Browser: string;
	"Protocol-Version": string;
	"User-Agent": string;
	"V8-Version": string;
	"WebKit-Version": string;
	webSocketDebuggerUrl: string;
}

export interface DevToolsMessage {
	id: number;
	method: string;
	params?: Record<string, unknown>;
	result?: Record<string, unknown>;
	error?: Record<string, unknown>;
}

export interface ConsoleMessage {
	level: "log" | "info" | "warn" | "error" | "debug" | "verbose";
	text?: string;
	args?: Array<{
		value?: string | number | boolean | null;
		description?: string;
		preview?: {
			description?: string;
		};
	}>;
	url?: string;
	line?: number;
	column?: number;
	timestamp?: number;
}

export interface ExceptionDetails {
	text: string;
	url?: string;
	lineNumber?: number;
	columnNumber?: number;
	stackTrace?: {
		callFrames: Array<{
			functionName: string;
			url: string;
			lineNumber: number;
			columnNumber: number;
		}>;
	};
}

export interface ChromeConfig {
	url: string;
	width: number;
	height: number;
	debugPort: number;
	headless: boolean;
}

export interface ClickCoordinates {
	x: number;
	y: number;
}

export interface ConsoleMonitorConfig {
	debugPort: number;
	targetUrlPattern: string;
	timeout: number;
}

export interface ChromeLauncherConfig extends ChromeConfig {
	waitForMessage?: string;
	clickAfterMessage?: boolean;
	clickDelay?: number;
}

export type LogLevel = "log" | "info" | "warn" | "error" | "debug";

export interface Logger {
	log(message: string, ...args: unknown[]): void;
	info(message: string, ...args: unknown[]): void;
	warn(message: string, ...args: unknown[]): void;
	error(message: string, ...args: unknown[]): void;
	debug(message: string, ...args: unknown[]): void;
}
