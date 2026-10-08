# Campus Customs: Design Rationale (P10)

**Goal:** make the storefront feel unmistakably *Yale*. It should stir Yale pride, and it should read as an established, Yale-rooted shop rather than a knock-off site selling discount merch. All P1–P9 functionality is unchanged: catalogue, filters, product pages, login, and the chat agent with memory, page context, alternatives, and clarifying questions.

---

## 1. It looks truly Yale

| Design choice | Why it reads as Yale |
|---|---|
| **Yale Blue `#00356b` as the anchor color**, with white and Yale's lighter blues (`#286dc0`, `#63aaff`) as accents only | Yale Blue is the university's signature color. Using one deep navy everywhere (nav button, hero, footer, prices, active filters, chat) makes the site feel like part of Yale's visual world. No off-brand reds, oranges or gradients-for-their-own-sake. |
| **Serif headlines (Libre Caslon)** + clean sans-serif body (Inter) | Old-style serifs are the language of Yale's crests, diplomas and building inscriptions. Caslon is a classic 18th-century face with an academic feel. Inter keeps prices, sizes and filters crisp and modern. |
| **Uppercase, letter-spaced labels** ("SHOP BY CATEGORY", "HARVARD–YALE · THE GAME") | The varsity and collegiate signage look, used sparingly as section kickers so headlines stay calm. |
| **Pinstripe texture in the hero** | A barely visible vertical stripe, like a varsity knit or rugby stripe, adds richness without noise. |
| **Heritage cream (`#faf8f3`)** for story sections | Evokes old paper and archival photos, separating "our story" from "shop now" while staying in the Yale palette. |
| **Handsome Dan** as the chatbot (launcher, header avatar, message avatar, welcome, home promo, footer) | Dan is Yale's bulldog, the most beloved Yale symbol after the "Y" itself. The art is cut out of **a graphic on Campus Customs' own merchandise** (the District V.I.T. vintage bulldog crewnecks), cleaned up as crisp navy-and-white illustrations. The mascot comes from the store's own shelves, not from clip art. |

## 2. It invokes Yale pride

- **"Wear Yale. Every day."** The hero headline speaks to identity, not discounts. The italic "Every day." gives it warmth.
- **Represent section: "Your college. Your school. Your team."** Three panels with direct links to every **residential college** with merch (Benjamin Franklin → Trumbull), every **graduate & professional school** (Law, SOM, Medicine, Nursing, Public Health, Engineering, Art, Architecture, Music, Divinity, Environment), and **14 Bulldog sports**. Shoppers find *their* corner of Yale in one click. Each link was checked to return real products.
- **"Gear up for The Game."** A full-width Harvard–Yale feature ("The rivalry that started in 1875") built around the store's 2025 The Game tee. Tradition and rivalry are core to Yale pride.
- **Local, specific references:** Old Campus, the Bowl, Ingalls Rink, Broadway. They signal that the shop is part of campus life, not a generic merch site.
- **Handsome Dan as the guide.** "Ask Handsome Dan" turns help into a moment of school spirit. The agent's persona allows an occasional "Boola boola!" but stays a helpful associate first, and says it's the store's virtual assistant if asked.
- **Product imagery on contrasting backdrops** (from P9) makes crests, wordmarks and the "Y" pop: navy on white, heather and cream on charcoal.

## 3. It reads as an established, Yale-rooted shop, not a knock-off

Knock-off merch sites share a look: loud sale banners, countdown timers, "70% OFF", stock photos, clashing colors, crowded grids. This design deliberately does the opposite.

