import WebSocket from "ws";
import type {
	ChromeTab,
	ChromeVersion,
	DevToolsMessage,
	ConsoleMessage,
	ExceptionDetails,
	ClickCoordinates,
	Logger,
} from "./types.js";
import { httpGetJson, delay, withTimeout, ColorLogger } from "./utils.js";

/**
 * Chrome DevTools Protocol 클라이언트
 */
export class ChromeDevToolsClient {
	private ws: WebSocket | null = null;
	private messageId = 0;
	private logger: Logger;
	private debugPort: number;

	constructor(debugPort: number, logger?: Logger) {
		this.debugPort = debugPort;
		this.logger = logger || new ColorLogger();
	}

	/**
	 * Chrome 버전 정보 가져오기
	 */
	async getVersion(): Promise<ChromeVersion> {
		const url = `http://localhost:${this.debugPort}/json/version`;
		return await httpGetJson<ChromeVersion>(url);
	}

	/**
	 * 모든 탭 목록 가져오기
	 */
	async getTabs(): Promise<ChromeTab[]> {
		const url = `http://localhost:${this.debugPort}/json`;
		return await httpGetJson<ChromeTab[]>(url);
	}

	/**
	 * URL 패턴으로 탭 찾기
	 */
	async findTab(urlPattern: string): Promise<ChromeTab | null> {
		const tabs = await this.getTabs();

		// 우선순위별 검색
		let targetTab = tabs.find((tab) => tab.url?.includes(urlPattern));

		if (!targetTab) {
			targetTab = tabs.find(
				(tab) =>
					tab.type === "page" && !tab.url?.startsWith("chrome-extension://"),
			);
		}

		if (!targetTab) {
			targetTab = tabs.find((tab) => tab.type === "page");
		}

		return targetTab || null;
	}

	/**
	 * 특정 탭에 연결
	 */
	async connectToTab(tab: ChromeTab): Promise<void> {
		if (this.ws) {
			this.ws.close();
		}

		this.logger.info(`🔗 탭에 연결 중: ${tab.title || "Unknown"}`);
		this.logger.info(`📄 URL: ${tab.url}`);
		this.logger.debug(`🆔 Tab ID: ${tab.id}`);

		return new Promise((resolve, reject) => {
			this.ws = new WebSocket(tab.webSocketDebuggerUrl);

			this.ws.on("open", () => {
				this.logger.info("✅ WebSocket 연결 성공");
				resolve();
			});

			this.ws.on("error", (error) => {
				this.logger.error(`❌ WebSocket 연결 오류: ${error.message}`);
				reject(error);
			});

			this.ws.on("close", () => {
				this.logger.warn("⚠️  WebSocket 연결이 종료되었습니다");
			});
		});
	}

	/**
	 * DevTools 도메인 활성화
	 */
	async enableDomain(domain: string): Promise<void> {
		await this.sendCommand(`${domain}.enable`);
	}

	/**
	 * DevTools 명령 전송
	 */
	async sendCommand(
		method: string,
		params?: Record<string, unknown>,
	): Promise<unknown> {
		if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
			throw new Error("WebSocket이 연결되지 않았습니다");
		}

		const id = ++this.messageId;
		const message: DevToolsMessage = { id, method, params };

		return new Promise((resolve, reject) => {
			const timeout = setTimeout(() => {
				reject(new Error(`명령 타임아웃: ${method}`));
			}, 5000);

			const messageHandler = (data: WebSocket.Data) => {
				try {
					const response = JSON.parse(data.toString()) as DevToolsMessage;

					if (response.id === id) {
						clearTimeout(timeout);
						this.ws?.off("message", messageHandler);

						if (response.error) {
							reject(
								new Error(`DevTools 오류: ${JSON.stringify(response.error)}`),
							);
						} else {
							resolve(response.result);
						}
					}
				} catch (error) {
					// 다른 메시지는 무시
				}
			};

			this.ws?.on("message", messageHandler);
			this.ws?.send(JSON.stringify(message));
		});
	}

	/**
	 * Console 메시지 리스너 등록
	 */
	onConsoleMessage(callback: (message: ConsoleMessage) => void): void {
		if (!this.ws) {
			throw new Error("WebSocket이 연결되지 않았습니다");
		}

		this.ws.on("message", (data) => {
			try {
				const message = JSON.parse(data.toString()) as DevToolsMessage;

				if (message.method === "Runtime.consoleAPICalled" && message.params) {
					callback(message.params as unknown as ConsoleMessage);
				}
			} catch (error) {
				// JSON 파싱 오류는 무시
			}
		});
	}

	/**
	 * Exception 리스너 등록
	 */
	onException(callback: (exception: ExceptionDetails) => void): void {
		if (!this.ws) {
			throw new Error("WebSocket이 연결되지 않았습니다");
		}

		this.ws.on("message", (data) => {
			try {
				const message = JSON.parse(data.toString()) as DevToolsMessage;

				if (message.method === "Runtime.exceptionThrown") {
					const params = message.params as {
						exceptionDetails: ExceptionDetails;
					};
					callback(params.exceptionDetails);
				}
			} catch (error) {
				// JSON 파싱 오류는 무시
			}
		});
	}

	/**
	 * 마우스 클릭 수행
	 */
	async click(coordinates: ClickCoordinates): Promise<void> {
		this.logger.info(
			`🖱️  좌표 (${coordinates.x}, ${coordinates.y})를 클릭합니다...`,
		);

		// 마우스 누르기
		await this.sendCommand("Input.dispatchMouseEvent", {
			type: "mousePressed",
			x: coordinates.x,
			y: coordinates.y,
			button: "left",
			clickCount: 1,
		});

		await delay(50);

		// 마우스 떼기
		await this.sendCommand("Input.dispatchMouseEvent", {
			type: "mouseReleased",
			x: coordinates.x,
			y: coordinates.y,
			button: "left",
			clickCount: 1,
		});

		this.logger.info("✅ 클릭 완료");
	}

	/**
	 * 특정 Console 메시지를 기다리기
	 */
	async waitForConsoleMessage(
		messagePattern: string,
		timeoutMs = 30000,
	): Promise<ConsoleMessage> {
		this.logger.info(`🔍 Console 메시지 대기 중: "${messagePattern}"`);

		return withTimeout(
			new Promise<ConsoleMessage>((resolve) => {
				this.onConsoleMessage((message) => {
					const text = this.extractConsoleText(message);
					this.logger.debug(`📝 Console: ${text}`);

					if (text.includes(messagePattern)) {
						this.logger.info(`🎉 메시지 감지: "${messagePattern}"`);
						resolve(message);
					}
				});
			}),
			timeoutMs,
			`Console 메시지 타임아웃: "${messagePattern}"`,
		);
	}

	/**
	 * Console 메시지에서 텍스트 추출
	 */
	private extractConsoleText(message: ConsoleMessage): string {
		if (message.text) {
			return message.text;
		}

		if (message.args && message.args.length > 0) {
			return message.args
				.map((arg) => {
					if (arg.value !== undefined) {
						return String(arg.value);
					}
					if (arg.description) {
						return arg.description;
					}
					return "[Object]";
				})
				.join(" ");
		}

		return "";
	}

	/**
	 * 연결 종료
	 */
	close(): void {
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
	}
}
