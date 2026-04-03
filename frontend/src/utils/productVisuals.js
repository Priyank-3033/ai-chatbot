const CATEGORY_META = {
  phone: { label: "Smartphone", icon: "PHONE" },
  laptop: { label: "Laptop", icon: "LAPTOP" },
  tablet: { label: "Tablet", icon: "TABLET" },
  watch: { label: "Watch", icon: "WATCH" },
  accessory: { label: "Accessory", icon: "AUDIO" },
};

const CATEGORY_PALETTES = {
  phone: [
    ["#DBEAFE", "#BFDBFE", "#1D4ED8", "#FFFFFF"],
    ["#E0F2FE", "#BAE6FD", "#0369A1", "#F8FAFC"],
    ["#EDE9FE", "#DDD6FE", "#6D28D9", "#F8FAFC"],
    ["#DCFCE7", "#BBF7D0", "#15803D", "#F8FAFC"],
  ],
  laptop: [
    ["#E0E7FF", "#C7D2FE", "#4338CA", "#F8FAFC"],
    ["#F5F3FF", "#DDD6FE", "#7C3AED", "#FFFFFF"],
    ["#E0F2FE", "#BAE6FD", "#0F766E", "#F8FAFC"],
    ["#FEF3C7", "#FDE68A", "#B45309", "#FFFFFF"],
  ],
  tablet: [
    ["#DCFCE7", "#BBF7D0", "#15803D", "#FFFFFF"],
    ["#DBEAFE", "#BFDBFE", "#2563EB", "#FFFFFF"],
    ["#FCE7F3", "#FBCFE8", "#BE185D", "#FFFFFF"],
    ["#FEF3C7", "#FDE68A", "#B45309", "#FFFFFF"],
  ],
  watch: [
    ["#FFF7ED", "#FED7AA", "#C2410C", "#FFFFFF"],
    ["#FCE7F3", "#FBCFE8", "#BE185D", "#FFFFFF"],
    ["#E0F2FE", "#BAE6FD", "#0369A1", "#FFFFFF"],
    ["#ECFDF5", "#A7F3D0", "#047857", "#FFFFFF"],
  ],
  accessory: [
    ["#FEF3C7", "#FDE68A", "#B45309", "#FFFFFF"],
    ["#FCE7F3", "#FBCFE8", "#BE185D", "#FFFFFF"],
    ["#E0F2FE", "#BAE6FD", "#1D4ED8", "#FFFFFF"],
    ["#F3E8FF", "#DDD6FE", "#6D28D9", "#FFFFFF"],
  ],
};

function normalizeImagePath(value) {
  if (!value || typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (trimmed.startsWith("data:image/")) return trimmed;
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) return trimmed;
  if (trimmed.startsWith("/")) return trimmed;
  return `/product-photos/${trimmed.replace(/^\/+/, "")}`;
}

function firstAvailableImage(...values) {
  for (const value of values) {
    const normalized = normalizeImagePath(value);
    if (normalized) return normalized;
  }
  return "";
}

function hashString(value) {
  return value.split("").reduce((sum, char, index) => sum + char.charCodeAt(0) * (index + 1), 0);
}

function getPalette(product, seed) {
  const palettes = CATEGORY_PALETTES[product.category] || CATEGORY_PALETTES.phone;
  return palettes[seed % palettes.length];
}

function getMeta(product) {
  return CATEGORY_META[product.category] || { label: "Product", icon: "ITEM" };
}

