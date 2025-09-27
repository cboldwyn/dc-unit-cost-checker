"""
DC Unit Cost Checker v1.0
Smart product matching and unit cost validation tool
"""

import streamlit as st
import pandas as pd
import io
import re
from google.oauth2.service_account import Credentials
import gspread
from gspread_dataframe import get_as_dataframe

# Configure page
st.set_page_config(
    page_title="DC Unit Cost Checker v1.0",
    page_icon="💰",
    layout="wide"
)

# Configuration
VERSION = "1.0"
CONNECT_CATALOG_URL = "https://docs.google.com/spreadsheets/d/1FG3K7Rj-a9xw-UegJ4yxM8DAyn1LhmxwopYn67ja5iI/edit?gid=172177068#gid=172177068"

# Exact match brands that require product-level matching
EXACT_PRODUCT_MATCH_BRANDS = {
    'Blazy Susan', 'Camino', 'Crave', 'Daily Dose', "Dr. Norm's", 'Good Tide', 
    'Happy Fruit', 'High Gorgeous', 'Kiva', 'Lost Farm', 'Made From Dirt', 
    'Papa & Barkley', 'Sip Elixirs', 'St. Ides', "Uncle Arnie's", 'Vet CBD', 
    'Wyld', 'Yummi Karma', "Not Your Father's"
}

def clean_price(price_value):
    """Clean and convert price value to float"""
    if pd.isna(price_value) or price_value == '':
        return None
    try:
        cleaned = str(price_value).replace('$', '').replace(',', '').strip()
        return float(cleaned)
    except:
        return None

def extract_brand_from_name(product_name):
    """Extract brand from product name (everything before the first ' - ')"""
    if pd.isna(product_name):
        return 'Unknown'
    
    name_str = str(product_name).strip()
    if ' - ' in name_str:
        brand = name_str.split(' - ')[0].strip()
        return brand if brand else 'Unknown'
    else:
        return 'Unknown'

def extract_weight_from_item(item_text):
    """Extract weight from item text (e.g., "Blue Dream 3.5g" → "3.5g")"""
    if pd.isna(item_text):
        return None
    
    item_str = str(item_text).strip()
    weight_patterns = [
        r'(\d+\.?\d*g)$',
        r'(\d+\.\d+\s?oz?)$',
        r'(\d+\s?oz?)$',
        r'(1/8\s?oz?)$',
        r'(1/4\s?oz?)$',
        r'(1/2\s?oz?)$',
    ]
    
    for pattern in weight_patterns:
        match = re.search(pattern, item_str, re.IGNORECASE)
        if match:
            return match.group(1).lower().replace(' ', '')
    
    return None

def extract_pack_size_from_item(item_text):
    """Extract pack size from item text (e.g., "OG Kush 3pk 1.5g" → "3pk")"""
    if pd.isna(item_text):
        return None
    
    item_str = str(item_text).strip()
    pack_patterns = [
        r'(\d+pk)\s+\d+\.?\d*g',
        r'(\d+pk)\s+\d+\s?oz',
        r'(\d+pk)\s+1/[248]\s?oz',
    ]
    
    for pattern in pack_patterns:
        match = re.search(pattern, item_str, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    
    return None
    """Extract category-specific distinguishing keywords from item text"""
    if pd.isna(item_text) or pd.isna(category):
        return None
    
    item_str = str(item_text).lower()
    category_lower = str(category).lower()
    
    if category_lower == 'vape':
        vape_keywords = ['originals', 'ascnd', 'dna', 'exotics', 'disposable', 'live resin', 'reload', 'rtu', 'curepen', 'curebar']
        found_keywords = [keyword for keyword in vape_keywords if keyword in item_str]
        return ', '.join(found_keywords) if found_keywords else None
    
    if 'flower' in category_lower:
        quality_tiers = ['top shelf', 'headstash', 'exotic', 'premium', 'private reserve', 'reserve']
        found_keywords = [tier for tier in quality_tiers if tier in item_str]
        return ', '.join(found_keywords) if found_keywords else None
    
    if category_lower == 'extract':
        found_keywords = []
        
        # Primary extract types (hierarchical)
        if 'live rosin' in item_str:
            found_keywords.append('live rosin')
        elif 'live resin' in item_str:
            found_keywords.append('live resin')
        elif 'hash rosin' in item_str:
            found_keywords.append('hash rosin')
        elif 'rosin' in item_str:
            found_keywords.append('rosin')
        elif 'resin' in item_str:
            found_keywords.append('resin')
        
        # Brand-specific tiers
        if any(brand in item_str for brand in ['bear labs', 'west coast cure']):
            tier_match = re.search(r'tier\s*([1-4])', item_str)
            if tier_match:
                found_keywords.append(f"tier {tier_match.group(1)}")
        
        # Processing modifiers
        modifiers = ['cold cure', 'fresh press', 'curated', 'hte blend', 'dino eggz']
        found_keywords.extend([modifier for modifier in modifiers if modifier in item_str])
        
        # Consistency types
        consistencies = ['diamonds', 'budder', 'badder', 'sauce', 'sugar', 'jam']
        found_keywords.extend([consistency for consistency in consistencies if consistency in item_str])
        
        # Product types
        product_types = ['rso', 'syringe']
        found_keywords.extend([product_type for product_type in product_types if product_type in item_str])
        
        return ', '.join(found_keywords) if found_keywords else None
    
    if category_lower == 'preroll':
        found_keywords = []
        
        # Preroll types
        preroll_types = ['blunts', 'preroll', 'prerolls', 'joints', 'mini']
        found_keywords.extend([preroll_type for preroll_type in preroll_types if preroll_type in item_str])
        
        # Special attributes
        if 'infused' in item_str:
            found_keywords.append('infused')
        
        return ', '.join(found_keywords) if found_keywords else None
    
    return None
    """Extract pack size from item text (e.g., "OG Kush 3pk 1.5g" → "3pk")"""
    if pd.isna(item_text):
        return None
    
    item_str = str(item_text).strip()
    pack_patterns = [
        r'(\d+pk)\s+\d+\.?\d*g',
        r'(\d+pk)\s+\d+\s?oz',
        r'(\d+pk)\s+1/[248]\s?oz',
    ]
    
    for pattern in pack_patterns:
        match = re.search(pattern, item_str, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    
    return None

@st.cache_data
def load_google_sheet_data(sheet_url):
    """Load data from Google Sheets using service account authentication"""
    try:
        credentials_dict = st.secrets["google_sheets"]
        creds = Credentials.from_service_account_info(
            credentials_dict,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly"
            ]
        )
        
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url)
        worksheet = sheet.get_worksheet(0)
        
        # Try different loading methods
        df = None
        try:
            df = get_as_dataframe(worksheet, parse_dates=True, header=0)
        except:
            pass
        
        if df is None or df.empty:
            try:
                df = get_as_dataframe(worksheet, parse_dates=True, header=1)
            except:
                pass
        
        if df is None or df.empty:
            try:
                all_values = worksheet.get_all_values()
                if len(all_values) > 1:
                    headers = all_values[0]
                    data_rows = all_values[1:]
                    df = pd.DataFrame(data_rows, columns=headers)
            except:
                return None, None
        
        if df is not None:
            df = df.dropna(how='all').dropna(axis=1, how='all')
            return df, worksheet.title
        else:
            return None, None
        
    except Exception as e:
        st.error(f"Error loading Google Sheet: {str(e)}")
        return None, None

