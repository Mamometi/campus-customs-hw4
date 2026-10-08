# Campus Customs: Usability Improvements (P9)

Four improvements, two on the storefront and two in the chatbot. For each: the problem, why it matters, what was built, and how it was checked against the real database.

---

## Frontend

### 1. Filter the catalogue by category and size

**Problem.** The catalogue has 102 products, and the Products page only offered a category filter and keyword search. A shopper who wears a size M had no way to see only what they can actually buy. Stock is uneven: **145 of 612 size rows are sold out**, and a product can be in stock overall but gone in your size. Shoppers had to click into product after product to find out.

**Why it matters.** Size is the first question for apparel. Filtering by it removes dead ends ("I love this… oh, not in my size") and saves the most frustrating clicks. Pairing it with category ("Hoodies in XS") matches how people shop: *what kind of item* plus *will it fit me*.

**What was built.**
- Two labeled filter rows on `/products`: **Category** (All, Hoodies, Quarter-Zips, T-Shirts, Crewnecks, Long Sleeve, Jackets & Fleece) and **Size** (Any, XS–XXL).
- Each size chip shows **how many items are in stock in that size**, and the counts update with the chosen category (e.g. Hoodies: XS 21, S 23, M 21…). Sizes with 0 items are disabled.
- The size filter means **in stock in that size**, not just "offered in that size".
- Filters live in the URL (`/products?category=Hoodies&size=XS`), so they're shareable and survive Back/refresh. The page title reads "Hoodies in size XS", with a "Showing 21 items… · Clear all filters" summary.
- Backend: `GET /api/products?size=` and `GET /api/sizes?category=`.

**Checked.** Hoodies + XS = 21 cards (SQL: 21). Size M across all = 80 (SQL: 80). "Clear all filters" returns to 102.

---

### 2. Product backgrounds that contrast with the merch

**Problem.** The product photos came from different sources: **74 of 102 had black backgrounds or black letterbox bars, and 28 had white studio backgrounds**, mixed at random. Navy hoodies sat on black (low contrast, garment outline lost), white letterbox bars showed up around some photos, and the grid looked patchy and unfinished.

**Why it matters.** Product imagery is the main thing a shopper evaluates in a clothing store. A consistent, high-contrast presentation (dark merch on white, light merch on dark) makes each garment's shape and graphic easy to read at thumbnail size, and makes the store look professional and trustworthy, which affects whether people buy.

**What was built.** `backend/scripts/make_cutouts.py` (offline, run once):
1. Removes each photo's background: every **near-pure black or near-pure white, colorless region connected to the image border** (the bars + studio backdrop). Tight thresholds keep navy shadows (blue-tinted) and off-white tees (~240) intact.
2. Smooths the edge (1px erode + slight blur) to hide JPEG halos.
3. Measures the garment's median brightness: **dark merch → white backdrop, light merch (white, cream, heather gray) → charcoal backdrop**. Result: 51 on white, 51 on charcoal.
4. Writes transparent WebP cutouts to `data/products_cutout/` plus `manifest.json`. **Original photos are untouched.** Safety net: if a cut keeps < 15% of the image, the original is used instead (0 needed after tuning).

The product data now includes `display_image_url` and `image_bg`. Every image frame (catalogue cards, product detail, home hero, category tiles, chat cards) paints `image_bg` behind the cutout with breathing room. Products without a cutout fall back to the original photo on white.

**Checked.** Visual QA contact sheet of all 102. A first pass damaged 6 dark-on-black garments and 1 white-on-white tee; thresholds were tightened until all 102 were clean.

---

## Chatbot (backend)

### 3. Recommend similar products when something is unavailable

**Problem.** Many requests can't be filled exactly: a size is sold out (145 sold-out size rows), a color doesn't exist (no pink, purple, or orange in the catalogue), a product type isn't sold (shorts, hats, mugs), or nothing fits a budget (no hoodie under $45). Before this change the bot often stopped at "sorry, we don't have that." It also had a bug where "shorts" matched "short-sleeve" tees and was presented as a match.

