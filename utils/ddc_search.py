import os
import re
import sys
import time
import tqdm
import string
import datetime
import requests
import textwrap
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup
import matplotlib.pyplot as plt
from collections import defaultdict
from utils.webpage_scraping import test_connection
from utils.pickle_dataframes import pickle_dataframe
from utils.drug_search import clean_drug_name
from utils.fda_sponsors import fda_sponsor_list, rename_sponsors

def scrape_drug_links(save_df=False):
	'''
	Scrape drugs.com for all drug links
	'''
	base_link = 'https://www.drugs.com'
	alphabet = list(string.ascii_lowercase) + ['0-9']
	drug_urls = defaultdict(dict)
	print(f'Scraping drug links from {base_link}...')
	for letter in alphabet:
		print('  Scraping drugs starting with letter:', letter)
		url = f'{base_link}/alpha/{letter}.html'
		response = test_connection(url)
		soup = BeautifulSoup(response.text, "html.parser")
		# get table from tag '<ul class="ddc-list-column-2">'
		table = soup.find_all("ul", class_="ddc-list-column-2")[0]
		# get all links
		links = table.find_all("a")
		# get hrefs for the links
		link_hrefs = [link["href"] for link in links]
		# get all text from the links
		drug_names = [link.get_text() for link in links]
		print(f'    Number of drugs starting with {letter}: {len(links)}')
		drug_url_list = [base_link + link for link in link_hrefs]
		# insert list into dictionary
		for i, drug_name in enumerate(drug_names):
			drug_urls[drug_name] = drug_url_list[i]
	# convert to dataframe
	df_drugs = pd.DataFrame(drug_urls.items(), columns=['drug_name', 'drug_link'])
	if save_df:
		pickle_dataframe(df_drugs, 'databases/ddc_drugs.pkl')
	return df_drugs

def scrape_drug_class(base_link, drug_class, drug_class_url):
	print(f'   Scraping drug class: {drug_class}...')
	response = test_connection(drug_class_url)
	soup = BeautifulSoup(response.text, "html.parser")
	# find all tables
	tables = soup.find_all("table", class_="data-list")
	if len(tables) == 0:
		print(f'    No tables found for {drug_class}')
		return None
	# print number of rows
	drugs = tables[0].find_all("tr")
	# get all links and text from <a class href="link">text</a>
	drug_dict = defaultdict(dict)
	for drug in drugs:
		# get <td> tags
		cols = drug.find_all("td")
		if len(cols) == 0:
			continue
		# get drug name
		drug_info = cols[0]
		# get everything between <b> and </b> tags
		drug_name_break = drug_info.find("b")
		if drug_name_break is None:
			continue
		drug_name = drug_name_break.get_text()
		print(f'      {drug_name}')
		# if "Generic name:" is in the text, get the text after it
		generic_name = None
		if "Generic name:" in drug_info.get_text():
			generic_name = drug_info.get_text().split("Generic name:")[1].strip()
		# get link
		drug_link = base_link + drug_info.find("a")["href"]
		# add to dictionary
		drug_dict[drug_name] = {
			"generic_name": generic_name,
			"drug_link": drug_link
		}
	print(f'    Number of drugs in class: {len(drug_dict)}')
	return drug_dict

def scrape_drug_classes(save_df=False):
	df_drug_classes = pd.DataFrame(columns=['drug_name', 'generic_name', 'drug_link', 'drug_class',  'drug_class_description', 'drug_class_url'])
	base_link = 'https://www.drugs.com'
	drug_class_suffix = '/drug-classes.html'
	# get all drug classes
	print(f'Scraping drug links from {base_link+drug_class_suffix}...')
	response = test_connection(base_link+drug_class_suffix)
	soup = BeautifulSoup(response.text, "html.parser")
	# get table from <div class="ddc-grid"
	table = soup.find_all("div", class_="ddc-grid")[0]
	# get all links and text from <a class href="link">text</a>
	links = table.find_all("a")
	# get hrefs for the links
	drug_classes_dict = defaultdict(str)
	for link in links:
		drug_classes_dict[link.get_text()] = base_link + link["href"]
	print(f'  Number of drug classes: {len(drug_classes_dict)}')
	# convert to dataframe
	for d_index, (drug_class, drug_class_url) in enumerate(drug_classes_dict.items()):
		drug_dict = scrape_drug_class(base_link, drug_class, drug_class_url)
		if drug_dict is None:
			continue
		for drug_name, drug_info in drug_dict.items():
			# add to dataframe
			df = pd.DataFrame({
				"drug_name": [drug_name],
				"generic_name": [drug_info['generic_name']],
				"drug_link": [drug_info['drug_link']],
				"drug_class": [drug_class],
				"drug_class_description": [None],
				"drug_class_url": [drug_class_url]
			})
			df_drug_classes = pd.concat([df_drug_classes, df], ignore_index=True)
	print(f' Total number of drugs in drug classes: {len(df_drug_classes)}')
	if save_df:
		pickle_dataframe(df_drug_classes, 'databases/ddc_drug_classes.pkl')
	return df_drug_classes