def load_csv_data(uploaded_file):
    """Load data from uploaded CSV file"""
    try:
        df = pd.read_csv(uploaded_file)
        return df, "DC Products"
    except Exception as e:
        st.error(f"Error loading CSV file: {str(e)}")
        return None, None

def process_dc_products(df, catalog_df=None):
    """Process DC products data and prepare for matching"""
    if df is None or df.empty:
        return None
    
    st.write(f"**DC Products** - Original data shape: {df.shape}")
    
    # Filter out inactive products
    if 'Inactive' in df.columns:
        # Keep products where Inactive is False/No/0
        inactive_values = ['True', 'true', 'TRUE', 'Yes', 'yes', 'YES', 'Y', 'y', '1', True]
        active_df = df[~df['Inactive'].isin(inactive_values)].copy()
        st.write(f"**DC Products** - After filtering inactive: {active_df.shape}")
    else:
        st.warning("No 'Inactive' column found. Using all data.")
        active_df = df.copy()
    
    # Exclude unwanted categories (from original price checker)
    categories_to_exclude = [
        'Display', 'Clones', 'Apparel', 'Sample', 'Promo', 'Compassion', 
        'Donation', 'Boxes', 'Non-Cannabis', 'Gift Cards', 'xxxDONOTUSE-Buzzers'
    ]
    
    if 'Category' in active_df.columns:
        before_category_filter = len(active_df)
        active_df = active_df[~active_df['Category'].isin(categories_to_exclude)]
        after_category_filter = len(active_df)
        removed_count = before_category_filter - after_category_filter
        st.write(f"**DC Products** - After excluding unwanted categories: {active_df.shape}")
        if removed_count > 0:
            st.info(f"🚫 Excluded {removed_count} products from categories: {', '.join(categories_to_exclude)}")
    
    # Extract brand from product name and prepare columns
    active_df['Brand'] = active_df['Name'].apply(extract_brand_from_name)
    active_df['Item'] = active_df['Name']
    active_df['Cost_Clean'] = active_df['Cost Per Unit ($)'].apply(clean_price)
    active_df['Price_Clean'] = active_df['Price Per Unit ($)'].apply(clean_price)
    
    # Show brand extraction results
    brand_counts = active_df['Brand'].value_counts()
    st.info(f"🔤 Extracted {len(brand_counts)} unique brands from product names")
    if len(brand_counts) > 0:
        st.write(f"**Top 5 brands:** {', '.join(brand_counts.head().index.tolist())}")
    
    # Filter by catalog brands if available
    if catalog_df is not None and 'Brand' in catalog_df.columns:
        valid_brands = catalog_df['Brand'].dropna().unique()
        valid_brands = [str(brand).strip() for brand in valid_brands if str(brand).strip()]
        
        # Store brand filtering debug info
        extracted_brands = set(active_df['Brand'].dropna().unique())
        catalog_brands = set(valid_brands)
        kept_brands = extracted_brands.intersection(catalog_brands)
        removed_brands = extracted_brands - catalog_brands
        
        active_df.brand_filter_debug = {
            'extracted_brands': extracted_brands,
            'catalog_brands': catalog_brands,
            'kept_brands': kept_brands,
            'removed_brands': removed_brands
        }
        
        st.info(f"🔍 Brand filtering: {len(extracted_brands)} extracted, {len(kept_brands)} kept, {len(removed_brands)} removed")
        
        before_filter = len(active_df)
        active_df = active_df[active_df['Brand'].isin(valid_brands)]
        after_filter = len(active_df)
        
        st.write(f"**DC Products** - After brand filtering: {active_df.shape}")
        if before_filter > after_filter:
            st.info(f"🎯 Kept products from {len(valid_brands)} catalog brands. Removed {before_filter - after_filter} products.")
    
    # Add matching helper columns
    active_df['Extracted_Weight'] = active_df['Item'].apply(extract_weight_from_item)
    active_df['Extracted_Pack_Size'] = active_df['Item'].apply(extract_pack_size_from_item)
    active_df['Extracted_Category_Keywords'] = active_df.apply(
        lambda row: extract_category_keywords(row['Item'], row['Category']), axis=1
    )
    
    # Show extraction stats
    weight_extracted_count = active_df['Extracted_Weight'].notna().sum()
    pack_extracted_count = active_df['Extracted_Pack_Size'].notna().sum()
    keywords_extracted_count = active_df['Extracted_Category_Keywords'].notna().sum()
    
    st.info(f"🔍 Extracted weights from {weight_extracted_count:,} products")
    st.info(f"📦 Extracted pack sizes from {pack_extracted_count:,} products")
    st.info(f"🔤 Extracted category keywords from {keywords_extracted_count:,} products")
    
    return active_df

