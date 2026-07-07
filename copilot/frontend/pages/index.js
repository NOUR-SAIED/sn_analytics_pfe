import { useEffect, useMemo, useRef, useState } from 'react';

const API_URL = 'http://localhost:8000/api/ask';

function LoadingDots() {
	return (
		<span className="loadingDots" aria-label="Loading" role="status">
			<span />
			<span />
			<span />
		</span>
	);
}

function TracePanel({ trace }) {
	const [open, setOpen] = useState(false);

	return (
		<div className="traceWrap">
			<button
				type="button"
				className="traceToggle"
				onClick={() => setOpen((value) => !value)}
				aria-expanded={open}
			>
				<span>Show reasoning steps</span>
				<span className={`chevron ${open ? 'open' : ''}`}>⌄</span>
			</button>

			<div className={`traceBody ${open ? 'open' : ''}`}>
				<div className="traceInner">
					{trace.map((step, index) => (
						<div key={`${step.tool}-${index}`} className="traceStep">
							<div className="traceStepTop">
								<span className="traceIndex">{index + 1}</span>
								<span className="traceTool">{step.tool}</span>
							</div>
							<pre>{JSON.stringify(step.arguments, null, 2)}</pre>
							<div className="traceResult">{step.result}</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}

function ChatMessage({ message }) {
	const isUser = message.role === 'user';

	return (
		<div className={`messageRow ${isUser ? 'user' : 'assistant'}`}>
			<div className={`messageCard ${isUser ? 'userCard' : 'assistantCard'} appear`}>
				<div className="messageMeta">{isUser ? 'You' : 'Assistant'}</div>
				<div className="messageBody">
					{message.loading ? <LoadingDots /> : <div className="messageText">{message.content}</div>}
				</div>
				{!isUser && message.trace && message.trace.length > 0 ? <TracePanel trace={message.trace} /> : null}
			</div>
		</div>
	);
}

function EmptyState() {
	return (
		<div className="emptyState appear">
			<div className="emptyBadge">Enterprise AI workspace</div>
			<h1>Ask a question about your gold warehouse data.</h1>
			<p>
				The assistant will inspect table docs, reason through the schema, and return a clear answer with
				optional transparency into its steps.
			</p>
		</div>
	);
}

export default function Home() {
	const [messages, setMessages] = useState([]);
	const [input, setInput] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const bottomRef = useRef(null);
	const inputRef = useRef(null);

	const canSubmit = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
	}, [messages, isLoading]);

	useEffect(() => {
		inputRef.current?.focus();
	}, []);

	async function handleSubmit(event) {
		event.preventDefault();
		const question = input.trim();
		if (!question || isLoading) {
			return;
		}

		setInput('');
		setIsLoading(true);

		const userMessage = { role: 'user', content: question };
		const pendingMessageId = Date.now();

		setMessages((current) => [
			...current,
			userMessage,
			{ id: pendingMessageId, role: 'assistant', content: 'Thinking…', loading: true, trace: [] },
		]);

		try {
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ question }),
			});

			const data = await response.json().catch(() => ({}));
			const nextContent = data?.answer || data?.error || 'No answer was returned.';
			const trace = Array.isArray(data?.trace) ? data.trace : [];

			setMessages((current) =>
				current.map((message) =>
					message.id === pendingMessageId
						? { ...message, content: nextContent, loading: false, trace }
						: message,
				),
			);
		} catch (error) {
			const fallback = error instanceof Error ? error.message : 'Unable to reach the assistant service.';
			setMessages((current) =>
				current.map((message) =>
					message.id === pendingMessageId
						? { ...message, content: fallback, loading: false, trace: [] }
						: message,
				),
			);
		} finally {
			setIsLoading(false);
		}
	}

	return (
		<div className="shell">
			<div className="ambient ambientOne" />
			<div className="ambient ambientTwo" />

			<main className="appFrame">
				<section className="chatCard">
					<header className="topBar">
						<div>
							<div className="eyebrow">Copilot Assistant</div>
							<h2>Focused workspace for gold-layer analysis</h2>
						</div>
						<div className="statusPill">
							<span className={`statusDot ${isLoading ? 'active' : ''}`} />
							<span>{isLoading ? 'Working' : 'Ready'}</span>
						</div>
					</header>

					<div className="conversation">
						{messages.length === 0 ? (
							<EmptyState />
						) : (
							<div className="messageList">
								{messages.map((message) => (
									<ChatMessage key={message.id || `${message.role}-${message.content}`} message={message} />
								))}
							</div>
						)}
						<div ref={bottomRef} />
					</div>
				</section>

				<div className="composerDock">
					<form className="composer" onSubmit={handleSubmit}>
						<textarea
							ref={inputRef}
							className="composerInput"
							value={input}
							onChange={(event) => setInput(event.target.value)}
							placeholder="Ask about case trends, SLA breaches, teams, or any gold table field…"
							rows={1}
							disabled={isLoading}
						/>
						<button className="sendButton" type="submit" disabled={!canSubmit}>
							{isLoading ? <LoadingDots /> : 'Send'}
						</button>
					</form>
				</div>
			</main>

			<style jsx global>{`
				:root {
					color-scheme: light;
					--bg: #eef2f7;
					--panel: rgba(255, 255, 255, 0.72);
					--panel-strong: rgba(255, 255, 255, 0.9);
					--border: rgba(15, 23, 42, 0.08);
					--text: #101828;
					--muted: #667085;
					--accent: #2a6df4;
					--accent-strong: #1d4ed8;
					--shadow: 0 24px 80px rgba(15, 23, 42, 0.12);
				}

				* {
					box-sizing: border-box;
				}

				html,
				body,
				#__next {
					width: 100%;
					height: 100%;
					margin: 0;
				}

				body {
					font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
					background:
						radial-gradient(circle at top left, rgba(42, 109, 244, 0.14), transparent 30%),
						radial-gradient(circle at bottom right, rgba(14, 165, 233, 0.16), transparent 28%),
						linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
					color: var(--text);
				}

				button,
				textarea {
					font: inherit;
				}

				textarea {
					resize: none;
				}

				.shell {
					position: relative;
					min-height: 100vh;
					overflow: hidden;
				}

				.ambient {
					position: absolute;
					border-radius: 999px;
					filter: blur(18px);
					opacity: 0.85;
					pointer-events: none;
				}

				.ambientOne {
					top: 4rem;
					left: 6rem;
					width: 18rem;
					height: 18rem;
					background: rgba(59, 130, 246, 0.12);
				}

				.ambientTwo {
					right: 5rem;
					bottom: 6rem;
					width: 16rem;
					height: 16rem;
					background: rgba(99, 102, 241, 0.12);
				}

				.appFrame {
					position: relative;
					z-index: 1;
					height: 100vh;
					width: min(100%, 1120px);
					margin: 0 auto;
					padding: 24px 20px 132px;
				}

				.chatCard {
					height: 100%;
					display: flex;
					flex-direction: column;
					gap: 16px;
					padding: 20px;
					border: 1px solid var(--border);
					border-radius: 28px;
					background: var(--panel);
					backdrop-filter: blur(20px);
					box-shadow: var(--shadow);
				}

				.topBar {
					display: flex;
					align-items: center;
					justify-content: space-between;
					gap: 16px;
					padding: 4px 2px 10px;
				}

				.eyebrow {
					font-size: 12px;
					font-weight: 700;
					letter-spacing: 0.12em;
					text-transform: uppercase;
					color: var(--accent);
				}

				h2 {
					margin: 4px 0 0;
					font-size: clamp(1.15rem, 2vw, 1.55rem);
					line-height: 1.2;
				}

				.statusPill {
					display: inline-flex;
					align-items: center;
					gap: 10px;
					padding: 10px 14px;
					border: 1px solid var(--border);
					border-radius: 999px;
					background: rgba(255, 255, 255, 0.65);
					color: var(--muted);
					font-size: 0.92rem;
					white-space: nowrap;
				}

				.statusDot {
					width: 10px;
					height: 10px;
					border-radius: 999px;
					background: #94a3b8;
					box-shadow: 0 0 0 0 rgba(42, 109, 244, 0.26);
				}

				.statusDot.active {
					background: var(--accent);
					animation: pulse 1.5s infinite;
				}

				.conversation {
					position: relative;
					flex: 1;
					overflow-y: auto;
					padding: 6px 4px 18px;
					scroll-behavior: smooth;
				}

				.messageList {
					display: flex;
					flex-direction: column;
					gap: 14px;
				}

				.messageRow {
					display: flex;
				}

				.messageRow.user {
					justify-content: flex-end;
				}

				.messageRow.assistant {
					justify-content: flex-start;
				}

				.messageCard {
					width: min(100%, 760px);
					border: 1px solid var(--border);
					border-radius: 24px;
					padding: 16px 18px;
					box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
					transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
				}

				.messageCard:hover {
					transform: translateY(-1px);
					box-shadow: 0 14px 40px rgba(15, 23, 42, 0.08);
				}

				.assistantCard {
					background: rgba(255, 255, 255, 0.82);
				}

				.userCard {
					background: linear-gradient(135deg, rgba(42, 109, 244, 0.12), rgba(59, 130, 246, 0.18));
				}

				.messageMeta {
					font-size: 0.78rem;
					font-weight: 700;
					letter-spacing: 0.06em;
					text-transform: uppercase;
					color: var(--muted);
					margin-bottom: 10px;
				}

				.messageBody {
					font-size: 1rem;
					line-height: 1.7;
					color: var(--text);
					white-space: pre-wrap;
					word-break: break-word;
				}

				.messageText {
					animation: fadeUp 220ms ease;
				}

				.emptyState {
					max-width: 720px;
					margin: auto;
					display: grid;
					gap: 14px;
					justify-items: start;
					padding: 36px 8px 12px;
				}

				.emptyBadge {
					display: inline-flex;
					align-items: center;
					gap: 8px;
					padding: 8px 12px;
					border-radius: 999px;
					background: rgba(42, 109, 244, 0.1);
					color: var(--accent-strong);
					font-size: 0.85rem;
					font-weight: 700;
					border: 1px solid rgba(42, 109, 244, 0.16);
				}

				.emptyState h1 {
					margin: 0;
					font-size: clamp(2rem, 4vw, 3.4rem);
					line-height: 1.05;
					letter-spacing: -0.04em;
					max-width: 12ch;
				}

				.emptyState p {
					margin: 0;
					max-width: 62ch;
					color: var(--muted);
					font-size: 1.02rem;
					line-height: 1.8;
				}

				.traceWrap {
					margin-top: 16px;
					border-top: 1px solid rgba(148, 163, 184, 0.2);
					padding-top: 12px;
				}

				.traceToggle {
					width: 100%;
					display: flex;
					align-items: center;
					justify-content: space-between;
					gap: 12px;
					border: 0;
					background: transparent;
					padding: 0;
					color: var(--muted);
					cursor: pointer;
					font-size: 0.92rem;
					font-weight: 600;
				}

				.chevron {
					display: inline-block;
					transition: transform 180ms ease;
				}

				.chevron.open {
					transform: rotate(180deg);
				}

				.traceBody {
					display: grid;
					grid-template-rows: 0fr;
					opacity: 0;
					transition: grid-template-rows 240ms ease, opacity 240ms ease;
				}

				.traceBody.open {
					grid-template-rows: 1fr;
					opacity: 1;
				}

				.traceInner {
					overflow: hidden;
					padding-top: 12px;
					display: grid;
					gap: 10px;
				}

				.traceStep {
					border-radius: 18px;
					border: 1px solid rgba(148, 163, 184, 0.16);
					background: rgba(248, 250, 252, 0.88);
					padding: 12px 14px;
				}

				.traceStepTop {
					display: flex;
					align-items: center;
					gap: 10px;
					margin-bottom: 8px;
				}

				.traceIndex {
					display: inline-flex;
					align-items: center;
					justify-content: center;
					width: 22px;
					height: 22px;
					border-radius: 999px;
					background: rgba(42, 109, 244, 0.12);
					color: var(--accent-strong);
					font-size: 0.78rem;
					font-weight: 700;
				}

				.traceTool {
					font-size: 0.86rem;
					font-weight: 700;
					color: var(--text);
				}

				.traceStep pre {
					margin: 0;
					overflow-x: auto;
					white-space: pre-wrap;
					word-break: break-word;
					font-size: 0.82rem;
					line-height: 1.6;
					color: #475467;
				}

				.traceResult {
					margin-top: 8px;
					font-size: 0.86rem;
					line-height: 1.6;
					color: #344054;
					white-space: pre-wrap;
					word-break: break-word;
				}

				.composerDock {
					position: fixed;
					left: 0;
					right: 0;
					bottom: 0;
					z-index: 10;
					padding: 0 20px 20px;
					pointer-events: none;
				}

				.composer {
					pointer-events: auto;
					width: min(100%, 1120px);
					margin: 0 auto;
					display: flex;
					gap: 12px;
					align-items: flex-end;
					padding: 14px;
					border-radius: 24px;
					border: 1px solid rgba(255, 255, 255, 0.7);
					background: rgba(255, 255, 255, 0.76);
					backdrop-filter: blur(20px);
					box-shadow: 0 -14px 40px rgba(15, 23, 42, 0.08);
				}

				.composerInput {
					flex: 1;
					min-height: 54px;
					max-height: 180px;
					padding: 16px 18px;
					border: 1px solid rgba(148, 163, 184, 0.18);
					border-radius: 18px;
					background: rgba(255, 255, 255, 0.92);
					color: var(--text);
					outline: none;
					box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
					transition: border-color 180ms ease, box-shadow 180ms ease;
				}

				.composerInput::placeholder {
					color: #98a2b3;
				}

				.composerInput:focus {
					border-color: rgba(42, 109, 244, 0.34);
					box-shadow: 0 0 0 4px rgba(42, 109, 244, 0.08);
				}

				.composerInput:disabled {
					background: #f8fafc;
					color: #98a2b3;
					cursor: not-allowed;
				}

				.sendButton {
					min-width: 110px;
					height: 54px;
					padding: 0 18px;
					border: 0;
					border-radius: 18px;
					background: linear-gradient(135deg, var(--accent), var(--accent-strong));
					color: white;
					font-weight: 700;
					letter-spacing: 0.01em;
					box-shadow: 0 12px 24px rgba(42, 109, 244, 0.24);
					cursor: pointer;
					transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
				}

				.sendButton:hover:not(:disabled) {
					transform: translateY(-1px);
					box-shadow: 0 16px 30px rgba(42, 109, 244, 0.28);
				}

				.sendButton:disabled {
					opacity: 0.6;
					cursor: not-allowed;
					box-shadow: none;
				}

				.appear {
					animation: fadeUp 220ms ease;
				}

				.loadingDots {
					display: inline-flex;
					gap: 6px;
					align-items: center;
					min-height: 18px;
				}

				.loadingDots span {
					width: 8px;
					height: 8px;
					border-radius: 50%;
					background: currentColor;
					opacity: 0.35;
					animation: bounce 1.1s infinite ease-in-out;
				}

				.loadingDots span:nth-child(2) {
					animation-delay: 0.15s;
				}

				.loadingDots span:nth-child(3) {
					animation-delay: 0.3s;
				}

				@keyframes fadeUp {
					from {
						opacity: 0;
						transform: translateY(8px);
					}
					to {
						opacity: 1;
						transform: translateY(0);
					}
				}

				@keyframes bounce {
					0%,
					80%,
					100% {
						transform: translateY(0);
						opacity: 0.35;
					}
					40% {
						transform: translateY(-4px);
						opacity: 1;
					}
				}

				@keyframes pulse {
					0% {
						box-shadow: 0 0 0 0 rgba(42, 109, 244, 0.28);
					}
					70% {
						box-shadow: 0 0 0 8px rgba(42, 109, 244, 0);
					}
					100% {
						box-shadow: 0 0 0 0 rgba(42, 109, 244, 0);
					}
				}

				@media (max-width: 768px) {
					.appFrame {
						padding: 16px 14px 122px;
					}

					.chatCard {
						padding: 16px;
						border-radius: 24px;
					}

					.topBar {
						flex-direction: column;
						align-items: flex-start;
					}

					.composerDock {
						padding: 0 14px 14px;
					}

					.composer {
						padding: 12px;
						border-radius: 20px;
						flex-direction: column;
						align-items: stretch;
					}

					.sendButton {
						width: 100%;
					}

					.messageCard {
						width: 100%;
					}

					.emptyState h1 {
						font-size: clamp(1.8rem, 9vw, 2.6rem);
					}
				}
			`}</style>
		</div>
	);
}
