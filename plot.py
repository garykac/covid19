from __future__ import division

import getopt
import matplotlib.patheffects as PathEffects
import matplotlib.pyplot as plt
import operator
import subprocess
import sys
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import ScalarFormatter
from matplotlib.ticker import LogFormatter

# Number of states to include in plot
top_n = 8

# List of state/territory abbreviations.
states = [
	'AK', 'AL', 'AR', 'AZ',
	'CA', 'CO', 'CT',
	'DC', 'DE',
	'FL',
	'GA',
	'HI',
	'IA', 'ID', 'IL', 'IN',
	'KS', 'KY',
	'LA',
	'MA', 'MD', 'ME', 'MI', 'MN', 'MO', 'MS', 'MT',
	'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY',
	'OH', 'OK', 'OR',
	'PA',
	'RI',
	'SC', 'SD',
	'TN', 'TX',
	'UT',
	'VA', 'VT',
	'WA', 'WI', 'WV', 'WY',
	# Territories
	'AS', 'GU', 'MP', 'PR', 'VI',
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
	'gray': '#535154',
	'green': '#3e9651',
	'orange': '#da7c30',
	'olive': '#948b3d',
	'purple': '#6b4c9a',
	'red': '#cc2529',
}

# Notes on data
# Changes in 20200319 dataset:
#  AL 17Mar positives changed from 26 -> 36
#     Typo fix since otherwise cases drop from 28 on 16Mar
#  NV 18Mar positives changes from 65 -> 55
#     The 18Mar data is now the same as the 17Mar data
# Other notes:
#  NV positives goes from 1 on 9Mar -> 0 on 10Mar -> 5 on 11Mar
class CovidData:
	def __init__(self, date):
		self.date = date
		self.data = {}

	def get_us_cases(self):
		return self.us_cases
	
	def get_state_cases(self, state):
		return self.data[state]
	
	def get_italy_cases(self):
		return self.italy_cases

	def get_case_rank(self):
		return self.ranking_case

	def get_case_rank_norm(self):
		return self.ranking_case_norm
	
	def get_date(self):
		return self.date
	
	def remove_last_day(self):
		self.dates.pop()
		self.date = self.dates[-1]
		
		self.us_cases.pop()
		self.italy_cases.pop()
		for s in states:
			self.data[s].pop()
	
	def load_data(self):
		self.load_us_data()
		self.load_italy_data()
	
	def load_us_data(self):
		self.data = {}
		for state in states:
			self.data[state] = []
		self.us_cases = []

		curr_date = None
		self.dates = []
		state_has_data = {}
		us_cases = 0
		with open('data/states-daily.csv') as fp:
			for line in fp:
				(date,state,positive,negative,pending,death,total,timestamp) = line.strip().split(',')
				if date == 'date':
					continue

				# Ignore all data before the specified date.
				if self.date != None and int(date) > int(self.date):
					continue

				if curr_date == None:
					curr_date = date
					self.dates.insert(0, date)
				if self.date == None:
					self.date = date

				# If new date, then make sure we close out the current date,
				# filling out missing state data with '0's.
				if curr_date != date:
					for s in states:
						if not state_has_data.has_key(s):
							self.data[s].insert(0, None)
					self.us_cases.insert(0, us_cases)
					us_cases = 0
					state_has_data = {}
					curr_date = date
					self.dates.insert(0, date)

				self.data[state].insert(0, int(positive))
				us_cases += int(positive)

				# Keep track of which states have data for this date.
				state_has_data[state] = True

		# Fill in missing data for final date.
		for s in states:
			if not state_has_data.has_key(s):
				self.data[s].insert(0, None)
		self.us_cases.insert(0, us_cases)

		self.rank_states()
		
	# Calculate states ranking based on how impacted they are (highest # of cases
	# per million people).
	def rank_states(self):
		ranking_case = {}
		ranking_case_norm = {}
		for s in states:
			data = self.data[s]
			if len(data) > 0:
				last = data[-1]
				if last == None:
					print 'ERROR ranking', s, data
				ranking_case[s] = last
				pop = state_pop[s]
				ranking_case_norm[s] = last / pop

		self.ranking_case = []
		for d in sorted(ranking_case, key=ranking_case.get, reverse=True):
			self.ranking_case.append(d)
		self.ranking_case_norm = []
		for d in sorted(ranking_case_norm, key=ranking_case_norm.get, reverse=True):
			self.ranking_case_norm.append(d)

	def load_italy_data(self):
		# Italy cases
		# From 'totale_casi' in https://github.com/pcm-dpc/COVID-19/blob/master/dati-json/dpc-covid19-ita-andamento-nazionale.json
		self.italy_cases = [
			# Hypothetical data back to roughly 100 cases (for alignment).
			120, 180,
			# 24-29 Feb 2020
			229, 322, 400, 650, 888, 1128,
			# 1-13 Mar 2020
			1694, 2036, 2502, 3089, 3858, 4636, 5883, 7375, 9172, 10149, 12462, 15113, 17660
		]

		# Extra Italy data (from same source as above).
		italy_extra_data = [
			['20200314', 21157],
			['20200315', 24747],
			['20200316', 27980],
			['20200317', 31506],
			['20200318', 35713],
			['20200319', 41035],
			['20200320', 47021],
		]

		# Add extra Italy data depending on the date being processed.
		for d in italy_extra_data:
			if int(d[0]) <= int(self.date):
				self.italy_cases.append(d[1])

