# Widby Outreach Experiment Framework — Specification

**Status:** Draft
**Author:** Antwoine Flowers / Kael
**Date:** 2026-04-03
**Classification:** Internal IP — Covariance
**Parent Spec:** Widby Algo Spec V1.1
**Relationship:** This framework is a module inside Widby that generates behavioral ground-truth data to calibrate the niche scoring algorithm — specifically the rentability signal that no SERP data can provide.

---

## 1. Purpose

Every signal in Widby's algo spec is a proxy. CPC proxies for lead value. Business density proxies for monetization potential. Review count proxies for competition difficulty. None of them answer the question rank-and-rent practitioners actually care about: **"If I build a site here, will a business pay me for the leads?"**

This framework answers that question empirically by:

1. Scanning real businesses in target niches and metros for SEO weaknesses
2. Generating personalized site audits that demonstrate the problem
3. Delivering those audits via cold outreach with controlled A/B variants
4. Measuring business response behavior (open, click, reply, intent)
5. Feeding response data back into Widby's scoring model as a **rentability signal**
6. Optionally routing interested businesses to partner SEO agencies for referral revenue

The outreach is the experiment. The data is the product.

---

## 2. System Overview

```
WIDBY ALGO SPEC (existing)              EXPERIMENT FRAMEWORK (this spec)
──────────────────────────              ────────────────────────────────
                                        
Phase 0: Config                    ──→  Experiment Config
Phase 1: Keyword Expansion               (inherits niche + metro targets)
Phase 2: Data Collection           ──→  Business Discovery
Phase 3: Signal Extraction         ──→  Business Qualification + Site Scanning
Phase 4: Scoring                   ←──  Rentability Signal (feedback)
Phase 5: Classification                  
Phase 6: Feedback Logging          ←──  Experiment Outcome Data
                                        
                                        Audit Generation
                                        Outreach Delivery
                                        Response Tracking
                                        A/B Analysis
                                        Rentability Model Update
```

### Processing Phases

| Phase | Name | Input | Output | Timing |
|-------|------|-------|--------|--------|
| E0 | Experiment Config | Niche + metro + variants | Validated experiment plan | Manual trigger |
| E1 | Business Discovery | Niche + metro | Qualified business list | Minutes |
| E2 | Site Scanning | Business URLs | Per-business audit data | 5-15 min per batch |
| E3 | Audit Generation | Scan data + variant template | Hosted HTML audit pages | 1-3 min per business |
| E4 | Outreach Delivery | Audits + email templates + contact info | Sent emails | Throttled over days |
| E5 | Response Tracking | Email events + replies | Classified response data | Ongoing (14-day window) |
| E6 | Analysis + Feedback | Response data | Rentability scores + A/B results | After experiment window closes |

---

## 3. Phase E0 — Experiment Configuration

### 3.1 Experiment Definition

```json
{
  "experiment_id": "uuid",
  "created_at": "2026-04-03T12:00:00Z",
  "status": "draft",

  "targeting": {
    "niche_keyword": "plumber",
    "cbsa_code": "38060",
    "cbsa_name": "Phoenix-Mesa-Chandler, AZ",
    "sample_size": 100,
    "business_filters": {
      "min_reviews": 0,
      "max_reviews": null,
      "has_website": true,
      "min_gbp_completeness": null,
      "exclude_chains": true
    }
  },

  "variants": [
    {
      "variant_id": "A",
      "name": "problem_focused",
      "audit_depth": "standard",
      "email_template": "problem_focused_v1",
      "value_prop": "problem",
      "allocation_pct": 0.50
    },
    {
      "variant_id": "B",
      "name": "competitor_comparison",
      "audit_depth": "visual_mockup",
      "email_template": "competitor_v1",
      "value_prop": "competitor_comparison",
      "allocation_pct": 0.50
    }
  ],

  "assignment_method": "stratified_random",
  "stratification_field": "site_quality_bucket",

  "outreach_config": {
    "sending_domain": "insights.widby.co",
    "daily_send_limit": 30,
    "follow_up_schedule": [3, 7],
    "experiment_window_days": 21
  },

  "agency_partner": {
    "partner_id": "uuid",
    "partner_name": "Phoenix SEO Co",
    "referral_url": "https://calendly.com/phoenix-seo/consult",
    "referral_fee_type": "flat",
    "referral_fee_amount": 250
  }
}
```

### 3.2 Variant Dimensions

Each experiment tests one or more dimensions. Only vary one dimension per experiment for clean attribution.

| Dimension | Options | What It Tests |
|-----------|---------|--------------|
| `audit_depth` | `minimal`, `standard`, `visual_mockup` | Does showing more detail increase response? |
| `value_prop` | `problem`, `revenue_loss`, `competitor_comparison`, `opportunity` | Which framing resonates by niche? |
| `email_length` | `short` (3 sentences), `medium` (1 paragraph + bullets), `detailed` (full analysis) | Attention span vs. credibility tradeoff |
| `personalization_level` | `generic`, `site_specific`, `competitor_aware` | How much personalization moves the needle? |
| `cta_type` | `reply`, `book_call`, `view_full_report` | What action are businesses willing to take? |

### 3.3 Statistical Requirements

```python
# Minimum sample size per variant for 80% power at p < 0.05
# Assuming baseline response rate of 5%, minimum detectable effect of 5 percentage points
# (i.e., detecting a lift from 5% to 10%)

MINIMUM_SAMPLE_PER_VARIANT = 200

# For early-stage experiments with smaller samples:
# Use Bayesian analysis instead of frequentist significance testing
# Report posterior probability that variant B > variant A
# Decision threshold: 90% posterior probability

# Practical minimum for directional signal:
MINIMUM_SAMPLE_DIRECTIONAL = 50  # per variant
```

