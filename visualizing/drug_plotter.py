import numpy as np
import datetime
import pandas as pd
import matplotlib.pyplot as plt
# plot number of drugs approved each month each year
def plot_nce_monthly(df_all):
	# convert approval_date to datetime
	approval_dates = pd.to_datetime(df_all['approval_date'])
	df_all['year_month'] = approval_dates.dt.to_period('M')
	df_all['year_month'] = df_all['year_month'].dt.to_timestamp()
	df_all['year_month'] = df_all['year_month'].dt.strftime('%Y-%m')
	df_all['year_month'] = pd.to_datetime(df_all['year_month'])
	df_all['year_month'] = df_all['year_month'].dt.strftime('%Y-%m')
	df_all['year_month'] = pd.to_datetime(df_all['year_month'])
	df_all['year'] = df_all['year_month'].dt.year
	df_all['count'] = 1
	df_all_grouped = df_all.groupby(['year_month', 'year']).count().reset_index()
	df_all_grouped = df_all_grouped[['year_month', 'count']]
	# plot
	f, ax = plt.subplots(1, 1, figsize=(12, 4))
	ax.plot(df_all_grouped['year_month'], df_all_grouped['count'], marker='o')
	# show each month-year on x-axis
	ax.set_xlabel('Year')
	ax.set_ylabel('Number of Drugs Approved')
	ax.set_title('Number of Drugs Approved Each Month Each Year')
	ax.set_ylim(0, 10)
	# y-axis shows 0-5-10
	ax.set_yticks(range(0, 11, 5))
	# plot average line
	ax.axhline(df_all_grouped['count'].mean(), color='grey', linestyle='--', label='Average')
	# show text above the average line at the end of the line with the greek letter mu = mean
	ax.text(df_all_grouped['year_month'].iloc[-1], df_all_grouped['count'].mean()+0.5, 
				 	f'$\mu = {round(df_all_grouped["count"].mean())}$', va='center', fontsize=10)
	plt.show()

def group_by_year(df_all):
	df_all['approval_date'] = pd.to_datetime(df_all['approval_date'])
	df_all['year'] = df_all['approval_date'].dt.year
	df_all['month'] = df_all['approval_date'].dt.month
	df_all_grouped = df_all.groupby(['year']).count().reset_index()
	df_all_grouped = df_all_grouped[['year', 'drug_name']]
	df_all_grouped.columns = ['year', 'count']
	return df_all_grouped

def plot_yearly(df_all_grouped):
	f, ax = plt.subplots(1, 1, figsize=(12, 4))
	# for the current year, show the projected number of drugs approved
	current_year = datetime.datetime.now().year
	current_month = datetime.datetime.now().month
	# get the number of drugs approved in the current year
	current_year_drugs = df_all_grouped[df_all_grouped['year'] == current_year]['count'].values[0]
	# get the number of months left in the year
	months_left = 12 - current_month
	current_year_more_drugs = int((current_year_drugs / current_month) * months_left)
	current_year_drugs_projected = current_year_drugs + current_year_more_drugs
	# show the projected number of drugs approved in the current year in dotted line behind the already-plotted bar
	# make the bar transparent but the edge black
	ax.bar(current_year, current_year_drugs_projected, ec='black', color='skyblue', alpha=0.5, hatch='//')
	# plot the number of drugs approved each year
	ax.bar(df_all_grouped['year'], df_all_grouped['count'], ec='black', color='skyblue')
	# show each year on x-axis
	ax.set_xlabel('Year')
	ax.set_ylabel('Number of Drugs Approved')
	ax.set_title('Number of Drugs Approved Each Year')
	# show all years
	ax.set_xticks(df_all_grouped['year'])
	# set y-limit as rounded max value + 10
	ylim = (df_all_grouped['count'].max() // 10 + 1) * 10
	ax.set_ylim(0, ylim)
	# y-axis shows every 10
	ax.set_yticks(range(0, ylim+1, 10))
	# dotted line for average across all years
	ax.axhline(df_all_grouped['count'].mean(), color='grey', linestyle='--', label='Average')
	# adjust the last year's count to include the projected number of drugs approved in the current year
	count_per_year = [count for count in df_all_grouped['count'] if count > 0]
	count_per_year_adj = count_per_year[:-1] + [count_per_year[-1] + current_year_more_drugs]
	count_mean = round(np.mean(count_per_year_adj))
	# show text above the average line at the end of the line with the greek letter mu = mean
	ax.text(df_all_grouped['year'].iloc[-1]+1.25, count_mean, 
				 	f'$\mu = {count_mean}$', va='center')
	# show each bar value
	for i, count in enumerate(df_all_grouped['count']):
		ax.text(df_all_grouped['year'].iloc[i], count+2, count, ha='center',
					 va='center', fontsize=8)
	plt.show()

# plot the number of drugs in each drug class for the top 20 drug classes
def plot_drug_classes(df, class_type='EPC', color='darkblue', unique_drugs=False):
	unique_str = ''
	df_dc = df.copy()
	if unique_drugs:
		# count only unique drug names
		df_dc = df_dc.drop_duplicates(subset=['drug_name'])
		unique_str = 'Unique '
	# count only drug classes that have [class_type] in the name
	df_dc['drug_class'] = df_dc['drug_class'].str.upper()
	# remove NaN/None values
	df_dc = df_dc.dropna(subset=['drug_class'])
	df_dc = df_dc[df_dc['class_type'].str.contains(class_type)]
	# get the top N drug classes
	top_drug_classes = df_dc['drug_class'].value_counts().nlargest(50)
	f, ax = plt.subplots(1, 1, figsize=(20, 4))
	ax.bar(top_drug_classes.index, top_drug_classes.values, color=color, edgecolor='black')
	# rotate x-axis labels
	plt.xticks(rotation=90, fontsize=10)
	# show each drug class on x-axis
	ax.set_xlabel('Drug Class', fontsize=16, fontweight='bold')
	ax.set_ylabel(f'Number of {unique_str}Drugs', fontsize=16, fontweight='bold')
	ax.set_title(f'Top DailyMed Drug Classes ({class_type})', fontsize=20, fontweight='bold')
	# print the number of unique drug classes
	print(f'Number of unique drug classes: {len(df["drug_class"].unique())}')
	print(f'Number of unique drugs: {len(df["drug_name"].unique())}')
	print(f'Number of total drugs: {len(df["drug_name"])}')
	plt.show()

def plot_packagers(dailymed_df, unique_drugs=False):
	if unique_drugs:
		# count only unique drug names
		dailymed_df = dailymed_df.drop_duplicates(subset=['drug_name'])
	top_packagers = dailymed_df['packager'].value_counts().nlargest(50)
	f, ax = plt.subplots(1, 1, figsize=(20, 4))
	ax.bar(top_packagers.index, top_packagers.values, color='skyblue', edgecolor='black')
	# rotate x-axis labels
	plt.xticks(rotation=90, fontsize=10)
	# show each packager on x-axis
	ax.set_xlabel('Packager', fontsize=16, fontweight='bold')
	ax.set_ylabel('Number of Drugs', fontsize=16, fontweight='bold')
	ax.set_title('Top DailyMed Packagers', fontsize=20, fontweight='bold')
	plt.show()
	# print the number of unique packagers
	print(f'Number of unique packagers: {len(dailymed_df["packager"].unique())}')
	print(f'Number of unique drugs: {len(dailymed_df["drug_name"].unique())}')