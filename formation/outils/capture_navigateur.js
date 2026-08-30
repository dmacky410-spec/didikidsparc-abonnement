window.__css = await (await fetch('/styles.css')).text();
window.__fonts = await (await fetch('/_fonts_capture.css')).text();
window.__shoot = async (name, sel, pad = 0) => {
  const el = sel ? document.querySelector(sel) : document.body;
  const r = el.getBoundingClientRect();
  const w = Math.ceil(r.width) + pad * 2, h = Math.ceil(r.height) + pad * 2;
  const clone = el.cloneNode(true);
  clone.querySelectorAll('.pulse').forEach(e => e.classList.remove('pulse'));
  const src = el.querySelectorAll('input, select, textarea');
  const dst = clone.querySelectorAll('input, select, textarea');
  src.forEach((s, i) => { const d = dst[i]; if (!d) return;
    if (s.tagName === 'SELECT') { d.innerHTML=''; const o = document.createElement('option');
      o.textContent = s.options[s.selectedIndex]?.text || ''; d.appendChild(o); }
    else if (s.tagName === 'TEXTAREA') d.textContent = s.value;
    else d.setAttribute('value', s.value); });
  const holder = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
  const b = getComputedStyle(document.body);
  holder.setAttribute('style',
    `font-family:${b.fontFamily};font-size:${b.fontSize};color:${b.color};` +
    `line-height:${b.lineHeight};padding:${pad}px;box-sizing:border-box;` +
    `width:${w}px;height:${h}px`);
  const style = document.createElementNS('http://www.w3.org/1999/xhtml', 'style');
  style.textContent = window.__fonts + '\n' + window.__css +
    '\nbody{margin:0}*{animation:none!important;transition:none!important}';
  holder.appendChild(style); holder.appendChild(clone);
  const xml = new XMLSerializer().serializeToString(holder);
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}">` +
              `<foreignObject x="0" y="0" width="${w}" height="${h}">${xml}</foreignObject></svg>`;
  const img = new Image();
  await new Promise((ok, ko) => { img.onload = ok; img.onerror = () => ko(new Error('svg'));
    img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg); });
  const cv = document.createElement('canvas');
  cv.width = w * 2; cv.height = h * 2;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cv.width, cv.height);
  ctx.scale(2, 2); ctx.drawImage(img, 0, 0);
  await fetch('http://localhost:8731/', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({name, png: cv.toDataURL('image/png')})});
  return name;
};
