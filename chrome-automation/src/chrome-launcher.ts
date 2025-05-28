import { spawn, ChildProcess } from "child_process";
import { ChromeDevToolsClient } from "./chrome-client.js";
import type {
	ChromeLauncherConfig,
	ClickCoordinates,
	Logger,
	ConsoleMessage,
} from "./types.js";
import {
	ColorLogger,
	delay,
	retry,
	setupGracefulShutdown,
	Colors,
} from "./utils.js";

/**
 * Chrome 프로세스 관리 및 자동화 클래스
 */
export class ChromeLauncher {
	private chromeProcess: ChildProcess | null = null;
	private client: ChromeDevToolsClient;
	private config: ChromeLauncherConfig;
	private logger: Logger;

	constructor(config: ChromeLauncherConfig, logger?: Logger) {
		this.config = config;
		this.logger = logger || new ColorLogger();
		this.client = new ChromeDevToolsClient(config.debugPort, this.logger);

		// 프로세스 종료 시 정리
		setupGracefulShutdown(() => this.cleanup());
	}

	/**
	 * Chrome 프로세스 시작
	 */
	async start(): Promise<void> {
		this.logger.info("🚀 Chrome 헤드리스 모드 실행");
		this.logger.info(`📍 URL: ${this.config.url}`);
		this.logger.info(`📐 창 크기: ${this.config.width}x${this.config.height}`);
		this.logger.info(`🔧 디버그 포트: ${this.config.debugPort}`);

		// 기존 프로세스 확인 및 종료
		await this.killExistingChrome();

		// Chrome 실행
		await this.launchChrome();

		// Chrome 초기화 대기
		await this.waitForChromeReady();

		// 탭 찾기 및 연결
		await this.findAndConnectToTab();

		// DevTools 도메인 활성화
		await this.enableDevToolsDomains();

		// 메시지 기반 자동 클릭 수행
		if (this.config.waitForMessage && this.config.clickAfterMessage) {
			await this.performMessageBasedClick();
		}

		this.logger.info(
			`${Colors.green}🎉 Chrome이 성공적으로 실행되었습니다!${Colors.reset}`,
		);
		this.printStatus();
	}

	/**
	 * 기존 Chrome 프로세스 종료
	 */
	private async killExistingChrome(): Promise<void> {
		try {
			const { execSync } = await import("child_process");
			const pids = execSync("pgrep -f chromium-browser", {
				encoding: "utf8",
			}).trim();

			if (pids) {
				this.logger.warn("⚠️  기존 Chrome 프로세스를 종료합니다...");
				execSync("pkill -f chromium-browser");
				await delay(2000);
			}
		} catch (error) {
			// 기존 프로세스가 없는 경우 무시
		}
	}

	/**
	 * Chrome 프로세스 실행
	 */
	private async launchChrome(): Promise<void> {
		const args = [
			"--headless",
			"--disable-gpu",
			`--remote-debugging-port=${this.config.debugPort}`,
			"--no-sandbox",
			"--disable-dev-shm-usage",
			`--window-size=${this.config.width},${this.config.height}`,
			"--disable-extensions",
			"--disable-plugins",
			"--disable-background-timer-throttling",
			"--disable-backgrounding-occluded-windows",
			"--disable-renderer-backgrounding",
			"--no-first-run",
			"--disable-default-apps",
			"--disable-sync",
			"--metrics-recording-only",
			"--no-report-upload",
			"--disable-web-security",
			"--allow-running-insecure-content",
			"--disable-features=VizDisplayCompositor",
			this.config.url,
		];

		this.logger.info("▶️  Chrome을 백그라운드에서 실행합니다...");

		this.chromeProcess = spawn("chromium-browser", args, {
			stdio: "pipe",
			detached: false,
		});

		if (!this.chromeProcess.pid) {
			throw new Error("Chrome 프로세스 시작 실패");
		}

		this.logger.info(
			`✅ Chrome이 시작되었습니다 (PID: ${this.chromeProcess.pid})`,
		);

		// 프로세스 이벤트 처리
		this.chromeProcess.on("error", (error) => {
			this.logger.error(`Chrome 프로세스 오류: ${error.message}`);
		});

		this.chromeProcess.on("exit", (code) => {
			this.logger.warn(`Chrome 프로세스가 종료되었습니다 (코드: ${code})`);
			this.chromeProcess = null;
		});
	}

	/**
	 * Chrome 초기화 대기
	 */
	private async waitForChromeReady(): Promise<void> {
		this.logger.info("⏳ Chrome 초기화를 기다리는 중...");

		await retry(
			async () => {
				await this.client.getVersion();
			},
			10,
			1000,
		);

		this.logger.info("✅ 디버그 포트가 활성화되었습니다!");
	}

