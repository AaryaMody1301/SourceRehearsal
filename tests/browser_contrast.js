// Runs in Chrome through agent-browser; checks rendered colors, not CSS source text.
(() => {
  const rgba = color => color.match(/[\d.]+/g).map(Number);
  const blend = (top, bottom) => top.slice(0, 3).map((v, i) => v * (top[3] ?? 1) + bottom[i] * (1 - (top[3] ?? 1)));
  const background = element => {
    const layers = [];
    for (let node = element; node; node = node.parentElement) layers.unshift(rgba(getComputedStyle(node).backgroundColor));
    return layers.reduce((bottom, top) => blend(top, bottom), [255, 255, 255]);
  };
  const luminance = rgb => rgb.map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
    .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
  const samples = {};
  for (const selector of [
    "h1", "h2", "h3", '[data-testid="stMarkdownContainer"] p',
    '[data-testid="stTextInput"] input', '[data-testid="stNumberInput"] input',
    '[data-testid="stMetricLabel"] p', '[data-testid="stMetricValue"]',
    '[data-testid="stAlertContainer"] p', '[data-testid="stCaptionContainer"] p',
    'button:not(:disabled) p',
  ]) {
    const elements = Array.from(document.querySelectorAll(selector)).filter(e => e.getClientRects().length && !e.closest('[aria-hidden="true"]'));
    if (!elements.length) continue;
    const ratios = elements.map(element => {
      const bg = background(element);
      const fg = blend(rgba(getComputedStyle(element).color), bg);
      const a = luminance(fg), b = luminance(bg);
      const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05);
      if (ratio < 4.5) throw new Error(`Low contrast ${ratio.toFixed(2)}: ${selector} ${element.textContent.slice(0, 70)}`);
      return ratio;
    });
    samples[selector] = Math.min(...ratios);
  }
  if (!samples.h2 || !samples['[data-testid="stMetricValue"]']) throw new Error("Missing contrast targets");
  return samples;
})();
