/**
 * MarkdownSourceViewer — displays canonical markdown source text
 * with lightweight markdown rendering (headings/lists/links/bold/rules).
 */

import type { ReactNode } from 'react';

interface Props {
  markdown: string;
  sourcePath?: string | null;
}

type Block =
  | { type: 'h1'; text: string }
  | { type: 'h2'; text: string }
  | { type: 'hr' }
  | { type: 'list'; items: string[] }
  | { type: 'paragraph'; text: string }
  | { type: 'meta'; items: Array<{ key: string; value: string }> };

function parseFrontmatter(lines: string[]): {
  frontmatter: Array<{ key: string; value: string }>;
  bodyStart: number;
} {
  if (lines.length < 3 || lines[0].trim() !== '---') {
    return { frontmatter: [], bodyStart: 0 };
  }

  const end = lines.findIndex((line, idx) => idx > 0 && line.trim() === '---');
  if (end === -1) {
    return { frontmatter: [], bodyStart: 0 };
  }

  const frontmatter = lines
    .slice(1, end)
    .map((line) => line.match(/^\s*([A-Za-z0-9_-]+):\s*(.*)$/))
    .filter((match): match is RegExpMatchArray => Boolean(match))
    .map((match) => ({
      key: match[1],
      value: match[2].replace(/^"|"$/g, ''),
    }));

  return { frontmatter, bodyStart: end + 1 };
}

function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const { frontmatter, bodyStart } = parseFrontmatter(lines);
  const blocks: Block[] = [];

  if (frontmatter.length > 0) {
    blocks.push({ type: 'meta', items: frontmatter });
  }

  let idx = bodyStart;
  while (idx < lines.length) {
    const line = lines[idx].trim();
    if (!line) {
      idx += 1;
      continue;
    }

    if (line === '---') {
      blocks.push({ type: 'hr' });
      idx += 1;
      continue;
    }

    if (line.startsWith('# ')) {
      blocks.push({ type: 'h1', text: line.slice(2).trim() });
      idx += 1;
      continue;
    }

    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', text: line.slice(3).trim() });
      idx += 1;
      continue;
    }

    if (line.startsWith('- ') || line.startsWith('* ')) {
      const items: string[] = [];
      while (idx < lines.length) {
        const item = lines[idx].trim();
        if (!(item.startsWith('- ') || item.startsWith('* '))) {
          break;
        }
        items.push(item.slice(2).trim());
        idx += 1;
      }
      blocks.push({ type: 'list', items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (idx < lines.length && lines[idx].trim() !== '') {
      const current = lines[idx].trim();
      if (
        current === '---' ||
        current.startsWith('# ') ||
        current.startsWith('## ') ||
        current.startsWith('- ') ||
        current.startsWith('* ')
      ) {
        break;
      }
      paragraphLines.push(current);
      idx += 1;
    }

    blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') });
  }

  return blocks;
}

function renderInline(text: string): ReactNode[] {
  const tokens = text.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^\)]+\))/g).filter(Boolean);
  return tokens.map((token, idx) => {
    if (token.startsWith('**') && token.endsWith('**')) {
      return <strong key={`strong-${idx}`}>{token.slice(2, -2)}</strong>;
    }

    const linkMatch = token.match(/^\[([^\]]+)\]\(([^\)]+)\)$/);
    if (linkMatch) {
      const [, label, href] = linkMatch;
      return (
        <a
          key={`link-${idx}`}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-emerald-700 underline hover:text-emerald-800"
        >
          {label}
        </a>
      );
    }

    return <span key={`text-${idx}`}>{token}</span>;
  });
}

export default function MarkdownSourceViewer({ markdown, sourcePath }: Props) {
  const blocks = parseBlocks(markdown);

  return (
    <article className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      <header className="px-5 py-4 bg-emerald-50 border-b border-emerald-100">
        <p className="text-xs font-sans font-semibold text-emerald-700 uppercase tracking-wide">
          Canonical Source (Markdown)
        </p>
        {sourcePath && (
          <p className="mt-1 text-xs font-mono text-emerald-700/80 break-all">
            {sourcePath}
          </p>
        )}
      </header>

      <div className="px-5 py-4 space-y-4">
        {blocks.map((block, idx) => {
          if (block.type === 'meta') {
            return (
              <dl key={`meta-${idx}`} className="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-emerald-50/60 border border-emerald-100 rounded-lg p-3">
                {block.items.map((item) => (
                  <div key={item.key} className="text-sm font-sans">
                    <dt className="inline font-semibold text-emerald-800">{item.key}: </dt>
                    <dd className="inline text-emerald-900">{item.value}</dd>
                  </div>
                ))}
              </dl>
            );
          }

          if (block.type === 'h1') {
            return (
              <h2 key={`h1-${idx}`} className="text-xl font-sans font-semibold text-ink">
                {renderInline(block.text)}
              </h2>
            );
          }

          if (block.type === 'h2') {
            return (
              <h3 key={`h2-${idx}`} className="text-lg font-sans font-semibold text-ink">
                {renderInline(block.text)}
              </h3>
            );
          }

          if (block.type === 'hr') {
            return <hr key={`hr-${idx}`} className="border-gray-200" />;
          }

          if (block.type === 'list') {
            return (
              <ul key={`list-${idx}`} className="list-disc pl-6 space-y-1 text-sm text-ink font-serif leading-relaxed">
                {block.items.map((item, itemIdx) => (
                  <li key={`li-${itemIdx}`}>{renderInline(item)}</li>
                ))}
              </ul>
            );
          }

          return (
            <p key={`p-${idx}`} className="text-sm text-ink font-serif leading-relaxed">
              {renderInline(block.text)}
            </p>
          );
        })}
      </div>
    </article>
  );
}
