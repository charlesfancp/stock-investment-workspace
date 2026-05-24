import http from "node:http";
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const publicDir = join(__dirname, "public");
const PORT = Number(process.env.PORT || 5173);
const execFileAsync = promisify(execFile);

const DEFAULT_STOCK = {
  code: "02510",
  yahooSymbol: "2510.HK",
  stooqSymbol: "2510.hk",
  searchText: '"02510" "TS Lines" OR "德翔海運"',
  researchText: '"德翔海運" "02510" 目標價 OR 评级 OR 評級 OR 研報 OR 摩通 OR 大行',
};

const STOCK_ALIASES = new Map([
  ["德翔海运", "02510"],
  ["德翔海運", "02510"],
  ["ts lines", "02510"],
  ["ts line", "02510"],
  ["tslines", "02510"],
  ["腾讯", "00700"],
  ["騰訊", "00700"],
  ["腾讯控股", "00700"],
  ["騰訊控股", "00700"],
  ["tencent", "00700"],
  ["阿里", "09988"],
  ["阿里巴巴", "09988"],
  ["alibaba", "09988"],
  ["美团", "03690"],
  ["美團", "03690"],
  ["meituan", "03690"],
  ["小米", "01810"],
  ["xiaomi", "01810"],
  ["汇丰", "00005"],
  ["匯豐", "00005"],
  ["hsbc", "00005"],
]);