| Knock-off signal | What this site does instead |
|---|---|
| Discount banners, "SALE", strike-through prices, urgency timers | **No discounts or fake urgency anywhere.** Prices are shown once, plainly ($32–$98). The announcement bar carries **heritage** ("Yale apparel since 1975 · Family-run on Broadway, New Haven"), not promotions. |
| Anonymous seller | **A real place and history**: Broadway, New Haven, since 1975, second-generation family business. This appears in the announcement bar, hero stats ("1975 · On Broadway since"), a full-width heritage section with an oversized serif "1975", the footer, and the About page. |
| Vague product info | **Specific, honest product data**: exact sizes in stock on every card (sold-out sizes crossed out), color swatches, real descriptions, per-size stock on product pages. "Live stock shown per size" is a reassurance we can actually back up. |
| Cluttered, inconsistent layouts | **Generous whitespace, consistent grid, restrained motion.** Cards lift slightly on hover, and a "View details" bar appears. Everything sits on a 1240px grid with 4–5rem section spacing. |
| Messy product photos | Uniform cutouts on color-matched backdrops (P9), tidied product names ("UA Men's Tech L/S 2.0", "¼-Zip", "V.I.T.") without changing the database. |
| Bots that feel bolted on | Chat styled as part of the site: same navy, serif header, Dan avatar on every reply, an "online" dot, a gentle one-time "Ask Handsome Dan" teaser, entry points in the hero, the home promo, product pages ("Ask Handsome Dan about this"), and the footer. Chat results open as a branded banner ("Handsome Dan found these for you"). |
| Trust badges that claim too much | **Only claims we can support**: family-run since 1975, in-house screen printing and embroidery (from Campus Customs' own description of its business), every college/school/team (verified against the catalogue), and help from Dan. |

### A note on "supported by Yale"

The design makes the shop *look and feel* Yale-rooted and premium, but **the site does not claim to be officially licensed or endorsed by Yale**, because we couldn't verify that. A false endorsement claim is exactly what would make a shop untrustworthy. If Campus Customs holds a license through Yale's Office of Trademark Licensing, the strongest next step would be to add the official "Officially Licensed Product" mark to the footer and product pages. The design has a natural place for it in the trust strip and the product-page reassurance list. Likewise, Handsome Dan and the "Y" are Yale marks, so a production site should confirm they're covered by that license.

---

## What changed (files)

| Area | Change |
|---|---|
| Design tokens | `src/index.css`: Yale Blue palette, Libre Caslon + Inter (Google Fonts in `index.html`), radii, shadows, 1240px container |
| Stylesheet | `src/App.css` rewritten as one organized design system (nav, footer, home, cards, filters, detail, about, auth, chat, responsive) |
| Brand helpers | `src/brand.ts`: Handsome Dan assets, `displayName()` (name tidying), color `swatch()` map, `openChat()` event, college/school/sport lists |
| Handsome Dan art | `backend/scripts/make_mascot.py` extracts the bulldog from two product photos → `frontend/public/handsome-dan-head.png` (launcher/avatars/favicon) and `handsome-dan.png` (full figure in "Y" sweater) as crisp two-tone navy/white art |
| Nav & footer | Announcement bar; white sticky nav with "CC" seal and underline-on-hover links; navy footer with Dan |
| Home | Hero with copy, stats and a 3-product collage; trust strip; category tiles; Represent (colleges/schools/sports); The Game feature; Campus favorites; Ask Handsome Dan promo with one-tap prompts; 1975 heritage band |
| Product cards | Tidied names, serif titles, size availability row, color swatches, "Selling fast" badge (≥ 2 sizes with ≤ 5 left), hover "View details" |
| Product detail | Swatches, low-stock emphasis, "Ask Handsome Dan about this" (opens chat with the size question; P8 page context does the rest), honest reassurance list |
| Chat | Handsome Dan launcher (head cutout, online dot), teaser, branded header, welcome with full Dan, avatar on each reply. Persona renamed in `config.py` + `prompt.md` |
| Search | Storefront search now matches word starts ("art" no longer matches "qu**art**er-zip"), needed for the School of Art link |

**Verified:** build passes, no new lint issues, `test_tools.py` 14/14, home/product/chat checked in the browser at desktop and mobile widths (no horizontal overflow), and the chat flow (prompt → clarifying question → quick-reply chips) still works.
