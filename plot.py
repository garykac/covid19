from __future__ import division

import getopt
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import operator
import os
import shutil
import subprocess
import sys
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import LogFormatter

# Number of states to include in plot
top_n = 8

# Graph parameters for Reported Tests
_num_days_for_tests = 35
_num_days_for_tests_norm = 30

_y_min_for_tests = 100
_y_max_for_tests = 1000000
_y_min_for_tests_norm = 10
_y_max_for_tests_norm = 10000

# Graph parameters for Reported Positive Cases
_num_days_for_cases = 35
_num_days_for_cases_norm = 30

_y_min_for_cases = 100
_y_max_for_cases = 200000
_y_min_for_cases_norm = 10
_y_max_for_cases_norm = 2000

# Graph parameters for Reported Deaths
_num_days_for_deaths = 30
_num_days_for_deaths_norm = 25

_y_min_for_deaths = 10
_y_max_for_deaths = 10000
_y_min_for_deaths_norm = 1
_y_max_for_deaths_norm = 150

# List of state/territory abbreviations.
states = [
	'AK', 'AL', 'AR', 'AS', 'AZ',
	'CA', 'CO', 'CT',
	'DC', 'DE',
	'FL',
	'GA', 'GU',
	'HI',
	'IA', 'ID', 'IL', 'IN',
	'KS', 'KY',
	'LA',
	'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MP', 'MS', 'MT',
	'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY',
	'OH', 'OK', 'OR',
	'PA', 'PR',
	'RI',
	'SC', 'SD',
	'TN', 'TX',
	'UT',
	'VA', 'VI', 'VT',
	'WA', 'WI', 'WV', 'WY',
]

# US state/territory population - Est. 1 July 2019
# From https://en.wikipedia.org/wiki/List_of_states_and_territories_of_the_United_States_by_population
state_pop = {
	'AK':   731545,
	'AL':  4903185,
	'AR':  3017825,
	'AZ':  7278717,
	'CA': 39512223,
	'CO':  5758736,
	'CT':  3565287,
	'DE':   973764,
	'FL': 21477737,
	'GA': 10617423,
	'HI':  1415872,
	'IA':  3155070,
	'ID':  1787147,
	'IL': 12671821,
	'IN':  6732219,
	'KS':  2913314,
	'KY':  4467673,
	'LA':  4648794,
	'MA':  6949503,
	'MD':  6045680,
	'ME':  1344212,
	'MI':  9986857,
	'MN':  5639632,
	'MO':  6137428,
	'MS':  2976149,
	'MT':  1068778,
	'NC': 10488084,
	'ND':   762062,
	'NE':  1934408,
	'NH':  1359711,
	'NJ':  8882190,
	'NM':  2096829,
	'NV':  3080156,
	'NY': 19453561,
	'OH': 11689100,
	'OK':  3956971,
	'OR':  4217737,
	'PA': 12801989,
	'RI':  1059361,
	'SC':  5148714,
	'SD':   884659,
	'TN':  6833174,
	'TX': 28995881,
	'UT':  3205958,
	'VA':  8535519,
	'VT':   623989,
	'WA':  7614893,
	'WI':  5822434,
	'WV':  1792065,
	'WY':   578759,

	'AS':    55641,
	'DC':   705749,
	'GU':   165718,
	'MP':    55194,
	'PR':  3193694,
	'VI':   104914,
}

us_pop = 331875705  # Total US population summed from state data.
italy_pop = 60549600  # 2020 from https://en.wikipedia.org/wiki/Demographics_of_Italy

# The order in which colors are assigned to plot lines.
color_order = [
	'red',
	'orange',
	'brown',
	'gray',
	'olive',
	'green',
	'blue',
	'purple',
]

line_colors = {
	'black': '#000000',
	'blue': '#396ab1',
	'brown': '#922428',
	'dk_blue': '#0050ff',
	'dk_gray': '#101010',
	'gray': '#535154',
	'green': '#3e9651',
	'lt_gray': '#d0d0d0',
	'orange': '#da7c30',
	'olive': '#948b3d',
	'purple': '#6b4c9a',
	'red': '#cc2529',
}

