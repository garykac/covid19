from __future__ import division

import os
import shutil

from usinfo import USInfo

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
		for s in USInfo.states:
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
		for state in USInfo.states:
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
				# date,state,positive,negative,pending,hospitalized,death,total,dateChecked,totalTestResults,fips,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
				# 21Mar2020: New field: ospitalized
				# 25Mar2020: New fields: totalTestResults,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
				# 27Mar2020: New field: fips
				(date,state,positive,negative,pending,hospitalized,death,total,timestamp,ttr,fips,di,hi,ni,pi,ttri) = line.strip().split(',')
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
					for s in USInfo.states:
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
		for s in USInfo.states:
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
		for s in USInfo.states:
			data = options.state_data[s]
			if len(data) > 0:
				last = data[-1]
				if last == None:
					print 'ERROR ranking', options.type, s, data
				ranking_data[s] = last
				pop = USInfo.state_pop[s]
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

