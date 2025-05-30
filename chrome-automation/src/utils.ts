import type { LogLevel, Logger } from "./types.js";

/**
 * 색상 코드 정의
 */
export const Colors = {
	reset: "\x1b[0m",
	bright: "\x1b[1m",
	red: "\x1b[31m",
	green: "\x1b[32m",
	yellow: "\x1b[33m",
	blue: "\x1b[34m",
	magenta: "\x1b[35m",
	cyan: "\x1b[36m",
	gray: "\x1b[90m",
} as const;

/**
 * 로그 레벨별 색상 매핑
 */
export const LevelColors: Record<LogLevel, string> = {
	log: Colors.gray,
	info: Colors.blue,
	warn: Colors.yellow,
	error: Colors.red,
	debug: Colors.magenta,
};

/**
 * 컬러 로거 클래스
 */
export class ColorLogger implements Logger {
	private formatMessage(level: LogLevel, message: string): string {
		const timestamp = new Date().toLocaleTimeString();
		const color = LevelColors[level];
		const levelTag = `${color}[${level.toUpperCase()}]${Colors.reset}`;
		const timeTag = `${Colors.gray}[${timestamp}]${Colors.reset}`;

		return `${timeTag} ${levelTag} ${message}`;
	}

	log(message: string, ...args: unknown[]): void {
		console.log(this.formatMessage("log", message), ...args);
	}

	info(message: string, ...args: unknown[]): void {
		console.info(this.formatMessage("info", message), ...args);
	}

	warn(message: string, ...args: unknown[]): void {
		console.warn(this.formatMessage("warn", message), ...args);
	}

	error(message: string, ...args: unknown[]): void {
		console.error(this.formatMessage("error", message), ...args);
	}

	debug(message: string, ...args: unknown[]): void {
		console.debug(this.formatMessage("debug", message), ...args);
	}
}

/**
 * 지연 함수
 */
export const delay = (ms: number): Promise<void> =>
	new Promise((resolve) => setTimeout(resolve, ms));

/**
 * HTTP 요청 함수 (fetch 대체)
 */
export async function httpGet(url: string): Promise<string> {
	try {
		const response = await fetch(url);
		if (!response.ok) {
			throw new Error(`HTTP ${response.status}: ${response.statusText}`);
		}
		return await response.text();
	} catch (error) {
		throw new Error(
			`HTTP 요청 실패: ${error instanceof Error ? error.message : String(error)}`,
		);
	}
}

/**
 * JSON HTTP 요청 함수
 */
export async function httpGetJson<T = unknown>(url: string): Promise<T> {
	const text = await httpGet(url);
	try {
		return JSON.parse(text) as T;
	} catch (error) {
		throw new Error(
			`JSON 파싱 실패: ${error instanceof Error ? error.message : String(error)}`,
		);
	}
}

/**
 * 프로세스 종료 시그널 처리
 */
export function setupGracefulShutdown(cleanup: () => void): void {
	const signals: NodeJS.Signals[] = ["SIGINT", "SIGTERM"];

	for (const signal of signals) {
		process.on(signal, () => {
			console.log(
				`\n${Colors.yellow}🛑 ${signal} 신호를 받았습니다. 정리 중...${Colors.reset}`,
			);
			cleanup();
			process.exit(0);
		});
	}
}

/**
 * 타임아웃과 함께 Promise 실행
 */
export function withTimeout<T>(
	promise: Promise<T>,
	timeoutMs: number,
	timeoutMessage = "작업 시간 초과",
): Promise<T> {
	return Promise.race([
		promise,
		new Promise<never>((_, reject) =>
			setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs),
		),
	]);
}

/**
 * 재시도 로직
 */
export async function retry<T>(
	fn: () => Promise<T>,
	maxAttempts = 3,
	delayMs = 1000,
): Promise<T> {
	let lastError: Error | undefined;

	for (let attempt = 1; attempt <= maxAttempts; attempt++) {
		try {
			return await fn();
		} catch (error) {
			lastError = error instanceof Error ? error : new Error(String(error));

			if (attempt === maxAttempts) {
				throw lastError;
			}

			await delay(delayMs);
		}
	}

	// 이 지점에 도달할 수 없지만 TypeScript를 위해 추가
	throw lastError || new Error("알 수 없는 오류");
}
