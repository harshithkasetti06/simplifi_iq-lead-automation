"""
enrichment.py
Scrapes and enriches company data from their website and public sources.
Completely free — no paid APIs required.
"""

import requests
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urlparse, urljoin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def clean_text(text: str) -> str:
    """Remove extra whitespace and newlines."""
    return re.sub(r'\s+', ' ', text).strip()


def safe_get(url: str, timeout: int = 10) -> requests.Response | None:
    """Safely fetch a URL, return None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_meta(soup: BeautifulSoup) -> dict:
    """Extract meta title, description, keywords from a page."""
    data = {}
    title_tag = soup.find("title")
    if title_tag:
        data["page_title"] = clean_text(title_tag.get_text())

    for attr in ["description", "keywords", "og:title", "og:description"]:
        tag = soup.find("meta", attrs={"name": attr}) or \
              soup.find("meta", attrs={"property": attr})
        if tag and tag.get("content"):
            data[attr.replace("og:", "og_")] = clean_text(tag["content"])

    return data


def scrape_homepage(website: str) -> dict:
    """Scrape the company homepage for key information."""
    if not website.startswith("http"):
        website = "https://" + website

    result = {
        "website": website,
        "homepage_text": "",
        "page_title": "",
        "description": "",
        "keywords": "",
        "hero_text": "",
        "about_snippet": "",
        "services": [],
        "social_links": {},
        "contact_email": "",
        "error": None
    }

    resp = safe_get(website)
    if not resp:
        result["error"] = "Could not access company website"
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove script and style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Meta info
    meta = extract_meta(soup)
    result.update(meta)

    # Hero / main heading
    hero = soup.find("h1")
    if hero:
        result["hero_text"] = clean_text(hero.get_text())

    # About snippet — look for about section
    about_keywords = ["about", "who we are", "our mission", "what we do"]
    for kw in about_keywords:
        about_section = soup.find(
            lambda tag: tag.name in ["section", "div", "p"] and
            kw in (tag.get_text() or "").lower()[:200]
        )
        if about_section:
            snippet = clean_text(about_section.get_text())[:600]
            if len(snippet) > 50:
                result["about_snippet"] = snippet
                break

    # Services / features list
    service_tags = soup.find_all(["li", "h3", "h4"])
    services = []
    for tag in service_tags[:20]:
        text = clean_text(tag.get_text())
        if 10 < len(text) < 100:
            services.append(text)
    result["services"] = services[:10]

    # General text body (first 1500 chars)
    body_text = clean_text(soup.get_text())
    result["homepage_text"] = body_text[:1500]

    # Social links
    social_patterns = {
        "linkedin": "linkedin.com",
        "twitter": "twitter.com",
        "facebook": "facebook.com",
        "instagram": "instagram.com",
        "youtube": "youtube.com",
    }
    for a in soup.find_all("a", href=True):
        href = a["href"]
        for platform, pattern in social_patterns.items():
            if pattern in href:
                result["social_links"][platform] = href

    # Contact email
    email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, resp.text)
    if emails:
        result["contact_email"] = emails[0]

    return result


def scrape_about_page(website: str) -> str:
    """Try to scrape the /about page for more context."""
    if not website.startswith("http"):
        website = "https://" + website

    about_urls = [
        urljoin(website, "/about"),
        urljoin(website, "/about-us"),
        urljoin(website, "/company"),
        urljoin(website, "/who-we-are"),
    ]

    for url in about_urls:
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = clean_text(soup.get_text())
            if len(text) > 200:
                return text[:1500]
    return ""


def scrape_services_page(website: str) -> str:
    """Try to scrape the /services or /products page."""
    if not website.startswith("http"):
        website = "https://" + website

    service_urls = [
        urljoin(website, "/services"),
        urljoin(website, "/products"),
        urljoin(website, "/solutions"),
        urljoin(website, "/offerings"),
    ]

    for url in service_urls:
        resp = safe_get(url)
        if resp:
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = clean_text(soup.get_text())
            if len(text) > 200:
                return text[:1500]
    return ""


def get_domain_info(website: str) -> dict:
    """Extract basic domain information."""
    if not website.startswith("http"):
        website = "https://" + website
    parsed = urlparse(website)
    domain = parsed.netloc.replace("www.", "")
    return {
        "domain": domain,
        "domain_extension": domain.split(".")[-1] if "." in domain else "",
        "company_slug": domain.split(".")[0] if "." in domain else domain,
    }


def enrich_company(lead_data: dict) -> dict:
    """
    Main enrichment function. Takes lead form data, returns enriched company data.
    """
    website = lead_data.get("website", "")
    company_name = lead_data.get("company_name", "")

    logger.info(f"Starting enrichment for: {company_name} ({website})")

    enriched = {
        "lead": lead_data,
        "domain_info": {},
        "homepage": {},
        "about_text": "",
        "services_text": "",
        "enrichment_status": "success",
    }

    # Domain info
    if website:
        enriched["domain_info"] = get_domain_info(website)

        # Scrape homepage
        logger.info("Scraping homepage...")
        enriched["homepage"] = scrape_homepage(website)

        # Scrape about page
        logger.info("Scraping about page...")
        enriched["about_text"] = scrape_about_page(website)

        # Scrape services page
        logger.info("Scraping services page...")
        enriched["services_text"] = scrape_services_page(website)

    if enriched["homepage"].get("error"):
        enriched["enrichment_status"] = "partial"
        logger.warning(f"Homepage scraping had issues: {enriched['homepage']['error']}")

    logger.info("Enrichment complete.")
    return enriched


def build_context_summary(enriched: dict) -> str:
    """
    Build a clean text summary of all enriched data for the AI to use.
    """
    lead = enriched.get("lead", {})
    hp = enriched.get("homepage", {})
    domain = enriched.get("domain_info", {})

    parts = []

    # Lead info
    full_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    parts.append(f"PROSPECT: {full_name}")
    parts.append(f"EMAIL: {lead.get('email', 'N/A')}")
    parts.append(f"PHONE: {lead.get('phone', 'N/A')}")
    parts.append(f"COMPANY: {lead.get('company_name', 'N/A')}")
    parts.append(f"WEBSITE: {lead.get('website', 'N/A')}")
    parts.append(f"INDUSTRY: {lead.get('industry', 'N/A')}")
    parts.append(f"COMPANY SIZE: {lead.get('company_size', 'N/A')}")
    parts.append(f"BIGGEST CHALLENGE: {lead.get('challenge', 'N/A')}")
    parts.append(f"HOW THEY FOUND US: {lead.get('source', 'N/A')}")
    parts.append("")

    # Domain info
    if domain:
        parts.append(f"DOMAIN: {domain.get('domain', '')}")

    # Homepage data
    if hp.get("page_title"):
        parts.append(f"PAGE TITLE: {hp['page_title']}")
    if hp.get("description"):
        parts.append(f"META DESCRIPTION: {hp['description']}")
    if hp.get("hero_text"):
        parts.append(f"HERO HEADING: {hp['hero_text']}")
    if hp.get("about_snippet"):
        parts.append(f"ABOUT SNIPPET: {hp['about_snippet']}")
    if hp.get("services"):
        parts.append(f"SERVICES/FEATURES FOUND: {', '.join(hp['services'][:8])}")
    if hp.get("contact_email"):
        parts.append(f"CONTACT EMAIL FOUND ON SITE: {hp['contact_email']}")
    if hp.get("social_links"):
        socials = ", ".join(f"{k}: {v}" for k, v in hp["social_links"].items())
        parts.append(f"SOCIAL MEDIA: {socials}")
    if hp.get("homepage_text"):
        parts.append(f"\nHOMEPAGE TEXT EXCERPT:\n{hp['homepage_text'][:800]}")

    # About page
    if enriched.get("about_text"):
        parts.append(f"\nABOUT PAGE TEXT:\n{enriched['about_text'][:600]}")

    # Services page
    if enriched.get("services_text"):
        parts.append(f"\nSERVICES PAGE TEXT:\n{enriched['services_text'][:600]}")

    return "\n".join(parts)