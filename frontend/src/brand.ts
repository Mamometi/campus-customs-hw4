/** Presentation helpers for the Yale-inspired design (P10). Data in the DB is unchanged. */

export const MASCOT_HEAD = "/handsome-dan-head.png";
export const MASCOT_FULL = "/handsome-dan.png";
export const ASSISTANT_NAME = "Handsome Dan";

/** Product names in the DB are slug-derived ("Ua Mens Tech L S 2 0"); tidy them for display. */
export function displayName(name: string): string {
  return name
    .replace(/\b1 4 Zip\b/g, "¼-Zip")
    .replace(/\bT Shirt\b/g, "T-Shirt")
    .replace(/\bL S 2 0\b/g, "L/S 2.0")
    .replace(/\bUa\b/g, "UA")
    .replace(/\bMens\b/g, "Men’s")
    .replace(/\bVit\b/g, "V.I.T.")
    .replace(/\bVs\b/g, "vs.")
    .replace(/\bCreqneck\b/g, "Crewneck")
    .replace(/\bHoodie 1\b/g, "Hoodie")
    .replace(/\bOf\b/g, "of")
    .replace(/\bAnd\b/g, "and")
    .replace(/\bTrack Field\b/g, "Track & Field");
}

/** Approximate swatch colors for the color names used in the catalogue. */
const SWATCHES: Record<string, string> = {
  navy: "#1d2a44", "navy blue": "#1d2a44", "royal blue": "#2350a8", blue: "#2f5fa7", "light blue": "#8fb8e8",
  white: "#ffffff", ivory: "#f6f1e3", cream: "#f2ead3", black: "#16181b",
  gray: "#9aa0a6", "light gray": "#c9ccd0", "heather gray": "#b7bbc0", "dark heather gray": "#6c7178",
  "charcoal gray": "#4a4f55", "heather charcoal gray": "#55595f", "dark heather charcoal": "#45494f",
  red: "#c8102e", "dusty coral": "#d98673", gold: "#c9a227", yellow: "#f2c230", green: "#2e7d4f",
  multicolor: "conic-gradient(#c8102e, #f2c230, #2e7d4f, #2350a8, #c8102e)",
};

export const swatch = (color: string) => SWATCHES[color.toLowerCase()] ?? "#c9ccd0";

/** Open the chat widget from anywhere (optionally sending a first message). */
export function openChat(message?: string) {
  window.dispatchEvent(new CustomEvent("cc:open-chat", { detail: { message } }));
}

export const RESIDENTIAL_COLLEGES = [
  "Benjamin Franklin", "Berkeley", "Branford", "Davenport", "Grace Hopper", "Jonathan Edwards",
  "Morse", "Pierson", "Saybrook", "Timothy Dwight", "Trumbull",
];

export const SCHOOLS = [
  { label: "Law", q: "law school" }, { label: "Management", q: "management" }, { label: "Medicine", q: "medicine" },
  { label: "Nursing", q: "nursing" }, { label: "Public Health", q: "public health" }, { label: "Engineering", q: "engineering" },
  { label: "Art", q: "school of art" }, { label: "Architecture", q: "architecture" }, { label: "Music", q: "music" },
  { label: "Divinity", q: "divinity" }, { label: "Environment", q: "forest" },
];

export const SPORTS = [
  "Football", "Hockey", "Basketball", "Baseball", "Soccer", "Lacrosse", "Tennis", "Squash",
  "Swimming", "Sailing", "Fencing", "Golf", "Volleyball", "Track",
];