class CovidCases:
	def __init__(self, covid_data):
		self.cdata = covid_data
		date = covid_data.get_date()
		if not date:
			print 'ERROR - Missing date'
			sys.exit(2)
		self.set_date(date)
		self.most_recent_date = self.date
		
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

	# Normalize raw case count data based on population.
	def process_normalize_and_filter10(self, data, pop):
		new_data = []
		for c in data:
			if c:
				n = c * 1000000 / pop
				if n >= 10:
					new_data.append(n)
		return new_data

	# Normalize raw case count data based on population.
	def process_filter100(self, data, pop):
		new_data = []
		for c in data:
			if c and c >= 100:
				new_data.append(c)
		return new_data

	def generate(self):
		print 'Processing data for', self.date_str
		self.generate_top_n_cases()

	def generate_top_n_cases(self):
		# Filtered for 100 cases, log-scale
		options = lambda: None  # An object that we can attach attributes to
		options.use_log_scale = True
		options.output_dir = 'out-cases'
		options.y_min = 100
		options.y_max = 100000
		options.max_days = 30
		options.title = 'COVID-19 US reported positive cases\n(Since first day with 100 cases. Top %d states. Log scale)' % top_n
		options.x_label = 'Days since 100th reported positive cases'
		options.y_label = 'Cumulative reported positive cases'
		options.processor = self.process_filter100
		options.ranking = self.cdata.get_case_rank()
		self.generate_cases_plot(options)
		# Filtered for 100 cases, linear-scale
		options.use_log_scale = False
		options.title = 'COVID-19 US reported positive cases\n(Since first day with 100 cases. Top %d states. Linear scale)' % top_n
		self.generate_cases_plot(options)

		# Normalized for population, filtered for 10 cases/million, log
		options.use_log_scale = True
		options.output_dir = 'out-cases-norm'
		options.y_min = 10
		options.y_max = 1000
		options.max_days = 25
		options.title = 'COVID-19 US reported positive cases \n(Since first day with 10 cases/million. Top %d states. Log scale)' % top_n
		options.x_label = 'Days since 10 reported positive cases per million people'
		options.y_label = 'Cumulative reported positive cases per million people'
		options.processor = self.process_normalize_and_filter10
		options.ranking = self.cdata.get_case_rank_norm()
		self.generate_cases_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = 'COVID-19 US reported positive cases \n(Since first day with 10 cases/million. Top %d states. Linear scale)' % top_n
		self.generate_cases_plot(options)

	def generate_cases_plot(self, options):
		self.fig, self.ax = plt.subplots()
		self.ax.axis([0, options.max_days, options.y_min, options.y_max])
		if options.use_log_scale:
			self.ax.set_yscale('log')
		for axis in [self.ax.xaxis, self.ax.yaxis]:
			formatter = FuncFormatter(lambda y, _: '{:.16g}'.format(y))
			axis.set_major_formatter(formatter)
		formatter = LogFormatter(labelOnlyBase=False, minor_thresholds=(2, 0.4))
		self.ax.yaxis.set_minor_formatter(formatter)
		self.ax.grid(True)
		self.ax.set_xlabel(options.x_label)
		self.ax.set_ylabel(options.y_label)
		plt.title(options.title)

		plt.annotate('US data from https://covidtracking.com', (0,0), (-40, -40),
				size=8, xycoords='axes fraction', textcoords='offset points', va='top')
		plt.annotate('Italy data from https://github.com/pcm-dpc/COVID-19', (0,0), (-40, -50),
				size=8, xycoords='axes fraction', textcoords='offset points', va='top')
		plt.annotate(self.date_str, (0,0), (310, -50),
				size=8, xycoords='axes fraction', textcoords='offset points', va='top')
	
		# Plot the top |top_n| states.
		for i in xrange(top_n):
			state = options.ranking[i];
			self.plot_data(self.cdata.get_state_cases(state), color_order[i],
					state_pop[state], state, options.processor)

		self.plot_data(self.cdata.get_italy_cases(), 'black', italy_pop, 'Italy',
				options.processor)
		self.plot_data(self.cdata.get_us_cases(), 'black', us_pop, 'US',
				options.processor)

		plt.legend(loc="lower right")
		logname = 'lin'
		if options.use_log_scale:
			logname = 'log'
		filename = '%s/cases-%s-%s.png' % (options.output_dir, logname, self.date)
		plt.savefig(filename, bbox_inches='tight')

	def plot_data(self, raw_data, color, pop, label, processor):
		# Default to thick, solid line.
		linewidth = 2
		linestyle = '-'
		# Thin US/Italy reference lines in black.
		if color == 'black':
			linewidth = 1
			linestyle = ':'  # Dotted
			if label == 'US':
				linestyle = '--'  # Dashed

		processed_data = processor(raw_data, pop)
		
		# Always plot the data (even if empty) so that it gets added to the Legend.
		# Otherwise the legend will jump when the images are stitched together for the
		# animation.
		self.ax.plot(processed_data, color=line_colors[color], linewidth = linewidth,
				linestyle = linestyle, label = label)
		if len(processed_data) > 0:	
			# Label each line at its last data point.
			label_x = len(processed_data) - 1
			label_y = processed_data[-1]
			text_bg = self.ax.text(label_x, label_y, label, size=12)
			text_bg.set_path_effects([
					PathEffects.Stroke(linewidth=3, foreground='white'),
					PathEffects.Normal()])
			text = self.ax.text(label_x, label_y, label, size=12, color=line_colors[color])
			text.set_path_effects([PathEffects.Normal()])

	def export_anim_gif(self):
		print 'Exporting animations'
		cmd = 'convert'
		args_base = ['-delay', '30' ,'-loop', '0']
		
		for dir in ['out-cases', 'out-cases-norm']:
			for f in ['cases-log', 'cases-lin']:
				args = args_base[:]
				args.append('%s/%s-2020*.png' % (dir, f))
				# Add delay before last frame.
				args.extend(['-delay', '120'])
				args.append('%s/%s-%s.png' % (dir, f, self.most_recent_date))
				# Output file.
				args.append('%s/%s.gif' % (dir, f))
				subprocess.call([cmd] + args)
		
def main(argv):
	try:
		opts, args = getopt.getopt(argv,"?had:",["?", "help", "anim", "date="])
	except getopt.GetoptError:
		print 'test.py --date <yyyymmdd>'
		sys.exit(2)

	date = None
	animated = False
	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			print 'plot.py [options]'
			print 'where options are:'
			print '  -d <yyyymmdd> Only plot data up to date'
		if opt in ("-a", "--anim"):
			animated = True
		if opt in ("-d", "--date"):
			date = arg

	covid_data = CovidData(date)
	covid_data.load_data()
	
	cases = CovidCases(covid_data)
	cases.generate()

	if animated:
		# Process previous day data using top-8 from current day.	
		while int(covid_data.get_date()) > int('20200316'):
			cases.remove_last_day()
			cases.process()
		cases.export_anim_gif()

if __name__ == "__main__":
	main(sys.argv[1:])
