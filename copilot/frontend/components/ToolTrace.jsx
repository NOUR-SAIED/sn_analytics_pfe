import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from './ui/accordion';
import { Badge } from './ui/badge';
import { ResultView } from './ResultTable';

// Plain-English gloss for each tool - the trace is a lot more useful mid-run
// (and a lot more "look, it's actually doing something") when it reads as a
// sentence instead of a bare function name.
const TOOL_LABELS = {
  list_cube_metrics: 'Checking which metrics are available',
  run_cube_query: 'Querying the semantic layer',
  list_tables: 'Looking up table schemas',
  describe_table: 'Reading a table definition',
  sample_values: 'Sampling column values',
  run_sql: 'Running a direct SQL query',
};

function stepLabel(tool) {
  return TOOL_LABELS[tool] || tool;
}

export function ToolTrace({ trace, loading }) {
  // Auto-open while the agent is actively working - a collapsed accordion
  // behind 3 static dots for 30-90s (this model's real latency on local
  // hardware, see copilot/backend/config.py) reads as "frozen", not "busy".
  // Snapping closed the one time `loading` flips false->true->false keeps
  // finished messages tidy without fighting the user's own manual toggling
  // afterward - `loading` doesn't change again after that transition.
  const [open, setOpen] = useState(!!loading);
  useEffect(() => {
    setOpen(!!loading);
  }, [loading]);

  if (!trace || trace.length === 0) return null;

  const isRunning = trace.some((step) => step.result === 'Running…');

  return (
    <Accordion
      type="single"
      collapsible
      value={open ? 'trace' : ''}
      onValueChange={(v) => setOpen(v === 'trace')}
      className="mt-3 border-t border-border pt-1"
    >
      <AccordionItem value="trace">
        <AccordionTrigger className="text-xs">
          <span className="flex items-center gap-2">
            {loading && isRunning ? (
              <Loader2 className="h-3 w-3 animate-spin text-primary" />
            ) : null}
            <span>{loading ? stepLabel(trace[trace.length - 1]?.tool) : 'Reasoning steps'}</span>
            <Badge variant="secondary">{trace.length}</Badge>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="flex flex-col gap-3">
            {trace.map((step, index) => (
              <div key={`${step.tool}-${index}`} className="rounded-lg border border-border bg-muted/30 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant="outline">{index + 1}</Badge>
                  <span className="text-xs font-semibold">{stepLabel(step.tool)}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">{step.tool}</span>
                  {step.result === 'Running…' ? (
                    <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                  ) : null}
                </div>
                {step.arguments && Object.keys(step.arguments).length > 0 ? (
                  <pre className="mb-2 whitespace-pre-wrap break-words rounded-md bg-background/60 p-2 text-[11px] text-muted-foreground">
                    {JSON.stringify(step.arguments, null, 2)}
                  </pre>
                ) : null}
                {step.result === 'Running…' ? (
                  <p className="text-[11px] text-muted-foreground">Waiting for a result…</p>
                ) : (
                  <ResultView result={step.result} />
                )}
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