def match_flower_products(row, templates):
    """Advanced matching for flower products using weight and keywords"""
    current_templates = templates
    match_steps = []
    
    # Filter by weight
    company_weight = row.get('Extracted_Weight')
    if company_weight:
        weight_matched_templates = []
        for template in current_templates:
            catalog_weight = extract_weight_from_item(template)
            if catalog_weight == company_weight:
                weight_matched_templates.append(template)
        
        if weight_matched_templates:
            current_templates = weight_matched_templates
            match_steps.append(f"weight: {company_weight}")
    
    # Filter by keywords if still multiple options
    company_keywords = row.get('Extracted_Category_Keywords')
    if company_keywords and len(current_templates) > 1:
        company_keyword_list = [kw.strip() for kw in str(company_keywords).split(',')]
        
        template_scores = []
        for template in current_templates:
            catalog_keywords = extract_category_keywords(template, 'Flower')
            if catalog_keywords:
                catalog_keyword_list = [kw.strip() for kw in catalog_keywords.split(',')]
                matches = sum(1 for ck in company_keyword_list if ck in catalog_keyword_list)
                template_scores.append((template, matches, len(catalog_keyword_list), catalog_keyword_list))
            else:
                template_scores.append((template, 0, 0, []))
        
        if template_scores:
            max_score = max(score for _, score, _, _ in template_scores)
            if max_score > 0:
                best_scored_templates = [(template, score, total_kw, kw_list) for template, score, total_kw, kw_list in template_scores if score == max_score]
                
                if len(best_scored_templates) == 1:
                    current_templates = [best_scored_templates[0][0]]
                    matched_keywords = [ck for ck in company_keyword_list if ck in best_scored_templates[0][3]]
                    match_steps.append(f"keywords: {', '.join(matched_keywords)}")
                else:
                    # Tiebreaker: prefer fewer total keywords
                    min_total_keywords = min(total_kw for _, _, total_kw, _ in best_scored_templates)
                    final_candidates = [template for template, score, total_kw, kw_list in best_scored_templates if total_kw == min_total_keywords]
                    
                    if len(final_candidates) == 1:
                        current_templates = final_candidates
                        winner_keywords = [kw_list for template, score, total_kw, kw_list in best_scored_templates if template == final_candidates[0]][0]
                        matched_keywords = [ck for ck in company_keyword_list if ck in winner_keywords]
                        match_steps.append(f"keywords: {', '.join(matched_keywords)} (tiebreaker)")
    
    return (current_templates[0], match_steps) if len(current_templates) == 1 else (None, [])

def match_preroll_products(row, templates):
    """Advanced matching for preroll products using infused status, weight, pack size, and keywords"""
    # Filter by infused status first
    company_has_infused = 'infused' in str(row['Item']).lower()
    
    infused_filtered_templates = []
    for template in templates:
        template_has_infused = 'infused' in str(template).lower()
        if company_has_infused == template_has_infused:
            infused_filtered_templates.append(template)
    
    current_templates = infused_filtered_templates if infused_filtered_templates else templates
    match_steps = []
    if infused_filtered_templates:
        match_steps.append(f"infused: {'yes' if company_has_infused else 'no'}")
    
    # Filter by weight
    company_weight = row.get('Extracted_Weight')
    if company_weight and len(current_templates) > 1:
        weight_matched_templates = []
        for template in current_templates:
            catalog_weight = extract_weight_from_item(template)
            if catalog_weight == company_weight:
                weight_matched_templates.append(template)
        
        if weight_matched_templates:
            current_templates = weight_matched_templates
            match_steps.append(f"weight: {company_weight}")
    
    # Filter by pack size
    company_pack = row.get('Extracted_Pack_Size')
    if company_pack and len(current_templates) > 1:
        pack_matched_templates = []
        for template in current_templates:
            catalog_pack = extract_pack_size_from_item(template)
            if catalog_pack == company_pack:
                pack_matched_templates.append(template)
        
        if pack_matched_templates:
            current_templates = pack_matched_templates
            match_steps.append(f"pack: {company_pack}")
    elif not company_pack and len(current_templates) > 1:
        # Fallback: prefer templates without pack sizes
        no_pack_templates = []
        for template in current_templates:
            catalog_pack = extract_pack_size_from_item(template)
            if not catalog_pack:
                no_pack_templates.append(template)
        
        if len(no_pack_templates) == 1:
            current_templates = no_pack_templates
            match_steps.append("no pack (fallback)")
    
    return (current_templates[0], match_steps) if len(current_templates) == 1 else (None, [])

