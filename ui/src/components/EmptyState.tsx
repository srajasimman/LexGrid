'use client';

interface Props {
  onSuggestion: (query: string) => void;
}

const SUGGESTIONS = [
  'What is Section 302 IPC?',
  'Bail conditions under CrPC Section 437',
  'Grounds for divorce under HMA',
  'What is culpable homicide under BNS?',
];

export default function EmptyState({ onSuggestion }: Props) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center gap-8">
      <div>
        <h1 className="font-serif text-4xl font-medium text-ink leading-tight">LexGrid</h1>
        <p className="mt-2 text-olive-gray font-sans text-base">
          Ask anything about Indian Bare Acts
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3 max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="px-4 py-2 bg-ivory border border-warm-sand rounded-2xl text-sm font-sans text-olive-gray hover:bg-warm-sand hover:text-ink transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
