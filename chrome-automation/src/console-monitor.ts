import { ChromeDevToolsClient } from "./chrome-client.js";
import type { ConsoleMonitorConfig, Logger } from "./types.js";
import { ColorLogger, setupGracefulShutdown, Colors } from "./utils.js";

/**
 * Console 모니터링 전용 클래스
 */
export class ConsoleMonitor {
	private client: ChromeDevToolsClient;
	private config: ConsoleMonitorConfig;
	private logger: Logger;
	private isRunning = false;

	constructor(config: ConsoleMonitorConfig, logger?: Logger) {
		this.config = config;
		this.logger = logger || new ColorLogger();
		this.client = new ChromeDevToolsClient(config.debugPort, this.logger);

		// 프로세스 종료 시 정리
		setupGracefulShutdown(() => this.stop());
	}

	/**
	 * Console 모니터링 시작
	 */
	async start(): Promise<void> {
		this.logger.info("🔍 Chrome DevTools Console Monitor");
		this.logger.info(`📍 디버그 포트: ${this.config.debugPort}`);
		this.logger.info(`🎯 대상 URL 패턴: ${this.config.targetUrlPattern}`);
		this.logger.info("");

		try {
			// Chrome 연결 확인
			await this.client.getVersion();
			this.logger.info("✅ Chrome DevTools에 연결되었습니다");

			// 대상 탭 찾기
			const tab = await this.client.findTab(this.config.targetUrlPattern);
			if (!tab) {
				throw new Error(
					`대상 탭을 찾을 수 없습니다. 패턴: ${this.config.targetUrlPattern}`,
				);
			}

			// 탭에 연결
			await this.client.connectToTab(tab);

			// DevTools 도메인 활성화
			await this.client.enableDomain("Runtime");
			await this.client.enableDomain("Console");
			await this.client.enableDomain("Log");

			// Console 모니터링 시작
			this.startMonitoring();
			this.isRunning = true;

			this.logger.info("📺 Console 메시지 모니터링 시작...");
			this.logger.info(
				`${Colors.yellow}💡 종료하려면 Ctrl+C를 누르세요${Colors.reset}`,
			);
			this.logger.info("");

			// 무한 대기 (Ctrl+C로 종료)
			await this.waitForever();
		} catch (error) {
			this.logger.error(
				`❌ 초기화 오류: ${error instanceof Error ? error.message : String(error)}`,
			);
			process.exit(1);
		}
	}

	/**
	 * Console 모니터링 설정
	 */
	private startMonitoring(): void {
		// Console API 호출 모니터링
		this.client.onConsoleMessage((message) => {
			const timestamp = this.getTimestamp();
			const level = message.level || "log";
			const color = this.getLevelColor(level);
			const levelTag = `${color}[${level.toUpperCase()}]${Colors.reset}`;

			// 메시지 텍스트 추출
			let text = "";
			if (message.text) {
				text = message.text;
			} else if (message.args && message.args.length > 0) {
				text = message.args
					.map((arg) => {
						if (arg.value !== undefined) {
							return String(arg.value);
						}
						if (arg.description) {
							return arg.description;
						}
						if (arg.preview?.description) {
							return arg.preview.description;
						}
						return "[Object]";
					})
					.join(" ");
			}

			// 소스 정보
			let source = "";
			if (message.url && message.line) {
				const filename = message.url.split("/").pop();
				source = `${Colors.gray}(${filename}:${message.line})${Colors.reset}`;
			}

			console.log(`${timestamp} ${levelTag} ${text} ${source}`);
		});

		// Exception 모니터링
		this.client.onException((exception) => {
			const timestamp = this.getTimestamp();
			console.log(
				`${timestamp} ${Colors.red}[EXCEPTION]${Colors.reset} ${exception.text}`,
			);

			if (exception.stackTrace) {
				for (const frame of exception.stackTrace.callFrames.slice(0, 3)) {
					console.log(
						`${Colors.gray}    at ${frame.functionName || "<anonymous>"} (${frame.url}:${frame.lineNumber})${Colors.reset}`,
					);
				}
			}
		});
	}

	/**
	 * 타임스탬프 생성
	 */
	private getTimestamp(): string {
		const now = new Date();
		return `${Colors.gray}[${now.toLocaleTimeString()}]${Colors.reset}`;
	}

	/**
	 * 로그 레벨별 색상 가져오기
	 */
	private getLevelColor(level: string): string {
		const colorMap: Record<string, string> = {
			log: Colors.gray,
			info: Colors.blue,
			warn: Colors.yellow,
			error: Colors.red,
			debug: Colors.magenta,
			verbose: Colors.cyan,
		};

		return colorMap[level] || Colors.gray;
	}

	/**
	 * 무한 대기 (프로세스 종료까지)
	 */
	private async waitForever(): Promise<void> {
		return new Promise(() => {
			// 무한 대기 - 시그널 핸들러에서 종료
		});
	}

	/**
	 * 모니터링 중지
	 */
	stop(): void {
		if (this.isRunning) {
			this.logger.info(
				`\n${Colors.yellow}🛑 Console 모니터링을 종료합니다...${Colors.reset}`,
			);
			this.client.close();
			this.isRunning = false;
		}
	}
}
