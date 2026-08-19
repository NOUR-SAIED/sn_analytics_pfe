import { Sparkles } from 'lucide-react';
import { Button } from './ui/button';

const SUGGESTIONS = [
  'How many cases were opened in the last 30 days?',
  'Which assignment groups have the most breached SLAs?',
  'Show me the top 10 agents by resolved case count.',
  'What is the average resolution time by priority?',
];

export function EmptyState({ onSuggestion }) {
  return (
    <div className="mx-auto flex max-w-2xl flex-1 flex-col items-center justify-center gap-6 px-4 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Sparkles className="h-6 w-6" />
      </div>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Ask a question about your gold warehouse data</h1>
        <p className="text-sm text-muted-foreground">
          The assistant inspects table docs, reasons through the schema, and returns a clear answer with full
          transparency into its steps.
        </p>
      </div>
      <div className="grid w-full gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((question) => (
          <Button
            key={question}
            variant="outline"
            className="h-auto justify-start whitespace-normal px-3 py-2.5 text-left text-sm font-normal"
            onClick={() => onSuggestion(question)}
          >
            {question}
          </Button>
        ))}
      </div>
    </div>
  );
}