def match_vape_extract_products(row, templates, category):
    """Advanced matching for vape and extract products using weight and keywords"""
    current_templates = templates
    match_steps = []
    
    # Filter by weight
    company_weight = row.get('Extracted_Weight')
    if company_weight and len(current_templates) > 1:
        weight_matched_templates = []
        for template in current_templates:
            catalog_weight = extract_weight_from_item(template)
            if catalog_weight == company_weight:
                weight_matched_templates.append(template)
        
        if weight_matched_templates:
            current_templates = weight_matched_templates
            match_steps.append(f"weight: {company_weight}")
    
    # Filter by keywords
    company_keywords = row.get('Extracted_Category_Keywords')
    if company_keywords and len(current_templates) > 1:
        company_keyword_list = [kw.strip() for kw in str(company_keywords).split(',')]
        
        template_scores = []
        for template in current_templates:
            catalog_keywords = extract_category_keywords(template, category)
            if catalog_keywords:
                catalog_keyword_list = [kw.strip() for kw in catalog_keywords.split(',')]
                matches = sum(1 for ck in company_keyword_list if ck in catalog_keyword_list)
                template_scores.append((template, matches, len(catalog_keyword_list), catalog_keyword_list))
            else:
                template_scores.append((template, 0, 0, []))
        
        if template_scores:
            max_score = max(score for _, score, _, _ in template_scores)
            if max_score > 0:
                best_scored_templates = [(template, score, total_kw, kw_list) for template, score, total_kw, kw_list in template_scores if score == max_score]
                
                if len(best_scored_templates) == 1:
                    current_templates = [best_scored_templates[0][0]]
                    matched_keywords = [ck for ck in company_keyword_list if ck in best_scored_templates[0][3]]
                    match_steps.append(f"keywords: {', '.join(matched_keywords)}")
                else:
                    # Tiebreaker: prefer fewer total keywords
                    min_total_keywords = min(total_kw for _, _, total_kw, _ in best_scored_templates)
                    final_candidates = [template for template, score, total_kw, kw_list in best_scored_templates if total_kw == min_total_keywords]
                    
                    if len(final_candidates) == 1:
                        current_templates = final_candidates
                        winner_keywords = [kw_list for template, score, total_kw, kw_list in best_scored_templates if template == final_candidates[0]][0]
                        matched_keywords = [ck for ck in company_keyword_list if ck in winner_keywords]
                        match_steps.append(f"keywords: {', '.join(matched_keywords)} (tiebreaker)")
    elif not company_keywords and len(current_templates) > 1:
        # Fallback: prefer templates without keywords
        no_keyword_templates = []
        for template in current_templates:
            catalog_keywords = extract_category_keywords(template, category)
            if not catalog_keywords:
                no_keyword_templates.append(template)
        
        if len(no_keyword_templates) == 1:
            current_templates = no_keyword_templates
            match_steps.append("no keywords (fallback)")
    
    return (current_templates[0], match_steps) if len(current_templates) == 1 else (None, [])

