# SEO Audit — elyanlabs.ai (Quiet Launch)

_Bounty #2957 — 10 RTC_

---

## Executive Summary

The site has solid foundations (good meta descriptions, OG tags, fast loading) but is missing critical SEO elements for a quiet launch: **canonical URLs, structured data, alt text on images, sitemap, and robots.txt**.

**SEO Score: 55/100** — fixable to 90+ with the recommendations below.

---

## 1. Critical Issues (Fix First)

### 1.1 No Canonical URLs
Every page is missing `<link rel="canonical">`. This can cause duplicate content issues.

**Fix:** Add to every page:
```html
<link rel="canonical" href="https://elyanlabs.ai/">
<link rel="canonical" href="https://elyanlabs.ai/vintage-voice.html">
<link rel="canonical" href="https://elyanlabs.ai/contact.html">
```

### 1.2 No Structured Data (Schema.org)
No `application/ld+json` found on any page. Rich results in Google require this.

**Fix for homepage:**
```json
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Elyan Labs",
  "url": "https://elyanlabs.ai",
  "description": "Private research lab for exotic-architecture LLM inference, persistent AI persona systems, and non-bijunctive attention.",
  "logo": "https://elyanlabs.ai/assets/elyan_tile_1_logo.jpg",
  "foundingLocation": "Lake Charles, Louisiana"
}
```

### 1.3 Images Missing Alt Text
**5 images on homepage** and **10 images on vintage-voice.html** lack meaningful alt text.

**Impact:** Screen readers can't describe images, and Google Image Search can't index them.

### 1.4 No sitemap.xml / robots.txt
(Addressed in separate PR #2959)

---

## 2. Important Issues (Fix Soon)

### 2.1 Missing OG Tags on Subpages
Only homepage has OG tags. `vintage-voice.html` and `contact.html` need them.

### 2.2 No Twitter Cards on Subpages
Only homepage has Twitter Card meta. Add to all pages.

### 2.3 Font Loading
Crimson Pro and IBM Plex Sans add ~2 round-trips. Consider preloading critical fonts.

---

## 3. Quick Wins

- Add `<meta name="robots" content="index, follow">`
- Add `favicon.ico` for legacy browsers
- Minify inline CSS (~500+ lines) to cached `.css` file
- Add BreadcrumbList schema for subpages

---

## 4. Page-by-Page Scores

| Page | Meta | OG | Canonical | Schema | Alt Text | Score |
|------|------|----|-----------|--------|----------|-------|
| `/` | ✅ | ✅ | ❌ | ❌ | ❌ | 55 |
| `/vintage-voice.html` | ✅ | ❌ | ❌ | ❌ | ❌ | 40 |
| `/contact.html` | ✅ | ❌ | ❌ | ❌ | N/A | 45 |

**Average: ~47/100**

---

## 5. Priority Action Plan

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| 🔴 P0 | Add canonical URLs | High | 5 min |
| 🔴 P0 | Add structured data | High | 15 min |
| 🔴 P0 | Add alt text to all images | High | 10 min |
| 🟠 P1 | Add sitemap.xml + robots.txt | Medium | Done ✅ |
| 🟠 P1 | Add OG tags to subpages | Medium | 5 min |
| 🟡 P2 | Preload fonts | Low | 5 min |
| 🟢 P3 | Add favicon.ico | Low | 2 min |

---

_Wallet: RTCb72a1accd46b9ba9f22dbd4b5c6aad5a5831572b_