let activeStockCache = null;

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function sendJson(res, status, data) {
  const body = JSON.stringify(data);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function sendText(res, status, text, type = "text/plain; charset=utf-8") {
  res.writeHead(status, { "Content-Type": type, "Cache-Control": "no-store" });
  res.end(text);
}

function decodeHtml(value = "") {
  return value
    .replace(/<[^>]*>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&#x2f;/gi, "/")
    .replace(/&#x3b;/gi, ";")
    .replace(/&#x27;/gi, "'")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, " ")
    .trim();
}

function csvRows(text) {
  return text
    .trim()
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const cells = [];
      let current = "";
      let quoted = false;
      for (let i = 0; i < line.length; i += 1) {
        const char = line[i];
        if (char === '"' && line[i + 1] === '"') {
          current += '"';
          i += 1;
        } else if (char === '"') {
          quoted = !quoted;
        } else if (char === "," && !quoted) {
          cells.push(current);
          current = "";
        } else {
          current += char;
        }
      }
      cells.push(current);
      return cells;
    });
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function yyyymmdd(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}${m}${d}`;
}

function normalizeCode(code) {
  return String(code || DEFAULT_STOCK.code).replace(/\D/g, "").padStart(5, "0");
}

function normalizeSearchText(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function symbolFromCode(code) {
  return `${normalizeCode(code).slice(-4)}.HK`;
}

function stooqSymbolFromCode(code) {
  const numeric = String(Number(normalizeCode(code)));
  return `${numeric}.hk`;
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 12000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        Accept: "*/*",
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function getActiveStocks() {
  if (activeStockCache) return activeStockCache;
  const [englishResponse, chineseResponse] = await Promise.all([
    fetchWithTimeout("https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_e.json"),
    fetchWithTimeout("https://www1.hkexnews.hk/ncms/script/eds/activestock_sehk_c.json"),
  ]);
  const english = await englishResponse.json();
  const chinese = await chineseResponse.json();
  const chineseByCode = new Map(chinese.map((stock) => [stock.c, stock]));
  const merged = english.map((stock) => {
    const zh = chineseByCode.get(stock.c);
    return {
      ...stock,
      enName: stock.n,
      zhName: zh?.n || "",
    };
  });
  chinese.forEach((stock) => {
    if (!merged.some((item) => item.c === stock.c)) {
      merged.push({ ...stock, enName: "", zhName: stock.n });
    }
  });
  activeStockCache = merged;
  return activeStockCache;
}

async function resolveStockCode(input) {
  const raw = String(input || DEFAULT_STOCK.code).trim();
  const digits = raw.match(/\d{1,5}/)?.[0];
  if (digits) return normalizeCode(digits);

  const alias = STOCK_ALIASES.get(normalizeSearchText(raw));
  if (alias) return alias;

  const query = normalizeSearchText(raw);
  const stocks = await getActiveStocks();
  const found = stocks.find((stock) => {
    const name = normalizeSearchText(`${stock.n} ${stock.enName || ""} ${stock.zhName || ""}`);
    return name === query || name.includes(query);
  });
  if (!found) {
    throw new Error(`没有找到股票简称或代码：${raw}`);
  }
  return found.c;
}

async function curlText(url) {
  const { stdout } = await execFileAsync(
    "curl",
    [
      "-L",
      "-s",
      "--max-time",
      "12",
      "-A",
      "Mozilla/5.0",
      url,
    ],
    { maxBuffer: 8 * 1024 * 1024 },
  );
  return stdout;
}

async function fetchYahooChart(code) {
  const symbol = symbolFromCode(code);
  const dailyUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(
    symbol,
  )}?range=1y&interval=1d&includePrePost=false&events=div%7Csplit`;
  const intradayUrl = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(
    symbol,
  )}?range=1d&interval=1m&includePrePost=false`;
  const [data, intradayData] = await Promise.all([
    curlText(dailyUrl).then(JSON.parse),
    curlText(intradayUrl)
      .then(JSON.parse)
      .catch(() => null),
  ]);
  const result = data?.chart?.result?.[0];
  if (!result) {
    throw new Error(data?.chart?.error?.description || "Yahoo chart returned no result");
  }

  const quote = result.indicators?.quote?.[0] || {};
  const timestamps = result.timestamp || [];
  const rows = timestamps
    .map((time, index) => ({
      date: new Date(time * 1000).toISOString().slice(0, 10),
      open: toNumber(quote.open?.[index]),
      high: toNumber(quote.high?.[index]),
      low: toNumber(quote.low?.[index]),
      close: toNumber(quote.close?.[index]),
      volume: toNumber(quote.volume?.[index]),
    }))
    .filter((row) => row.close !== null && row.close > 0);

  const last = rows.at(-1) || {};
  const previous = rows.length > 1 ? rows[rows.length - 2] : {};
  const meta = result.meta || {};
  const regularPrice = toNumber(meta.regularMarketPrice) ?? last.close;
  const previousClose = previous.close ?? toNumber(meta.chartPreviousClose);
  const intraday = parseYahooRows(intradayData?.chart?.result?.[0], "time");
  const intradayVolume = intraday.reduce((sum, row) => sum + (row.volume || 0), 0);
  const intradayTurnover = intraday.reduce((sum, row) => {
    const priceForTurnover = row.close ?? row.open ?? row.high ?? row.low;
    return sum + (Number.isFinite(priceForTurnover) ? priceForTurnover * (row.volume || 0) : 0);
  }, 0);

  return {
    source: "Yahoo Finance",
    symbol,
    code: normalizeCode(code),
    currency: meta.currency || "HKD",
    exchange: meta.fullExchangeName || meta.exchangeName || "HKEX",
    marketTime: meta.regularMarketTime
      ? new Date(meta.regularMarketTime * 1000).toISOString()
      : null,
    price: regularPrice,
    previousClose,
    change:
      regularPrice !== null && previousClose !== null ? regularPrice - previousClose : null,
    changePercent:
      regularPrice !== null && previousClose
        ? ((regularPrice - previousClose) / previousClose) * 100
        : null,
    dayHigh: toNumber(meta.regularMarketDayHigh) ?? last.high,
    dayLow: toNumber(meta.regularMarketDayLow) ?? last.low,
    volume: toNumber(meta.regularMarketVolume) || intradayVolume || last.volume,
    turnover: intradayTurnover || null,
    fiftyTwoWeekHigh: toNumber(meta.fiftyTwoWeekHigh),
    fiftyTwoWeekLow: toNumber(meta.fiftyTwoWeekLow),
    intraday,
    history: rows,
  };
}

function parseYahooRows(result, dateKey = "date") {
  const quote = result?.indicators?.quote?.[0] || {};
  const timestamps = result?.timestamp || [];
  return timestamps
    .map((time, index) => {
      const date = new Date(time * 1000);
      return {
        [dateKey]: dateKey === "time" ? date.toISOString() : date.toISOString().slice(0, 10),
        open: toNumber(quote.open?.[index]),
        high: toNumber(quote.high?.[index]),
        low: toNumber(quote.low?.[index]),
        close: toNumber(quote.close?.[index]),
        volume: toNumber(quote.volume?.[index]),
      };
    })
    .filter((row) => row.close !== null && row.close > 0);
}

async function fetchStooqQuote(code) {
  const symbol = stooqSymbolFromCode(code);
  const url = `https://stooq.com/q/l/?s=${encodeURIComponent(
    symbol,
  )}&f=sd2t2ohlcvn&h&e=csv`;
  const response = await fetchWithTimeout(url);
  const rows = csvRows(await response.text());
  if (rows.length < 2) {
    throw new Error("Stooq returned no quote");
  }
  const header = rows[0];
  const values = rows[1];
  const row = Object.fromEntries(header.map((key, index) => [key, values[index]]));
  return {
    source: "Stooq",
    symbol: row.Symbol,
    code: normalizeCode(code),
    currency: "HKD",
    exchange: "HKEX",
    marketTime: row.Date && row.Time ? `${row.Date}T${row.Time}+08:00` : null,
    price: toNumber(row.Close),
    previousClose: null,
    change: null,
    changePercent: null,
    dayHigh: toNumber(row.High),
    dayLow: toNumber(row.Low),
    volume: toNumber(row.Volume),
    turnover: null,
    name: row.Name,
    intraday: [],
    history: [],
  };
}

async function fetchQuote(code) {
  try {
    return await fetchYahooChart(code);
  } catch (error) {
    const fallback = await fetchStooqQuote(code);
    return { ...fallback, warning: `Yahoo Finance 暂时不可用，已使用 Stooq 备用报价：${error.message}` };
  }
}

async function getHkexStockInfo(code) {
  const normalized = normalizeCode(code);
  const stocks = await getActiveStocks();
  const found = stocks.find((stock) => stock.c === normalized);
  if (!found) {
    throw new Error(`HKEX active stock list did not contain ${normalized}`);
  }
  return {
    id: found.i,
    code: found.c,
    shortName: found.enName || found.n,
    displayName: found.c === DEFAULT_STOCK.code ? "德翔海运" : found.zhName || found.n,
    securityId: found.s,
  };
}

async function searchStocks(query) {
  const q = normalizeSearchText(query);
  if (!q) {
    return [
      {
        code: DEFAULT_STOCK.code,
        shortName: "TS LINES",
        displayName: "德翔海运",
        aliases: ["德翔海運", "TS LINES"],
      },
    ];
  }
  const stocks = await getActiveStocks();
  const results = [];
  const aliasCode = STOCK_ALIASES.get(q);
  if (aliasCode) {
    const match = stocks.find((stock) => stock.c === aliasCode);
    if (match) {
      results.push({
        code: match.c,
        shortName: match.enName || match.n,
        displayName: match.c === DEFAULT_STOCK.code ? "德翔海运" : match.zhName || match.n,
        aliases: [match.zhName, match.enName]
          .filter(Boolean)
          .filter((name, index, names) => names.indexOf(name) === index),
      });
    }
  }
  const addDefault =
    "德翔海运 德翔海運 ts lines 02510".toLowerCase().includes(q) ||
    DEFAULT_STOCK.code.includes(q);
  if (addDefault) {
    results.push({
      code: DEFAULT_STOCK.code,
      shortName: "TS LINES",
      displayName: "德翔海运",
      aliases: ["德翔海運", "TS LINES"],
    });
  }
  for (const stock of stocks) {
    if (results.length >= 8) break;
    const haystack = `${stock.c} ${stock.n} ${stock.enName || ""} ${stock.zhName || ""}`.toLowerCase();
    if (haystack.includes(q) && !results.some((item) => item.code === stock.c)) {
      results.push({
        code: stock.c,
        shortName: stock.enName || stock.n,
        displayName: stock.c === DEFAULT_STOCK.code ? "德翔海运" : stock.zhName || stock.n,
        aliases: [stock.zhName, stock.enName]
          .filter(Boolean)
          .filter((name, index, names) => names.indexOf(name) === index),
      });
    }
  }
  return results;
}

function parseReleaseDate(raw) {
  const text = decodeHtml(raw);
  const match = text.match(/(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/);
  if (!match) return text;
  const [, dd, mm, yyyy, hh, min] = match;
  return `${yyyy}-${mm}-${dd} ${hh}:${min}`;
}

function stripLabel(text, labels) {
  return labels.reduce((value, label) => value.replace(label, ""), text).trim();
}

function parseAnnouncements(html) {
  const rows = html.match(/<tr[\s\S]*?<\/tr>/gi) || [];
  return rows
    .map((row) => {
      if (!row.includes("stock-short-code")) return null;
      const cells = row.match(/<td[\s\S]*?<\/td>/gi) || [];
      const releaseCell = cells[0] || "";
      const codeCell = cells[1] || "";
      const nameCell = cells[2] || "";
      const documentCell = cells[3] || "";
      const headlineMatch = documentCell.match(/<div class="headline">([\s\S]*?)<\/div>/i);
      const linkMatch = documentCell.match(/<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/i);
      const sizeMatch = documentCell.match(/attachment_filesize">([^<]+)/i);
      const href = linkMatch?.[1] || "";
      return {
        releaseTime: parseReleaseDate(releaseCell),
        stockCode: stripLabel(decodeHtml(codeCell), ["Stock Code:", "股份代號:"]),
        stockName: stripLabel(decodeHtml(nameCell), ["Stock Short Name:", "股份簡稱:"]),
        category: decodeHtml(headlineMatch?.[1] || ""),
        title: decodeHtml(linkMatch?.[2] || ""),
        fileSize: sizeMatch ? decodeHtml(sizeMatch[1]) : "",
        url: href.startsWith("http") ? href : `https://www1.hkexnews.hk${href}`,
      };
    })
    .filter((item) => item && item.url && item.title);
}

