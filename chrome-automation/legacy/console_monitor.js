const WebSocket = require("ws");

// 명령행 인수 처리
const debugPort = process.argv[2] || "9222";
const targetUrl = process.argv[3] || "localhost:5175";

console.log("🔍 Chrome DevTools Console Monitor");
console.log(`📍 디버그 포트: ${debugPort}`);
console.log(`🎯 대상 URL 패턴: ${targetUrl}`);
console.log("");

// 색상 정의
const colors = {
	reset: "\x1b[0m",
	bright: "\x1b[1m",
	red: "\x1b[31m",
	green: "\x1b[32m",
	yellow: "\x1b[33m",
	blue: "\x1b[34m",
	magenta: "\x1b[35m",
	cyan: "\x1b[36m",
	gray: "\x1b[90m",
};

// 로그 레벨별 색상 매핑
const levelColors = {
	log: colors.gray,
	info: colors.blue,
	warn: colors.yellow,
	error: colors.red,
	debug: colors.magenta,
	verbose: colors.cyan,
};

// 타임스탬프 생성
function getTimestamp() {
	const now = new Date();
	return `${colors.gray}[${now.toLocaleTimeString()}]${colors.reset}`;
}

// Console 메시지 포맷팅
function formatConsoleMessage(message) {
	const timestamp = getTimestamp();
	const level = message.level || "log";
	const color = levelColors[level] || colors.gray;
	const levelTag = `${color}[${level.toUpperCase()}]${colors.reset}`;

	// 메시지 텍스트 추출
	let text = "";
	if (message.text) {
		text = message.text;
	} else if (message.args && message.args.length > 0) {
		text = message.args
			.map((arg) => {
				if (arg.value !== undefined) {
					return arg.value;
				} else if (arg.description) {
					return arg.description;
				} else if (arg.preview && arg.preview.description) {
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
		source = `${colors.gray}(${filename}:${message.line})${colors.reset}`;
	}

	return `${timestamp} ${levelTag} ${text} ${source}`;
}

// 탭 정보 가져오기
async function getTabs() {
	try {
		const response = await fetch(`http://localhost:${debugPort}/json`);
		const tabs = await response.json();
		return tabs;
	} catch (error) {
		console.error(`❌ 탭 정보를 가져올 수 없습니다: ${error.message}`);
		process.exit(1);
	}
}

// 대상 탭 찾기
function findTargetTab(tabs, urlPattern) {
	// 우선순위별 검색
	let targetTab = tabs.find((tab) => tab.url && tab.url.includes(urlPattern));

	if (!targetTab) {
		targetTab = tabs.find(
			(tab) =>
				tab.type === "page" && !tab.url.startsWith("chrome-extension://"),
		);
	}

	if (!targetTab) {
		targetTab = tabs.find((tab) => tab.type === "page");
	}

	return targetTab;
}

// WebSocket 연결 및 Console 모니터링
function connectToTab(tab) {
	console.log(`🔗 연결 중: ${tab.title || "Unknown"}`);
	console.log(`📄 URL: ${tab.url}`);
	console.log(`🆔 Tab ID: ${tab.id}`);
	console.log("");

	const ws = new WebSocket(tab.webSocketDebuggerUrl);

	ws.on("open", function () {
		console.log(`${colors.green}✅ WebSocket 연결 성공${colors.reset}`);
		console.log(
			`${colors.blue}📺 Console 메시지 모니터링 시작...${colors.reset}`,
		);
		console.log("");

		// Runtime 도메인 활성화 (Console 이벤트를 위해 필요)
		ws.send(
			JSON.stringify({
				id: 1,
				method: "Runtime.enable",
			}),
		);

		// Console 도메인 활성화
		ws.send(
			JSON.stringify({
				id: 2,
				method: "Console.enable",
			}),
		);

		// Log 도메인 활성화 (추가 로그 이벤트)
		ws.send(
			JSON.stringify({
				id: 3,
				method: "Log.enable",
			}),
		);
	});

	ws.on("message", function (data) {
		try {
			const message = JSON.parse(data);

			// Console API 호출 이벤트
			if (message.method === "Runtime.consoleAPICalled") {
				const consoleMessage = message.params;
				console.log(formatConsoleMessage(consoleMessage));
			}

			// Exception 이벤트
			else if (message.method === "Runtime.exceptionThrown") {
				const exception = message.params.exceptionDetails;
				const timestamp = getTimestamp();
				console.log(
					`${timestamp} ${colors.red}[EXCEPTION]${colors.reset} ${exception.text}`,
				);
				if (exception.stackTrace) {
					exception.stackTrace.callFrames.forEach((frame, index) => {
						if (index < 3) {
							// 상위 3개 프레임만 표시
							console.log(
								`${colors.gray}    at ${frame.functionName || "<anonymous>"} (${frame.url}:${frame.lineNumber})${colors.reset}`,
							);
						}
					});
				}
			}

			// Log 엔트리 이벤트
			else if (message.method === "Log.entryAdded") {
				const entry = message.params.entry;
				const timestamp = getTimestamp();
				const level = entry.level || "info";
				const color = levelColors[level] || colors.gray;
				console.log(
					`${timestamp} ${color}[${level.toUpperCase()}]${colors.reset} ${entry.text}`,
				);
			}
		} catch (error) {
			console.error(`❌ 메시지 파싱 오류: ${error.message}`);
		}
	});

	ws.on("error", function (error) {
		console.error(
			`${colors.red}❌ WebSocket 오류: ${error.message}${colors.reset}`,
		);
	});

	ws.on("close", function () {
		console.log(
			`${colors.yellow}⚠️  WebSocket 연결이 종료되었습니다${colors.reset}`,
		);
		console.log("재연결을 시도합니다...");
		setTimeout(() => {
			connectToTab(tab);
		}, 2000);
	});

	// 종료 시그널 처리
	process.on("SIGINT", function () {
		console.log(
			`\n${colors.yellow}🛑 Console 모니터링을 종료합니다...${colors.reset}`,
		);
		ws.close();
		process.exit(0);
	});
}

// 메인 실행
async function main() {
	try {
		const tabs = await getTabs();
		const targetTab = findTargetTab(tabs, targetUrl);

		if (!targetTab) {
			console.error(`❌ 대상 탭을 찾을 수 없습니다. 패턴: ${targetUrl}`);
			console.log("\n📋 사용 가능한 탭들:");
			tabs.forEach((tab) => {
				if (tab.type === "page") {
					console.log(`  - ${tab.title} (${tab.url})`);
				}
			});
			process.exit(1);
		}

		connectToTab(targetTab);
	} catch (error) {
		console.error(`❌ 초기화 오류: ${error.message}`);
		process.exit(1);
	}
}

// fetch polyfill for older Node.js versions
if (typeof fetch === "undefined") {
	global.fetch = require("node-fetch");
}

main();
