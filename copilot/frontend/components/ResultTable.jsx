import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from './ui/table';

function tryParseJson(value) {
  if (typeof value !== 'string') return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function isRowArray(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((row) => row && typeof row === 'object' && !Array.isArray(row))
  );
}

function formatCell(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function ResultView({ result }) {
  const parsed = tryParseJson(result);

  if (isRowArray(parsed)) {
    const columns = Array.from(new Set(parsed.flatMap((row) => Object.keys(row))));
    return (
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col}>{col}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {parsed.map((row, index) => (
            <TableRow key={index}>
              {columns.map((col) => (
                <TableCell key={col}>{formatCell(row[col])}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    );
  }

  if (Array.isArray(parsed) && parsed.length === 0) {
    return <p className="text-xs text-muted-foreground">No rows returned.</p>;
  }

  const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
  return (
    <pre className="whitespace-pre-wrap break-words rounded-md bg-background/60 p-2 text-[11px] leading-relaxed text-muted-foreground">
      {text}
    </pre>
  );
}
