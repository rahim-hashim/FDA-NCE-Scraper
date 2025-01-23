import os
import re
import sys
import time
import json
import string
import datetime
import pprint
import pandas as pd
import numpy as np
from tqdm.auto import tqdm
from bs4 import BeautifulSoup
from textwrap import indent
import matplotlib.pyplot as plt
from pprint import pprint, pformat
import urllib.request, urllib.parse, urllib.error
from collections import defaultdict, Counter
# api_keys.py contains the API key for NCBI Entrez
from utils.api_keys import ncbi_api_key

# Class Instantiation
### Called within SalzmanParser to instantiate class objects and attributes
class SearchParameters:
		def __init__(self, parameters):
				
				self.database = parameters['database']
				self.searchTerms = parameters['searchTerms']
				self.searchLimit = parameters['searchLimit']
				self.startIndex = parameters['startIndex']

class Affiliation:
		def __init__(self):

				self.department = []
				self.university = []
				self.institute = []
				self.zipcode = []
				self.city = []
				self.state = []
				self.country = []
				self.email = []

class Author:
		def __init__(self):
				
				self.name = 'No Author Listed'
				self.listed_order = 0
				self.affiliations = {}

# eSearchLinkGenerator : Generates URL using user-specified [Database][SearchTerms][NumOfPMIDs] for NCBI Entrez Search Engine
#	Base URL : https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi
#	For more info on Entrez : https://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch
def eSearchLinkGenerator(url, searchParameters, api=None): 
	print('Generating Entrez XML...')
	urlList = []
	url = url.split('=')
	print('  Search Terms:', searchParameters.searchTerms)
	for term in searchParameters.searchTerms:
		termSplit = term.split (' ')
		finalTerm = ''
		for word in termSplit:
			finalTerm += word + '+'
		databaseTemp = searchParameters.database + url[1]
		finalTerm = finalTerm[:-1] # remove trailing '+' from finalTerm
		finalTerm += url[2]
		articleVolumeTemp = str(searchParameters.searchLimit) + url[3]
		indexTemp = str(searchParameters.startIndex) + url[4]
		updated_url = '='.join([url[0], databaseTemp, finalTerm, articleVolumeTemp, indexTemp])
		if api != None:
			updated_url += '&api_key=' + api
		urlList.append(updated_url)
		print(f'   [ {term} ] complete')
	return urlList


# PMID_ListGenerator : Reads eSearchLinkGenerator output and generating a list of PMIDs resulting from [SearchTerms] search
def PMID_ListGenerator(eSearchList):
	print('\nGenerating list of PMIDs...')
	finalList = []
	for term in eSearchList:
		r = urllib.request.urlopen(term).read().decode('utf-8')
		PMID_List = re.findall('<Id>(.*?)</Id>', r)
		prefix = 'https://www.ncbi.nlm.nih.gov/pubmed/'
		resultsList = []
		for PMID in PMID_List:
			link = prefix+PMID
			resultsList.append(link)
		finalList.append(resultsList)
		# searchTerm = re.findall('<From>(.*?)</From>', r)[0]
		print(f'  {term} : {len(PMID_List)} results')
	print(f'  Number of PMIDs: {len(finalList)}')
	return finalList

def entrezSearch(searchParameters):
	'''
	entrezSearch generates resultsList, which is
	a list of all article URLs for each search term

	Args:
		searchParameters (SearchParameters): SearchParameters object
		containing search parameters assigned above

	Returns:
		resultsList (list): list of all article URLs for each search term
	'''
	eSearchCore = 'http://eutils.ncbi.nlm.nih.gov/entrez//eutils/esearch.fcgi/?db=&term=&retmax=&retstart='
	api = ncbi_api_key
	eSearchLinkList = eSearchLinkGenerator(eSearchCore, searchParameters, api)
	resultsList = PMID_ListGenerator(eSearchLinkList)
	return resultsList