def advanced_brand_matching(dc_df, catalog_df):
    """Advanced brand-based matching using proven logic from original price checker"""
    if dc_df is None or catalog_df is None:
        return dc_df
    
    st.info("🧠 Starting advanced brand matching...")
    
    matched_df = dc_df.copy()
    matched_df['Catalog_Match_Found'] = False
    matched_df['Catalog_Template'] = None
    matched_df['Match_Type'] = None
    matched_df['Match_Strategy'] = None
    matched_df['Match_Keywords'] = None
    
    # Build brand and category mappings
    brand_catalog_map = {}
    brand_category_catalog_map = {}
    
    for _, cat_row in catalog_df.iterrows():
        brand = cat_row.get('Brand')
        template = cat_row.get('Profile Template')
        category = cat_row.get('Category', 'Unknown')
        
        if pd.notna(brand) and pd.notna(template) and str(template).strip():
            if brand not in brand_catalog_map:
                brand_catalog_map[brand] = []
            brand_catalog_map[brand].append(template)
            
            brand_category_key = f"{brand}|{category}"
            if brand_category_key not in brand_category_catalog_map:
                brand_category_catalog_map[brand_category_key] = []
            brand_category_catalog_map[brand_category_key].append(template)
    
    # Categorize brands by complexity
    single_entry_brands = {}
    multiple_entry_brands = {}
    
    for brand, templates in brand_catalog_map.items():
        if len(templates) == 1:
            single_entry_brands[brand] = templates[0]
        else:
            multiple_entry_brands[brand] = templates
    
    single_entry_brand_categories = {}
    multiple_entry_brand_categories = {}
    
    for brand_category_key, templates in brand_category_catalog_map.items():
        if len(templates) == 1:
            single_entry_brand_categories[brand_category_key] = templates[0]
        else:
            multiple_entry_brand_categories[brand_category_key] = templates
    
    # Filter out exact match brands from auto-matching
    filtered_single_entry_brands = {brand: template for brand, template in single_entry_brands.items() 
                                  if brand not in EXACT_PRODUCT_MATCH_BRANDS}
    filtered_single_entry_brand_categories = {key: template for key, template in single_entry_brand_categories.items() 
                                            if key.split('|')[0] not in EXACT_PRODUCT_MATCH_BRANDS}
    
    # Store debug info
    debug_info = {
        'dc_brands': set(dc_df['Brand'].dropna().unique()),
        'catalog_brands': set(brand_catalog_map.keys()),
        'single_brands': single_entry_brands,
        'multi_brands': multiple_entry_brands,
        'brand_templates': brand_catalog_map
    }
    
    st.write(f"Found {len(filtered_single_entry_brands)} single-template brands and {len(multiple_entry_brands)} multi-template brands")
    
    # Perform matching with all strategies
    exact_matches = 0
    single_entry_matches = 0
    brand_category_matches = 0
    flower_weight_matches = 0
    preroll_matches = 0
    vape_extract_matches = 0
    no_matches = 0
    troubleshooting_data = []
    
    for idx, row in matched_df.iterrows():
        brand = row.get('Brand')
        item = row.get('Item')
        category = row.get('Category', 'Unknown')
        
        if pd.isna(brand) or brand == 'Unknown':
            no_matches += 1
            troubleshooting_data.append({
                'Brand': brand,
                'Item': item,
                'Issue': 'Missing brand or Unknown',
                'Templates_Available': 0,
                'Notes': 'Brand extraction failed or no brand found'
            })
            continue
        
        match_found = False
        templates_available = len(brand_catalog_map.get(brand, []))
        
        # 1. Try exact match first
        if brand in brand_catalog_map:
            for template in brand_catalog_map[brand]:
                if str(item).lower() == str(template).lower():
                    matched_df.at[idx, 'Catalog_Match_Found'] = True
                    matched_df.at[idx, 'Catalog_Template'] = template
                    matched_df.at[idx, 'Match_Type'] = 'exact'
                    matched_df.at[idx, 'Match_Strategy'] = 'exact'
                    exact_matches += 1
                    match_found = True
                    troubleshooting_data.append({
                        'Brand': brand,
                        'Item': item,
                        'Issue': 'MATCHED - Exact',
                        'Templates_Available': templates_available,
                        'Notes': f'Exact match found: {template}'
                    })
                    break
        
        # Skip auto-matching for exact product match brands
        skip_auto_matching = brand in EXACT_PRODUCT_MATCH_BRANDS
        
        # 2. Try single entry brand auto-match
        if not match_found and not skip_auto_matching and brand in filtered_single_entry_brands:
            template = filtered_single_entry_brands[brand]
            matched_df.at[idx, 'Catalog_Match_Found'] = True
            matched_df.at[idx, 'Catalog_Template'] = template
            matched_df.at[idx, 'Match_Type'] = 'brand_auto'
            matched_df.at[idx, 'Match_Strategy'] = 'single_entry'
            single_entry_matches += 1
            match_found = True
            troubleshooting_data.append({
                'Brand': brand,
                'Item': item,
                'Issue': 'MATCHED - Single Entry Auto',
                'Templates_Available': templates_available,
                'Notes': f'Auto-matched to only catalog option: {template}'
            })
        
        # 3. Try brand+category auto-match
        if not match_found and not skip_auto_matching:
            brand_category_key = f"{brand}|{category}"
            if brand_category_key in filtered_single_entry_brand_categories:
                template = filtered_single_entry_brand_categories[brand_category_key]
                matched_df.at[idx, 'Catalog_Match_Found'] = True
                matched_df.at[idx, 'Catalog_Template'] = template
                matched_df.at[idx, 'Match_Type'] = 'brand_category_auto'
                matched_df.at[idx, 'Match_Strategy'] = 'brand_category_single'
                brand_category_matches += 1
                match_found = True
                troubleshooting_data.append({
                    'Brand': brand,
                    'Item': item,
                    'Issue': 'MATCHED - Brand+Category Auto',
                    'Templates_Available': templates_available,
                    'Notes': f'Auto-matched to only {category} option: {template}'
                })
        
        # 4. Try advanced weight/keyword matching for complex categories
        if not match_found and str(category).lower() in ['flower', 'preroll', 'vape', 'extract'] and brand in multiple_entry_brands:
            brand_category_key = f"{brand}|{category}"
            if brand_category_key in multiple_entry_brand_categories:
                templates = multiple_entry_brand_categories[brand_category_key]
                
                # Advanced matching logic for different categories
                matched_template = None
                match_steps = []
                
                if str(category).lower() == 'flower':
                    matched_template, match_steps = match_flower_products(row, templates)
                elif str(category).lower() == 'preroll':
                    matched_template, match_steps = match_preroll_products(row, templates)
                elif str(category).lower() in ['vape', 'extract']:
                    matched_template, match_steps = match_vape_extract_products(row, templates, category)
                
                if matched_template:
                    matched_df.at[idx, 'Catalog_Match_Found'] = True
                    matched_df.at[idx, 'Catalog_Template'] = matched_template
                    matched_df.at[idx, 'Match_Type'] = f'{str(category).lower()}_weight_keywords'
                    matched_df.at[idx, 'Match_Strategy'] = f'{str(category).lower()}_weight_keywords'
                    matched_df.at[idx, 'Match_Keywords'] = ', '.join(match_steps)
                    
                    if str(category).lower() == 'flower':
                        flower_weight_matches += 1
                    elif str(category).lower() == 'preroll':
                        preroll_matches += 1
                    else:
                        vape_extract_matches += 1
                    
                    match_found = True
                    troubleshooting_data.append({
                        'Brand': brand,
                        'Item': item,
                        'Issue': f'MATCHED - {category} Advanced',
                        'Templates_Available': templates_available,
                        'Notes': f'Advanced match by: {", ".join(match_steps)}'
                    })
        
        if not match_found:
            no_matches += 1
            if brand not in brand_catalog_map:
                issue = 'Brand not in catalog'
                notes = 'Brand extracted but not found in catalog'
            elif brand in EXACT_PRODUCT_MATCH_BRANDS:
                issue = 'Exact-match-only brand'
                notes = f'Brand requires exact product matches, has {templates_available} templates'
            elif brand in multiple_entry_brands:
                issue = 'Multi-template brand'
                notes = f'Brand has {templates_available} templates, needs advanced matching'
            else:
                issue = 'Unknown reason'
                notes = 'Could not determine why no match found'
            
            troubleshooting_data.append({
                'Brand': brand,
                'Item': item,
                'Issue': issue,
                'Templates_Available': templates_available,
                'Notes': notes
            })
    
    total_matches = exact_matches + single_entry_matches + brand_category_matches + flower_weight_matches + preroll_matches + vape_extract_matches
    match_rate = (total_matches / len(matched_df)) * 100 if len(matched_df) > 0 else 0
    
    st.success(f"🎉 Advanced Matching Results:")
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        st.metric("🎯 Exact", f"{exact_matches:,}")
    with col2:
        st.metric("1️⃣ Single Brand", f"{single_entry_matches:,}")
    with col3:
        st.metric("📂 Brand+Category", f"{brand_category_matches:,}")
    with col4:
        st.metric("🌸 Flower", f"{flower_weight_matches:,}")
    with col5:
        st.metric("🚬 Preroll", f"{preroll_matches:,}")
    with col6:
        st.metric("💨 Vape/Extract", f"{vape_extract_matches:,}")
    with col7:
        st.metric("📊 Total", f"{total_matches:,}")
    with col8:
        st.metric("📈 Rate", f"{match_rate:.1f}%")
    
    # Store troubleshooting data and merge debug info
    troubleshooting_df = pd.DataFrame(troubleshooting_data)
    matched_df.troubleshooting_data = troubleshooting_df
    matched_df.debug_info = debug_info
    
    return matched_df

