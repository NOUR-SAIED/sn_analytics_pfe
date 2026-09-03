import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Card, CardContent } from './ui/card';
import { ToolTrace } from './ToolTrace';
import { cn } from '../lib/utils';

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 py-1 text-muted-foreground">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-current opacity-40 animate-bounce-dot"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </span>
  );
}

export function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground shadow-sm animate-fade-up">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3">
      <Avatar className="mt-0.5 h-7 w-7 bg-primary/10">
        <AvatarFallback className="bg-transparent text-[11px] text-primary">AI</AvatarFallback>
      </Avatar>
      <Card className={cn('max-w-[80%] flex-1 animate-fade-up', message.isError && 'border-destructive/40')}>
        <CardContent className="p-4">
          {message.loading && !message.content ? (
            // Once the trace has its first step, the (now auto-expanded)
            // ToolTrace below is the "something is happening" indicator -
            // showing both it and bouncing dots at once is redundant. The
            // dots only cover the brief gap before that first tool call.
            message.trace?.length ? null : <TypingDots />
          ) : (
            <div className="prose prose-sm max-w-none text-foreground dark:prose-invert prose-p:leading-relaxed prose-pre:bg-muted prose-p:my-1 prose-ul:my-1">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content || ''}</ReactMarkdown>
            </div>
          )}
          <ToolTrace trace={message.trace} loading={message.loading} />
        </CardContent>
      </Card>
    </div>
  );
}
