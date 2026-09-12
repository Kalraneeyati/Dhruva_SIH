/**
 * The reason codebook. CLAUDE.md commits to 256 entries x 12 languages; this
 * seeds 24 entries x 3 languages (English, Hindi, Tamil) covering every
 * hazard/risk/PFZ/boundary combination the mock fixtures and the 8 official
 * query types actually exercise. The schema is the full-scale one — going to
 * 256x12 is content work (more rows in REASON_CODEBOOK, more locale keys per
 * row), not an architecture change. This is flagged here and in
 * frontend/README.md rather than left for someone to discover later.
 *
 * Every template is filled ONLY from the capsule's own fields — this is the
 * numeric firewall for the offline path, enforced by construction: there is no
 * free-text slot a hallucinated number could occupy. render() cannot emit a
 * number that was not already on the wire.
 */
import type { Capsule } from "../types/domain";
import { COMPASS_16_LABELS } from "./quantizers";

export type CodebookLocale = "en" | "hi" | "ta";
export const CODEBOOK_LOCALES: readonly CodebookLocale[] = ["en", "hi", "ta"];

interface CodebookEntry {
  code: number;
  category: string;
  templates: Record<CodebookLocale, string>;
}

// {slot} placeholders are resolved by render() from the capsule + its derived
// display values (see slotValues() below) — never from arbitrary text.
export const REASON_CODEBOOK: readonly CodebookEntry[] = [
  { code: 0, category: "all_clear", templates: {
    en: "Conditions are safe. Wave height {waveHs} m, wind {windKt} kt from {windDir}.",
    hi: "स्थिति सुरक्षित है। लहर की ऊँचाई {waveHs} मीटर, हवा {windKt} नॉट {windDir} दिशा से।",
    ta: "நிலைமை பாதுகாப்பானது. அலை உயரம் {waveHs} மீ, காற்று {windKt} நாட் {windDir} திசையில்.",
  }},
  { code: 1, category: "caution_wave", templates: {
    en: "Caution: wave height {waveHs} m is elevated. Small craft should stay alert.",
    hi: "सावधान: लहर की ऊँचाई {waveHs} मीटर अधिक है। छोटी नौकाएँ सतर्क रहें।",
    ta: "எச்சரிக்கை: அலை உயரம் {waveHs} மீ அதிகமாக உள்ளது. சிறு படகுகள் எச்சரிக்கையாக இருக்கவும்.",
  }},
  { code: 2, category: "caution_wind", templates: {
    en: "Caution: wind {windKt} kt from {windDir}. Expect rougher handling near shore.",
    hi: "सावधान: हवा {windKt} नॉट {windDir} दिशा से। तट के पास नाव चलाना मुश्किल हो सकता है।",
    ta: "எச்சரிக்கை: காற்று {windKt} நாட் {windDir} திசையில். கரைக்கு அருகில் படகு இயக்குவது கடினமாக இருக்கும்.",
  }},
  { code: 3, category: "caution_squall", templates: {
    en: "Caution: squall risk in the zone. Watch the horizon for sudden dark cloud lines.",
    hi: "सावधान: क्षेत्र में झोंकेदार तूफान का खतरा है। अचानक काले बादलों पर नज़र रखें।",
    ta: "எச்சரிக்கை: பகுதியில் திடீர் புயல் ஆபத்து உள்ளது. திடீர் கருமேகங்களை கவனிக்கவும்.",
  }},
  { code: 4, category: "no_go_cyclone", templates: {
    en: "NO-GO: cyclone warning active within range. Do not venture out. Return to port.",
    hi: "मत जाइए: चक्रवात चेतावनी सक्रिय है। समुद्र में न जाएँ। बंदरगाह लौट आएँ।",
    ta: "செல்ல வேண்டாம்: புயல் எச்சரிக்கை செயலில் உள்ளது. கடலுக்குச் செல்ல வேண்டாம். துறைமுகத்திற்குத் திரும்பவும்.",
  }},
  { code: 5, category: "no_go_lightning", templates: {
    en: "NO-GO: lightning risk within 50 km. Do not venture out until this clears.",
    hi: "मत जाइए: 50 किमी के भीतर बिजली गिरने का खतरा है। साफ होने तक समुद्र में न जाएँ।",
    ta: "செல்ல வேண்டாம்: 50 கிமீ சுற்றளவில் மின்னல் ஆபத்து உள்ளது. தெளிவாகும் வரை செல்ல வேண்டாம்.",
  }},
  { code: 6, category: "no_go_tsunami", templates: {
    en: "NO-GO: tsunami alert in effect. Move away from the coast immediately.",
    hi: "मत जाइए: सुनामी चेतावनी लागू है। तुरंत तट से दूर हट जाएँ।",
    ta: "செல்ல வேண்டாம்: சுனாமி எச்சரிக்கை நடைமுறையில் உள்ளது. உடனே கடற்கரையிலிருந்து விலகவும்.",
  }},
  { code: 7, category: "no_go_combined", templates: {
    en: "NO-GO: wave {waveHs} m combined with wind {windKt} kt exceeds safe limits for this boat class.",
    hi: "मत जाइए: लहर {waveHs} मीटर और हवा {windKt} नॉट मिलकर इस नाव श्रेणी की सुरक्षित सीमा से अधिक है।",
    ta: "செல்ல வேண்டாம்: அலை {waveHs} மீ மற்றும் காற்று {windKt} நாட் இணைந்து இந்த படகு வகைக்கான பாதுகாப்பு வரம்பை மீறுகிறது.",
  }},
  { code: 8, category: "caution_current", templates: {
    en: "Caution: current {currKt} kt setting toward {currDir}. Account for drift.",
    hi: "सावधान: धारा {currKt} नॉट {currDir} दिशा की ओर बह रही है। बहाव का ध्यान रखें।",
    ta: "எச்சரிக்கை: நீரோட்டம் {currKt} நாட் {currDir} திசையை நோக்கி. நகர்வை கணக்கில் கொள்ளவும்.",
  }},
  { code: 9, category: "caution_fog", templates: {
    en: "Caution: reduced visibility reported in the zone. Use navigation lights and horn signals.",
    hi: "सावधान: क्षेत्र में दृश्यता कम बताई गई है। नेविगेशन लाइट और हॉर्न का प्रयोग करें।",
    ta: "எச்சரிக்கை: பகுதியில் பார்வைத்திறன் குறைவாக உள்ளது. வழிசெலுத்தல் விளக்குகள் மற்றும் ஹாரன் பயன்படுத்தவும்.",
  }},
  { code: 10, category: "pfz_favourable", templates: {
    en: "Potential fishing zone {pfzDistNm} nm to the {pfzBearing}, confidence {pfzConf}/3.",
    hi: "संभावित मछली पकड़ने का क्षेत्र {pfzBearing} दिशा में {pfzDistNm} समुद्री मील दूर, विश्वास {pfzConf}/3।",
    ta: "சாத்தியமான மீன்பிடி மண்டலம் {pfzBearing} திசையில் {pfzDistNm} நா.மைல் தொலைவில், நம்பகத்தன்மை {pfzConf}/3.",
  }},
  { code: 11, category: "pfz_none", templates: {
    en: "No confident potential fishing zone found nearby today.",
    hi: "आज आसपास कोई विश्वसनीय संभावित मछली पकड़ने का क्षेत्र नहीं मिला।",
    ta: "இன்று அருகில் நம்பகமான மீன்பிடி மண்டலம் எதுவும் கிடைக்கவில்லை.",
  }},
  { code: 12, category: "pfz_with_caution", templates: {
    en: "PFZ {pfzDistNm} nm {pfzBearing} noted, but sea-state caution above applies first.",
    hi: "पीएफजेड {pfzBearing} दिशा में {pfzDistNm} मील पर है, लेकिन पहले ऊपर दी गई समुद्री स्थिति की चेतावनी लागू होती है।",
    ta: "PFZ {pfzBearing} திசையில் {pfzDistNm} மைல் தொலைவில் உள்ளது, ஆனால் மேலே உள்ள கடல் நிலை எச்சரிக்கை முதலில் பொருந்தும்.",
  }},
  { code: 13, category: "boundary_imbl", templates: {
    en: "Indicative IMBL line {bndDistNm} nm away, ETA {bndEta} min at current heading. Not a legal boundary reading.",
    hi: "सांकेतिक IMBL रेखा {bndDistNm} मील दूर, वर्तमान दिशा पर अनुमानित समय {bndEta} मिनट। यह कानूनी सीमा नहीं है।",
    ta: "குறிப்பிடும் IMBL கோடு {bndDistNm} மைல் தொலைவில், தற்போதைய திசையில் {bndEta} நிமிடங்களில் அடையலாம். இது சட்டப்பூர்வ எல்லை அல்ல.",
  }},
  { code: 14, category: "boundary_mpa", templates: {
    en: "Marine protected area {bndDistNm} nm away, ETA {bndEta} min. Fishing restrictions may apply.",
    hi: "समुद्री संरक्षित क्षेत्र {bndDistNm} मील दूर, अनुमानित समय {bndEta} मिनट। मछली पकड़ने पर प्रतिबंध हो सकता है।",
    ta: "கடல் பாதுகாக்கப்பட்ட பகுதி {bndDistNm} மைல் தொலைவில், {bndEta} நிமிடங்களில். மீன்பிடி கட்டுப்பாடுகள் இருக்கலாம்.",
  }},
  { code: 15, category: "boundary_closed", templates: {
    en: "Closed area {bndDistNm} nm away, ETA {bndEta} min. Entry is not permitted.",
    hi: "बंद क्षेत्र {bndDistNm} मील दूर, अनुमानित समय {bndEta} मिनट। प्रवेश की अनुमति नहीं है।",
    ta: "மூடப்பட்ட பகுதி {bndDistNm} மைல் தொலைவில், {bndEta} நிமிடங்களில். நுழைவு அனுமதிக்கப்படவில்லை.",
  }},
  { code: 16, category: "chl_high", templates: {
    en: "Chlorophyll levels are high in this zone — favourable for productivity.",
    hi: "इस क्षेत्र में क्लोरोफिल का स्तर उच्च है — उत्पादकता के लिए अनुकूल।",
    ta: "இந்த மண்டலத்தில் குளோரோபில் அளவு அதிகமாக உள்ளது — உற்பத்தித்திறனுக்கு சாதகமானது.",
  }},
  { code: 17, category: "chl_low", templates: {
    en: "Chlorophyll levels are low in this zone, consistent with reduced productivity.",
    hi: "इस क्षेत्र में क्लोरोफिल का स्तर कम है, जो घटती उत्पादकता के अनुरूप है।",
    ta: "இந்த மண்டலத்தில் குளோரோபில் அளவு குறைவாக உள்ளது, இது குறைந்த உற்பத்தித்திறனுடன் ஒத்துப்போகிறது.",
  }},
  { code: 18, category: "sst_warm_anomaly", templates: {
    en: "Sea surface temperature {sst} °C is warmer than usual for this zone.",
    hi: "समुद्र सतह तापमान {sst} °C इस क्षेत्र के लिए सामान्य से अधिक गर्म है।",
    ta: "கடல் மேற்பரப்பு வெப்பநிலை {sst} °C இந்த மண்டலத்திற்கு வழக்கத்தை விட வெப்பமானது.",
  }},
  { code: 19, category: "safe_to_venture", templates: {
    en: "Yes, it is safe to venture out. Verdict computed {dataAge} ago.",
    hi: "हाँ, समुद्र में जाना सुरक्षित है। यह निर्णय {dataAge} पहले लिया गया।",
    ta: "ஆம், கடலுக்குச் செல்வது பாதுகாப்பானது. இந்த முடிவு {dataAge} முன்பு கணக்கிடப்பட்டது.",
  }},
  { code: 20, category: "unsafe_multi_hazard", templates: {
    en: "No, conditions are unsafe: multiple hazards active. Verdict computed {dataAge} ago.",
    hi: "नहीं, स्थिति असुरक्षित है: कई खतरे सक्रिय हैं। यह निर्णय {dataAge} पहले लिया गया।",
    ta: "இல்லை, நிலைமை பாதுகாப்பற்றது: பல ஆபத்துகள் செயலில் உள்ளன. இந்த முடிவு {dataAge} முன்பு கணக்கிடப்பட்டது.",
  }},
  { code: 21, category: "route_advised", templates: {
    en: "A route avoiding the flagged hazard cells has been computed. Follow the plotted line.",
    hi: "चिह्नित खतरनाक क्षेत्रों से बचने वाला मार्ग तैयार किया गया है। अंकित रेखा का पालन करें।",
    ta: "குறிக்கப்பட்ட ஆபத்து பகுதிகளை தவிர்க்கும் பாதை கணக்கிடப்பட்டுள்ளது. வரையப்பட்ட கோட்டைப் பின்பற்றவும்.",
  }},
  { code: 22, category: "data_stale", templates: {
    en: "Note: freshest contributing reading is {dataAge} old. Treat this advisory with added caution.",
    hi: "ध्यान दें: सबसे ताज़ा डेटा {dataAge} पुराना है। इस सलाह को अतिरिक्त सावधानी से लें।",
    ta: "குறிப்பு: மிகவும் புதிய தரவு {dataAge} பழையது. இந்த ஆலோசனையை கூடுதல் எச்சரிக்கையுடன் எடுத்துக்கொள்ளவும்.",
  }},
  { code: 23, category: "test", templates: {
    en: "Test capsule — no real advisory content.",
    hi: "परीक्षण कैप्सूल — कोई वास्तविक सलाह सामग्री नहीं।",
    ta: "சோதனை காப்ஸூல் — உண்மையான ஆலோசனை உள்ளடக்கம் இல்லை.",
  }},
];