def add_cost_comparison(dc_df, catalog_df):
    """Compare DC costs against catalog Max Unit Cost"""
    if dc_df is None or catalog_df is None:
        return dc_df
    
    matched_products = dc_df[dc_df['Catalog_Match_Found'] == True].copy()
    
    if len(matched_products) == 0:
        st.warning("⚠️ No matched products for cost comparison")
        return dc_df
    
    st.info(f"💰 Comparing costs for {len(matched_products)} matched products...")
    
    # Build catalog lookup
    catalog_lookup = {}
    for _, cat_row in catalog_df.iterrows():
        template = cat_row.get('Profile Template')
        if pd.notna(template):
            catalog_lookup[template] = cat_row
    
    # Initialize comparison columns
    dc_df['Catalog_Max_Cost'] = None
    dc_df['Cost_Diff'] = None
    dc_df['Price_Diff'] = None
    dc_df['Cost_Status'] = None
    dc_df['Price_Status'] = None
    
    cost_violations = 0
    price_violations = 0
    
    for idx, row in matched_products.iterrows():
        template = row.get('Catalog_Template')
        if pd.isna(template):
            continue
        
        catalog_data = catalog_lookup.get(template)
        if catalog_data is None:
            continue
        
        max_cost = clean_price(catalog_data.get('Max Unit Cost'))
        dc_cost = row.get('Cost_Clean')
        dc_price = row.get('Price_Clean')
        
        dc_df.at[idx, 'Catalog_Max_Cost'] = max_cost
        
        # Check Cost Per Unit
        if max_cost is not None and dc_cost is not None:
            cost_diff = dc_cost - max_cost
            dc_df.at[idx, 'Cost_Diff'] = round(cost_diff, 2)
            
            if abs(cost_diff) <= 0.01:
                dc_df.at[idx, 'Cost_Status'] = 'Match'
            elif cost_diff > 0.01:
                dc_df.at[idx, 'Cost_Status'] = 'Over Max'
                cost_violations += 1
            else:
                dc_df.at[idx, 'Cost_Status'] = 'Under Max'
        else:
            dc_df.at[idx, 'Cost_Status'] = 'Missing Data'
        
        # Check Price Per Unit
        if max_cost is not None and dc_price is not None:
            price_diff = dc_price - max_cost
            dc_df.at[idx, 'Price_Diff'] = round(price_diff, 2)
            
            if abs(price_diff) <= 0.01:
                dc_df.at[idx, 'Price_Status'] = 'Match'
            elif price_diff > 0.01:
                dc_df.at[idx, 'Price_Status'] = 'Over Max'
                price_violations += 1
            else:
                dc_df.at[idx, 'Price_Status'] = 'Under Max'
        else:
            dc_df.at[idx, 'Price_Status'] = 'Missing Data'
    
    st.success(f"💰 Cost comparison complete!")
    if cost_violations > 0:
        st.warning(f"🔴 {cost_violations} products have Cost Per Unit over Max Unit Cost")
    if price_violations > 0:
        st.warning(f"🔴 {price_violations} products have Price Per Unit over Max Unit Cost")
    
    return dc_df