async function fetchAnnouncements(code) {
  const stock = await getHkexStockInfo(code);
  const now = new Date();
  const from = new Date(now);
  from.setFullYear(from.getFullYear() - 1);
  const params = new URLSearchParams({
    lang: "ZH",
    category: "0",
    market: "SEHK",
    searchType: "0",
    documentType: "",
    t1code: "-2",
    t2Gcode: "-2",
    t2code: "-2",
    stockId: String(stock.id),
    from: yyyymmdd(from),
    to: yyyymmdd(now),
    title: "",
  });

  const response = await fetchWithTimeout(
    "https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh",
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params,
    },
  );
  const html = await response.text();
  const total = Number(
    (html.match(/Total records found:\s*([0-9]+)/i) || html.match(/共有\s*([0-9]+)\s*紀錄/i) || [])[1] ||
      0,
  );
  return {
    source: "HKEXnews",
    stock,
    total,
    searchUrl: `https://www1.hkexnews.hk/search/titlesearch.xhtml?lang=zh&market=SEHK&stockId=${stock.id}&stockCode=${stock.code}`,
    disclosureUrl: `https://di.hkex.com.hk/di/NSSrchCorpQW.aspx?src=MAIN&lang=ZH&in=1&sc=${stock.code}`,
    items: parseAnnouncements(html),
  };
}

