#!/usr/bin/env node

import { ChromeLauncher } from "./chrome-launcher.js";
import { ConsoleMonitor } from "./console-monitor.js";
import type { ChromeLauncherConfig, ConsoleMonitorConfig } from "./types.js";
import { ColorLogger } from "./utils.js";

/**
 * 기본 설정값
 */
const DEFAULT_CONFIG = {
	url: "http://localhost:5175",
	width: 1920,
	height: 1080,
	debugPort: 9222,
	headless: true,
	waitForMessage: "Loaded pyxel",
	clickAfterMessage: true,
	clickDelay: 1000,
};

/**
 * 명령행 인수 파싱
 */
function parseArgs(): {
	command: string;
	config: ChromeLauncherConfig | ConsoleMonitorConfig;
} {
	const args = process.argv.slice(2);
	const command = args[0] || "start";

	const config = { ...DEFAULT_CONFIG };

	// 명령행 인수 처리
	for (let i = 1; i < args.length; i += 2) {
		const key = args[i]?.replace(/^--/, "");
		const value = args[i + 1];

		if (key && value) {
			switch (key) {
				case "url":
					config.url = value;
					break;
				case "width":
					config.width = Number.parseInt(value, 10);
					break;
				case "height":
					config.height = Number.parseInt(value, 10);
					break;
				case "debug-port":
					config.debugPort = Number.parseInt(value, 10);
					break;
				case "wait-message":
					config.waitForMessage = value;
					break;
				case "click-delay":
					config.clickDelay = Number.parseInt(value, 10);
					break;
			}
		}
	}

	return { command, config };
}

/**
 * 도움말 출력
 */
function printHelp(): void {
	console.log(`
🚀 Chrome Automation Tool

사용법:
  pnpm start [command] [options]

명령어:
  start         Chrome을 시작하고 자동 클릭 수행 (기본값)
  monitor       Console 메시지 모니터링만 수행
  help          이 도움말 출력

옵션:
  --url <url>           대상 URL (기본값: http://localhost:5175)
  --width <number>      창 너비 (기본값: 1920)
  --height <number>     창 높이 (기본값: 1080)
  --debug-port <number> 디버그 포트 (기본값: 9222)
  --wait-message <text> 대기할 Console 메시지 (기본값: "Loaded pyxel")
  --click-delay <ms>    클릭 전 딜레이 (기본값: 1000)

예시:
  pnpm start
  pnpm start monitor --debug-port 9223
  pnpm start start --url http://localhost:3000 --wait-message "App ready"
`);
}

/**
 * 메인 함수
 */
async function main(): Promise<void> {
	const { command, config } = parseArgs();
	const logger = new ColorLogger();

	try {
		switch (command) {
			case "start": {
				const launcher = new ChromeLauncher(
					config as ChromeLauncherConfig,
					logger,
				);
				await launcher.start();
				break;
			}

			case "monitor": {
				const monitorConfig: ConsoleMonitorConfig = {
					debugPort: config.debugPort,
					targetUrlPattern: "localhost:5175",
					timeout: 30000,
				};
				const monitor = new ConsoleMonitor(monitorConfig, logger);
				await monitor.start();
				break;
			}

			case "help":
				printHelp();
				break;

			default:
				logger.error(`알 수 없는 명령어: ${command}`);
				printHelp();
				process.exit(1);
		}
	} catch (error) {
		logger.error(
			`실행 오류: ${error instanceof Error ? error.message : String(error)}`,
		);
		process.exit(1);
	}
}

// 메인 함수 실행
if (import.meta.url === `file://${process.argv[1]}`) {
	main().catch((error) => {
		console.error("치명적 오류:", error);
		process.exit(1);
	});
}