	/**
	 * 탭 찾기 및 연결
	 */
	private async findAndConnectToTab(): Promise<void> {
		this.logger.info("🎯 목표 탭을 찾는 중...");

		const urlPattern =
			new URL(this.config.url).hostname + ":" + new URL(this.config.url).port;
		const tab = await this.client.findTab(urlPattern);

		if (!tab) {
			throw new Error("대상 탭을 찾을 수 없습니다");
		}

		this.logger.info(`🎯 대상 탭 발견: ${tab.id}`);
		await this.client.connectToTab(tab);
	}

	/**
	 * DevTools 도메인 활성화
	 */
	private async enableDevToolsDomains(): Promise<void> {
		await this.client.enableDomain("Runtime");
		await this.client.enableDomain("Console");
		await this.client.enableDomain("Page");
	}

	/**
	 * 메시지 기반 자동 클릭 수행
	 */
	private async performMessageBasedClick(): Promise<void> {
		if (!this.config.waitForMessage) return;

		this.logger.info(
			`⏳ "${this.config.waitForMessage}" 메시지를 기다리는 중...`,
		);

		// Console 메시지 대기
		await this.client.waitForConsoleMessage(this.config.waitForMessage);

		// 클릭 딜레이
		const clickDelay = this.config.clickDelay || 1000;
		this.logger.info(`⏳ ${clickDelay}ms 후 클릭을 수행합니다...`);
		await delay(clickDelay);

		// 화면 중앙 클릭
		const coordinates: ClickCoordinates = {
			x: Math.floor(this.config.width / 2),
			y: Math.floor(this.config.height / 2),
		};

		await this.client.click(coordinates);
		this.logger.info("✅ 메시지 기반 자동 클릭이 완료되었습니다!");
	}

	/**
	 * 상태 정보 출력
	 */
	private printStatus(): void {
		this.logger.info("");
		this.logger.info(`${Colors.blue}📊 상태 확인 명령어:${Colors.reset}`);
		this.logger.info(
			`  프로세스 확인: ps -ef | grep chromium-browser | grep -v grep`,
		);
		this.logger.info(
			`  종료: pnpm run stop 또는 kill ${this.chromeProcess?.pid || "PID"}`,
		);
		this.logger.info("");
		this.logger.info(`${Colors.blue}🌐 원격 디버깅 URL:${Colors.reset}`);
		this.logger.info(`  http://localhost:${this.config.debugPort}`);
	}

	/**
	 * Console 모니터링 시작
	 */
	async startConsoleMonitoring(): Promise<void> {
		this.logger.info("📺 Console 메시지 모니터링 시작...");

		this.client.onConsoleMessage((message) => {
			const text = this.extractConsoleText(message);
			const timestamp = new Date().toLocaleTimeString();
			const level = message.level || "log";
			const color = this.getLogColor(level);

			console.log(
				`${Colors.gray}[${timestamp}]${Colors.reset} ${color}[${level.toUpperCase()}]${Colors.reset} ${text}`,
			);
		});

		this.client.onException((exception) => {
			const timestamp = new Date().toLocaleTimeString();
			console.log(
				`${Colors.gray}[${timestamp}]${Colors.reset} ${Colors.red}[EXCEPTION]${Colors.reset} ${exception.text}`,
			);

			if (exception.stackTrace) {
				exception.stackTrace.callFrames.slice(0, 3).forEach((frame) => {
					console.log(
						`${Colors.gray}    at ${frame.functionName || "<anonymous>"} (${frame.url}:${frame.lineNumber})${Colors.reset}`,
					);
				});
			}
		});
	}

	/**
	 * Console 메시지에서 텍스트 추출
	 */
	private extractConsoleText(
		message: ConsoleMessage | Record<string, unknown>,
	): string {
		if (typeof message.text === "string") {
			return message.text;
		}

		if (Array.isArray(message.args) && message.args.length > 0) {
			return message.args
				.map((arg: Record<string, unknown>) => {
					if (arg.value !== undefined) {
						return String(arg.value);
					}
					if (typeof arg.description === "string") {
						return arg.description;
					}
					return "[Object]";
				})
				.join(" ");
		}

		return "";
	}

	/**
	 * 로그 레벨별 색상 가져오기
	 */
	private getLogColor(level: string): string {
		const colorMap: Record<string, string> = {
			log: Colors.gray,
			info: Colors.blue,
			warn: Colors.yellow,
			error: Colors.red,
			debug: Colors.magenta,
		};

		return colorMap[level] || Colors.gray;
	}

	/**
	 * 정리 작업
	 */
	private cleanup(): void {
		this.logger.info("🧹 정리 작업을 수행합니다...");

		this.client.close();

		if (this.chromeProcess && !this.chromeProcess.killed) {
			this.chromeProcess.kill("SIGTERM");
			this.chromeProcess = null;
		}
	}

	/**
	 * Chrome 프로세스 종료
	 */
	async stop(): Promise<void> {
		this.cleanup();
		this.logger.info("🛑 Chrome이 종료되었습니다");
	}
}