function parseRssItems(xml, limit = 20) {
  const items = xml.match(/<item>[\s\S]*?<\/item>/gi) || [];
  return items.slice(0, limit).map((item) => {
    const pick = (tag) => {
      const match = item.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
      return decodeHtml(match?.[1] || "");
    };
    const sourceMatch = item.match(/<source[^>]*url="([^"]+)"[^>]*>([\s\S]*?)<\/source>/i);
    return {
      title: pick("title"),
      url: pick("link"),
      publishedAt: pick("pubDate"),
      source: sourceMatch ? decodeHtml(sourceMatch[2]) : "",
      sourceUrl: sourceMatch?.[1] || "",
    };
  });
}

async function fetchNews(code) {
  const normalized = normalizeCode(code);
  const query =
    normalized === DEFAULT_STOCK.code
      ? DEFAULT_STOCK.searchText
      : `"${normalized}" HK stock`;
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(
    query,
  )}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant`;
  const response = await fetchWithTimeout(url);
  const items = parseRssItems(await response.text(), 30);
  const preferredSources =
    /aastocks|investing|fx168|etnet|經濟通|信報|hkej|智通|cnyes|鉅亨|格隆|hket|經濟日報/i;
  const unique = [];
  for (const item of items) {
    if (!unique.some((existing) => existing.title === item.title)) {
      unique.push(item);
    }
  }
  unique.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));
  const preferred = unique.filter((item) => preferredSources.test(`${item.source} ${item.title}`));
  const merged = [...preferred, ...unique.filter((item) => !preferred.includes(item))];
  return {
    source: "Google News RSS",
    searchUrl: `https://news.google.com/search?q=${encodeURIComponent(query)}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant`,
    items: merged.slice(0, 5),
  };
}