### 3.4 Experiment Lifecycle

```
DRAFT → DISCOVERY → SCANNING → GENERATING → SENDING → TRACKING → ANALYSIS → CLOSED
                                                         ↑
                                                    (21-day window)
```

---

## 4. Phase E1 — Business Discovery

### 4.1 Data Source

Primary: DataForSEO Business Listings API (already used in Widby's Phase 2).
Secondary: DataForSEO Google Maps SERP API for local pack businesses.

### 4.2 Discovery Query

```python
def discover_businesses(niche_keyword, cbsa_code, sample_size, filters):
    """
    Pull candidate businesses from DataForSEO Business Listings.
    Returns more candidates than sample_size to allow for filtering.
    """
    # Step 1: Map niche keyword to business category
    category = map_niche_to_category(niche_keyword)
    # e.g., "plumber" → "Plumber" (Google business category)

    # Step 2: Pull listings for the metro area
    listings = dataforseo_business_listings_search(
        category=category,
        location_code=cbsa_to_dataforseo_location(cbsa_code),
        limit=sample_size * 3  # over-fetch for filtering headroom
    )

    # Step 3: Filter
    candidates = []
    for listing in listings:
        if filters.get("has_website") and not listing.domain:
            continue
        if filters.get("exclude_chains") and is_chain(listing):
            continue
        if filters.get("min_reviews") and listing.review_count < filters["min_reviews"]:
            continue
        if filters.get("max_reviews") and listing.review_count > filters["max_reviews"]:
            continue
        candidates.append(listing)

    # Step 4: Sample to target size
    if len(candidates) > sample_size:
        candidates = stratified_sample(candidates, sample_size, strat_field="site_quality_bucket")

    return candidates
```

### 4.3 Business Record Schema

```json
{
  "business_id": "uuid",
  "experiment_id": "uuid",
  "variant_id": "A",

  "business_data": {
    "name": "Joe's Plumbing",
    "category": "Plumber",
    "address": "123 Main St, Phoenix, AZ 85001",
    "phone": "602-555-1234",
    "domain": "joesplumbing.com",
    "website_url": "https://joesplumbing.com",
    "gbp_url": "https://maps.google.com/...",
    "review_count": 23,
    "rating": 4.2,
    "gbp_completeness": 0.57,
    "years_in_business": null
  },

  "contact": {
    "email": null,
    "email_source": null,
    "email_confidence": null,
    "contact_name": null,
    "contact_role": null
  },

  "qualification": {
    "site_quality_bucket": null,
    "seo_weakness_score": null,
    "scan_completed": false,
    "audit_generated": false,
    "outreach_eligible": false,
    "disqualification_reason": null
  }
}
```

### 4.4 Email Discovery

DataForSEO Business Listings often don't include email addresses. Email discovery is a separate step:

| Method | Source | Reliability | Cost |
|--------|--------|------------|------|
| GBP profile | DataForSEO My Business Info | Medium — many businesses don't list email | Included in existing API calls |
| Website scrape | Headless browser on business domain | High — most small biz sites have contact page | ~$0.01/site (compute) |
| Pattern inference | firstname@domain.com, info@domain.com | Low — high bounce risk | Free but risky |
| Email finder API | Hunter.io, Apollo, Snov.io | High | $0.01-0.05/lookup |

**Recommendation for V1:** Scrape the website contact page first (free, high quality). Fall back to Hunter.io for businesses where scraping fails. Budget $0.03/business for email discovery.

**Disqualification:** If no email can be found with reasonable confidence, the business is marked `outreach_eligible: false` with `disqualification_reason: "no_email_found"`. Do not guess.

---

## 5. Phase E2 — Site Scanning

### 5.1 Scan Pipeline

For each business with a website, run the following scans:

```python
def scan_business_site(business):
    """
    Comprehensive site scan producing audit data.
    Uses a combination of DataForSEO APIs and direct scanning.
    """
    url = business.website_url
    results = {}

    # 1. Lighthouse performance audit
    results["lighthouse"] = dataforseo_lighthouse(url)
    # Returns: performance_score, accessibility_score, seo_score, best_practices_score

    # 2. On-page SEO signals
    results["onpage"] = dataforseo_onpage_instant(url)
    # Returns: title, description, h1, h2s, canonical, schema_types,
    #          word_count, internal_links, external_links, images_without_alt

    # 3. Mobile responsiveness
    results["mobile"] = {
        "is_mobile_friendly": results["lighthouse"].get("mobile_friendly", None),
        "viewport_configured": results["onpage"].get("has_viewport", None),
    }

    # 4. Schema markup check
    results["schema"] = {
        "has_local_business_schema": "LocalBusiness" in results["onpage"].get("schema_types", []),
        "has_organization_schema": "Organization" in results["onpage"].get("schema_types", []),
        "schema_types_found": results["onpage"].get("schema_types", []),
    }

    # 5. Core Web Vitals (from Lighthouse)
    results["cwv"] = {
        "lcp": results["lighthouse"].get("lcp", None),
        "fid": results["lighthouse"].get("fid", None),
        "cls": results["lighthouse"].get("cls", None),
    }

    # 6. Content quality signals
    results["content"] = {
        "word_count": results["onpage"].get("word_count", 0),
        "has_service_pages": detect_service_pages(results["onpage"]),
        "has_location_pages": detect_location_pages(results["onpage"]),
        "images_without_alt": results["onpage"].get("images_without_alt", 0),
        "title_includes_city": business.city.lower() in results["onpage"].get("title", "").lower(),
        "title_includes_niche": business.niche.lower() in results["onpage"].get("title", "").lower(),
    }

    # 7. Competitor comparison (optional, for competitor_comparison variant)
    # Pull the top 3 organic results for "{niche} in {city}" and compare
    results["competitor_comparison"] = None  # populated in audit generation if needed

    return results
```

### 5.2 SEO Weakness Score

Each business gets a composite weakness score indicating how much room for improvement exists. **Higher score = more problems = better outreach target** (they have the most to gain from SEO help).

```python
def seo_weakness_score(scan_results):
    """
    Score from 0-100 indicating how many SEO problems the site has.
    Higher = more problems = better outreach candidate.
    """
    issues = []

    # Performance
    perf = scan_results["lighthouse"].get("performance_score", 50)
    if perf < 50:
        issues.append(("slow_site", 15))
    elif perf < 75:
        issues.append(("moderate_speed", 8))

    # SEO basics
    seo_score = scan_results["lighthouse"].get("seo_score", 50)
    if seo_score < 50:
        issues.append(("poor_seo_basics", 15))
    elif seo_score < 80:
        issues.append(("mediocre_seo_basics", 8))

    # Schema
    if not scan_results["schema"]["has_local_business_schema"]:
        issues.append(("missing_local_schema", 12))

    # Mobile
    if not scan_results["mobile"]["is_mobile_friendly"]:
        issues.append(("not_mobile_friendly", 15))

    # Content
    if scan_results["content"]["word_count"] < 300:
        issues.append(("thin_content", 10))
    if not scan_results["content"]["title_includes_city"]:
        issues.append(("no_city_in_title", 8))
    if not scan_results["content"]["title_includes_niche"]:
        issues.append(("no_niche_in_title", 8))
    if not scan_results["content"]["has_service_pages"]:
        issues.append(("no_service_pages", 10))
    if scan_results["content"]["images_without_alt"] > 3:
        issues.append(("missing_alt_text", 5))

    # Core Web Vitals
    lcp = scan_results["cwv"].get("lcp", 0)
    if lcp and lcp > 4000:  # > 4 seconds
        issues.append(("poor_lcp", 8))
    cls = scan_results["cwv"].get("cls", 0)
    if cls and cls > 0.25:
        issues.append(("poor_cls", 5))

    total = sum(weight for _, weight in issues)
    return clamp(total, 0, 100), issues
```

### 5.3 Qualification Gates

```python
def qualify_for_outreach(business, scan_results, weakness_score):
    """
    Determine if this business should receive outreach.
    """
    # Must have a website to audit
    if not business.website_url:
        return False, "no_website"

    # Must have a discoverable email
    if not business.contact.email:
        return False, "no_email_found"

    # Must have meaningful SEO problems (otherwise audit has no value)
    if weakness_score < 20:
        return False, "site_already_good"

    # Must not be a chain/franchise (they have corporate SEO teams)
    if is_chain(business):
        return False, "chain_franchise"

    # Must have a real site (not a Facebook page, Yelp redirect, etc.)
    if is_social_redirect(business.website_url):
        return False, "social_redirect_not_real_site"

    return True, None
```

### 5.4 Site Quality Bucketing

For stratified random assignment to variants:

```python
def bucket_site_quality(weakness_score, review_count, gbp_completeness):
    """
    Assign businesses to quality buckets for stratified sampling.
    Ensures each variant gets a representative mix.
    """
    # Combine into a composite "business maturity" signal
    maturity = (
        inverse_scale(weakness_score, 0, 100) * 0.40 +  # better site = more mature
        scale(review_count, 0, 100) * 0.30 +
        gbp_completeness * 100 * 0.30
    )

    if maturity >= 70:
        return "established"    # decent site, many reviews, active GBP
    elif maturity >= 40:
        return "developing"     # some effort but significant gaps
    else:
        return "nascent"        # minimal online presence, most to gain
```

---

## 6. Phase E3 — Audit Generation

### 6.1 Audit Depth Tiers

| Tier | Contents | Generation Cost | When to Use |
|------|----------|----------------|-------------|
| `minimal` | 3-5 bullet point issues, text only | ~$0.01 (LLM) | A/B test: does less work still convert? |
| `standard` | Scored audit with issue details, competitor gap summary, prioritized fix list | ~$0.03 (LLM) | Default tier |
| `visual_mockup` | Everything in standard + HTML rendering of their site with annotations showing problems + a "fixed" version showing improvements | ~$0.08 (LLM + rendering) | Premium tier for high-value tests |

### 6.2 Audit Page Architecture

Each audit is a hosted HTML page with a unique URL per business. The page serves dual purposes: it's the deliverable that creates the "oh shit" moment, and it's a tracking pixel that tells us the business engaged.

```
https://insights.widby.co/audit/{audit_id}

┌─────────────────────────────────────────────┐
│  SEO Health Report for Joe's Plumbing       │
│  Generated April 3, 2026                    │
├─────────────────────────────────────────────┤
│                                             │
│  Overall Score: 38/100                      │
│  [visual score bar — red/yellow/green]      │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │  YOUR SITE          COMPETITOR  │        │
│  │  [screenshot]       [screenshot]│        │
│  │  Score: 38          Score: 82   │        │
│  └─────────────────────────────────┘        │
│                                             │
│  Top Issues Found:                          │
│  1. Missing LocalBusiness schema markup     │
│  2. Site loads in 6.2 seconds (target: <3s) │
│  3. No city name in page title              │
│  4. No dedicated service pages              │
│  5. Missing alt text on 8 images            │
│                                             │
│  What This Means For Your Business:         │
│  You're currently invisible to 73% of       │
│  customers searching for plumbers in        │
│  Phoenix. Your top competitor ranks for     │
│  12 keywords you don't appear for.          │
│                                             │
│  ┌─────────────────────────────────┐        │
│  │  Want help fixing this?         │        │
│  │  [Book a Free Consultation]     │        │
│  │  (routes to partner agency)     │        │
│  └─────────────────────────────────┘        │
│                                             │
│  Powered by Widby                           │
└─────────────────────────────────────────────┘
```

### 6.3 Audit Generation Pipeline

```python
def generate_audit(business, scan_results, weakness_issues, variant):
    """
    Generate a personalized audit page for the business.
    Returns a hosted URL.
    """
    # Step 1: Prepare audit data
    audit_data = {
        "business_name": business.name,
        "business_url": business.website_url,
        "niche": business.category,
        "city": business.city,
        "overall_score": 100 - scan_results.weakness_score,
        "issues": weakness_issues,
        "lighthouse_scores": scan_results["lighthouse"],
        "cwv": scan_results["cwv"],
        "schema_status": scan_results["schema"],
        "content_analysis": scan_results["content"],
    }

    # Step 2: Generate competitor comparison (if variant requires it)
    if variant.audit_depth == "visual_mockup" or variant.value_prop == "competitor_comparison":
        top_competitor = get_top_organic_result(business.niche, business.city)
        audit_data["competitor"] = {
            "name": top_competitor.name,
            "url": top_competitor.url,
            "score": top_competitor.lighthouse_seo_score,
            "keywords_ranking": top_competitor.keyword_count,
        }

    # Step 3: Generate audit HTML
    if variant.audit_depth == "minimal":
        html = generate_minimal_audit(audit_data)
    elif variant.audit_depth == "standard":
        html = generate_standard_audit(audit_data)
    elif variant.audit_depth == "visual_mockup":
        # Uses headless browser to capture screenshots
        screenshots = capture_site_screenshots(business.website_url)
        audit_data["screenshots"] = screenshots
        html = generate_visual_audit(audit_data)

    # Step 4: Host the audit page
    audit_id = generate_uuid()
    hosted_url = host_audit_page(audit_id, html)
    # Supabase Storage or Vercel static deploy

    # Step 5: Embed tracking
    # The hosted page includes a 1x1 tracking pixel and JS event tracking
    # Events: page_load, scroll_depth_25/50/75/100, cta_click, time_on_page

    return {
        "audit_id": audit_id,
        "url": hosted_url,
        "generated_at": datetime.now().isoformat(),
        "variant_id": variant.variant_id,
        "audit_depth": variant.audit_depth,
    }
```

### 6.4 LLM-Generated Audit Copy

The audit narrative is generated by Claude, not templated. This ensures each audit reads as genuinely personalized rather than fill-in-the-blank.

```python
AUDIT_GENERATION_PROMPT = """
You are an SEO consultant preparing a site audit for a local business.
Write a concise, professional audit report for {business_name}, a {niche} in {city}.

Site scan results:
{scan_results_json}

Rules:
- Lead with the most impactful finding (the one that costs them the most business)
- Use plain language — the reader is a business owner, not an SEO professional
- Quantify impact where possible ("You're missing ~X potential customers per month")
- Do NOT be salesy or pushy. Be helpful and factual.
- Do NOT mention Widby or any brand in the audit body
- Keep it under 300 words
- End with 3 prioritized recommendations they could act on

Value proposition angle: {value_prop}
- "problem": Focus on what's broken and why it matters
- "revenue_loss": Estimate lost revenue from poor SEO
- "competitor_comparison": Compare their site to the top-ranking competitor
- "opportunity": Focus on untapped potential rather than problems
"""
```

---

## 7. Phase E4 — Outreach Delivery

### 7.1 Email Infrastructure Decision

This is the most consequential infrastructure choice for the experiment framework. Three viable options:

| Option | How It Works | Pros | Cons | Cost |
|--------|-------------|------|------|------|
| **Resend + custom domain** | Resend API sends via your domain (insights.widby.co). You manage domain warming, reputation. | Full control, integrates with Supabase Edge Functions, cheapest at scale | You own deliverability — if you burn the domain, you start over. No built-in warmup. | $0.001/email + domain costs |
| **Instantly.ai** | Managed cold email platform. Handles domain warming, rotation, deliverability optimization, reply detection. | Battle-tested for cold outreach, auto-warmup, built-in A/B testing, reply tracking | Less control, another vendor dependency, data lives in their platform | $30-97/month + sending accounts |
| **Smartlead** | Similar to Instantly but with more API access and multi-channel (email + LinkedIn). | Good API, webhook support for Supabase integration, multi-sender rotation | More complex setup, potential overkill for V1 | $39-94/month |

**Recommendation:** Start with **Instantly** for the experiment phase. The domain warming and deliverability management alone is worth the $30-97/month. You're running experiments, not building an email platform. Once you've validated the model and need tighter integration, evaluate migrating to Resend + custom infrastructure.

**Critical regardless of platform:**
- Dedicated sending domain (NOT widby.com — use a separate domain like widbyinsights.com)
- SPF, DKIM, DMARC properly configured
- Warm the domain for 2-3 weeks before first experiment send
- Maximum 30-50 sends/day/domain during experiment phase
- Dedicated reply inbox monitored by the system

### 7.2 Email Templates

Each variant has a corresponding email template. Templates use merge fields populated from the audit data.

**Template: problem_focused_v1**

```
Subject: {business_name} — your site is losing you customers in {city}

Hi {contact_name | "there"},

I ran an SEO analysis on {domain} and found a few things that are likely costing you leads.

The biggest issue: {top_issue_plain_language}

I put together a quick report showing what I found and how it compares to your top-ranking competitor:

{audit_url}

No pitch here — just thought you'd want to know.

Best,
{sender_name}

---
{sender_name}
Widby SEO Insights
{unsubscribe_link}
```

**Template: competitor_comparison_v1**

```
Subject: How {business_name} compares to {competitor_name} on Google

Hi {contact_name | "there"},

I was researching {niche_plural} in {city} and noticed {competitor_name} is ranking above {business_name} for most local searches.

I dug into why and put together a side-by-side comparison:

{audit_url}

The gap is fixable — your competitor isn't doing anything special, they're just doing the basics that your site is missing.

Happy to point you in the right direction if you want to close the gap.

{sender_name}

---
{sender_name}
Widby SEO Insights
{unsubscribe_link}
```

**Template: revenue_loss_v1**

```
Subject: {business_name} is missing ~{estimated_monthly_searches} searches/month in {city}

Hi {contact_name | "there"},

I analyzed the local search landscape for {niche_plural} in {city} and noticed {business_name} isn't showing up for several high-value searches.

Based on the search volume data, that's roughly {estimated_monthly_searches} people looking for {niche_plural} each month who can't find you.

I put together a quick breakdown of what's happening and what it would take to fix it:

{audit_url}

No strings attached — just data I thought you'd find useful.

{sender_name}

---
{sender_name}
Widby SEO Insights
{unsubscribe_link}
```

### 7.3 Follow-Up Sequence

```python
FOLLOW_UP_SCHEDULE = [
    {
        "day": 0,
        "type": "initial",
        "send_if": "always"
    },
    {
        "day": 3,
        "type": "follow_up_1",
        "send_if": "no_reply AND (opened OR NOT opened)",
        "template": "follow_up_soft",
        # "Just checking if you had a chance to look at the report I sent over"
    },
    {
        "day": 7,
        "type": "follow_up_2",
        "send_if": "no_reply AND opened",  # only follow up if they showed interest
        "template": "follow_up_value_add",
        # "I noticed one more thing about your Google Business Profile..."
    },
]

# STOP CONDITIONS:
# - Business replied (any reply, including negative)
# - Business unsubscribed
# - Email bounced
# - 3 follow-ups sent with no engagement (no opens)
```

### 7.4 Compliance Checklist

| Requirement | Implementation |
|-------------|---------------|
| CAN-SPAM: Physical address | Footer of every email |
| CAN-SPAM: Opt-out mechanism | Unsubscribe link in footer, processed within 24 hours |
| CAN-SPAM: Honest subject line | No deceptive subjects — all templates are factual |
| CAN-SPAM: Identify as ad | Not required for B2B relationship-building emails, but include "Widby SEO Insights" branding for transparency |
| GDPR: Not applicable | US B2B outreach only in V1. If expanding to EU, requires consent-first approach. |
| Domain reputation | Separate sending domain from primary (widby.com) |
| Bounce handling | Hard bounces immediately removed, soft bounces retried once then removed |
| Suppression list | Global suppression list across all experiments — once someone opts out, they're out forever |

---

## 8. Phase E5 — Response Tracking

### 8.1 Event Schema

Every interaction is logged as an event:

```json
{
  "event_id": "uuid",
  "experiment_id": "uuid",
  "business_id": "uuid",
  "variant_id": "A",
  "timestamp": "2026-04-05T14:32:00Z",
  "event_type": "email_opened",
  "metadata": {
    "email_sequence": 0,
    "device_type": "mobile",
    "geo": "Phoenix, AZ"
  }
}
```

### 8.2 Event Types

| Event Type | Source | Signal Value |
|-----------|--------|-------------|
| `email_delivered` | Email platform webhook | Baseline — email reached inbox |
| `email_bounced` | Email platform webhook | Bad contact data — disqualify |
| `email_opened` | Tracking pixel | Awareness — they saw it |
| `email_link_clicked` | Link tracking | Interest — they looked at the audit |
| `audit_page_loaded` | Audit page tracking pixel | Confirmed engagement |
| `audit_scroll_25` | Audit page JS event | Light engagement |
| `audit_scroll_75` | Audit page JS event | Deep engagement |
| `audit_cta_clicked` | Audit page JS event | Strong interest — clicked "get help" |
| `email_replied` | Email platform / inbox monitoring | Direct response |
| `email_unsubscribed` | Unsubscribe link click | Negative signal |
| `referral_booked` | Calendly/partner webhook | Conversion — agency consultation booked |
| `referral_closed` | Agency partner reporting (manual) | Revenue outcome |

### 8.3 Reply Classification

Replies are classified by intent using an LLM:

```python
REPLY_CLASSIFICATION_PROMPT = """
Classify this email reply from a business owner who received an SEO audit.

Reply text: {reply_text}

Classify as one of:
- POSITIVE_INTENT: Interested in learning more, wants help, asks about pricing/next steps
- CURIOUS: Asks questions about the audit findings but hasn't committed to action
- POLITE_DECLINE: Thanks but no thanks, not interested right now
- NEGATIVE: Angry, tells you to stop emailing, accuses of spam
- ALREADY_HANDLED: Says they already have an SEO person/agency
- UNRELATED: Reply is about something else entirely
- AUTORESPONDER: Out of office, auto-reply, generic acknowledgment

Return JSON: {"classification": "...", "confidence": 0.0-1.0, "key_phrases": [...]}
"""
```

### 8.4 Engagement Scoring

Each business gets a composite engagement score based on their interaction pattern:

```python
def engagement_score(events):
    """
    Score from 0-100 indicating how engaged this business was.
    Used as input to the rentability model.
    """
    score = 0

    if any(e.type == "email_opened" for e in events):
        score += 10
    if any(e.type == "email_link_clicked" for e in events):
        score += 15
    if any(e.type == "audit_page_loaded" for e in events):
        score += 10
    if any(e.type == "audit_scroll_75" for e in events):
        score += 10
    if any(e.type == "audit_cta_clicked" for e in events):
        score += 20

    # Reply scoring
    reply_events = [e for e in events if e.type == "email_replied"]
    if reply_events:
        classification = reply_events[0].metadata.get("classification")
        if classification == "POSITIVE_INTENT":
            score += 30
        elif classification == "CURIOUS":
            score += 20
        elif classification == "ALREADY_HANDLED":
            score += 5   # still tells us they care about SEO
        elif classification == "POLITE_DECLINE":
            score += 0
        elif classification == "NEGATIVE":
            score -= 10

    # Referral conversion
    if any(e.type == "referral_booked" for e in events):
        score += 15
    if any(e.type == "referral_closed" for e in events):
        score += 20

    return clamp(score, 0, 100)
```

---

## 9. Phase E6 — Analysis + Feedback

### 9.1 Experiment-Level Metrics

After the experiment window closes (21 days), compute:

```python
def analyze_experiment(experiment):
    results = {}

    for variant in experiment.variants:
        businesses = get_businesses_for_variant(experiment.id, variant.id)

        results[variant.id] = {
            "sample_size": len(businesses),
            "delivered_rate": count(delivered) / len(businesses),
            "open_rate": count(opened) / count(delivered),
            "click_rate": count(clicked) / count(delivered),
            "audit_engagement_rate": count(audit_loaded) / count(clicked),
            "reply_rate": count(replied) / count(delivered),
            "positive_intent_rate": count(positive_intent) / count(delivered),
            "cta_click_rate": count(cta_clicked) / count(audit_loaded),
            "referral_rate": count(referral_booked) / count(positive_intent),

            # Breakdown by business characteristics
            "reply_rate_by_review_bucket": {
                "0-10": ...,
                "11-50": ...,
                "51-100": ...,
                "100+": ...,
            },
            "reply_rate_by_site_quality_bucket": {
                "nascent": ...,
                "developing": ...,
                "established": ...,
            },
            "reply_rate_by_gbp_completeness": {
                "low": ...,    # < 0.33
                "medium": ..., # 0.33 - 0.66
                "high": ...,   # > 0.66
            },
        }

    # A/B comparison
    if len(experiment.variants) == 2:
        results["ab_comparison"] = {
            "metric": "positive_intent_rate",
            "variant_a": results["A"]["positive_intent_rate"],
            "variant_b": results["B"]["positive_intent_rate"],
            "relative_lift": (b - a) / a if a > 0 else None,
            "bayesian_probability_b_better": compute_bayesian_ab(a_data, b_data),
            "is_significant": bayesian_prob > 0.90,
        }

    return results
```

### 9.2 Rentability Signal Generation

This is where experiment data feeds back into Widby's scoring model:

```python
def generate_rentability_signal(experiment_results, niche, cbsa_code):
    """
    Compute a rentability signal for this niche+metro based on experiment data.
    This signal feeds into Widby's algo spec as a calibration input.
    """
    # Aggregate across variants (use winning variant if A/B test concluded)
    agg = aggregate_variant_results(experiment_results)

    signal = {
        "niche": niche,
        "cbsa_code": cbsa_code,
        "sample_size": agg.sample_size,
        "measurement_date": datetime.now().isoformat(),

        # Core rentability indicators
        "response_rate": agg.reply_rate,
        "positive_intent_rate": agg.positive_intent_rate,
        "referral_conversion_rate": agg.referral_rate,

        # Business characteristic correlations
        "best_responding_segment": identify_best_segment(agg),
        # e.g., "developing businesses with 10-50 reviews respond at 2x the average"

        # Derived rentability score (0-100)
        "rentability_score": compute_rentability(
            response_rate=agg.reply_rate,
            intent_rate=agg.positive_intent_rate,
            referral_rate=agg.referral_rate,
            sample_size=agg.sample_size,
        ),

        "confidence": "high" if agg.sample_size >= 200 else
                      "medium" if agg.sample_size >= 50 else "low",
    }

    # Write to Widby's rentability signal table
    upsert_rentability_signal(signal)

    return signal
```

### 9.3 Rentability Score Computation

```python
def compute_rentability(response_rate, intent_rate, referral_rate, sample_size):
    """
    Convert behavioral signals into a 0-100 rentability score.

    Interpretation:
    80-100: High rentability — businesses actively seek SEO help, strong agency demand
    60-80:  Good rentability — meaningful interest, viable market
    40-60:  Moderate — some interest, may need stronger value prop or different angle
    20-40:  Low — businesses are resistant to outreach, hard to rent leads
    0-20:   Very low — market is unresponsive, avoid or retest with different approach

    Calibration notes:
    - Expected cold email response rate for personalized B2B: 3-8%
    - Expected positive intent rate: 1-4% of sends
    - These benchmarks should be updated as data accumulates
    """
    # Response rate component
    # 3% = baseline (score 30), 8% = good (score 70), 15%+ = exceptional (score 100)
    response_score = scale(response_rate, floor=0.01, ceiling=0.15)

    # Intent rate component (most important — measures actual willingness to pay)
    intent_score = scale(intent_rate, floor=0.005, ceiling=0.08)

    # Referral conversion (only meaningful with enough data)
    if referral_rate is not None and sample_size >= 50:
        referral_score = scale(referral_rate, floor=0.01, ceiling=0.10)
    else:
        referral_score = 50  # neutral prior when insufficient data

    # Sample size confidence adjustment
    # Small samples get pulled toward 50 (uncertain)
    confidence_weight = min(sample_size / 200, 1.0)
    raw = (
        intent_score * 0.45 +
        response_score * 0.30 +
        referral_score * 0.25
    )
    # Bayesian shrinkage toward prior of 50 (uncertain)
    adjusted = (raw * confidence_weight) + (50 * (1 - confidence_weight))

    return clamp(adjusted, 0, 100)
```

### 9.4 Integration with Widby Algo Spec

The rentability signal modifies the monetization score in Widby's Phase 4:

```python
# In Widby algo spec, Phase 4, Section 7.4 (Monetization Score):

def monetization_score(signals, rentability_signal=None):
    """
    Updated to incorporate behavioral rentability data when available.
    """
    # Proxy-based components (always available)
    cpc_score = scale(signals.avg_cpc, floor=1.0, ceiling=30.0)
    density_score = scale(signals.business_density, floor=5, ceiling=100)
    active_market = (
        signals.lsa_present * 30 +
        signals.ads_present * 20 +
        min(signals.aggregator_presence, 3) * 10
    )
    gbp_score = signals.gbp_completeness_avg * 100

    if rentability_signal and rentability_signal.confidence in ("high", "medium"):
        # Behavioral data available — blend with proxy signals
        proxy_score = (
            cpc_score * 0.35 +
            density_score * 0.25 +
            active_market * 0.25 +
            gbp_score * 0.15
        )
        behavioral_score = rentability_signal.rentability_score

        # Weight behavioral data by confidence
        if rentability_signal.confidence == "high":
            blend = 0.60  # 60% behavioral, 40% proxy
        else:
            blend = 0.35  # 35% behavioral, 65% proxy

        raw = (behavioral_score * blend) + (proxy_score * (1 - blend))
    else:
        # No behavioral data — pure proxy (current V1.1 behavior)
        raw = (
            cpc_score * 0.35 +
            density_score * 0.25 +
            active_market * 0.25 +
            gbp_score * 0.15
        )

    return clamp(raw, 0, 100)
```

---

## 10. Data Model (Supabase)

### 10.1 Tables

```sql
-- Experiment configuration
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),
    status TEXT CHECK (status IN ('draft', 'discovery', 'scanning', 'generating', 'sending', 'tracking', 'analysis', 'closed')),
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    cbsa_name TEXT,
    sample_size INT NOT NULL,
    business_filters JSONB,
    outreach_config JSONB,
    agency_partner JSONB,
    experiment_window_days INT DEFAULT 21,
    results JSONB,  -- populated after analysis
    rentability_signal JSONB  -- populated after analysis
);

-- Experiment variants
CREATE TABLE experiment_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    variant_id TEXT NOT NULL,  -- "A", "B", etc.
    name TEXT,
    audit_depth TEXT CHECK (audit_depth IN ('minimal', 'standard', 'visual_mockup')),
    email_template TEXT,
    value_prop TEXT,
    allocation_pct NUMERIC,
    UNIQUE(experiment_id, variant_id)
);

-- Discovered businesses
CREATE TABLE experiment_businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    variant_id TEXT,
    business_data JSONB NOT NULL,
    contact JSONB,
    scan_results JSONB,
    weakness_score INT,
    weakness_issues JSONB,
    site_quality_bucket TEXT,
    outreach_eligible BOOLEAN DEFAULT false,
    disqualification_reason TEXT,
    audit_id UUID,
    audit_url TEXT,
    engagement_score INT,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Outreach events (high-volume event log)
CREATE TABLE outreach_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    business_id UUID REFERENCES experiment_businesses(id),
    variant_id TEXT,
    event_type TEXT NOT NULL,
    email_sequence INT,  -- 0 = initial, 1 = follow-up 1, etc.
    metadata JSONB,
    timestamp TIMESTAMPTZ DEFAULT now()
);

-- Reply classifications
CREATE TABLE reply_classifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES outreach_events(id),
    business_id UUID REFERENCES experiment_businesses(id),
    reply_text TEXT,
    classification TEXT,
    confidence NUMERIC,
    key_phrases JSONB,
    classified_at TIMESTAMPTZ DEFAULT now()
);

-- Rentability signals (feeds into Widby scoring)
CREATE TABLE rentability_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    niche_keyword TEXT NOT NULL,
    cbsa_code TEXT NOT NULL,
    experiment_id UUID REFERENCES experiments(id),
    sample_size INT,
    response_rate NUMERIC,
    positive_intent_rate NUMERIC,
    referral_conversion_rate NUMERIC,
    rentability_score INT,
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    best_responding_segment JSONB,
    measurement_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(niche_keyword, cbsa_code)  -- one signal per niche+metro, upserted
);

-- Global suppression list
CREATE TABLE suppression_list (
    email TEXT PRIMARY KEY,
    reason TEXT,  -- 'unsubscribed', 'bounced', 'complained'
    suppressed_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_events_experiment ON outreach_events(experiment_id);
CREATE INDEX idx_events_business ON outreach_events(business_id);
CREATE INDEX idx_events_type ON outreach_events(event_type);
CREATE INDEX idx_businesses_experiment ON experiment_businesses(experiment_id);
CREATE INDEX idx_rentability_niche_metro ON rentability_signals(niche_keyword, cbsa_code);
```

### 10.2 Row-Level Security

```sql
-- Experiments and related data are internal-only
-- No public access — all queries go through Edge Functions with service role
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
ALTER TABLE experiment_businesses ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE reply_classifications ENABLE ROW LEVEL SECURITY;

-- Rentability signals are read-accessible by the Widby scoring engine
ALTER TABLE rentability_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "widby_read_rentability"
    ON rentability_signals FOR SELECT
    USING (true);  -- readable by any authenticated Widby service
```

---

## 11. Cost Model

### 11.1 Per-Experiment Cost (100 businesses, one niche+metro)

| Component | Calculation | Cost |
|-----------|-----------|------|
| Business discovery | 1 Business Listings API call | $0.31 |
| Email discovery | 100 × $0.03 (scraping + Hunter fallback) | $3.00 |
| Site scanning (Lighthouse) | 100 × $0.002 | $0.20 |
| Site scanning (OnPage) | 100 × $0.002 | $0.20 |
| Audit generation (LLM) | 80 qualified × $0.03 avg | $2.40 |
| Audit hosting | Supabase Storage / Vercel | ~$0.00 (negligible) |
| Email delivery | 80 × 3 emails avg × $0.001 | $0.24 |
| Reply classification (LLM) | ~5 replies × $0.01 | $0.05 |
| Email platform (Instantly) | Monthly subscription amortized | ~$1.00 |
| **Total per experiment** | | **~$7.40** |

### 11.2 Scale Economics

To build a meaningful rentability dataset:

| Scale | Experiments | Businesses Contacted | Estimated Cost | Timeline |
|-------|------------|---------------------|---------------|----------|
| Pilot | 3 niches × 1 metro | 300 | ~$22 | 2 months |
| V1 | 10 niches × 5 metros | 5,000 | ~$370 | 4-6 months |
| V2 | 20 niches × 20 metros | 40,000 | ~$2,960 | 8-12 months |

At V2 scale, the rentability signal covers enough niche×metro combinations to materially improve Widby's scoring model. The $3K investment produces a proprietary dataset that no competitor can replicate without running their own experiments.

---

## 12. Experiment Playbook (First 3 Experiments)

### Experiment 1: Baseline Measurement

**Goal:** Establish baseline response rates and validate the full pipeline.

| Parameter | Value |
|-----------|-------|
| Niche | Plumber |
| Metro | Phoenix-Mesa-Chandler, AZ (CBSA 38060) |
| Sample | 100 businesses |
| Variants | A: problem_focused + standard audit (50), B: revenue_loss + standard audit (50) |
| Hypothesis | Revenue loss framing outperforms problem framing by 3+ percentage points |
| Success criteria | ≥3% overall reply rate, pipeline runs end-to-end without manual intervention |

### Experiment 2: Audit Depth Test

**Goal:** Determine if visual mockups justify the extra generation cost.

| Parameter | Value |
|-----------|-------|
| Niche | Plumber (same niche for controlled comparison) |
| Metro | Tucson, AZ (CBSA 46060) |
| Sample | 100 businesses |
| Variants | A: standard audit (50), B: visual_mockup audit (50) |
| Hypothesis | Visual mockup increases click-to-audit rate by 5+ percentage points |
| Email template | Same for both (winning template from Exp 1) |

### Experiment 3: Cross-Niche Comparison

**Goal:** First rentability signal comparison across niches.

| Parameter | Value |
|-----------|-------|
| Niches | Plumber, HVAC, Roofer |
| Metro | Phoenix-Mesa-Chandler (same metro for controlled comparison) |
| Sample | 60 per niche (180 total) |
| Variants | Single variant per niche (winning combo from Exp 1+2) |
| Hypothesis | Response rates vary by ≥3 percentage points across niches |
| Key output | First rentability score comparison: plumber vs. HVAC vs. roofer in Phoenix |

---

## 13. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Domain gets burned (spam flagged) | Experiment pipeline stops | Medium | Use dedicated sending domain, warm properly, keep volume low, rotate domains |
| Low response rates (<2%) | Insufficient data for rentability signal | Medium | Test more value props, increase personalization, try different niches |
| Email discovery failure (can't find emails) | Reduced sample sizes | Medium | Multi-source approach (scrape + API), accept that some businesses are unreachable |
| Legal complaint from business owner | Reputation risk | Low | Full CAN-SPAM compliance, immediate unsubscribe processing, professional tone |
| Agency partners don't close leads | Can't measure full referral funnel | Medium | Start with 2-3 agency partners, track close rates, replace underperformers |
| LLM-generated audits contain errors | Trust damage, angry responses | Medium | Validate audit claims against scan data programmatically before generating copy |
| Competitor copies the playbook | Loss of data advantage | Low (short-term) | Speed of execution + data accumulation = compounding advantage. By the time someone copies it, you have 6 months of rentability data they don't. |

---

## 14. Success Metrics

### Framework Validation (First 3 Months)

| Metric | Target | Why It Matters |
|--------|--------|---------------|
| Pipeline completion rate | >90% of experiments run to analysis without manual intervention | Proves the system is automatable |
| Email deliverability | >85% inbox rate | Below this, data is unreliable |
| Overall reply rate | >3% | Below this, sample sizes need to be impractically large |
| Positive intent rate | >1% | The actual signal — below this, outreach angle needs rethinking |
| Rentability score variance across niches | >15 points between highest and lowest | If all niches score the same, the signal isn't discriminating |

### Data Value (6-12 Months)

| Metric | Target | Why It Matters |
|--------|--------|---------------|
| Niche×metro cells with rentability data | >50 | Minimum for broad scoring model improvement |
| Widby scoring accuracy improvement | Measurable via practitioner feedback | Proves the feedback loop works |
| Referral revenue | Covers experiment operating costs | Self-sustaining data collection |
| A/B test learnings logged | >10 significant findings | Builds institutional knowledge about outreach optimization |