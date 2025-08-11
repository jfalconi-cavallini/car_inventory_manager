import requests
from bs4 import BeautifulSoup
import json

def save_cars_to_file(cars, filename='scraped_cars.json'):
    with open(filename, 'w') as f:
        json.dump(cars, f, indent=4)

def parse_price(price_str):
    try:
        return float(price_str.replace('$', '').replace(',', '').strip())
    except:
        return 0.0

def scrape_inventory_page(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CarInventoryScraper/1.0)'
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve page: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    cars = []
    seen_links = set()  # avoid duplicates

    car_blocks = soup.select('div.elementor-widget-wrap')

    for block in car_blocks:
        a_tags = block.select('h2.elementor-heading-title a')
        if len(a_tags) >= 2:
            year_make = a_tags[0].get_text(strip=True)
            model = a_tags[1].get_text(strip=True)
            link = a_tags[0]['href']

            if link in seen_links:
                continue
            seen_links.add(link)

            if year_make.startswith("New "):
                year_make = year_make[len("New "):]

            parts = year_make.split(' ', 1)
            year = parts[0] if len(parts) > 0 else ''
            make = parts[1] if len(parts) > 1 else ''

            info_p = block.select_one('div.elementor-widget-container > p.elementor-heading-title.elementor-size-default')
            info_text = info_p.get_text(strip=True) if info_p else ''

            vin = ''
            if info_text:
                parts = [part.strip() for part in info_text.split('|')]
                for part in parts:
                    if part.startswith("VIN:"):
                        vin = part.replace("VIN:", "").strip() 

            img_div = block.select_one('div.elementor-image')
            if img_div and img_div.has_attr('data-auto5-image'):
                image_url = img_div['data-auto5-image']
                if image_url.startswith('//'):
                    image_url = 'https:' + image_url
            else:
                img_tag = block.select_one('div.elementor-image img')
                if img_tag:
                    image_url = img_tag.get('src')
                    if image_url and image_url.startswith('//'):
                        image_url = 'https:' + image_url
                else:
                    image_url = None

            # MSRP price
            msrp_price = 0.0
            pricing_root = block.select_one('div.jzl-pricing-viewer-root')
            if pricing_root:
                rows = pricing_root.select('div.row')
                for row in rows:
                    label_span = row.select_one('div > span.label')
                    value_span = row.select_one('span.value')
                    if label_span and value_span:
                        if label_span.get_text(strip=True) == 'MSRP':
                            msrp_price = parse_price(value_span.get_text(strip=True))
                            break

            cars.append({
                'condition': 'New',
                'year': year,
                'make': make,
                'model': model,
                'vin': vin,
                'link': link,
                'image_url': image_url,
                'price': msrp_price
            })

    return cars

def get_total_pages(url):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; CarInventoryScraper/1.0)'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to retrieve page: {response.status_code}")
        return 1

    soup = BeautifulSoup(response.text, 'html.parser')
    pager_div = soup.find('div', class_='pager-body pager-body-full', attrs={'data-event': 'click_pagination'})

    if not pager_div:
        print("Pagination div not found, assuming 1 page")
        return 1

    page_numbers = []
    for a_tag in pager_div.find_all('a'):
        text = a_tag.get_text(strip=True)
        if text.isdigit():
            page_numbers.append(int(text))

    return max(page_numbers) if page_numbers else 1

def scrape_all_new_cars(base_url):
    total_pages = 30 #get_total_pages(base_url)  # static for now
    print(f"Total pages found: {total_pages}")

    all_cars = []
    for page_num in range(1, total_pages + 1):
        url = base_url if page_num == 1 else f"{base_url}srp-page-{page_num}/"
        print(f"Scraping page {page_num}: {url}")
        cars = scrape_inventory_page(url)
        all_cars.extend(cars)

    return all_cars

def scrape_and_save():
    """Run the scraper and save results to scraped_cars.json"""
    base_url = 'https://www.claycooley.com/inventory/new-cars/'
    all_new_cars = scrape_all_new_cars(base_url)
    print(f"Total new cars scraped: {len(all_new_cars)}")
    save_cars_to_file(all_new_cars)
    return all_new_cars

if __name__ == "__main__":
    scrape_and_save()
