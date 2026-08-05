// app.js -- dashboard for the home page (stats, sensor, weather, AQI).

function fmtBytes(n) {
  if (n === undefined || n === null) return "--";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  if (n < 1024 * 1024 * 1024) return (n / 1024 / 1024).toFixed(1) + " MB";
  return (n / 1024 / 1024 / 1024).toFixed(2) + " GB";
}

function setBar(id, used, total) {
  const wrap = document.getElementById(id);
  if (!wrap || !total) return 0;
  const pct = Math.min(100, Math.round((used / total) * 100));
  wrap.querySelector("span").style.width = pct + "%";
  wrap.classList.toggle("warn", pct >= 80);
  return pct;
}

async function refreshStats() {
  try {
    const s = await (await fetch("/api/stats")).json();
    document.getElementById("ram-used").textContent = (s.ram.used / 1024).toFixed(0);
    document.getElementById("ram-total").textContent = fmtBytes(s.ram.total) + " total";
    document.getElementById("ram-pct").textContent = setBar("ram-bar", s.ram.used, s.ram.total) + "%";

    document.getElementById("flash-used").textContent = fmtBytes(s.flash.used);
    document.getElementById("flash-total").textContent = fmtBytes(s.flash.total) + " total";
    document.getElementById("flash-pct").textContent = setBar("flash-bar", s.flash.used, s.flash.total) + "%";

    if (s.sd && s.sd.mounted) {
      document.getElementById("sd-used").textContent = fmtBytes(s.sd.used);
      document.getElementById("sd-total").textContent = fmtBytes(s.sd.total) + " total";
      document.getElementById("sd-pct").textContent = setBar("sd-bar", s.sd.used, s.sd.total) + "%";
    } else {
      document.getElementById("sd-used").textContent = "not mounted";
      document.getElementById("sd-total").textContent = "using flash fallback";
      document.getElementById("sd-pct").textContent = "--";
      setBar("sd-bar", 0, 1);
    }
  } catch (e) { /* ignore transient errors */ }
}

async function refreshSensor() {
  try {
    const d = await (await fetch("/api/sensor")).json();
    const t = document.getElementById("temp");
    const h = document.getElementById("hum");
    const note = document.getElementById("sensor-note");
    if (d.temperature_c === null || d.temperature_c === undefined) {
      t.textContent = "--"; h.textContent = "--";
      note.textContent = d.error ? ("sensor: " + d.error) : "waiting for DHT11...";
    } else {
      t.textContent = d.temperature_c + "\u00b0C / " + d.temperature_f + "\u00b0F";
      h.textContent = d.humidity + "%";
      note.textContent = "";
    }
  } catch (e) {}
}

function aqiClass(v) {
  if (v <= 50) return ["Good", "good"];
  if (v <= 100) return ["Moderate", "warn"];
  if (v <= 150) return ["Unhealthy (sensitive)", "warn"];
  if (v <= 200) return ["Unhealthy", "bad"];
  if (v <= 300) return ["Very Unhealthy", "bad"];
  return ["Hazardous", "bad"];
}

async function refreshWeather() {
  try {
    const w = await (await fetch("/api/weather")).json();
    const loc = document.getElementById("weather-loc");
    const body = document.getElementById("weather-body");
    if (w.error) { loc.textContent = "Weather unavailable"; body.textContent = w.error; return; }
    loc.textContent = w.location || "Forecast";
    body.innerHTML = (w.periods || []).slice(0, 4).map(p =>
      `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border)">
         <span>${p.name}</span>
         <span><b>${p.temperature}\u00b0${p.unit}</b> &middot; ${p.short}</span>
       </div>`).join("");
  } catch (e) {}
}

async function refreshAqi() {
  try {
    const a = await (await fetch("/api/aqi")).json();
    const el = document.getElementById("aqi");
    const label = document.getElementById("aqi-label");
    const detail = document.getElementById("aqi-detail");
    if (a.error || a.us_aqi === null || a.us_aqi === undefined) {
      el.textContent = "--"; detail.textContent = a.error || ""; return;
    }
    el.textContent = a.us_aqi;
    const [name, cls] = aqiClass(a.us_aqi);
    label.textContent = name;
    label.className = "stat-unit pill " + cls;
    detail.innerHTML = `PM2.5 ${a.pm2_5} &middot; PM10 ${a.pm10} &middot; O&#8323; ${a.ozone} &micro;g/m&sup3;`;
  } catch (e) {}
}

function tickClock() {
  const c = document.getElementById("clock");
  if (c) c.textContent = new Date().toLocaleString();
}

function boot() {
  refreshStats(); refreshSensor(); refreshWeather(); refreshAqi(); tickClock();
  setInterval(refreshStats, 3000);
  setInterval(refreshSensor, 4000);
  setInterval(refreshWeather, 600000);
  setInterval(refreshAqi, 600000);
  setInterval(tickClock, 1000);
}

boot();
