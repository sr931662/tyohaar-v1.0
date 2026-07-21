import { useEffect, useRef } from 'react';

const TOOLBAR = [
  { cmd: 'bold', label: 'B', style: { fontWeight: 700 } },
  { cmd: 'italic', label: 'I', style: { fontStyle: 'italic' } },
  { cmd: 'underline', label: 'U', style: { textDecoration: 'underline' } },
  { cmd: 'formatBlock:H1', label: 'H1' },
  { cmd: 'formatBlock:H2', label: 'H2' },
  { cmd: 'formatBlock:P', label: 'P' },
  { cmd: 'insertUnorderedList', label: '• List' },
  { cmd: 'insertOrderedList', label: '1. List' },
  { cmd: 'createLink', label: 'Link' },
  { cmd: 'removeFormat', label: 'Clear' },
];

// Dependency-free WYSIWYG editor for legal-document content (Terms, Privacy,
// Cancellation Policy). Uses contentEditable + document.execCommand rather
// than pulling in a rich-text library — the formatting needs here are basic
// (headings, bold/italic, lists, links) and this avoids a new dependency for
// what is effectively a single admin-only text field.
export default function RichTextEditor({ value, onChange, placeholder }) {
  const ref = useRef(null);
  const isInternalChange = useRef(false);

  // Only push external value changes into the DOM (e.g. switching which
  // document is being edited) — never on every keystroke, or the cursor
  // would jump to the start on each render.
  useEffect(() => {
    if (isInternalChange.current) {
      isInternalChange.current = false;
      return;
    }
    if (ref.current && ref.current.innerHTML !== (value ?? '')) {
      ref.current.innerHTML = value ?? '';
    }
  }, [value]);

  const exec = (cmd) => {
    ref.current?.focus();
    if (cmd.startsWith('formatBlock:')) {
      document.execCommand('formatBlock', false, cmd.split(':')[1]);
    } else if (cmd === 'createLink') {
      const url = window.prompt('Link URL:');
      if (url) document.execCommand('createLink', false, url);
    } else {
      document.execCommand(cmd, false, null);
    }
    handleInput();
  };

  const handleInput = () => {
    isInternalChange.current = true;
    onChange(ref.current?.innerHTML ?? '');
  };

  return (
    <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 8, overflow: 'hidden' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, padding: 6, borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-subtle)' }}>
        {TOOLBAR.map((t) => (
          <button
            key={t.label}
            type="button"
            className="btn btn-secondary btn-sm"
            style={{ padding: '2px 8px', fontSize: 12, ...(t.style ?? {}) }}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => exec(t.cmd)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={handleInput}
        data-placeholder={placeholder}
        className="rich-text-editor-content"
        style={{
          minHeight: 200,
          maxHeight: 400,
          overflowY: 'auto',
          padding: '10px 12px',
          fontSize: 13,
          lineHeight: 1.6,
          color: 'var(--text-primary)',
          outline: 'none',
        }}
      />
    </div>
  );
}
