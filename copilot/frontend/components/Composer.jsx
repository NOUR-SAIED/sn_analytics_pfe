import { forwardRef } from 'react';
import { ArrowUp } from 'lucide-react';
import { Textarea } from './ui/textarea';
import { Button } from './ui/button';

export const Composer = forwardRef(function Composer({ value, onChange, onSubmit, disabled, canSubmit }, ref) {
  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmit(event);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm">
      <Textarea
        ref={ref}
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        placeholder="Ask about case trends, SLA breaches, teams, or any gold table field…"
        rows={1}
        disabled={disabled}
        className="max-h-40 min-h-[44px] flex-1 border-0 shadow-none focus-visible:ring-0"
      />
      <Button type="submit" size="icon" disabled={!canSubmit} className="mb-1" aria-label="Send message">
        <ArrowUp className="h-4 w-4" />
      </Button>
    </form>
  );
});