async function fetchResearch(code) {
  const normalized = normalizeCode(code);
  const query =
    normalized === DEFAULT_STOCK.code
      ? DEFAULT_STOCK.researchText
      : `"${normalized}" 目標價 OR 评级 OR 評級 OR 研報 OR 分析師`;
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(
    query,
  )}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant`;
  const response = await fetchWithTimeout(url);
  const cutoff = Date.now() - 90 * 24 * 60 * 60 * 1000;
  const researchKeywords = /大行|目標價|目标价|评级|評級|研報|分析師|分析员|摩通|花旗|高盛|中金|券商|買入|买入|增持|跑赢|跑贏/i;
  const items = parseRssItems(await response.text(), 30)
    .filter((item) => new Date(item.publishedAt).getTime() >= cutoff)
    .filter((item) => researchKeywords.test(`${item.title} ${item.source}`))
    .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt))
    .slice(0, 6);
  const forumLinks = [
    {
      title: "雪球 HK02510",
      source: "雪球",
      url: `https://xueqiu.com/S/HK${normalized}`,
      note: "散户讨论、买入理由、分红预期和运价周期分歧。",
    },
    {
      title: "富途牛牛 02510-HK",
      source: "富途牛牛",
      url: `https://www.futunn.com/stock/${normalized}-HK`,
      note: "评论热度、新闻解读、券商观点和短线资金情绪。",
    },
    {
      title: "TradingView HKEX:2510",
      source: "TradingView",
      url: `https://www.tradingview.com/symbols/HKEX-${Number(normalized)}/ideas/`,
      note: "趋势线、支撑阻力和活跃交易想法。",
    },
  ];
  return {
    source: "Google News RSS",
    searchUrl: `https://news.google.com/search?q=${encodeURIComponent(query)}&hl=zh-HK&gl=HK&ceid=HK:zh-Hant`,
    items,
    forumLinks,
  };
}

async function handleApi(req, res, url) {
  let code = DEFAULT_STOCK.code;
  try {
    if (url.pathname === "/api/search") {
      sendJson(res, 200, { items: await searchStocks(url.searchParams.get("q") || "") });
      return;
    }
    code = await resolveStockCode(url.searchParams.get("code") || DEFAULT_STOCK.code);
    if (url.pathname === "/api/quote") {
      sendJson(res, 200, await fetchQuote(code));
      return;
    }
    if (url.pathname === "/api/announcements") {
      sendJson(res, 200, await fetchAnnouncements(code));
      return;
    }
    if (url.pathname === "/api/news") {
      sendJson(res, 200, await fetchNews(code));
      return;
    }
    if (url.pathname === "/api/research") {
      sendJson(res, 200, await fetchResearch(code));
      return;
    }
    if (url.pathname === "/api/stock") {
      sendJson(res, 200, await getHkexStockInfo(code));
      return;
    }
    sendJson(res, 404, { error: "Not found" });
  } catch (error) {
    sendJson(res, 502, {
      error: error.message,
      code,
      source: url.pathname.replace("/api/", ""),
    });
  }
}

async function serveStatic(res, pathname) {
  const requested = pathname === "/" ? "/index.html" : pathname;
  const safePath = normalize(requested).replace(/^(\.\.[/\\])+/, "");
  const filePath = join(publicDir, safePath);
  if (!filePath.startsWith(publicDir)) {
    sendText(res, 403, "Forbidden");
    return;
  }
  try {
    const content = await readFile(filePath);
    const type = MIME_TYPES[extname(filePath)] || "application/octet-stream";
    res.writeHead(200, { "Content-Type": type, "Cache-Control": "no-store" });
    res.end(content);
  } catch {
    sendText(res, 404, "Not found");
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (url.pathname.startsWith("/api/")) {
    await handleApi(req, res, url);
    return;
  }
  await serveStatic(res, url.pathname);
});

server.listen(PORT, () => {
  console.log(`Single stock dashboard is running at http://localhost:${PORT}`);
});
