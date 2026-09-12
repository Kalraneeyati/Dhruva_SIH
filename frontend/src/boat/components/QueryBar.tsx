import { useState } from "react";
import { useLocale } from "../../shared/hooks/useLocale";
import { recognizeSpeech, speechRecognitionAvailable } from "../../shared/voice/speech";
import { EXAMPLE_QUERIES } from "../../shared/api/mock";

interface QueryBarProps {
  onSubmit: (text: string) => void;
  busy: boolean;
}

export function QueryBar({ onSubmit, busy }: QueryBarProps) {
  const { locale, t } = useLocale();
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);

  const submit = (value: string) => {
    if (!value.trim()) return;
    onSubmit(value.trim());
  };

  const handleMic = async () => {
    setListening(true);
    try {
      const result = await recognizeSpeech(locale);
      setText(result.text);
      submit(result.text);
    } catch {
      // Mic denied, unsupported, or backend proxy not wired yet — the text
      // box remains fully usable, so this is a silent no-op rather than an
      // error banner over a non-critical feature.
    } finally {
      setListening(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(text);
        }}
        style={{ display: "flex", gap: "var(--space-2)" }}
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t("askPlaceholder")}
          style={{
            flex: 1,
            minHeight: "var(--touch-target)",
            padding: "0 var(--space-4)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--color-border)",
            background: "var(--color-surface-raised)",
            color: "var(--color-text)",
          }}
        />
        {speechRecognitionAvailable() && (
          <button
            type="button"
            onClick={handleMic}
            aria-label={t("speak")}
            style={{
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              background: listening ? "var(--color-accent)" : "var(--color-surface-raised)",
              color: listening ? "var(--color-accent-text)" : "var(--color-text)",
              fontSize: 20,
            }}
          >
            {listening ? "●" : "🎙"}
          </button>
        )}
        <button
          type="submit"
          disabled={busy}
          style={{
            borderRadius: "var(--radius-md)",
            border: "none",
            background: "var(--color-accent)",
            color: "var(--color-accent-text)",
            fontWeight: 700,
            padding: "0 var(--space-5)",
          }}
        >
          {t("ask")}
        </button>
      </form>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q.intent}
            type="button"
            onClick={() => submit(q.text)}
            style={{
              fontSize: 12,
              padding: "6px 10px",
              minHeight: 36,
              borderRadius: 999,
              border: "1px solid var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-text-muted)",
            }}
          >
            {q.text}
          </button>
        ))}
      </div>
    </div>
  );
}
