export function normalizeTranscript(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

function lower(value: string): string {
  return value.toLowerCase();
}

/**
 * Merge two pieces of one utterance.
 *
 * Browsers are inconsistent: one returns separate fragments ("создай",
 * "событие"), another returns a growing cumulative phrase ("создай",
 * "создай событие"). Blind concatenation turns the second shape into
 * "создай создай событие". This helper recognises the cumulative shape and
 * returns the longest version instead of repeating it.
 */
export function mergeTranscript(current: string, next: string): string {
  const base = normalizeTranscript(current);
  const addition = normalizeTranscript(next);
  if (!base) {
    return addition;
  }
  if (!addition) {
    return base;
  }

  if (lower(addition) === lower(base) || lower(base).endsWith(lower(addition))) {
    return base;
  }
  if (lower(base).startsWith(lower(addition))) {
    return base;
  }
  if (lower(addition).startsWith(lower(base))) {
    return addition;
  }

  // A cumulative phrase can be revised mid-word: "на завтра" becomes
  // "на послезавтра". If both versions share almost the whole prefix, keep
  // the newer one.
  const maxCommon = Math.min(base.length, addition.length);
  let common = 0;
  while (common < maxCommon && lower(base[common]) === lower(addition[common])) {
    common += 1;
  }
  if (common >= 3 && common >= maxCommon * 0.7) {
    return addition;
  }

  // The same phrase can arrive with the first fragment cut off, e.g.
  // "создай событие" + "событие на завтра". Join them over the common words.
  const limit = Math.min(base.length, addition.length);
  for (let size = limit; size >= 2; size -= 1) {
    const suffix = base.slice(-size);
    const prefix = addition.slice(0, size);
    if (lower(suffix) !== lower(prefix)) {
      continue;
    }
    const baseBoundary =
      size === base.length || base[base.length - size - 1] === " ";
    const additionBoundary =
      size === addition.length || addition[size] === " ";
    if (baseBoundary && additionBoundary) {
      return normalizeTranscript(base + addition.slice(size));
    }
  }

  return normalizeTranscript(`${base} ${addition}`);
}

export function joinTranscript(base: string, addition: string): string {
  const left = normalizeTranscript(base);
  const right = normalizeTranscript(addition);
  if (!left) {
    return right;
  }
  if (!right) {
    return left;
  }
  return `${left} ${right}`;
}