# Notes on data
# Changes in 20200319 dataset:
# Other notes:
#  NV positives goes from 1 on 9Mar -> 0 on 10Mar -> 5 on 11Mar
class CovidData:
	def __init__(self, date):
		self.date = date
		self.state_tests = {}
		self.state_cases = {}
		self.state_deaths = {}

	def get_us_tests(self):
		return self.us_tests
	
	def get_us_cases(self):
		return self.us_cases
	
	def get_us_deaths(self):
		return self.us_deaths

	def get_state_tests(self, state):
		return self.state_tests[state]
		
	def get_state_cases(self, state):
		return self.state_cases[state]
	
	def get_state_deaths(self, state):
		return self.state_deaths[state]
	
	def get_italy_tests(self):
		return self.italy_tests

	def get_italy_cases(self):
		return self.italy_cases

	def get_italy_deaths(self):
		return self.italy_deaths

	def get_test_rank(self):
		return self.ranking_test

	def get_test_rank_norm(self):
		return self.ranking_test_norm
	
	def get_case_rank(self):
		return self.ranking_case

	def get_case_rank_norm(self):
		return self.ranking_case_norm
	
	def get_death_rank(self):
		return self.ranking_death

	def get_death_rank_norm(self):
		return self.ranking_death_norm
	
	def get_date(self):
		return self.date
	
	def remove_last_day(self):
		self.dates.pop()
		self.date = self.dates[-1]
		
		self.us_tests.pop()
		self.us_cases.pop()
		self.us_deaths.pop()
		self.italy_tests.pop()
		self.italy_cases.pop()
		self.italy_deaths.pop()
		for s in states:
			self.state_tests[s].pop()
			self.state_cases[s].pop()
			self.state_deaths[s].pop()
	
	def load_data(self):
		self.load_us_data()
		self.load_italy_data()
	
	def load_us_data(self):
		self.state_tests = {}
		self.state_cases = {}
		self.state_deaths = {}
		for state in states:
			self.state_tests[state] = []
			self.state_cases[state] = []
			self.state_deaths[state] = []
		self.us_tests = []
		self.us_cases = []
		self.us_deaths = []

		curr_date = None
		self.dates = []
		state_has_data = {}
		us_tests = 0
		us_cases = 0
		us_deaths = 0
		with open('data/states-daily.csv') as fp:
			for line in fp:
				# date,state,positive,negative,pending,hospitalized,death,total,dateChecked,totalTestResults,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
				# 21Mar2020: New field: ospitalized
				# 25Mar2020: New fields: totalTestResults,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
				(date,state,positive,negative,pending,hospitalized,death,total,timestamp,ttr,di,hi,ni,pi,ttri) = line.strip().split(',')
				if date == 'date':
					continue

				# Ignore all data before the specified date.
				if self.date != None and int(date) > int(self.date):
					continue

				if curr_date == None:
					curr_date = date
					self.dates.insert(0, date)
				if self.date == None:
					# Assumes that most recent date is first in file.
					self.date = date

				# If new date, then make sure we close out the current date,
				# filling out missing state data with '0's.
				if curr_date != date:
					for s in states:
						if not state_has_data.has_key(s):
							self.state_tests[s].insert(0, None)
							self.state_cases[s].insert(0, None)
							self.state_deaths[s].insert(0, None)
					# Record total US infos for current date.
					self.us_tests.insert(0, us_tests)
					self.us_cases.insert(0, us_cases)
					self.us_deaths.insert(0, us_deaths)
					us_tests = 0
					us_cases = 0
					us_deaths = 0
					state_has_data = {}
					curr_date = date
					self.dates.insert(0, date)

				num_tests = int(total)
				self.state_tests[state].insert(0, num_tests)
				us_tests += num_tests
				
				if positive == '':
					pos = 0
				else:
					pos = int(positive)
				self.state_cases[state].insert(0, pos)
				us_cases += pos

				if death == '':
					d = 0
				else:
					d = int(death)
				self.state_deaths[state].insert(0, d)
				us_deaths += d

				# Keep track of which states have data for this date.
				state_has_data[state] = True
		
		# Fill in missing data for final date.
		for s in states:
			if not state_has_data.has_key(s):
				self.state_tests[s].insert(0, None)
				self.state_cases[s].insert(0, None)
				self.state_deaths[s].insert(0, None)
		self.us_tests.insert(0, us_tests)
		self.us_cases.insert(0, us_cases)
		self.us_deaths.insert(0, us_deaths)

		self.rank_states()
	
	def rank_states(self):
		self.rank_states_tests()
		self.rank_states_cases()
		self.rank_states_deaths()

	def rank_states_tests(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_tests
		options.type = 'tests'

		self.ranking_test, self.ranking_test_norm = self.rank_states_data(options)
	
	def rank_states_cases(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_cases
		options.type = 'cases'

		self.ranking_case, self.ranking_case_norm = self.rank_states_data(options)
	
	def rank_states_deaths(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_deaths
		options.type = 'deaths'

		self.ranking_death, self.ranking_death_norm = self.rank_states_data(options)
	
	def rank_states_data(self, options):
		ranking_data = {}
		ranking_norm_data = {}
		for s in states:
			data = options.state_data[s]
			if len(data) > 0:
				last = data[-1]
				if last == None:
					print 'ERROR ranking', options.type, s, data
				ranking_data[s] = last
				pop = state_pop[s]
				ranking_norm_data[s] = (last * 1000000) / pop

		out_ranking = []
		for d in sorted(ranking_data, key=ranking_data.get, reverse=True):
			out_ranking.append(d)

		out_ranking_norm = []
		for d in sorted(ranking_norm_data, key=ranking_norm_data.get, reverse=True):
			out_ranking_norm.append(d)
		
		self.rank_states_data_export(ranking_data, out_ranking, options.type, 'int')
		self.rank_states_data_export(ranking_norm_data, out_ranking_norm, '%s-norm' % options.type, 'float')

		return out_ranking, out_ranking_norm
	
	def rank_states_data_export(self, data, ranking, type, format):
		outdir_date = '%s/%s' % (type, self.date)
		if not os.path.exists(outdir_date):
			os.makedirs(outdir_date)

		file_csv = '%s/%s-data.csv' % (type, type)
		# Export ranking.
		with open(file_csv, 'w') as fp:
			fp.write('state,%s\n' % type)
			for state in ranking:
				if format == 'float':
					fp.write('{:s},{:.2f}\n'.format(state, data[state]))
				else:
					fp.write('{:s},{:d}\n'.format(state, data[state]))
		shutil.copy(file_csv, '%s/%s-data.csv' % (outdir_date, type))
		shutil.copy(file_csv, '%s/%s-data.txt' % (type, type))

	def load_italy_data(self):
		self.italy_tests = []
		self.italy_cases = []
		self.italy_deaths = []

		# Hypothetical data back to roughly 100 total cases (for alignment).
		self.italy_tests.append(0)
		self.italy_tests.append(0)
		self.italy_cases.append(120)
		self.italy_cases.append(180)
		self.italy_deaths.append(0)
		self.italy_deaths.append(0)

		with open('data/dpc-covid19-ita-andamento-nazionale.csv') as fp:
			for line in fp:
				# data,stato,ricoverati_con_sintomi,terapia_intensiva,totale_ospedalizzati,isolamento_domiciliare,totale_attualmente_positivi,nuovi_attualmente_positivi,dimessi_guariti,deceduti,totale_casi,tamponi,note_it,note_en
				# data = date and time: yyyy-mm-dd hh:mm:ss
				# stato = state (always ITA)
				# ricoverati_con_sintomi = hospitalized with symptoms
				# terapia_intensiva = intensive care
				# totale_ospedalizzati = total hospitalized
				# isolamento_domiciliare = home isolation
				# totale_attualmente_positivi = total currently positive
				# nuovi_attualmente_positivi = new currently positive
				# dimessi_guariti = discharged healed
				# deceduti = deceased
				# totale_casi = total cases
				# tamponi = swabs
				# note_it = note italian
				# note_en = note english
				(datetime,state,hos,ic,hos_total,home,curr_pos,new_pos,discharged,deaths,total,swabs,nita,neng) = line.strip().split(',')
				if datetime == 'data':
					continue
				
				date = datetime[0:4] + datetime[5:7] + datetime[8:10]
				self.italy_tests.append(int(swabs))
				self.italy_cases.append(int(total))
				self.italy_deaths.append(int(deaths))
	
		# Verify most recent dates match between US/Italy
		if not date == self.date:
			print 'ERROR - US and Italy data not consistent:', date, 'vs', self.date
			exit(1)

class CovidCases:
	def __init__(self, covid_data):
		self.cdata = covid_data
		date = covid_data.get_date()
		if not date:
			print 'ERROR - Missing date'
			sys.exit(2)
		self.set_date(date)
		
		# The |plot_date| is the latest date that we're plotting data for. This can differ
		# from the |date| because we plot previous days based on the top-n states
		# on the |plot_date|.
		self.plot_date = self.date
		
	def remove_last_day(self):
		self.cdata.remove_last_day()
		self.set_date(self.cdata.get_date())

	def set_date(self, date):
		self.date = date

		month_str = {
			'01': 'Jan',
			'02': 'Feb',
			'03': 'Mar',
			'04': 'Apr',
			'05': 'May',
			'06': 'Jun',
			'07': 'Jul',
			'08': 'Aug',
			'09': 'Sep',
			'10': 'Oct',
			'11': 'Nov',
			'12': 'Dec',
		}

		self.date_str = date[6:8] + ' ' + month_str[date[4:6]] + ' ' + date[0:4]

	# Normalize data based on population, filter by threshold.
	def process_normalize_and_filter(self, data, threshold, pop):
		new_data = []
		for c in data:
			if c:
				n = c * 1000000 / pop
				if n >= threshold:
					new_data.append(n)
		return new_data

	# Filter data by threshold.
	def process_filter(self, data, threshold, pop):
		new_data = []
		for c in data:
			if c and c >= threshold:
				new_data.append(c)
		return new_data

	def format_axes(self, ax, log):
		if log:
			ax.set_yscale('log')
		for axis in [ax.xaxis, ax.yaxis]:
			formatter = FuncFormatter(lambda y, _: '{:.16g}'.format(y))
			axis.set_major_formatter(formatter)
		#formatter = LogFormatter(labelOnlyBase=False, minor_thresholds=(2, 0.4))
		#ax.yaxis.set_minor_formatter(formatter)

	# Generate main graphs for |plot_date|.
	def generate_top_n(self):
		print 'Processing data for', self.date_str
		self.generate_top_n_tests()
		self.generate_top_n_cases()
		self.generate_top_n_deaths()
	
	def generate_combined(self):
		print 'Generating combined state graphs'
		self.generate_states_combined()

		self.generate_states_individual()

	# Generate graphs for a previous date (used for animations).
	def generate_anim_data(self):
		print 'Processing data for', self.date_str
		self.generate_top_n_tests()
		self.generate_top_n_cases()
		self.generate_top_n_deaths()

	def generate_top_n_tests(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_tests
		options.us_data = self.cdata.get_us_tests
		options.italy_data = self.cdata.get_italy_tests
		
		# Filtered for 100 cases, log-scale
		title = 'COVID-19 US reported tests\n(Since first day with 100 tests. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'tests'
		options.output_filebase = 'tests'
		options.y_min = _y_min_for_tests
		options.y_max = _y_max_for_tests
		options.max_days = _num_days_for_tests
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 100th reported test'
		options.y_label = 'Cumulative reported tests'
		options.processor = self.process_filter
		options.threshold = 100
		options.ranking = self.cdata.get_test_rank()
		self.generate_plot(options)
		# Filtered for 100 tests, linear-scale
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 10 cases/million, log
		title = 'COVID-19 US reported tests per million\n(Since first day with 10 tests/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'tests-norm'
		options.output_filebase = 'tests'
		options.y_min = _y_min_for_tests_norm
		options.y_max = _y_max_for_tests_norm
		options.max_days = _num_days_for_tests_norm
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 10 reported tests per million people'
		options.y_label = 'Cumulative reported tests per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		options.ranking = self.cdata.get_test_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

	def generate_top_n_cases(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_cases
		options.us_data = self.cdata.get_us_cases
		options.italy_data = self.cdata.get_italy_cases
		
		# Filtered for 100 cases, log-scale
		title = 'COVID-19 US reported positive cases\n(Since first day with 100 cases. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'cases'
		options.output_filebase = 'cases'
		options.y_min = _y_min_for_cases
		options.y_max = _y_max_for_cases
		options.max_days = _num_days_for_cases
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 100th reported positive case'
		options.y_label = 'Cumulative reported positive cases'
		options.processor = self.process_filter
		options.threshold = 100
		options.ranking = self.cdata.get_case_rank()
		self.generate_plot(options)
		# Filtered for 100 cases, linear-scale
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 10 cases/million, log
		title = 'COVID-19 US reported positive cases per million\n(Since first day with 10 cases/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'cases-norm'
		options.output_filebase = 'cases'
		options.y_min = _y_min_for_cases_norm
		options.y_max = _y_max_for_cases_norm
		options.max_days = _num_days_for_cases_norm
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 10 reported positive cases per million people'
		options.y_label = 'Cumulative reported positive cases per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		options.ranking = self.cdata.get_case_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

	def generate_top_n_deaths(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_deaths
		options.us_data = self.cdata.get_us_deaths
		options.italy_data = self.cdata.get_italy_deaths
		
		# Filtered for 100 cases, log-scale
		title = 'COVID-19 US reported deaths\n(Since first day with 10 deaths. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'deaths'
		options.output_filebase = 'deaths'
		options.y_min = _y_min_for_deaths
		options.y_max = _y_max_for_deaths
		options.max_days = _num_days_for_deaths
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 10th reported death'
		options.y_label = 'Cumulative reported deaths'
		options.processor = self.process_filter
		options.threshold = 10
		options.ranking = self.cdata.get_death_rank()
		self.generate_plot(options)
		# Filtered for 100 cases, linear-scale
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 1 cases/million, log
		title = 'COVID-19 US reported death per million\n(Since first day with 1 death/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'deaths-norm'
		options.output_filebase = 'deaths'
		options.y_min = _y_min_for_deaths_norm
		options.y_max = _y_max_for_deaths_norm
		options.max_days = _num_days_for_deaths_norm
		options.title = title % (top_n, 'Log')
		options.x_label = 'Days since 1 reported death per million people'
		options.y_label = 'Cumulative reported deaths per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 1
		options.ranking = self.cdata.get_death_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (top_n, 'Linear')
		self.generate_plot(options)

	def generate_plot(self, options):
		if not os.path.exists(options.output_dir):
			os.makedirs(options.output_dir)

		plt.close('all')
		self.fig, ax = plt.subplots()
		ax.axis([0, options.max_days, options.y_min, options.y_max])
		self.format_axes(ax, options.use_log_scale)
		ax.grid(True)
		ax.set_xlabel(options.x_label)
		ax.set_ylabel(options.y_label)
		plt.title(options.title)

		plt.annotate('US data from https://covidtracking.com',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, -40), textcoords='offset points',
				size=8, ha='left', va='top')
		plt.annotate('Italy data from https://github.com/pcm-dpc/COVID-19',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, -50), textcoords='offset points',
				size=8, ha='left', va='top')
		plt.annotate(self.date_str,
				xy=(1,0), xycoords='axes fraction',
				xytext=(0, -40), textcoords='offset points',
				size=14, ha='right', va='top')

		# Plot the top |top_n| states.
		for i in xrange(top_n):
			state = options.ranking[i];
			self.plot_data(ax, options.state_data(state), color_order[i],
					state_pop[state], state, False,
					options.processor, options.threshold)

		self.plot_data(ax, options.italy_data(), 'black', italy_pop, 'Italy', True,
				options.processor, options.threshold)
		self.plot_data(ax, options.us_data(), 'black', us_pop, 'US', True,
				options.processor, options.threshold)

		outdir = '%s/%s' % (options.output_dir, self.plot_date)
		if not os.path.exists(outdir):
			os.makedirs(outdir)

		logname = 'lin'
		if options.use_log_scale:
			logname = 'log'
			plt.legend(loc="lower right")
		else:
			plt.legend(loc="upper left")
		
		filename = '%s/%s-%s-%s.png' % (outdir, options.output_filebase, logname, self.date)
		plt.savefig(filename, bbox_inches='tight')

	def generate_states_combined(self):
		plt.close('all')
		fig, axs = plt.subplots(14, 4, sharex=True, sharey=True)

		#fig.suptitle('States')
		axs[0,1].annotate('COVID-19 US States Reported Positive Cases per Million',
				xy=(1,1), xycoords='axes fraction',
				xytext=(0, 44), textcoords='offset points',
				size=16, ha='center', va='top')
		axs[0,1].annotate('Since first day with 10 positive cases/million',
				xy=(1,1), xycoords='axes fraction',
				xytext=(0, 22), textcoords='offset points',
				size=10, ha='center', va='top')
		axs[13,0].annotate('Data from https://covidtracking.com',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-20, -40), textcoords='offset points',
				size=8, ha='left', va='bottom')
		axs[13,3].annotate(self.date_str,
				xy=(1,0), xycoords='axes fraction',
				xytext=(0, -40), textcoords='offset points',
				size=14, ha='right', va='bottom')

		# Build a dictionary of state -> ax
		state_ax = {}
		s = 0
		for ax in axs.flat:
			state = states[s]
			state_ax[state] = ax
			s += 1

		for s in states:
			ax = state_ax[s]
			#ax.set_title(s)
			ax.axis([0, _num_days_for_cases_norm, _y_min_for_cases_norm, _y_max_for_cases_norm])
			self.format_axes(ax, True)
			# Plot data for all the states in light gray for reference.
			for s2 in states:
				self.plot_data(ax, self.cdata.get_state_cases(s2), 'lt_gray',
						state_pop[s2], '', False, self.process_normalize_and_filter, 10)	
			self.plot_data(ax, self.cdata.get_state_cases(s), 'dk_gray',
					state_pop[s], s, True, self.process_normalize_and_filter, 10)

		fig.set_size_inches(8, 18)
		plt.savefig('cases-norm/states.png', dpi=150, bbox_inches='tight')

	def generate_states_individual(self):
		options = lambda: None  # An object that we can attach attributes to

		options.use_log_scale = True
		options.y_min = _y_min_for_cases_norm
		options.y_max = _y_max_for_cases_norm
		options.max_days = _num_days_for_cases_norm
		options.x_label = 'Days since 10 reported positive cases per million people'
		options.y_label = 'Cumulative reported positive cases per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		for state in states:
			options.output_dir = 'state/%s' % state
			options.title = 'COVID-19 %s reported positive cases per million\n(Since first day with 10 cases/million. Log scale)' % state
			self.generate_state(state, options)
	
	def generate_state(self, state, options):
		plt.close('all')
		self.fig, ax = plt.subplots()
		ax.axis([0, options.max_days, options.y_min, options.y_max])
		self.format_axes(ax, options.use_log_scale)
		ax.grid(True)
		ax.set_xlabel(options.x_label)
		ax.set_ylabel(options.y_label)
		plt.title(options.title)

		plt.annotate('US data from https://covidtracking.com',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, -40), textcoords='offset points',
				size=8, ha='left', va='top')
		plt.annotate('Italy data from https://github.com/pcm-dpc/COVID-19',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, -50), textcoords='offset points',
				size=8, ha='left', va='top')
		plt.annotate(self.date_str,
				xy=(1,0), xycoords='axes fraction',
				xytext=(0, -40), textcoords='offset points',
				size=14, ha='right', va='top')
	
		# Plot data for all the states in light gray for reference.
		for s2 in states:
			self.plot_data(ax, self.cdata.get_state_cases(s2), 'lt_gray',
					state_pop[s2], '', False, options.processor, options.threshold)

		self.plot_data(ax, self.cdata.get_state_cases(state), 'dk_blue',
				state_pop[state], state, True, options.processor, options.threshold)
		self.plot_data(ax, self.cdata.get_us_cases(), 'black', us_pop, 'US', True,
				options.processor, options.threshold)
		self.plot_data(ax, self.cdata.get_italy_cases(), 'black', italy_pop, 'Italy', True,
				options.processor, options.threshold)

		plt.legend(loc="lower right")

		if not os.path.exists(options.output_dir):
			os.makedirs(options.output_dir)

		filename_date = '%s/cases-norm.png' % options.output_dir
		plt.savefig(filename_date, bbox_inches='tight')

	def plot_data(self, ax, raw_data, color, pop, label, always_label, processor, threshold):
		# Default to thick, solid line.
		linewidth = 2
		linestyle = '-'
		# Thin US/Italy reference lines in black.
		if color == 'black':
			linewidth = 1
			linestyle = ':'  # Dotted
			if label == 'US':
				linestyle = '--'  # Dashed

		processed_data = processor(raw_data, threshold, pop)
		
		# Always plot the data (even if empty) so that it gets added to the Legend.
		# Otherwise the legend will jump when the images are stitched together for the
		# animation.
		ax.plot(processed_data, color=line_colors[color], linewidth = linewidth,
				linestyle = linestyle, label = label)
		if always_label or len(processed_data) > 0:
			# Label each line at its last data point.
			if len(processed_data) > 0:
				label_x = len(processed_data) - 1
				label_y = processed_data[-1]
			else:
				label_x = 0
				label_y = threshold
			text_bg = ax.text(label_x, label_y, label, size=12)
			text_bg.set_path_effects([
					PathEffects.Stroke(linewidth=3, foreground='white'),
					PathEffects.Normal()])
			text = ax.text(label_x, label_y, label, size=12, color=line_colors[color])
			text.set_path_effects([PathEffects.Normal()])

	def export_anim(self):
		print 'Exporting animations'
		cmd = 'convert'
		args_base = ['-delay', '20' ,'-loop', '0']

		templates = []
		for dir in ['tests', 'tests-norm']:
			for f in ['tests-log', 'tests-lin']:
				base_template = '%s%%s/%s' % (dir, f)
				templates.append(base_template)
		for dir in ['cases', 'cases-norm']:
			for f in ['cases-log', 'cases-lin']:
				base_template = '%s%%s/%s' % (dir, f)
				templates.append(base_template)
		for dir in ['deaths', 'deaths-norm']:
			for f in ['deaths-log', 'deaths-lin']:
				base_template = '%s%%s/%s' % (dir, f)
				templates.append(base_template)

		for t in templates:
			filebase = t % ''
			filebase_date = t % ('/' + self.plot_date)

			args = args_base[:]
			args.append('%s-2020*.png' % (filebase_date))
			# Hold the last frame for a longer time.
			args.extend(['-delay', '240'])
			last_frame = '%s-%s.png' % (filebase_date, self.plot_date)
			args.append(last_frame)
			# Output file.
			out_gif = '%s.gif' % (filebase_date)
			args.append(out_gif)
			subprocess.call([cmd] + args)

			# Make copies of the latest version in the top level dir.
			shutil.copy(out_gif, '%s.gif' % (filebase))
			shutil.copy(last_frame, '%s.png' % (filebase))
		
def usage():
	print 'plot.py [options]'
	print 'where options are:'
	print '  --all Generate all plots'
	print '  --anim Generate animated plots'
	print '  --combined Generate combined state plots'
	print '  --date <yyyymmdd> Only plot data up to date'
	sys.exit(1)

def main(argv):
	try:
		opts, args = getopt.getopt(argv,"?hancd:",["?", "help", "all", "anim", "combined", "date="])
	except getopt.GetoptError:
		usage()

	date = None
	animated = False
	combined = False
	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			usage()
		if opt in ("-a", "--all"):
			animated = True
			combined = True
		if opt in ("-n", "--anim"):
			animated = True
		if opt in ("-c", "--combined"):
			combined = True
		if opt in ("-d", "--date"):
			date = arg

	covid_data = CovidData(date)
	covid_data.load_data()
	
	cases = CovidCases(covid_data)
	cases.generate_top_n()
	
	if combined:
		cases.generate_combined()
	
	if animated:
		# Process previous day data using top-8 from current day.	
		while int(covid_data.get_date()) > int('20200316'):
			cases.remove_last_day()
			cases.generate_anim_data()
		cases.export_anim()

if __name__ == "__main__":
	main(sys.argv[1:])
