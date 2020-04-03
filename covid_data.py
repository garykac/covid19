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
		self.state_tests_pn = {}
		self.state_tests_pnp = {}
		self.state_cases = {}
		self.state_deaths = {}

	def get_us_tests_pn(self):
		return self.us_tests_pn
	
	def get_us_tests_pnp(self):
		return self.us_tests_pnp
	
	def get_us_cases(self):
		return self.us_cases
	
	def get_us_deaths(self):
		return self.us_deaths

	def get_state_tests_pn(self, state):
		return self.state_tests_pn[state]
		
	def get_state_tests_pnp(self, state):
		return self.state_tests_pnp[state]

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
		
		self.us_tests_pn.pop()
		self.us_tests_pnp.pop()
		self.us_cases.pop()
		self.us_deaths.pop()
		self.italy_tests.pop()
		self.italy_cases.pop()
		self.italy_deaths.pop()
		for s in USInfo.states:
			self.state_tests_pn[s].pop()
			self.state_tests_pnp[s].pop()
			self.state_cases[s].pop()
			self.state_deaths[s].pop()
	
	def load_data(self):
		self.load_us_data()
		self.load_italy_data()
	
	def load_us_data(self):
		self.state_tests_pn = {}  # pos + neg
		self.state_tests_pnp = {}  # pos + neg + pend
		self.state_cases = {}
		self.state_deaths = {}
		self.states_with_pending = {}
		for state in USInfo.states:
			self.state_tests_pn[state] = []
			self.state_tests_pnp[state] = []
			self.state_cases[state] = []
			self.state_deaths[state] = []
		self.us_tests_pn = []
		self.us_tests_pnp = []
		self.us_cases = []
		self.us_deaths = []
		
		curr_date = None
		self.dates = []
		state_has_data = {}
		us_tests_pn = 0
		us_tests_pnp = 0
		us_cases = 0
		us_deaths = 0
		
		fields = [
			'date',
			'state',
			'positive',
			'negative',
			'pending',
			'hospitalizedCurrently',
			'hospitalizedCumulative',
			'inIcuCurrently',
			'inIcuCumulative',
			'onVentilatorCurrently',
			'onVentilatorCumulative',
			'recovered',
			'hash',
			'dateChecked',
			'death',
			'hospitalized',
			'total',  # deprecated (= positive + negative + pending)
			          # Will be removed at some point because |pending| is not consistent between states.
			'totalTestResults',
			'posNeg',
			'fips',
			'deathIncrease',
			'hospitalizedIncrease',
			'negativeIncrease',
			'positiveIncrease',
			'totalTestResultsIncrease',
		]
		index = {}
		for i in xrange(0, len(fields)):
			index[fields[i]] = i
		with open('data/states-daily.csv') as fp:
			for line in fp:
				# 21Mar2020: New field: hospitalized
				# 25Mar2020: New fields: totalTestResults,deathIncrease,hospitalizedIncrease,negativeIncrease,positiveIncrease,totalTestResultsIncrease
				# 27Mar2020: New field: fips
				# 28Mar2020: New field: hash
				# 02Apr2020: 
				data = line.strip().split(',')
				if data[0] == 'date':
					# Verify that fields match expected values.
					for i in xrange(0, len(fields)):
						if data[i] != fields[i]:
							print 'ERROR - changed fields:', fields[i]
					continue
				date = data[index['date']]
				state = data[index['state']]
				positive = int(data[index['positive']]) if data[index['positive']] else 0
				negative = int(data[index['negative']]) if data[index['negative']] else 0
				pending = int(data[index['pending']]) if data[index['pending']] else 0
				death = int(data[index['death']]) if data[index['death']] else 0
				total_pn = positive + negative
				total_pnp = positive + negative + pending

				# Ignore all data for dates after the specified date.
				# Note that the most recent dates appear first in the file.
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
							self.state_tests_pn[s].insert(0, None)
							self.state_tests_pnp[s].insert(0, None)
							self.state_cases[s].insert(0, None)
							self.state_deaths[s].insert(0, None)
					# Record total US infos for current date.
					self.us_tests_pn.insert(0, us_tests_pn)
					self.us_tests_pnp.insert(0, us_tests_pnp)
					self.us_cases.insert(0, us_cases)
					self.us_deaths.insert(0, us_deaths)
					us_tests_pn = 0
					us_tests_pnp = 0
					us_cases = 0
					us_deaths = 0
					state_has_data = {}
					curr_date = date
					self.dates.insert(0, date)

				self.state_tests_pn[state].insert(0, total_pn)
				self.state_tests_pnp[state].insert(0, total_pnp)
				us_tests_pn += total_pn
				us_tests_pnp += total_pnp
				
				self.state_cases[state].insert(0, positive)
				us_cases += positive

				self.state_deaths[state].insert(0, death)
				us_deaths += death

				# Keep track of which states have data for this date.
				state_has_data[state] = True
		
		for s in self.states_with_pending:
			print 'Pending', s, self.states_with_pending[s]
			
		# Fill in missing data for final date.
		for s in USInfo.states:
			if not state_has_data.has_key(s):
				self.state_tests_pn[s].insert(0, None)
				self.state_tests_pnp[s].insert(0, None)
				self.state_cases[s].insert(0, None)
				self.state_deaths[s].insert(0, None)
		self.us_tests_pn.insert(0, us_tests_pn)
		self.us_tests_pnp.insert(0, us_tests_pnp)
		self.us_cases.insert(0, us_cases)
		self.us_deaths.insert(0, us_deaths)

		self.rank_states()
	
	def rank_states(self):
		self.rank_states_tests()
		self.rank_states_cases()
		self.rank_states_deaths()

	def rank_states_tests(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_tests_pn
		options.type = 'tests'
		options.label = 'Tests'

		self.ranking_test, self.ranking_test_norm = self.rank_states_data(options)
	
	def rank_states_cases(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_cases
		options.type = 'cases'
		options.label = 'Positive Cases'
		options.ranking_norm = 'Normalized for Population'

		self.ranking_case, self.ranking_case_norm = self.rank_states_data(options)
	
	def rank_states_deaths(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.state_deaths
		options.type = 'deaths'
		options.label = 'Deaths'
		options.ranking_norm = 'Normalized for Population'

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
		
		self.rank_states_data_export(ranking_data, out_ranking, options.type,
				'int', options.label, '', '')
		self.rank_states_data_export(ranking_norm_data, out_ranking_norm, '%s-norm' % options.type,
				'float', options.label, ', Normalized for Population', '  per million residents')

		return out_ranking, out_ranking_norm
	
	def rank_states_data_export(self, data, ranking, type, format, label, ranking_norm, units):
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

		d = self.date
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		date_str = d[6:8] + ' ' + months[int(d[4:6])-1] + ' ' + d[0:4]
		datafile = '%s/%s-data' % (type, type)
		
		extra_info = ''
		if type.startswith('tests'):
			extra_info = '<p align=center>Counting positive and negative tests only. Pending tests are not included.</p>\n'
		file_template = 'state-ranking-template.txt'
		file_html = 'state-ranking-%s.html' % type
		with open(file_template) as fpin:
			with open(file_html, 'w') as fpout:
				for line in fpin:
					if line.startswith('%%RANKING%%'):
						fpout.write('<table class="ranking-table">\n')
						fpout.write('<thead><tr>\n')
						fpout.write('\t<th>Rank</th>\n')
						fpout.write('\t<th>State</th>\n')
						fpout.write('\t<th>%s%s</th>\n' % (label, units))
						fpout.write('</tr></thead>\n')
						fpout.write('<tbody>\n')
						rank = 1
						for state in ranking:
							fpout.write('<tr>\n')
							fpout.write('\t<td>%d</td>\n' % rank)
							url = 'state/%s/index.html' % state
							fpout.write('\t<td><a href="%s">%s</a></td>\n' % (url, USInfo.state_name[state]))
							if format == 'float':
								fpout.write('\t<td>{:.2f}</td>\n'.format(data[state]))
							else:
								fpout.write('\t<td>{:d}</td>\n'.format(data[state]))
							fpout.write('</tr>\n')
							rank += 1
						fpout.write('</tbody>\n')
						fpout.write('</table>\n')
					else:
						line = line.replace('%%DATE%%', date_str)
						line = line.replace('%%TYPE%%', label)
						line = line.replace('%%RANKING_NORM%%', ranking_norm)
						line = line.replace('%%DATAFILE%%', datafile)
						line = line.replace('%%INFO%%', extra_info)
						fpout.write(line)


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
				# data,stato,ricoverati_con_sintomi,terapia_intensiva,totale_ospedalizzati,isolamento_domiciliare,totale_positivi,variazione_totale_positivi,nuovi_positivi,dimessi_guariti,deceduti,totale_casi,tamponi,note_it,note_en
				# data,stato,ricoverati_con_sintomi,terapia_intensiva,totale_ospedalizzati,isolamento_domiciliare,totale_positivi,variazione_totale_positivi,nuovi_positivi,dimessi_guariti,deceduti,totale_casi,tamponi,note_it,note_en
				# data = date and time: yyyy-mm-dd hh:mm:ss
				# stato = state (always ITA)
				# ricoverati_con_sintomi = hospitalized with symptoms
				# terapia_intensiva = intensive care
				# totale_ospedalizzati = total hospitalized
				# isolamento_domiciliare = home isolation
				# totale_positivi - total positive
				# variazione_totale_positivi - change total positive
				# nuovi_positivi - new positive
				# Previously:
					# totale_attualmente_positivi = total currently positive
					# nuovi_attualmente_positivi = new currently positive
				# dimessi_guariti = discharged healed
				# deceduti = deceased
				# totale_casi = total cases
				# tamponi = swabs
				# note_it = note italian
				# note_en = note english
				# 31 Mar 2020 - totale_attualmente_positivi,nuovi_attualmente_positivi split into totale_positivi,variazione_totale_positivi,nuovi_positivi
				(datetime,state,hos,ic,hos_total,home,total_pos,delta_pos,new_pos,discharged,deaths,total,swabs,nita,neng) = line.strip().split(',')
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

