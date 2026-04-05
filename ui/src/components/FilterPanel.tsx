'use client';

/**
 * FilterPanel — vertical checkbox list of all 9 supported acts.
 * Calls onChange with the array of currently selected act codes.
 */

import { useState } from 'react';

const ACT_OPTIONS = [
  { code: 'ipc', name: 'Indian Penal Code 1860' },
  { code: 'bns', name: 'Bharatiya Nyaya Sanhita 2023' },
  { code: 'crpc', name: 'Code of Criminal Procedure 1973' },
  { code: 'cpc', name: 'Code of Civil Procedure 1908' },
  { code: 'iea', name: 'Indian Evidence Act 1872' },
  { code: 'hma', name: 'Hindu Marriage Act 1955' },
  { code: 'ida', name: 'Indian Divorce Act 1869' },
  { code: 'mva', name: 'Motor Vehicles Act 1988' },
  { code: 'nia', name: 'NIA Act 2008' },
];

interface Props {
  onChange: (selectedCodes: string[]) => void;
}

export default function FilterPanel({ onChange }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  function toggle(code: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(code) ? next.delete(code) : next.add(code);
      onChange(Array.from(next));
      return next;
    });
  }

  return (
    <aside className="space-y-2">
      <p className="text-xs font-sans font-semibold text-gray-500 uppercase tracking-wide">
        Filter by Act
      </p>
      <ul className="space-y-1.5">
        {ACT_OPTIONS.map(({ code, name }) => (
          <li key={code}>
            <label className="flex items-center gap-2 cursor-pointer text-sm font-sans text-ink hover:text-amber-800">
              <input
                type="checkbox"
                checked={selected.has(code)}
                onChange={() => toggle(code)}
                className="rounded border-gray-300 text-amber-700 focus:ring-amber-700"
              />
              <span>{name}</span>
            </label>
          </li>
        ))}
      </ul>
      {selected.size > 0 && (
        <button
          onClick={() => { setSelected(new Set()); onChange([]); }}
          className="mt-2 text-xs text-gray-400 hover:text-gray-600 underline font-sans"
        >
          Clear filters
        </button>
      )}
    </aside>
  );
}