def get_drug_subtitle(soup, info_headers):
	# get all <b> tags from <p class="drug_subtitle>"
	try:
		subtitles = soup.find_all("p", class_="drug-subtitle")[0]
	except:
		return None
	subtitles_text = subtitles.get_text()
	info = defaultdict(dict)
	for header in info_headers:
		info[header] = None
	subtitles_text_split = subtitles_text.split("\n")
	past_header = None
	for i, text in enumerate(subtitles_text_split):
		header_split = text.split(':')
		if len(header_split) > 1 and header_split[0].strip() in info_headers:
			info[header_split[0].strip()] = header_split[1].strip()
			past_header = header_split[0].strip()
		elif past_header == 'Brand names':
			# get all text after '... show all <int> brands'
			more_brands = re.search(r'... show all \d+ brands', text)
			if more_brands:
				info['Brand names'] += subtitles_text_split[i+2]
	try:
		# class="ddc-box ddc-accordion ddc-accordion-no-border"
		drug_status = soup.find_all("div", class_="ddc-box ddc-accordion ddc-accordion-no-border")[0]
	except:
		return info
	# get all <b> tags and text
	drug_status_header_tags = drug_status.find_all("div", class_="ddc-status-info-item-heading")
	for i, header in enumerate(drug_status_header_tags):
		# get all text
		header_text = [text for text in header.get_text().split('\n') if text]
		info[header_text[0]] = ' '.join(header_text[1:])
	# APPROVAL HISTORY LEFT UNSCRAPED
	return info

def scrape_h2_text(soup, id="warnings"):
	text = ""
	text_found = soup.find_all("h2", id=id)
	# keep getting <p> tags until the next <h2> tag
	if len(text_found) > 0:
		for tag in text_found[0].find_next_siblings():
			if tag.name == "h2":
				break
			if tag.name == "p":
				text += tag.get_text() + " "
	return text

def scrape_manufacturer(soup):
	manufacturer_text = ""
	manufacturer = soup.find_all("h2")
	manufacturer_block = [m for m in manufacturer if 'Manufacturer' in m.get_text()]
	if len(manufacturer_block) == 0:
		return manufacturer_text
	# get children of the manufacturer block
	manufacturer_text = manufacturer_block[0].find_next_siblings()
	# get <p> tags
	manufacturer_p = [m for m in manufacturer_text if m.name == 'p']
	# get text
	manufacturer_text = manufacturer_p[0].get_text()
	return manufacturer_text

def scrape_drug_info(drug, info_headers):
	'''
	Scrape drug name, active ingredient, and description from drugs.com
	'''
	dosage_types = ['(oral)', '(injection)', '(topical)', '(intravenous)', '(subcutaneous)', '(nasal)', '(ophthalmic)', '(vaginal)', '(rectal)', '(inhalation)']
	url  = drug['drug_link']
	print(f'  Scraping drug info from {url}...')
	response = test_connection(url)
	soup = BeautifulSoup(response.text, 'html.parser')
	# get drug name
	try:
		drug_name = soup.find_all("h1")[0].get_text()
	except:
		print(f'    No drug name found for {url}')
		return drug
	drug_info = get_drug_subtitle(soup, info_headers)
	if not drug_info:
		return drug
	drug_info['uses']  = scrape_h2_text(soup, id="uses")
	drug_info['side_effects'] = scrape_h2_text(soup, id="side-effects")
	drug_info['warnings'] = scrape_h2_text(soup, id="warnings")
	drug_info['before_taking'] = scrape_h2_text(soup, id="before-taking")
	drug_info['dosage'] = scrape_h2_text(soup, id="dosage")
	drug_info['avoid'] = scrape_h2_text(soup, id="what-to-avoid")
	drug_info['interactions'] = scrape_h2_text(soup, id="interactions")
	drug_info['storage'] = scrape_h2_text(soup, id="storage")
	drug_info['ingredients'] = scrape_h2_text(soup, id="ingredients")
	drug_info['manufacturer'] = scrape_manufacturer(soup)
	# update the dataframe
	for header in info_headers:
		# if Generic name is not available, use the drug name
		if header == 'Generic name':
			if not drug_info[header]:
				drug_info[header] = drug_name
			# parse out aripiprazole (oral) [ AR-i-PIP-ra-zole ] -> oral
			for dosage_type in dosage_types:
				if dosage_type in drug_info[header]:
					# generic name
					drug_info[header] = drug_info[header].split(dosage_type)[0].strip()
					# dosage form
					drug_info['Dosage form'] = dosage_type.replace('(', '').replace(')', '').strip()
				# eliminate pronunciation
				if '[' in drug_info[header]:
					drug_info[header] = drug_info[header].split('[')[0].strip()
		drug[header] = drug_info[header]
	return drug

