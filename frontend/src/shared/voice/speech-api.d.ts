/**
 * Minimal ambient types for the Web Speech API, which TypeScript's DOM lib
 * does not ship (it is still a non-standard, browser-vendor API). Only the
 * surface speech.ts actually uses.
 */
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognitionResultEvent extends Event {
  results: { [index: number]: { [index: number]: { transcript: string } } };
}

interface SpeechRecognition extends EventTarget {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionResultEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

interface Window {
  SpeechRecognition?: { new (): SpeechRecognition };
  webkitSpeechRecognition?: { new (): SpeechRecognition };
}