function getInitials(product) {
  return product.name
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function escapeXml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function renderShapeByCategory(category, variant, accent, textOnDark) {
  if (category === "phone") {
    if (variant % 2 === 0) {
      return `
        <rect x="318" y="110" width="264" height="392" rx="38" fill="#0F172A" />
        <rect x="334" y="126" width="232" height="360" rx="28" fill="${accent}" fill-opacity="0.92" />
        <circle cx="450" cy="148" r="7" fill="${textOnDark}" fill-opacity="0.72" />
        <rect x="390" y="176" width="120" height="12" rx="6" fill="${textOnDark}" fill-opacity="0.55" />
        <rect x="372" y="216" width="156" height="112" rx="24" fill="${textOnDark}" fill-opacity="0.18" />
        <rect x="372" y="348" width="68" height="68" rx="18" fill="${textOnDark}" fill-opacity="0.22" />
        <rect x="460" y="348" width="68" height="68" rx="18" fill="${textOnDark}" fill-opacity="0.14" />
      `;
    }
    return `
      <g transform="translate(268 82) rotate(8 182 206)">
        <rect x="88" y="0" width="188" height="412" rx="34" fill="#111827" />
        <rect x="102" y="16" width="160" height="380" rx="26" fill="${accent}" fill-opacity="0.92" />
        <rect x="142" y="46" width="80" height="10" rx="5" fill="${textOnDark}" fill-opacity="0.55" />
        <circle cx="182" cy="80" r="28" fill="${textOnDark}" fill-opacity="0.14" />
        <rect x="124" y="132" width="116" height="18" rx="9" fill="${textOnDark}" fill-opacity="0.25" />
        <rect x="124" y="172" width="116" height="92" rx="20" fill="${textOnDark}" fill-opacity="0.18" />
      </g>
    `;
  }

  if (category === "laptop") {
    if (variant % 2 === 0) {
      return `
        <rect x="200" y="160" width="500" height="280" rx="28" fill="#CBD5E1" />
        <rect x="224" y="182" width="452" height="232" rx="20" fill="#1E293B" />
        <rect x="352" y="230" width="196" height="22" rx="11" fill="${accent}" fill-opacity="0.7" />
        <rect x="352" y="268" width="142" height="16" rx="8" fill="${textOnDark}" fill-opacity="0.26" />
        <rect x="314" y="320" width="274" height="74" rx="20" fill="${accent}" fill-opacity="0.22" />
        <path d="M146 470H754" stroke="#94A3B8" stroke-width="18" stroke-linecap="round" />
      `;
    }
    return `
      <g transform="translate(174 156)">
        <rect x="84" y="0" width="468" height="276" rx="26" fill="#E2E8F0" />
        <rect x="104" y="20" width="428" height="236" rx="18" fill="#0F172A" />
        <rect x="164" y="66" width="168" height="18" rx="9" fill="${accent}" fill-opacity="0.74" />
        <rect x="164" y="100" width="220" height="14" rx="7" fill="${textOnDark}" fill-opacity="0.22" />
        <rect x="164" y="150" width="252" height="86" rx="18" fill="${accent}" fill-opacity="0.2" />
        <path d="M0 308H636" stroke="#64748B" stroke-width="20" stroke-linecap="round" />
      </g>
    `;
  }

  if (category === "tablet") {
    if (variant % 2 === 0) {
      return `
        <g transform="translate(222 104) rotate(-6 228 180)">
          <rect x="56" y="0" width="344" height="420" rx="30" fill="#F8FAFC" stroke="#CBD5E1" stroke-width="8" />
          <rect x="76" y="20" width="304" height="380" rx="22" fill="${accent}" fill-opacity="0.9" />
          <circle cx="228" cy="42" r="7" fill="${textOnDark}" fill-opacity="0.65" />
          <rect x="126" y="92" width="204" height="20" rx="10" fill="${textOnDark}" fill-opacity="0.28" />
          <rect x="108" y="138" width="240" height="140" rx="20" fill="${textOnDark}" fill-opacity="0.16" />
        </g>
      `;
    }
    return `
      <rect x="174" y="152" width="552" height="316" rx="30" fill="#E2E8F0" />
      <rect x="198" y="176" width="504" height="268" rx="20" fill="#0F172A" />
      <rect x="268" y="226" width="164" height="120" rx="18" fill="${accent}" fill-opacity="0.28" />
      <rect x="462" y="226" width="160" height="18" rx="9" fill="${textOnDark}" fill-opacity="0.28" />
      <rect x="462" y="260" width="124" height="14" rx="7" fill="${textOnDark}" fill-opacity="0.18" />
      <rect x="462" y="308" width="180" height="74" rx="18" fill="${accent}" fill-opacity="0.18" />
    `;
  }

  if (category === "watch") {
    if (variant % 2 === 0) {
      return `
        <rect x="396" y="58" width="108" height="478" rx="48" fill="#94A3B8" />
        <rect x="332" y="180" width="236" height="240" rx="58" fill="#1E293B" />
        <rect x="356" y="204" width="188" height="192" rx="38" fill="#111827" />
        <circle cx="450" cy="278" r="56" fill="${accent}" fill-opacity="0.22" />
        <path d="M450 246V278L484 298" stroke="${textOnDark}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" />
      `;
    }
    return `
      <g transform="translate(288 86) rotate(8 162 210)">
        <rect x="118" y="0" width="88" height="432" rx="40" fill="#334155" />
        <rect x="36" y="106" width="252" height="248" rx="62" fill="#0F172A" />
        <rect x="60" y="130" width="204" height="200" rx="42" fill="#111827" />
        <circle cx="162" cy="218" r="58" fill="${accent}" fill-opacity="0.18" />
        <rect x="124" y="282" width="76" height="16" rx="8" fill="${textOnDark}" fill-opacity="0.34" />
      </g>
    `;
  }

  if (variant % 2 === 0) {
    return `
      <rect x="316" y="244" width="268" height="126" rx="30" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="8" />
      <rect x="344" y="270" width="212" height="74" rx="22" fill="#F8FAFC" />
      <circle cx="394" cy="306" r="24" fill="${accent}" fill-opacity="0.28" />
      <path d="M466 284H526" stroke="${accent}" stroke-width="18" stroke-linecap="round" />
      <path d="M466 316H510" stroke="${textOnDark}" stroke-width="12" stroke-linecap="round" />
      <path d="M268 404C328 336 390 302 450 302C510 302 572 336 632 404" stroke="${accent}" stroke-width="24" stroke-linecap="round" />
    `;
  }
  return `
    <g transform="translate(262 166)">
      <circle cx="188" cy="114" r="78" fill="#1E293B" />
      <circle cx="188" cy="114" r="54" fill="#334155" />
      <rect x="156" y="164" width="64" height="124" rx="28" fill="#334155" />
      <rect x="274" y="196" width="168" height="104" rx="30" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="8" />
      <path d="M306 228H394" stroke="${accent}" stroke-width="18" stroke-linecap="round" />
      <path d="M306 260H366" stroke="${textOnDark}" stroke-width="12" stroke-linecap="round" />
    </g>
  `;
}

function buildArtSvg(product, variantSeed) {
  const [surface, accent, text, textOnDark] = getPalette(product, variantSeed);
  const meta = getMeta(product);
  const initials = getInitials(product);
  const shortTag = product.tag.split(" ").slice(0, 2).join(" ");
  const deviceArt = renderShapeByCategory(product.category, variantSeed, accent, textOnDark);
  const badgeText = `${meta.icon} · ${shortTag}`;

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 900 600">
      <defs>
        <linearGradient id="bg-${variantSeed}" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="${surface}" />
          <stop offset="100%" stop-color="${accent}" />
        </linearGradient>
      </defs>
      <rect width="900" height="600" rx="36" fill="url(#bg-${variantSeed})" />
      <circle cx="130" cy="508" r="86" fill="#FFFFFF" fill-opacity="0.3" />
      <circle cx="748" cy="92" r="92" fill="#FFFFFF" fill-opacity="0.24" />
      <rect x="48" y="48" width="804" height="504" rx="32" fill="#FFFFFF" fill-opacity="0.64" />
      <rect x="84" y="86" width="218" height="48" rx="24" fill="${text}" fill-opacity="0.08" />
      <text x="108" y="116" font-family="Segoe UI, Arial, sans-serif" font-size="22" font-weight="700" fill="${text}">${escapeXml(badgeText)}</text>
      <text x="96" y="486" font-family="Segoe UI, Arial, sans-serif" font-size="56" font-weight="800" fill="${text}">${escapeXml(product.name)}</text>
      <text x="96" y="532" font-family="Segoe UI, Arial, sans-serif" font-size="26" font-weight="600" fill="${text}" fill-opacity="0.8">${escapeXml(product.brand)} • ${escapeXml(meta.label)}</text>
      <text x="728" y="500" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="96" font-weight="800" fill="${text}" fill-opacity="0.12">${escapeXml(initials)}</text>
      ${deviceArt}
    </svg>
  `;
}

function toDataUri(svg) {
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export function getLocalProductImage(product, offset = 0) {
  const realImage = firstAvailableImage(product.image_local, product.image);
  if (offset === 0 && realImage) return realImage;
  const seed = hashString(`${product.id}-${product.name}-${product.brand}`) + offset * 13;
  return toDataUri(buildArtSvg(product, seed));
}

export function getProductImageSources(product) {
  const localMain = normalizeImagePath(product.image_local);
  const remoteMain = normalizeImagePath(product.image);
  const generated = getProductPlaceholder(product);
  return [localMain, remoteMain, generated].filter((image, index, all) => image && all.indexOf(image) === index);
}

export function getLocalProductGallery(product) {
  const realImages = [
    product.image,
    ...(product.gallery || []),
    product.image_local,
    ...(product.gallery_local || []),
  ]
    .map((image) => normalizeImagePath(image))
    .filter(Boolean);

  const generatedImages = [0, 1, 2, 3].map((offset) => getLocalProductImage(product, offset));

  return [...realImages, ...generatedImages]
    .filter((image, index, all) => all.indexOf(image) === index)
    .slice(0, 4);
}

export function getProductPlaceholder(product) {
  return getLocalProductImage(product, 7);
}