def main():
    st.title(f"💰 DC Unit Cost Checker v{VERSION}")
    st.markdown("Smart product matching and unit cost validation against catalog Max Unit Cost")
    
    # Check for Google Sheets configuration
    try:
        google_sheets_available = "google_sheets" in st.secrets
    except:
        google_sheets_available = False
    
    st.sidebar.header("📊 Data Sources")
    
    # File upload
    uploaded_file = st.sidebar.file_uploader(
        "Upload DC Products CSV:",
        type=['csv'],
        help="Upload your DC product CSV file"
    )
    
    # Google Sheets status
    if google_sheets_available:
        st.sidebar.success("✅ Product Catalog - Configured")
    else:
        st.sidebar.warning("⚠️ Google Sheets API not configured")
    
    # Load data button
    if st.sidebar.button("🚀 Load Data", type="primary"):
        with st.spinner("Loading data..."):
            
            # Load catalog
            catalog_df = None
            if google_sheets_available:
                st.info("📊 Loading Product Catalog...")
                catalog_df, _ = load_google_sheet_data(CONNECT_CATALOG_URL)
                if catalog_df is not None:
                    st.success(f"✅ Loaded Product Catalog: {len(catalog_df)} records")
                    st.session_state['catalog_df'] = catalog_df
                else:
                    st.error("❌ Failed to load Product Catalog")
            
            # Load and process DC products
            if uploaded_file is not None:
                st.info("📄 Processing DC Products...")
                dc_df, _ = load_csv_data(uploaded_file)
                if dc_df is not None:
                    # Process the data
                    processed_df = process_dc_products(dc_df, catalog_df)
                    
                    if processed_df is not None and catalog_df is not None:
                        # Add advanced matching and cost comparison
                        matched_df = advanced_brand_matching(processed_df, catalog_df)
                        final_df = add_cost_comparison(matched_df, catalog_df)
                        
                        # Preserve debug info from both processing and matching
                        if hasattr(processed_df, 'brand_filter_debug'):
                            final_df.brand_filter_debug = processed_df.brand_filter_debug
                        if hasattr(matched_df, 'debug_info'):
                            final_df.debug_info = matched_df.debug_info
                        if hasattr(matched_df, 'troubleshooting_data'):
                            final_df.troubleshooting_data = matched_df.troubleshooting_data
                        
                        st.session_state['dc_df'] = final_df
                        st.success(f"✅ Processed {len(final_df)} DC products with matching and cost comparison")
                    elif processed_df is not None:
                        st.session_state['dc_df'] = processed_df
                        st.success(f"✅ Processed {len(processed_df)} DC products (no catalog for matching)")
                    else:
                        st.error("❌ Failed to process DC Products")
                else:
                    st.error("❌ Failed to load DC Products CSV")
    
    # Display results
    if 'dc_df' in st.session_state:
        df = st.session_state['dc_df']
        
        # Create tabs
        if 'Catalog_Match_Found' in df.columns:
            if hasattr(df, 'troubleshooting_data'):
                tabs = st.tabs(["📊 Overview", "📄 All Products", "💰 Cost Issues", "🔧 Troubleshooting"])
            else:
                tabs = st.tabs(["📊 Overview", "📄 All Products", "💰 Cost Issues"])
        else:
            tabs = st.tabs(["📊 Overview", "📄 All Products"])
        
        # Overview tab
        with tabs[0]:
            st.subheader("📊 Overview")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Products", f"{len(df):,}")
            
            if 'Catalog_Match_Found' in df.columns:
                matched_count = df['Catalog_Match_Found'].sum()
                match_rate = (matched_count / len(df) * 100) if len(df) > 0 else 0
                
                with col2:
                    st.metric("Match Rate", f"{match_rate:.1f}%")
                
                if 'Cost_Status' in df.columns:
                    cost_violations = (df['Cost_Status'] == 'Over Max').sum()
                    price_violations = (df['Price_Status'] == 'Over Max').sum()
                    
                    with col3:
                        st.metric("Cost Violations", cost_violations)
                    with col4:
                        st.metric("Price Violations", price_violations)
                    
                    # Status breakdown
                    if cost_violations > 0 or price_violations > 0:
                        st.write("**💰 Cost Analysis:**")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Cost Per Unit vs Max:**")
                            cost_counts = df['Cost_Status'].value_counts()
                            for status, count in cost_counts.items():
                                icon = "✅" if status == "Match" else "🔴" if status == "Over Max" else "🟡"
                                st.write(f"{icon} {status}: {count}")
                        
                        with col2:
                            st.write("**Price Per Unit vs Max:**")
                            price_counts = df['Price_Status'].value_counts()
                            for status, count in price_counts.items():
                                icon = "✅" if status == "Match" else "🔴" if status == "Over Max" else "🟡"
                                st.write(f"{icon} {status}: {count}")
        
        # All products tab
        with tabs[1]:
            st.subheader("📄 All DC Products")
            st.dataframe(df, use_container_width=True)
            
            # Download button
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            st.download_button(
                label="📥 Download Results",
                data=csv_buffer.getvalue(),
                file_name="dc_unit_cost_analysis.csv",
                mime="text/csv"
            )
        
        # Cost issues tab (if matching was performed)
        if len(tabs) > 2:
            with tabs[2]:
                st.subheader("💰 Cost Violations")
                
                # Filter to only violations
                violations = df[
                    (df['Cost_Status'] == 'Over Max') | 
                    (df['Price_Status'] == 'Over Max')
                ]
                
                if len(violations) > 0:
                    st.write(f"Found {len(violations)} products with cost violations:")
                    
                    display_cols = [
                        'Brand', 'Item', 'Cost Per Unit ($)', 'Price Per Unit ($)', 
                        'Catalog_Max_Cost', 'Cost_Diff', 'Price_Diff', 
                        'Cost_Status', 'Price_Status'
                    ]
                    available_cols = [col for col in display_cols if col in violations.columns]
                    
                    st.dataframe(violations[available_cols], use_container_width=True)
                    
                    # Download violations
                    csv_buffer = io.StringIO()
                    violations[available_cols].to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="📥 Download Cost Violations",
                        data=csv_buffer.getvalue(),
                        file_name="dc_cost_violations.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("🎉 No cost violations found!")
        
        # Troubleshooting tab (if available)
        if hasattr(df, 'troubleshooting_data') and len(tabs) > 3:
            with tabs[3]:
                st.subheader("🔧 Troubleshooting")
                st.info("Debug information for brand extraction, filtering, and matching")
                
                troubleshooting_df = df.troubleshooting_data
                debug_info = df.debug_info
                
                # Brand extraction and filtering analysis
                st.write("**🔍 Brand Analysis:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("DC Brands Extracted", len(debug_info['dc_brands']))
                with col2:
                    st.metric("Catalog Brands", len(debug_info['catalog_brands']))
                with col3:
                    overlap = debug_info['dc_brands'].intersection(debug_info['catalog_brands'])
                    st.metric("Brand Overlap", len(overlap))
                
                # Show brand lists
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**DC Brands (first 10):**")
                    dc_brands_list = sorted(list(debug_info['dc_brands']))[:10]
                    for brand in dc_brands_list:
                        st.write(f"• {brand}")
                
                with col2:
                    st.write("**Catalog Brands (first 10):**")
                    catalog_brands_list = sorted(list(debug_info['catalog_brands']))[:10]
                    for brand in catalog_brands_list:
                        st.write(f"• {brand}")
                
                # Show brands not in catalog
                missing_brands = debug_info['dc_brands'] - debug_info['catalog_brands']
                if len(missing_brands) > 0:
                    st.write(f"**❌ DC Brands NOT in Catalog ({len(missing_brands)}):**")
                    st.write(", ".join(sorted(list(missing_brands))[:20]))
                
                # Show multi-template brands
                multi_in_dc = {brand: templates for brand, templates in debug_info['multi_brands'].items() 
                              if brand in debug_info['dc_brands']}
                if len(multi_in_dc) > 0:
                    st.write(f"**🔀 Multi-Template Brands in DC ({len(multi_in_dc)}):**")
                    for brand, templates in list(multi_in_dc.items())[:5]:
                        st.write(f"• **{brand}**: {len(templates)} templates")
                        for template in templates[:3]:
                            st.write(f"  - {template}")
                        if len(templates) > 3:
                            st.write(f"  - ... and {len(templates)-3} more")
                
                # Issue breakdown
                st.write("**📊 Matching Issues Breakdown:**")
                issue_counts = troubleshooting_df['Issue'].value_counts()
                
                for issue, count in issue_counts.items():
                    if issue.startswith('MATCHED'):
                        icon = "✅"
                    elif issue == 'Multi-template brand':
                        icon = "🔀"
                    elif issue == 'Brand not in catalog':
                        icon = "❌"
                    else:
                        icon = "⚠️"
                    
                    st.write(f"{icon} **{issue}**: {count:,} products")
                
                # Detailed troubleshooting data
                st.write("**📋 Detailed Troubleshooting Data:**")
                
                # Filter options
                selected_issue = st.selectbox(
                    "Filter by Issue Type:",
                    options=['All Issues'] + list(issue_counts.index),
                    index=0
                )
                
                filtered_troubleshooting = troubleshooting_df.copy()
                if selected_issue != 'All Issues':
                    filtered_troubleshooting = filtered_troubleshooting[
                        filtered_troubleshooting['Issue'] == selected_issue
                    ]
                
                st.write(f"Showing {len(filtered_troubleshooting)} of {len(troubleshooting_df)} records")
                st.dataframe(filtered_troubleshooting, use_container_width=True)
                
                # Download troubleshooting data
                csv_buffer = io.StringIO()
                filtered_troubleshooting.to_csv(csv_buffer, index=False)
                st.download_button(
                    label="📥 Download Troubleshooting Data",
                    data=csv_buffer.getvalue(),
                    file_name="dc_troubleshooting_data.csv",
                    mime="text/csv"
                )
    
    else:
        # Welcome screen
        st.info("👆 Upload your DC Products CSV and click 'Load Data' to get started")
        
        st.markdown(f"""
        **💰 DC Unit Cost Checker v{VERSION} Features:**
        
        1. **📄 DC Products Processing**
           - Extract brands from product names (before " - ")
           - Filter out inactive products
           - Smart brand matching with catalog
        
        2. **💰 Unit Cost Validation**
           - Compare Cost Per Unit vs Catalog Max Unit Cost
           - Compare Price Per Unit vs Catalog Max Unit Cost
           - Flag violations exceeding max costs
        
        3. **📊 Results & Export**
           - Overview with violation counts
           - Detailed product listings
           - Export capabilities for further analysis
        """)

if __name__ == "__main__":
    main()