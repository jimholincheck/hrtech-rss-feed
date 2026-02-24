#!/usr/bin/env python3
"""
Mercer HR Tech Content RSS Feed Scraper
Scrapes articles from Mercer's HR Tech Content page and generates an RSS feed.
Preserves original discovery dates for articles.
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import json
import os

# Configuration
BASE_URL = "https://taap.mercer.com/more-hr-tech-content"
MAX_PAGES = 4  # Scrape all 4 pages
DELAY_SECONDS = 1  # Delay between requests
DATES_FILE = 'article_dates.json'  # Store article discovery dates

def load_article_dates():
    """Load previously saved article dates from JSON file."""
    if os.path.exists(DATES_FILE):
        try:
            with open(DATES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load dates file: {e}")
            return {}
    return {}

def save_article_dates(dates_dict):
    """Save article dates to JSON file."""
    try:
        with open(DATES_FILE, 'w') as f:
            json.dump(dates_dict, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save dates file: {e}")

# Date parsing removed - using scrape date instead

# Date fetching removed - we'll use scrape date for discovery instead

def scrape_articles(max_pages=MAX_PAGES):
    """
    Scrape articles from Mercer HR Tech content pages.
    
    Args:
        max_pages: Number of pages to scrape (default: 4)
    
    Returns:
        List of article dictionaries with title, link, description, and pubDate
    """
    articles = []
    seen_links = set()
    
    # Load existing article dates
    article_dates = load_article_dates()
    current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
    dates_updated = False
    
    print(f"Starting scrape of {max_pages} pages...")
    print(f"Loaded {len(article_dates)} existing article dates")
    
    for page_num in range(1, max_pages + 1):
        # Construct URL for pagination
        if page_num == 1:
            url = BASE_URL
        else:
            url = f"{BASE_URL}?page={page_num}"
        
        print(f"\nScraping page {page_num}: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all article links - look for links that go to /article/
            article_links = soup.find_all('a', href=lambda x: x and '/article/' in x)
            
            page_count = 0
            for link in article_links:
                article_url = link.get('href')
                
                # Make URL absolute if it's relative
                if article_url.startswith('/'):
                    article_url = f"https://taap.mercer.com{article_url}"
                elif not article_url.startswith('http'):
                    article_url = f"https://taap.mercer.com{article_url}"
                
                # Clean up URL
                article_url = article_url.strip()
                
                # Skip duplicates and "See More" links in same paragraph
                if article_url in seen_links:
                    continue
                
                seen_links.add(article_url)
                
                # Extract title (from link text, not from the page)
                # Look for the title in the heading above the link
                title = ""
                parent = link.find_parent()
                if parent:
                    # Look for heading tags
                    heading = parent.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if heading:
                        title = heading.get_text(strip=True)
                
                if not title:
                    title = link.get_text(strip=True)
                    # Skip if it's just "See More"
                    if title.lower() in ['see more', 'learn more', 'read more']:
                        continue
                
                # Extract description (paragraph text near the link)
                description = ""
                if parent:
                    # Look for paragraph near this link
                    para = parent.find('p')
                    if para:
                        description = para.get_text(strip=True)
                
                if not description:
                    description = title
                
                # Check if we have a cached date for this article
                if article_url in article_dates:
                    # Use existing date
                    pub_date = article_dates[article_url]
                else:
                    # New article - use current time and save it
                    pub_date = current_time
                    article_dates[article_url] = pub_date
                    dates_updated = True
                    print(f"  NEW: {title[:60]}...")
                
                articles.append({
                    'title': title,
                    'link': article_url,
                    'description': description,
                    'pubDate': pub_date
                })
                page_count += 1
                
                # No need for delay since we're not fetching article pages
                # time.sleep(DELAY_SECONDS)
            
            print(f"  Found {page_count} articles on page {page_num}")
            
            # Rate limiting between page requests
            if page_num < max_pages:
                time.sleep(DELAY_SECONDS)
                
        except requests.RequestException as e:
            print(f"Error scraping page {page_num}: {e}")
            continue
    
    # Save updated dates if we found new articles
    if dates_updated:
        save_article_dates(article_dates)
        print(f"\n✓ Saved updated article dates ({len(article_dates)} total)")
    
    print(f"\nTotal articles scraped: {len(articles)}")
    return articles

def escape_xml(text):
    """Escape special XML characters"""
    if not text:
        return ""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;'))

def generate_rss_feed(articles, output_file='hrtech_feed.xml'):
    """
    Generate RSS 2.0 XML feed from articles with actual publication dates.
    
    Args:
        articles: List of article dictionaries
        output_file: Output filename for RSS feed
    """
    
    # Build RSS feed manually to support CDATA for HTML content
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<rss version="2.0">')
    xml_lines.append('  <channel>')
    xml_lines.append(f'    <title>Mercer HR Tech Content</title>')
    xml_lines.append(f'    <link>{BASE_URL}</link>')
    xml_lines.append(f'    <description>Latest HR technology insights, market briefs, and event coverage from Mercer</description>')
    xml_lines.append(f'    <language>en-us</language>')
    xml_lines.append(f'    <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>')
    
    # Add articles as items
    for article in articles:
        xml_lines.append('    <item>')
        xml_lines.append(f'      <title>{escape_xml(article["title"])}</title>')
        xml_lines.append(f'      <link>{escape_xml(article["link"])}</link>')
        xml_lines.append(f'      <description><![CDATA[{article["description"]}]]></description>')
        xml_lines.append(f'      <guid isPermaLink="true">{escape_xml(article["link"])}</guid>')
        xml_lines.append(f'      <pubDate>{article["pubDate"]}</pubDate>')
        xml_lines.append('    </item>')
    
    xml_lines.append('  </channel>')
    xml_lines.append('</rss>')
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_lines))
    
    print(f"\n✓ RSS feed generated: {output_file}")
    print(f"✓ Total items in feed: {len(articles)}")

def main():
    """Main execution function."""
    print("=" * 70)
    print("Mercer HR Tech Content RSS Feed Generator")
    print("=" * 70)
    print()
    
    # Scrape articles
    articles = scrape_articles(max_pages=MAX_PAGES)
    
    if not articles:
        print("No articles found. Check the website structure or your internet connection.")
        return
    
    # Generate RSS feed
    generate_rss_feed(articles)
    
    print("\n" + "=" * 70)
    print("Feed generation complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
