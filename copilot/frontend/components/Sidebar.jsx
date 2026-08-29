import { useState } from 'react';
import { Menu, MessageSquare, Plus } from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Separator } from './ui/separator';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { cn } from '../lib/utils';

function Brand() {
  return (
    <div className="flex items-center gap-2 px-1 pb-4">
      <div
        className="flex h-8 w-8 items-center justify-center rounded-lg font-bold text-primary-foreground shadow-sm"
        style={{ background: 'linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary) / 0.72))' }}
        aria-hidden="true"
      >
        P
      </div>
      <div>
        <p className="text-sm font-semibold leading-none">SN Analytics</p>
        <p className="text-xs text-muted-foreground">Parking Ops Copilot</p>
      </div>
    </div>
  );
}

function ConversationList({ conversations, activeId, onSelect }) {
  if (conversations.length === 0) {
    return <p className="px-2 py-4 text-xs text-muted-foreground">No conversations yet.</p>;
  }

  return (
    <div className="flex flex-col gap-1">
      {conversations.map((conv) => (
        <button
          key={conv.threadId}
          type="button"
          onClick={() => onSelect(conv.threadId)}
          className={cn(
            'flex items-center gap-2 rounded-lg px-2 py-2 text-left text-sm transition-colors hover:bg-accent',
            conv.threadId === activeId ? 'bg-accent text-accent-foreground' : 'text-muted-foreground',
          )}
        >
          <MessageSquare className="h-3.5 w-3.5 shrink-0" />
          {/* min-w-0 is load-bearing here: a flex item's default min-width
              is "auto" (= its content's full width for nowrap text), which
              silently overrides truncate's overflow-hidden and lets the
              button - and the whole aside up the tree - stretch past the
              sidebar's actual w-72 instead of clipping with an ellipsis. */}
          <span className="min-w-0 flex-1 truncate">{conv.title}</span>
        </button>
      ))}
    </div>
  );
}

function SidebarBody({ conversations, activeId, onSelect, onNewChat }) {
  return (
    // w-full + min-w-0: `aside` is a row-direction flex container, and this
    // div is its only child - without an explicit width, a flex item's
    // default min-width is "auto" (its content's own natural size), so once
    // the ScrollArea fix let content genuinely shrink, this div started
    // sizing itself off whatever was smallest inside it instead of filling
    // the sidebar. Same underlying bug, one level up the tree.
    <div className="flex h-full w-full min-w-0 flex-col">
      <Brand />
      <Button onClick={onNewChat} variant="secondary" className="mb-3 justify-start gap-2">
        <Plus className="h-4 w-4" />
        New chat
      </Button>
      <Separator className="mb-2" />
      <ScrollArea className="-mx-1 flex-1 px-1">
        <ConversationList conversations={conversations} activeId={activeId} onSelect={onSelect} />
      </ScrollArea>
    </div>
  );
}

export function Sidebar({ conversations, activeId, onSelect, onNewChat }) {
  return (
    <aside className="hidden w-72 shrink-0 border-r border-border bg-card p-4 md:flex">
      <SidebarBody conversations={conversations} activeId={activeId} onSelect={onSelect} onNewChat={onNewChat} />
    </aside>
  );
}

export function MobileSidebar({ conversations, activeId, onSelect, onNewChat }) {
  const [open, setOpen] = useState(false);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open conversations">
          <Menu className="h-4 w-4" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="p-4">
        <SidebarBody
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => {
            onSelect(id);
            setOpen(false);
          }}
          onNewChat={() => {
            onNewChat();
            setOpen(false);
          }}
        />
      </SheetContent>
    </Sheet>
  );
}