export function codebookEntry(code: number): CodebookEntry {
  return REASON_CODEBOOK[code] ?? REASON_CODEBOOK[REASON_CODEBOOK.length - 1];
}

/** Every value a template may reference — derived only from the capsule's own
 * fields, so render() cannot introduce a number the capsule didn't carry. */
function slotValues(c: Capsule, dataAgeLabel: string): Record<string, string> {
  return {
    waveHs: c.waveHs.toFixed(2),
    windKt: c.windKt.toFixed(0),
    windDir: COMPASS_16_LABELS[c.windDir16],
    currKt: c.currKt.toFixed(1),
    currDir: COMPASS_16_LABELS[c.currDir16],
    sst: c.sstC.toFixed(1),
    pfzDistNm: c.pfzDistNm.toFixed(0),
    pfzBearing: COMPASS_16_LABELS[c.pfzBearing16],
    pfzConf: String(c.pfzConfidence),
    bndDistNm: c.bndDistNm.toFixed(0),
    bndEta: c.bndEtaMin.toFixed(0),
    dataAge: dataAgeLabel,
  };
}

export function renderReason(c: Capsule, locale: CodebookLocale, dataAgeLabel: string): string {
  const entry = codebookEntry(c.reasonCode);
  const template = entry.templates[locale] ?? entry.templates.en;
  const values = slotValues(c, dataAgeLabel);
  return template.replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? `{${key}}`);
}