def scrape_drugs(df, df_name='ddc_drugs', save_df=False, verbose=True):
	'''
	Scrape drug name, active ingredient, and description for all drug urls
	'''
	info_headers = ['Generic name', 'Brand names', 'Dosage form', 'Drug class', 'uses', 'side-effects', 'warnings', 'before_taking', 'dosage', 'avoid', 'interactions', 'storage', 'ingredients', 'manufacturer']
	for header in info_headers:
		df[header] = None
	for d_index, (drug_row, drug) in enumerate(df.iterrows()):
		if verbose:
			print(f'Scraping drug {drug["drug_name"]} ({d_index+1}/{len(df)})...')
		df.iloc[d_index] = scrape_drug_info(drug, info_headers)
	if save_df:
		pickle_dataframe(df, f'databases/{df_name}.pkl')
	return df

# see overlap between dataframes
def combine_fda_ddc(df_1, df_2, field_1='fda_drug_name', field_2='active_ingredient', sponsor_field='fda_2_sponsor', manufacturer_field='ddc_manufacturer'):
	print(f'Finding overlap between {field_1} in dataframes...')
	fda_columns = list(df_1.columns)
	ddc_columns = list(map('ddc_{}'.format, list(df_2.columns)))
	combined_columns = fda_columns + ddc_columns
	fda_ddc_df = pd.DataFrame(columns=combined_columns)
	for i, drug in df_1.iterrows():
		# check if the drug name is in the active ingredient field
		drug_1_lower = clean_drug_name(drug[field_1].lower())
		active_ingredient_lower = drug[field_2].lower()
		ddc_found = False
		for j, drug_2 in df_2.iterrows():
			# check if the drug name is in the active ingredient field
			drug_2_lower = clean_drug_name(drug_2['drug_name'].lower())
			generic_name_2 = drug_2['drug_name_generic']
			if generic_name_2 is None:
				generic_name_2 = ''
			generic_name_2_lower = generic_name_2.lower()
			if drug_1_lower == drug_2_lower or \
				 drug_1_lower == generic_name_2_lower or \
				 active_ingredient_lower == generic_name_2_lower or \
				 active_ingredient_lower == drug_2_lower:
				# concatenate drug_2 to the fda_ddc_df with all the columns
				ddc_row = [*drug, *drug_2]
				fda_ddc_df.loc[i] = ddc_row
				print(f'  {drug[field_1]:<20} -> {fda_ddc_df.loc[i]["ddc_drug_name"]:<20}...({i}/{len(df_1)})')
				ddc_found = True
				break
			# add the drug to the fda_ddc_df with the fda_name and fda_active_ingredient
		drug_name = '-'.join(drug[field_1].split(' '))
		if not ddc_found:
			# concatenate drug_2 to the fda_ddc_df with all the columns
			test_dict = defaultdict(str)
			drug_name = '-'.join(drug[field_1].split(' '))
			ddc_urls = [f'https://www.drugs.com/{drug_name}.html', f'https://www.drugs.com/pro/{drug_name}.html']
			drug_found = False
			for ddc_url in ddc_urls:
				test_dict[drug[field_1]] = ddc_url
				test_df = pd.DataFrame(test_dict.items(), columns=['drug_name', 'drug_link'])
				ddc_row = scrape_drugs(test_df, verbose=False)
				if ddc_row['Generic name'].values[0] != None:
					# same columns as df_2 but with nans
					new_row = pd.DataFrame(None, index=[0], columns=df_2.columns)
					# insert nan
					# concatenate drug_2 to the fda_ddc_df with all the columns
					for col in new_row.columns:
						if col in ddc_row.columns:
							new_row.loc[0, col] = ddc_row.loc[0, col]
					ddc_row = [*drug] + new_row.values.tolist()[0]
					fda_ddc_df.loc[i] = ddc_row
					print(f'  FOUND: {drug[field_1]:<20} -> {fda_ddc_df.loc[i]["ddc_drug_name"]:<20}...({i}/{len(df_1)})')
					drug_found = True
					break
			if drug_found == False:
				new_row = pd.DataFrame(None, index=[0], columns=df_2.columns)
				ddc_row = [*drug] + new_row.values.tolist()[0]
				fda_ddc_df.loc[i] = ddc_row
				missing_str = 'No match found...'
				print(f'  {drug[field_1]:<20} -> {missing_str:<20}...({i}/{len(df_1)})')
	# count number of drugs with non-nan values for ddc_drug_name
	print(f'Number of drugs with ddc_drug_name: {len(fda_ddc_df.dropna(subset=["ddc_drug_name"]))}')
	# add sponsors
	if sponsor_field in fda_ddc_df.columns:
		fda_ddc_df = rename_sponsors(fda_ddc_df, sponsor_field=sponsor_field, new_field='fda_sponsor')
	if manufacturer_field in fda_ddc_df.columns:
		fda_ddc_df = rename_sponsors(fda_ddc_df, sponsor_field=manufacturer_field, new_field='ddc_sponsor')
	return fda_ddc_df