**Why it matters.** "No" is where a sale is lost. A good store associate says "we're out of XL in that one, but the lacrosse crewneck is the same style and price, and it's in XL." Offering a close, **in-stock** substitute keeps the shopper engaged, improves their experience, and raises the chance they buy something from Campus Customs instead of leaving.

**What was built.** Alternatives are built into the tools, so the model can't forget them:
- `check_stock`: when the requested size is sold out, the result automatically includes 3 `alternatives` in stock in that size, plus a summary sentence naming them.
- `search_products`: when nothing matches, it fills `alternatives` + `alternatives_reason` by **relaxing filters in a sensible order**: color → price (cheapest first) → size → category (keeping keywords, e.g. "Saybrook" hoodie → Saybrook crewneck/tee/fleece) → popular in-stock picks.
- **Color families**: pink/rose/salmon → dusty coral; maroon → red; beige → cream/ivory, etc. The note tells the agent to say so honestly.
- **Not-carried items** (shorts, pants, hats, beanies, mugs…) return "We don't carry X" plus the closest category (shorts → tees, beanie → fleece), keeping theme words ("hockey shorts" → hockey tees).
- `find_alternatives` ranks by **similarity**: same category, shared college/sport/graphic words, shared colors, closest price.
- Every product summary now carries exact `quantity_by_size`. The bot once said "only 1 left" when the DB had 5, so it now quotes real numbers.
- Prompt: "Never a dead end". Be honest first, then recommend 2–3 in-stock items with a one-line reason each, as clickable cards.

**Checked** (live, guest):

| Customer | Bot |
|---|---|
| "Baseball Left Chest Crewneck in XL" | Sold out in XL; available S, M, L, XXL; suggests Lacrosse ($58, same style), Diving ($58, 5 left in XL: SQL 5 ✔), Davenport |
| "any pink shirts?" | No pink; closest is Big Yale Tri Blend Tee in dusty coral |
| "Yale gym shorts" | Don't carry shorts; 3 in-stock athletic tees |
| "hoodies under $30?" | None under $30; cheapest are UA Gameday and Yale Sports Tennis at $45 |

`test_tools.py` has 4 new tests (14 total, all pass).

---

### 4. Ask a clarifying question when a request is vague

**Problem.** Requests like "I need a gift for my dad", "show me something nice", or "something warm" have many valid answers. Before this change the bot guessed: it picked a search, dumped results, and hoped. Guessing often shows the wrong items and makes the customer start over.

**Why it matters.** One quick question ("Hoodie, crewneck, tee, or quarter-zip?") gets the customer to the *right* product faster than a page of guesses. It's what a helpful associate does. Tappable answers make it nearly effortless, especially on mobile.

**What was built.**
- `AgentReply.quick_replies` (structured output): 2–4 short answers shown as **tappable chips** under the bot's question. Tapping one sends it as the customer's reply, and the chips disappear.
- Prompt section "Ask clarifying questions instead of guessing", with examples (gift / something nice / my size / something warm / my college) and guardrails:
  - **Don't ask if the request is specific enough** ("navy hoodie in M" → just search).
  - One question about the **most important missing detail**, never two clarifying turns in a row.
  - No search and no page results while asking.
  - Use known context first (the product being viewed, the logged-in customer's earlier chats).

**Checked** (live):

| Customer | Bot |
|---|---|
| "I need a gift for my dad" | "What kind of item?" chips: Hoodie · Crewneck · T-shirt · Quarter-zip. Tap **Hoodie** → Yale Dad Hoodie, $68 |
| "show me something nice" | Asks which style. Chips: Classic Yale · My college · A sport · School / grad |
| "I need something warm" (browser) | "Pullover or zip-up?" Tap **Hoodie** → page shows all 27 hoodies |
| "navy hoodie in M" | **No question**: 19 results straight away |