def linksParser(termLinks, searchParameters, searchTerm):
	'''
	linksParser reads each URL from PMID_ListGenerator output 
	and parses specified info
	'''
	print('  ', searchTerm)
	articleCount = 0
	abstract_text = []
	searchesHash = defaultdict(lambda: defaultdict(list)) # primary key = PMID
	for link in tqdm(termLinks):
		searchHash = defaultdict(str)
		authorAffiliationDict = defaultdict(list)
		affiliationDict = defaultdict(str)
		searchHash['articleCount'] = articleCount
		articleCount += 1
		# Open, read and process link through BeautifulSoup
		r1 = urllib.request.urlopen(link).read()
		soup = BeautifulSoup(r1, "html.parser")
		# ARTICLE NAME Parser
		article_title = soup.find('title').text
		searchHash['article_title'] = article_title
		# META INFO (journal title, date published)
		meta = soup.find_all('meta')
		author_list = []
		author_institutions = []
		for tag in meta:
			if 'name' in tag.attrs.keys():
				if tag.attrs['name'] == 'citation_journal_title':
					searchHash['journal_title'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_journal_abbrev':
					searchHash['journal_title_abv'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_publisher':
					searchHash['publisher'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_abstract':
					searchHash['abstract'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_keywords':
					keywords_uncleaned = tag.attrs['content'].split(';')
					keywords = [keyword.strip().rstrip('.').lower() for keyword in keywords_uncleaned]
					searchHash['keywords'] = keywords
				elif tag.attrs['name'] == 'citation_publication_date' or tag.attrs['name'] == 'citation_online_date':
					if len(tag.attrs['content'].split('/')) == 2: # date format (YYYY/MM)
						tag.attrs['content'] = tag.attrs['content'].split('/')[0]
					searchHash['publication_date'] = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_author':
					author_list.append(tag.attrs['content'])
				elif tag.attrs['name'] == 'citation_author_institution':
					author_institutions.append(tag.attrs['content'])
				elif tag.attrs['name'] == 'citation_pmid':
					PMID = tag.attrs['content']
				elif tag.attrs['name'] == 'citation_doi':
					searchHash['doi'] = 'doi.org/' + tag.attrs['content']
		searchHash['authors'] = author_list
		searchHash['author_institutions'] = author_institutions
		searchesHash[PMID] = searchHash
		# pause for a second to avoid overloading the server
		time.sleep(1)
		# AUTHOR AFFILIATION Parser
		# author_soup = soup.find_all("span", {"class": "authors-list-item"})
		# for index, author_info in enumerate(author_soup):
		# 	author = author_list[index]
		# 	author_text = author_info.text.split()
		# 	author_affiliations = [item for item in author_text if item.isnumeric()]
		# 	affiliations = author_info.find_all(class_='affiliation-link')
		# 	affiliation_list = [affiliation_title['title'] for affiliation_title in affiliations]
		# 	for affiliation_index, affiliation_number in enumerate(author_affiliations):
		# 		affiliationDict[affiliation_number] = affiliation_list[affiliation_index]
		# 		authorAffiliationDict[author].append(affiliation_number)
		# searchHash['affiliation_dict'] = affiliationDict
		# searchHash['author_affiliation_dict'] = authorAffiliationDict
		# # PAPER LINK Parser
		# paper_soup = soup.find_all("a", {"class": "link-item"})
		# for paper in paper_soup:
		# 	print(paper['href'])
		# 	break
	return searchesHash


def semantic_scholar_query(PMID):
	"""
	Queries the Semantic Scholar API for the given PMID and returns the
	citation count and the weighted citation count

	Args:
		PMID (str): A PubMed ID

	Returns:
		citation_count (int): The number of citations for the given PMID
		ss_citation_count (int): The weighted number of citations for the given PMID
	"""
	fields = ['title',
						'journal',
						'year',
						'fieldsOfStudy',
						'referenceCount',
						'citationCount',
						'influentialCitationCount',
						'influentialCitationCount',
						'authors.name,authors.hIndex']
	fields_str = ','.join(fields)
	semantic_scholar_base = 'https://api.semanticscholar.org/graph/v1/paper/PMID:<>?fields=' + fields_str
	semantic_scholar_url = semantic_scholar_base.replace('<>', PMID)
	r = urllib.request.urlopen(semantic_scholar_url).read().decode('utf-8')
	ss_dict = json.loads(r)
	citation_count = ss_dict['citationCount']
	ss_weighted_citation_count = ss_dict['influentialCitationCount']
	return citation_count, ss_weighted_citation_count

def semantic_scholar_search(searchesHash, verbose=False):
	"""
	semantic_scholar_search searches the Semantic Scholar API for the given
	PMID and returns the citation count and the weighted citation count

	Args:
		searchesHash (dict): A dictionary of PubMed IDs (PMIDs) and their
			associated search terms
		verbose (bool): If True, print all the search terms and the results of
			the Semantic Scholar API query

	Returns:
		searchesHash (dict): The input dictionary with the citation count and
			the weighted citation count added to each PMID
	"""
	for q_index, query in enumerate(searchesHash):
		print('Query: {}'.format(query))
		for r_index, PMID in enumerate(searchesHash[query]):
			try:
				citation_count, ss_citation_count = semantic_scholar_query(PMID)
			# maximum requests hit for Semantic Scholar (100 per 5 minutes)			
			except:
				citation_count = np.nan
				ss_citation_count = np.nan
			searchesHash[query][PMID]['citation_count'] = citation_count
			searchesHash[query][PMID]['semantic_scholar_citation_count'] = ss_citation_count
			if (q_index < 5 and r_index < 5) or verbose == True:
				print_str = 'Title: {} ({})'.format(
									searchesHash[query][PMID]['article_title'],
									searchesHash[query][PMID]['publication_date'])
				print(indent(pformat(print_str), 
										prefix='  '))
				print(indent(pformat('PMID: {}'.format(PMID)),
										prefix='\t'))
				print(indent(pformat('Citation Count: {}'.format(citation_count)),
										prefix='\t'))
				print(indent(pformat('Semantic Scholar Citation Count: {}'.format(ss_citation_count)),
										prefix='\t'))
			# pause for a second to avoid overloading the server
			time.sleep(1)
	return searchesHash


def construct_dataframe(searchesHash: dict) -> pd.DataFrame:
	"""
	construct_dataframe creates a pandas dataframe
	containing all article data for each search term

	Args:
		searchesHash (dict): multi-nested dictionary containing all article data for each search term

	Returns:
		df (pandas dataframe): pandas dataframe containing all article data for each search term
	"""
	print('\nConstructing dataframe...')
	df = pd.DataFrame()
	for query in searchesHash.keys():
		for PMID in searchesHash[query].keys():
			for author in searchesHash[query][PMID]['authors']:
				authorHash = {}
				authorHash['author'] = author
				authorHash['PMID'] = PMID
				authorHash_added = dict(authorHash, **searchesHash[query][PMID])
				collaborators = searchesHash[query][PMID]['authors'][:]
				# Unncessary columns to remove
				remove_columns = ['authors', 'journal_title_abv', 'publisher']
				authorHash_added.pop('authors')
				authorHash_added.pop('journal_title_abv')
				collaborators.remove(author)
				authorHash_added['collaborators'] = collaborators
				# append authorHash_added to df
				df = pd.concat([df, pd.DataFrame([authorHash_added])], ignore_index=True)
	return df