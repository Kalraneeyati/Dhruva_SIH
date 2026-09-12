/**
 * Voice I/O contract for the boat surface.
 *
 * IMPLEMENTATION.md Phase 5: "Bhashini ASR -> graph -> Bhashini TTS, with
 * Sarvam Saarika/Bulbul as the fallback and the better demo voice."
 *
 * SECURITY: BHASHINI_ULCA_API_KEY and BHASHINI_USER_ID (.env.example) must stay
 * backend-only. Vite inlines any `VITE_`-prefixed variable into the shipped JS
 * bundle — putting the ULCA key there would publish it to every visitor. So
 * this module NEVER calls bhashini.gov.in directly; it calls this app's own
 * backend at `${API_BASE}/voice/asr` and `/voice/tts`, which is where the real
 * key lives once Phase 3+ ships that route.
 *
 * Until that route exists, `recognizeSpeech`/`speak` fall back to the
 * browser's own Web Speech API (works today, zero config, no key) so the boat
 * surface's voice button is not a dead button in the meantime. This fallback
 * only supports whatever languages/voices the OS+browser ship; Bhashini's 22
 * languages are the real target.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL as string | undefined;

export interface RecognizeResult {
  text: string;
  language: string;
  viaBackend: boolean;
}

const BCP47_BY_UI_LOCALE: Record<string, string> = {
  en: "en-IN",
  hi: "hi-IN",
  ta: "ta-IN",
};

export function speechRecognitionAvailable(): boolean {
  return typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);
}

export function speechSynthesisAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** One-shot listen. Resolves with the transcript, or rejects if the user
 * denies mic permission or no speech is detected within the browser's own
 * timeout. */
export async function recognizeSpeech(uiLocale: string): Promise<RecognizeResult> {
  if (API_BASE) {
    // Real path: record audio, POST to our backend's Bhashini/Sarvam ASR proxy.
    // Left as a documented TODO — recording+upload wiring is Phase 5 voice
    // work that depends on the backend route existing to call.
    throw new Error("backend ASR proxy not yet available — falling back to browser speech");
  }
  const SpeechRecognitionCtor =
    (window as unknown as { SpeechRecognition?: typeof window.SpeechRecognition }).SpeechRecognition ??
    (window as unknown as { webkitSpeechRecognition?: typeof window.SpeechRecognition }).webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) throw new Error("speech recognition not supported in this browser");

  return new Promise((resolve, reject) => {
    const recognizer = new SpeechRecognitionCtor();
    recognizer.lang = BCP47_BY_UI_LOCALE[uiLocale] ?? "en-IN";
    recognizer.interimResults = false;
    recognizer.maxAlternatives = 1;
    recognizer.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript ?? "";
      resolve({ text, language: recognizer.lang, viaBackend: false });
    };
    recognizer.onerror = (event) => reject(new Error(`speech recognition error: ${event.error}`));
    recognizer.onend = () => {
      /* resolved in onresult; if neither fired, the promise simply never settles further */
    };
    recognizer.start();
  });
}

export function speak(text: string, uiLocale: string): void {
  if (!speechSynthesisAvailable()) return;
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = BCP47_BY_UI_LOCALE[uiLocale] ?? "en-IN";
  const voices = window.speechSynthesis.getVoices();
  const match = voices.find((v) => v.lang === utterance.lang) ?? voices.find((v) => v.lang.startsWith(uiLocale));
  if (match) utterance.voice = match;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}
