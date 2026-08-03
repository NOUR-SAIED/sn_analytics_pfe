import { useEffect, useMemo, useRef, useState } from 'react';
import Head from 'next/head';
import { TooltipProvider } from '../components/ui/tooltip';
import { ScrollArea } from '../components/ui/scroll-area';
import { Sidebar, MobileSidebar } from '../components/Sidebar';
import { ChatMessage } from '../components/ChatMessage';
import { EmptyState } from '../components/EmptyState';
import { Composer } from '../components/Composer';
import { ThemeToggle } from '../components/ThemeToggle';

const API_URL = 'http://localhost:8000/api/ask';
const STORAGE_KEY = 'copilot_conversations';

function loadConversations() {
	if (typeof window === 'undefined') return [];
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		return raw ? JSON.parse(raw) : [];
	} catch {
		return [];
	}
}

function saveConversations(conversations) {
	window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

function makeThreadId() {
	return typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `thread-${Date.now()}`;
}

function titleFromQuestion(question) {
	const trimmed = question.trim();
	return trimmed.length > 48 ? `${trimmed.slice(0, 48)}…` : trimmed;
}

export default function Home() {
	const [conversations, setConversations] = useState([]);
	const [activeId, setActiveId] = useState(null);
	const [input, setInput] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const bottomRef = useRef(null);
	const textareaRef = useRef(null);

	useEffect(() => {
		const stored = loadConversations();
		setConversations(stored);
		if (stored.length > 0) {
			setActiveId(stored[0].threadId);
		}
	}, []);

	const activeConversation = useMemo(
		() => conversations.find((conv) => conv.threadId === activeId) || null,
		[conversations, activeId],
	);
	const messages = activeConversation?.messages || [];

	useEffect(() => {
		bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
	}, [messages, isLoading]);

	useEffect(() => {
		textareaRef.current?.focus();
	}, [activeId]);

	function persist(next) {
		setConversations(next);
		saveConversations(next);
	}

	function handleNewChat() {
		const threadId = makeThreadId();
		const conversation = { threadId, title: 'New conversation', messages: [], updatedAt: Date.now() };
		persist([conversation, ...conversations]);
		setActiveId(threadId);
		setInput('');
	}

	async function sendQuestion(question) {
		let threadId = activeId;

		if (!threadId) {
			threadId = makeThreadId();
			const conversation = { threadId, title: titleFromQuestion(question), messages: [], updatedAt: Date.now() };
			persist([conversation, ...conversations]);
			setActiveId(threadId);
		}

		const pendingId = `${Date.now()}`;
		const userMessage = { id: `${pendingId}-user`, role: 'user', content: question };
		const assistantMessage = { id: pendingId, role: 'assistant', content: '', loading: true, trace: [] };

		setConversations((current) => {
			const next = current.map((conv) => {
				if (conv.threadId !== threadId) return conv;
				const isFirstMessage = conv.messages.length === 0;
				return {
					...conv,
					title: isFirstMessage ? titleFromQuestion(question) : conv.title,
					messages: [...conv.messages, userMessage, assistantMessage],
					updatedAt: Date.now(),
				};
			});
			saveConversations(next);
			return next;
		});

		setIsLoading(true);

		function patchAssistant(patch) {
			setConversations((current) => {
				const next = current.map((conv) => {
					if (conv.threadId !== threadId) return conv;
					return {
						...conv,
						messages: conv.messages.map((m) => (m.id === pendingId ? { ...m, ...patch(m) } : m)),
					};
				});
				saveConversations(next);
				return next;
			});
		}

		try {
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question, thread_id: threadId }),
			});

			if (!response.body) {
				throw new Error('Streaming is not supported by this browser.');
			}

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';
			let finalAnswer = null;
			let sawError = false;

			while (true) {
				const { value, done } = await reader.read();
				if (done) break;
				buffer += decoder.decode(value, { stream: true });

				let boundary;
				while ((boundary = buffer.indexOf('\n\n')) !== -1) {
					const rawEvent = buffer.slice(0, boundary);
					buffer = buffer.slice(boundary + 2);

					const dataLine = rawEvent.split('\n').find((line) => line.startsWith('data:'));
					if (!dataLine) continue;
					const payload = JSON.parse(dataLine.slice(5).trim());

					if (payload.type === 'tool_call') {
						patchAssistant((m) => ({
							trace: [...m.trace, { tool: payload.name, arguments: payload.arguments, result: 'Running…' }],
						}));
					} else if (payload.type === 'tool_result') {
						patchAssistant((m) => {
							const trace = [...m.trace];
							for (let i = trace.length - 1; i >= 0; i -= 1) {
								if (trace[i].tool === payload.name && trace[i].result === 'Running…') {
									trace[i] = { ...trace[i], result: payload.result };
									break;
								}
							}
							return { trace };
						});
					} else if (payload.type === 'final') {
						finalAnswer = payload.answer;
					} else if (payload.type === 'error') {
						finalAnswer = payload.error;
						sawError = true;
					}
				}
			}

			patchAssistant(() => ({
				content: finalAnswer ?? 'No answer was returned.',
				loading: false,
				isError: sawError,
			}));
		} catch (error) {
			const fallback = error instanceof Error ? error.message : 'Unable to reach the assistant service.';
			patchAssistant(() => ({ content: fallback, loading: false, isError: true }));
		} finally {
			setIsLoading(false);
		}
	}

	async function handleSubmit(event) {
		event.preventDefault();
		const question = input.trim();
		if (!question || isLoading) return;
		setInput('');
		await sendQuestion(question);
	}

	const canSubmit = input.trim().length > 0 && !isLoading;

	return (
		<TooltipProvider delayDuration={200}>
			<Head>
				<title>SN Analytics Copilot</title>
			</Head>
			<div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
				<Sidebar conversations={conversations} activeId={activeId} onSelect={setActiveId} onNewChat={handleNewChat} />

				<div className="flex min-w-0 flex-1 flex-col">
					<header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
						<div className="flex items-center gap-2">
							<MobileSidebar
								conversations={conversations}
								activeId={activeId}
								onSelect={setActiveId}
								onNewChat={handleNewChat}
							/>
							<div>
								<p className="text-sm font-semibold leading-none">
									{activeConversation?.title || 'Gold-layer analysis'}
								</p>
								<p className="text-xs text-muted-foreground">Ask questions in plain English</p>
							</div>
						</div>
						<div className="flex items-center gap-2">
							<span className="inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-3 py-1 text-xs text-muted-foreground">
								<span className={`h-2 w-2 rounded-full ${isLoading ? 'animate-pulse bg-primary' : 'bg-emerald-500'}`} />
								{isLoading ? 'Working' : 'Ready'}
							</span>
							<ThemeToggle />
						</div>
					</header>

					<div className="flex flex-1 flex-col overflow-hidden">
						{messages.length === 0 ? (
							<EmptyState onSuggestion={(q) => sendQuestion(q)} />
						) : (
							<ScrollArea className="flex-1">
								<div className="mx-auto flex max-w-3xl flex-col gap-5 px-4 py-6">
									{messages.map((message) => (
										<ChatMessage key={message.id} message={message} />
									))}
									<div ref={bottomRef} />
								</div>
							</ScrollArea>
						)}
					</div>

					<div className="border-t border-border bg-background/80 p-4 backdrop-blur">
						<div className="mx-auto max-w-3xl">
							<Composer
								ref={textareaRef}
								value={input}
								onChange={(e) => setInput(e.target.value)}
								onSubmit={handleSubmit}
								disabled={isLoading}
								canSubmit={canSubmit}
							/>
						</div>
					</div>
				</div>
			</div>
		</TooltipProvider>
	);
}
