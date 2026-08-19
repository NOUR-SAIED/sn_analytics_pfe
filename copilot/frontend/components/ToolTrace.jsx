import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from './ui/accordion';
import { Badge } from './ui/badge';
import { ResultView } from './ResultTable';

export function ToolTrace({ trace }) {
  if (!trace || trace.length === 0) return null;

  return (
    <Accordion type="single" collapsible className="mt-3 border-t border-border pt-1">
      <AccordionItem value="trace">
        <AccordionTrigger className="text-xs">
          <span className="flex items-center gap-2">
            <span>Reasoning steps</span>
            <Badge variant="secondary">{trace.length}</Badge>
          </span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="flex flex-col gap-3">
            {trace.map((step, index) => (
              <div key={`${step.tool}-${index}`} className="rounded-lg border border-border bg-muted/30 p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Badge variant="outline">{index + 1}</Badge>
                  <span className="text-xs font-semibold">{step.tool}</span>
                </div>
                {step.arguments && Object.keys(step.arguments).length > 0 ? (
                  <pre className="mb-2 whitespace-pre-wrap break-words rounded-md bg-background/60 p-2 text-[11px] text-muted-foreground">
                    {JSON.stringify(step.arguments, null, 2)}
                  </pre>
                ) : null}
                <ResultView result={step.result} />
              </div>
            ))}
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
