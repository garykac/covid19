from __future__ import division

import copy
import datetime
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

from usinfo import USInfo
from covid_data import CovidData

_italy_pop = 60549600  # 2020 from https://en.wikipedia.org/wiki/Demographics_of_Italy

# Number of states to include in plot
_top_n = 8

# Dummy object for passing option attributes.
class Options(object):
	pass

# Graph parameters for Reported Tests
class C19Tests:
	num_days = 75
	threshold = 150
	y_min = threshold
	y_max = 9000000
	title = 'COVID-19 US reported tests'
	subtitle = 'Since first day with %d tests' % threshold
	output_dir = 'tests'
	output_filebase = 'tests'
	x_label = 'Days since %dth reported test' % threshold
	y_label = 'Cumulative reported tests'

	label = 'Reported Tests (pos+neg)'
	units = ''

class C19TestsNorm:
	num_days = 75
	threshold = 10
	y_min = threshold
	y_max = 80000
	title = 'COVID-19 US States Reported Tests (Pos + Neg) per Million'
	subtitle = 'Since first day with %d tests/million' % threshold
	output_dir = 'tests-norm'
	output_filebase = 'tests'
	x_label = 'Days since %d reported tests per million people' % threshold
	y_label = 'Cumulative reported tests per million people'

	label = 'Reported Tests (per capita, pos+neg)'
	units = 'per million'

	combined_num_days = num_days - 5
	combined_y_max = y_max
	y_ticks_lin = [0, 5000, 10000]
	y_ticks_log = [10,100,1000,10000]
	combined_footer = ['Each US state Pos + Neg tests compared with all other states',
			'Data is cumulative but some reported data is inconsistent',
			'Note: y=10000 is 1% of the state\'s population']

	individual_title = 'COVID-19 %s Reported Tests (Pos + Neg) per Million'

# Graph parameters for Reported Positive Cases
class C19Cases:
	num_days = 80
	threshold = 100
	y_min = threshold
	y_max = 1400000
	title = 'COVID-19 US reported positive cases'
	subtitle = 'Since first day with %d cases' % threshold
	output_dir = 'cases'
	output_filebase = 'cases'
	x_label = 'Days since %dth reported positive case' % threshold
	y_label = 'Cumulative reported positive cases'

	label = 'Reported Positive Cases'
	units = ''
	
class C19CasesNorm:
	num_days = 75
	threshold = 10
	y_min = threshold
	y_max = 20000
	title = 'COVID-19 US States Reported Positive Cases per Million'
	subtitle = 'Since first day with %d positive cases/million' % threshold
	output_dir = 'cases-norm'
	output_filebase = 'cases'
	x_label = 'Days since %d reported positive cases per million people' % threshold
	y_label = 'Cumulative reported positive cases per million people'

	label = 'Reported Positive Cases (per capita)'
	units = 'per million'

	combined_num_days = num_days - 10
	combined_y_max = y_max
	y_ticks_lin = []
	y_ticks_log = []
	combined_footer = []
	
	individual_title = 'COVID-19 %s Reported Positive Cases per Million'

# Graph parameters for Reported Deaths
class C19Deaths:
	num_days = 75
	threshold = 10
	y_min = threshold
	y_max = 80000
	title = 'COVID-19 US reported deaths'
	subtitle = 'Since first day with %d deaths' % threshold
	output_dir = 'deaths'
	output_filebase = 'deaths'
	x_label = 'Days since %dth reported death' % threshold
	y_label = 'Cumulative reported deaths'

	label = 'Reported Deaths'
	units = ''

class C19DeathsNorm:
	num_days = 70
	threshold = 1
	y_min = threshold
	y_max = 1200
	title = 'COVID-19 US States Reported Deaths per Million'
	subtitle = 'Since first day with %d death/million' % threshold
	output_dir = 'deaths-norm'
	output_filebase = 'deaths'
	x_label = 'Days since %d reported death per million people' % threshold
	y_label = 'Cumulative reported deaths per million people'

	label = 'Reported Deaths (per capita)'
	units = 'per million'

	combined_num_days = num_days
	combined_y_max = y_max
	y_ticks_lin = []
	y_ticks_log = []
	combined_footer = []
	
	individual_title = 'COVID-19 %s Reported Deaths per Million'

	
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

class CovidCases:
	def __init__(self, covid_data):
		self.cdata = covid_data
		date = covid_data.get_date()
		if not date:
			print('ERROR - Missing date')
			sys.exit(2)
		self.set_date(date)
		
		# The |plot_date| is the latest date that we're plotting data for. This can differ
		# from the |date| because we plot previous days based on the top-n states
		# on the |plot_date|.
		self.plot_date = self.date
		self.plot_date_str = self.calc_date_str(self.plot_date)
		
		self.info = {}
		self.info[C19Cases.output_dir] = C19Cases
		self.info[C19CasesNorm.output_dir] = C19CasesNorm
		self.info[C19Deaths.output_dir] = C19Deaths
		self.info[C19DeathsNorm.output_dir] = C19DeathsNorm
		self.info[C19Tests.output_dir] = C19Tests
		self.info[C19TestsNorm.output_dir] = C19TestsNorm
		
	def remove_last_day(self):
		self.cdata.remove_last_day()
		self.set_date(self.cdata.get_date())

	def set_date(self, date):
		self.date = date
		self.date_str = self.calc_date_str(self.date)

	# Return date as a datetime.date.
	def get_date_as_datetime(self):
		return datetime.date(int(self.date[0:4]), int(self.date[4:6]), int(self.date[6:8]))
		
	def calc_date_str(self, date):
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

		day = date[6:8]
		if day[0] == '0':
			day = day[1:]
		return day + ' ' + month_str[date[4:6]] + ' ' + date[0:4]

	def normalize_pop(self, val, pop):
		return (val * 1000000) / pop
	
	# Normalize data based on population, filter by threshold.
	def process_normalize_and_filter(self, data, threshold, pop, filter=True):
		new_data = []
		for c in data:
			if c:
				n = self.normalize_pop(c, pop)
				if (not filter) or n >= threshold:
					new_data.append(n)
		return new_data

	# Filter data by threshold.
	def process_filter(self, data, threshold, pop, filter=True):
		new_data = []
		for c in data:
			if c and ((not filter) or c >= threshold):
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

	def new_tests_options(self):
		options = Options()
		options.state_data = self.cdata.get_state_tests_pn
		options.state_data2 = self.cdata.get_state_tests_pnp
		options.us_data = self.cdata.get_us_tests_pnp
		options.italy_data = self.cdata.get_italy_tests
		return options
	
	def new_cases_options(self):
		options = Options()
		options.state_data = self.cdata.get_state_cases
		options.state_data2 = None
		options.us_data = self.cdata.get_us_cases
		options.italy_data = self.cdata.get_italy_cases
		return options

	def new_deaths_options(self):
		options = Options()
		options.state_data = self.cdata.get_state_deaths
		options.state_data2 = None
		options.us_data = self.cdata.get_us_deaths
		options.italy_data = self.cdata.get_italy_deaths
		return options

	# Generate main graphs for |plot_date|.
	def calc_top_n(self):
		self.top_n_plots = []
		self.ranking = {}
		self.ranking_data = {}

		self.calc_top_n_tests()
		self.calc_top_n_cases()
		self.calc_top_n_deaths()
	
	def calc_top_n_tests(self):
		options = self.new_tests_options()		
		options.info_direct = C19Tests
		options.ranking_direct = self.cdata.get_test_rank()
		options.info_norm = C19TestsNorm
		options.ranking_norm = self.cdata.get_test_rank_norm()

		self.calc_top_n_data(options)
		
	def calc_top_n_cases(self):
		options = self.new_cases_options()
		options.info_direct = C19Cases
		options.ranking_direct = self.cdata.get_case_rank()
		options.info_norm = C19CasesNorm
		options.ranking_norm = self.cdata.get_case_rank_norm()
		
		self.calc_top_n_data(options)

	def calc_top_n_deaths(self):
		options = self.new_deaths_options()
		options.info_direct = C19Deaths
		options.ranking_direct = self.cdata.get_death_rank()
		options.info_norm = C19DeathsNorm
		options.ranking_norm = self.cdata.get_death_rank_norm()
		
		self.calc_top_n_data(options)

	# Generate a linear and a log top-n graph.
	def calc_top_n_data(self, options):
		options.info = options.info_direct
		options.processor = self.process_filter
		options.ranking = options.ranking_direct
		self.calc_top_n_data_scale(options, True)
		self.calc_top_n_data_scale(options, False)

		options.info = options.info_norm
		options.processor = self.process_normalize_and_filter
		options.ranking = options.ranking_norm
		self.calc_top_n_data_scale(options, True)
		self.calc_top_n_data_scale(options, False)

	# Generate top-n graph.
	def calc_top_n_data_scale(self, options, use_log_scale):
		scale = 'Linear'
		if use_log_scale:
			scale = 'Log'
		options.use_log_scale = use_log_scale
		options.output_dir = options.info.output_dir
		options.output_filebase = options.info.output_filebase
		options.y_min = options.info.y_min
		options.y_max = options.info.y_max
		options.max_days = options.info.num_days
		options.title = '%s\n(%s. Top %d states. %s scale)' % (options.info.title, options.info.subtitle, _top_n, scale)
		options.x_label = options.info.x_label
		options.y_label = options.info.y_label
		
		self.record_top_n_plots(options)
		self.record_ranking(options)
	
	# Keep track of which plots to perform	
	def record_top_n_plots(self, options):
		self.top_n_plots.append(copy.copy(options))	

	def record_ranking(self, options):
		ranking = {}  # Ranking for most recent date.
		ranking_data = {}  # full data needed to calcuate ranking.
		rank = 1
		for state in options.ranking:
			raw_data = options.state_data(state)
			data = options.processor(raw_data, options.info.threshold, USInfo.state_pop[state], False)
			if len(data) > 0:
				val = data[-1]
				delta = val
				if len(data) > 1:
					delta = data[-1] - data[-2]
			else:
				val = 0
				delta = 0
			ranking[state] = [rank, val, delta]
			ranking_data[state] = data
			rank += 1
		
		self.ranking[options.output_dir] = ranking
		self.ranking_data[options.output_dir] = ranking_data

	def generate_top_n_plots(self):
		print('Generating top-n graphs for', self.date_str, end='')
		self.last_print = 'xxx'
		for options in self.top_n_plots:
			self.generate_plot(options)
		print()
	
	def generate_plot(self, options):
		if not os.path.exists(options.output_dir):
			os.makedirs(options.output_dir)

		new_plot_type = True
		if options.output_dir.startswith(self.last_print):
			if options.output_dir.endswith('-norm'):
				new_plot_type = False
				if options.use_log_scale:
					print('(norm) ', end='')
				print(options.use_log_scale, '', end='')
			elif options.output_dir == self.last_print:
				new_plot_type = False
				print(options.use_log_scale, '', end='')
		if new_plot_type:
			print()
			print('  ', options.output_dir, options.use_log_scale, '', end='')
			self.last_print = options.output_dir
		sys.stdout.flush()

		plt.close('all')
		self.fig, ax = plt.subplots()
		ax.axis([0, options.max_days, options.y_min, options.y_max])
		self.format_axes(ax, options.use_log_scale)
		ax.grid(True)
		ax.set_xlabel(options.x_label)
		ax.set_ylabel(options.y_label)
		plt.title(options.title)
		self.add_footer(plt, False)

		# Plot the top |_top_n| states.
		for i in range(_top_n):
			state = options.ranking[i];
			self.plot_data(ax, options.state_data(state), color_order[i],
					USInfo.state_pop[state], state, False,
					options.processor, options.info.threshold)

		self.plot_data(ax, options.italy_data(), 'black', _italy_pop, 'Italy', True,
				options.processor, options.info.threshold)
		self.plot_data(ax, options.us_data(), 'black', USInfo.us_pop, 'US', True,
				options.processor, options.info.threshold)

		outdir = '%s/%s' % (options.output_dir, self.plot_date)
		if not os.path.exists(outdir):
			os.makedirs(outdir)

		suffix = 'lin'
		if options.use_log_scale:
			suffix = 'log'
			plt.legend(loc="lower right")
		else:
			plt.legend(loc="upper left")
		
		filename = '%s/%s-%s-%s.png' % (outdir, options.output_filebase, suffix, self.date)
		plt.savefig(filename, bbox_inches='tight')

	def add_footer(self, plt, has_pending):
		# Left side
		y = -40
		if has_pending:
			plt.annotate('Solid line for completed (pos+neg). Dotted line for pending tests.',
					xy=(0,0), xycoords='axes fraction',
					xytext=(-40, y), textcoords='offset points',
					size=8, ha='left', va='top')
			y -= 10
		plt.annotate('US data from https://covidtracking.com',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, y), textcoords='offset points',
				size=8, ha='left', va='top')
		y -= 10
		plt.annotate('Italy data from https://github.com/pcm-dpc/COVID-19',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-40, y), textcoords='offset points',
				size=8, ha='left', va='top')
		
		# Right side
		y += 10
		plt.annotate(self.date_str,
				xy=(1,0), xycoords='axes fraction',
				xytext=(0, y), textcoords='offset points',
				size=14, ha='right', va='top')

	def generate_states_combined(self):
		print('Generating combined state graphs')
		self.generate_states_combined_tests()
		self.generate_states_combined_cases()
		self.generate_states_combined_deaths()
	
	def generate_states_combined_tests(self):
		print('  combined state tests')
		options = self.new_tests_options()
		options.info = C19TestsNorm
		options.ranking = self.cdata.get_test_rank_norm()
		options.processor = self.process_normalize_and_filter

		self.generate_states_combined_data(options, True)
		self.generate_states_combined_data(options, False)
	
	def generate_states_combined_cases(self):
		print('  combined state cases')
		options = self.new_cases_options()
		options.info = C19CasesNorm
		options.ranking = self.cdata.get_case_rank_norm()
		options.processor = self.process_normalize_and_filter

		self.generate_states_combined_data(options, True)
		self.generate_states_combined_data(options, False)

	def generate_states_combined_deaths(self):
		print('  combined state deaths')
		options = self.new_deaths_options()
		options.info = C19DeathsNorm
		options.ranking = self.cdata.get_death_rank_norm()
		options.processor = self.process_normalize_and_filter

		self.generate_states_combined_data(options, True)
		self.generate_states_combined_data(options, False)

	def generate_states_combined_data(self, options, use_log_scale):
		plt.close('all')
		fig, axs = plt.subplots(14, 4, sharex=True, sharey=True)

		scale = 'Linear'
		if use_log_scale:
			scale = 'Log'

		footer = options.info.combined_footer[:]
		footer.append('Data from https://covidtracking.com')
		self.add_combined_title(axs[0,1], 
				options.info.title,
				'%s. %s scale' % (options.info.subtitle, scale))
		self.add_combined_footer(axs[13,0], footer,
				axs[13,3], self.date_str)

		# Build a dictionary of state -> ax
		state_ax = {}
		s = 0
		for ax in axs.flat:
			state = USInfo.states[s]
			state_ax[state] = ax
			s += 1

		for s in USInfo.states:
			ax = state_ax[s]
			ax.axis([0, options.info.combined_num_days, options.info.y_min, options.info.combined_y_max])
			self.format_axes(ax, use_log_scale)
			ticks = options.info.y_ticks_lin
			if use_log_scale:
				ticks = options.info.y_ticks_log
			if ticks and len(ticks) > 0:
				ax.set_yticks(ticks)
			
			# Plot data for all the states in light gray for reference.
			for s2 in USInfo.states:
				self.plot_data(ax, options.state_data(s2), 'lt_gray',
						USInfo.state_pop[s2], '', False, options.processor, options.info.threshold)	
			self.plot_data(ax, options.state_data(s), 'dk_gray',
					USInfo.state_pop[s], s, True, options.processor, options.info.threshold)

		fig.set_size_inches(8, 18)
		suffix = 'lin'
		if use_log_scale:
			suffix = 'log'
		plt.savefig('%s/states-%s.png' % (options.info.output_dir, suffix),
				dpi=150, bbox_inches='tight')
	
	def add_combined_title(self, ax, title, sub):
		ax.annotate(title,
				xy=(1,1), xycoords='axes fraction',
				xytext=(0, 44), textcoords='offset points',
				size=16, ha='center', va='top')
		ax.annotate(sub,
				xy=(1,1), xycoords='axes fraction',
				xytext=(0, 22), textcoords='offset points',
				size=10, ha='center', va='top')
	
	def add_combined_footer(self, axl, left, axr, right):
		x = -20
		y = -28
		dy = -12
		for str in left:
			y += dy
			axl.annotate(str,
					xy=(0,0), xycoords='axes fraction',
					xytext=(x, y), textcoords='offset points',
					size=8, ha='left', va='bottom')
		axr.annotate(right,
				xy=(1,0), xycoords='axes fraction',
				xytext=(0, y), textcoords='offset points',
				size=14, ha='right', va='bottom')

	def generate_states_individual(self):
		print('Generating individual state graphs')
		self.generate_states_individual_tests()
		self.generate_states_individual_cases()
		self.generate_states_individual_deaths()
	
	def generate_states_individual_tests(self):
		print('  individual state tests')
		options = self.new_tests_options()
		self.generate_states_individual_data(C19TestsNorm, options)
	
	def generate_states_individual_cases(self):
		print('  individual state cases')
		options = self.new_cases_options()
		self.generate_states_individual_data(C19CasesNorm, options)
		
	def generate_states_individual_deaths(self):
		print('  individual state deaths')
		options = self.new_deaths_options()
		self.generate_states_individual_data(C19DeathsNorm, options)
		
	def generate_states_individual_data(self, info, options):
		options.output_filebase = info.output_filebase
		options.processor = self.process_normalize_and_filter

		for state in USInfo.states:
			self.generate_state(state, info, options, True)
			self.generate_state(state, info, options, False)
	
	def generate_state(self, state, info, options, use_log_scale):
		plt.close('all')
		self.fig, ax = plt.subplots()
		ax.axis([0, info.num_days, info.y_min, info.y_max])
		self.format_axes(ax, use_log_scale)
		ax.grid(True)
		ax.set_xlabel(info.x_label)
		ax.set_ylabel(info.y_label)

		has_pending_data = False
		if options.state_data2:
			has_pending_data = True

		scale = 'Linear'
		if use_log_scale:
			scale = 'Log'
		title1 = info.individual_title % state
		title = '%s\n(%s. %s scale)' % (title1, info.subtitle, scale)
		plt.title(title)
		self.add_footer(plt, has_pending_data)
	
		# Plot data for all the states in light gray for reference.
		for s2 in USInfo.states:
			self.plot_data(ax, options.state_data(s2), 'lt_gray',
					USInfo.state_pop[s2], '', False, options.processor, info.threshold)

		days_plotted = self.plot_data(ax, options.state_data(state), 'dk_blue',
				USInfo.state_pop[state], state, True, options.processor, info.threshold)
		if has_pending_data:
			self.plot_data(ax, options.state_data2(state), 'dk_blue2',
					USInfo.state_pop[state], '', False, options.processor, info.threshold,
					days_plotted)
		self.plot_data(ax, options.us_data(), 'black', USInfo.us_pop, 'US', True,
				options.processor, info.threshold)
		self.plot_data(ax, options.italy_data(), 'black', _italy_pop, 'Italy', True,
				options.processor, info.threshold)

		output_dir = 'state/%s' % state
		if not os.path.exists(output_dir):
			os.makedirs(output_dir)

		suffix = 'lin'
		if use_log_scale:
			suffix = 'log'
			plt.legend(loc="lower right")
		else:
			plt.legend(loc="upper left")

		# Note: Use |info.output_dir| as filename since we don't create subdir for states.
		filename = '%s/%s-%s.png' % (output_dir, info.output_dir, suffix)
		plt.savefig(filename, bbox_inches='tight')

	def plot_data(self, ax, raw_data, color, pop, label, always_label, processor, threshold, max_days=None):
		# Default to thick, solid line.
		linewidth = 2
		linestyle = '-'
		# Thin US/Italy reference lines in black.
		if color == 'black':
			linewidth = 1
			linestyle = ':'  # Dotted
			if label == 'US':
				linestyle = '--'  # Dashed
		# On combined graphs, the other states are in lt_gray
		if color == 'lt_gray':
			linewidth = 1
		# Secondary data lines (like tests+pending) are dotted.
		if color[-1] == '2':
			color = color[0:-1]
			linestyle = ':'  # Dotted

		# Clamp to max days so that data2 (eg: pending tests) aligns properly with data.
		if max_days:
			raw_data = raw_data[-max_days:]
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

		# Return the number of days plotted.
		return len(processed_data)

	def calc_state_ranks(self):
		self.rank_states = {}
		self.rank_states_inv = {}
		self.days_with_ranking_data = {}
		self.num_states_for_ranking = 56
		self.num_days_for_ranking = 31

		ranking_data = copy.deepcopy(self.ranking_data)
		for type in ['cases-norm', 'deaths-norm', 'tests-norm']:
			data = ranking_data[type]
			rank_states = {}
			rank_states_inv = {}
			days_with_data = {}
			for s in USInfo.states:
				rank_states[s] = []
				rank_states_inv[s] = []
				days_with_data[s] = 0

			for day in range(0, self.num_days_for_ranking):
				# Get latest data for each state.
				curr = {}
				for s in USInfo.states:
					if len(data[s]) != 0:
						curr[s] = data[s][-1]
						data[s].pop()
						days_with_data[s] += 1
					else:
						curr[s] = 0

				rank = []
				for d in sorted(curr, key=curr.get, reverse=True):
					rank.append(d)

				for i in range(0, len(rank)):
					s = rank[i]
					rank_states_inv[s].append(self.num_states_for_ranking - i)
					rank_states[s].append(i + 1)

			self.rank_states[type] = rank_states
			self.rank_states_inv[type] = rank_states_inv
			self.days_with_ranking_data[type] = days_with_data
	
	def calc_ranking_plot(self):
		print('Generating state ranking graphs')
		print('  ', end='')
		self.calc_ranking_plot_type('tests-norm', self.cdata.get_state_tests_pn)
		self.calc_ranking_plot_type('cases-norm', self.cdata.get_state_cases)
		self.calc_ranking_plot_type('deaths-norm', self.cdata.get_state_deaths)
		print()
			
	def calc_ranking_plot_type(self, type, raw_data):
		print(type, end='')
		sys.stdout.flush()
		for s in USInfo.states:
			self.calc_ranking_plot_type_state(type, s, raw_data)
		self.calc_ranking_plot_type_state(type, 'all', raw_data)

	def calc_ranking_plot_type_state(self, type, state, raw_data):
		info = self.info[type]
		
		rank_states = self.rank_states_inv[type]
		days_with_data = self.days_with_ranking_data[type]
		
		num_states = self.num_states_for_ranking
		num_days = self.num_days_for_ranking
		
		plt.close('all')
		fig, ax = plt.subplots()
		ax.axis([0, num_days, 0, num_states+1])
		title = 'US State Ranking of COVID-19 %s\nChanges over Time' % (info.label)
		if state != 'all':
			title +=  ' (%s)' % USInfo.state_name[state]
		ax.set_title(title)
		#ax.set_xlabel('x label')
		ax.set_ylabel('Ranking of %s' % info.label)
		ax.set_xticks([])
		ax.set_yticks([])

		plt.annotate('US data from https://covidtracking.com',
				xy=(0,0), xycoords='axes fraction',
				xytext=(-20, -40), textcoords='offset points',
				size=8, ha='left', va='top')
		
		# Add labels on right side next to most recent ranking data.
		for s in USInfo.states:
			rank = rank_states[s][0]
			text_bg = ax.text(num_days - 0.4, rank - 0.25, s, size=8)
			val = self.normalize_pop(raw_data(s)[-1], USInfo.state_pop[s])
			text_bg = ax.text(num_days + 0.9, rank - 0.25, '{:.2f}'.format(val), size=8, ha='right')
		text_bg = ax.text(num_days + 0.5, 0, '{:s}\nper\nmillion'.format(info.output_filebase), size=8, ha='center', va='top')

		# Labels for the y-axis.
		for y in [1,5,10,15,20,25,30,35,40,45,50,55]:
			text_bg = ax.text(0.45, num_states - (y-1) - 0.25, '#%d' % y, size=8, ha='right')

		# Labels for the x-axis.
		x_labels = []
		cdate = self.get_date_as_datetime()
		delta = datetime.timedelta(days=1)
		for n in reversed(range(1, num_days+1)):
			x_labels.append([n, '{:d} {:s} {:d}'.format(cdate.day, cdate.strftime('%b'), cdate.year)])
			cdate -= delta
		for d in x_labels:
			day = d[0]
			label = d[1]
			x = day - 0.5
			if (day - num_days) % 2 == 0:
				text_bg = ax.text(x, -1, label, size=8, ha='center')
			ax.plot(x, 0, 'bo')

		# Plot the data for each state.		
		x = list([x+0.5 for x in reversed(range(0, num_days))])
		for s in USInfo.states:
			linewidth = 1
			if s == state:
				linewidth = 4
			ax.plot(x[:days_with_data[s]], rank_states[s][:days_with_data[s]], linewidth = linewidth)

		if state == 'all':
			filename = 'state-ranking-%s.png' % type
		else:
			filename = 'state/%s/state-ranking-%s.png' % (state, type)
		fig.set_size_inches(24, 10)
		plt.savefig(filename, dpi=90, bbox_inches='tight')
		
	def export_anim(self):
		print('Exporting animations')
		cmd = 'convert'
		args_base = ['-delay', '7' ,'-loop', '0']

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
			print('  ', t)
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
		
	def create_test_page_html(self):
		print('Generating test page html files')

		with open('test-page-template.txt') as fpin:
			with open('test-page.html', 'w') as fpout:
				for line in fpin:
					if '%%' in line:
						line = line.replace('%%DATE%%', self.plot_date_str)
						line = line.replace('%%YYYYMMDD%%', self.plot_date)
					fpout.write(line)

	def create_state_html(self):
		print('Generating state html files')

		with open('index-template.txt') as fpin:
			with open('index.html', 'w') as fpout:
				for line in fpin:
					fpout.write(line.replace('%%DATE%%', self.plot_date_str))

		for s in USInfo.states:
			ranking = self.calc_ranking_for_state_html(s)
			maps = ''
			if s in USInfo.STATES_WITH_MAPS:
				maps = self.calc_state_maps_html(s)
			with open('state-index-template.txt') as fpin:
				with open('state/%s/index.html' % s, 'w') as fpout:
					for line in fpin:
						if '%%' in line:
							line = line.replace('%%DATE%%', self.plot_date_str)
							line = line.replace('%%STATE%%', USInfo.state_name[s])
							line = line.replace('%%RANKING%%', ranking)
							line = line.replace('%%MAPS%%', maps)
						fpout.write(line)

	def calc_state_maps_html(self, state):
		width = '550px'
		if state in USInfo.TALL_STATES:
			width = '300px'

		map = ''
		map += '<div class="graphcontainer">\n'
		map += '<div class="graphbox">\n'
		map += '	<div class="map"><a href="map-cases.svg"><img src="map-cases.svg" width="%s"/></a></div>\n' % width
		map += '</div>\n'
		map += '<div class="graphbox">\n'
		map += '	<div class="map"><a href="map-deaths.svg"><img src="map-deaths.svg" width="%s"/></a></div>\n' % width
		map += '</div>\n'
		map += '</div><!-- graphcontainer -->\n'
		return map
				
	def calc_ranking_for_state_html(self, state):
		ranking = ''
		ranking += '<h2>%s Ranking</h2>\n' % USInfo.state_name[state]
		ranking += '<div class="h2subheading">Ranking out of 56 US states and territories</div>\n'
		ranking += '<table class="ranking-table">\n'
		ranking += '<thead><tr>\n'
		ranking += '\t<th>Metric</th>\n'
		ranking += '\t<th>Rank</th>\n'
		ranking += '\t<th>Rank<br/>Change&#x2020;</th>\n'
		ranking += '\t<th>Value</th>\n'
		ranking += '\t<th>Value<br/>Change&#x2020;</th>\n'
		ranking += '</tr></thead>\n'
		ranking += '<tbody>\n'

		for type in sorted(self.ranking.keys()):
			info = self.info[type]
			ranking += '<tr>\n'
			url = '../../state-ranking-{:s}.html'.format(type)
			ranking += '<td><a href="{:s}">{:s}</a></td>\n'.format(url, info.label)

			rank = self.ranking[type][state]
			ranking_ord = rank[0]
			val = rank[1]
			delta = rank[2]
			ranking += '<td>#{:d}</td>\n'.format(ranking_ord)
			
			if type in ['cases-norm', 'deaths-norm', 'tests-norm']:
				rank_states = self.rank_states[type]
				print(state, type, rank_states)
				curr_rank = ranking_ord
				prev_rank = rank_states[state][1]
				if curr_rank == prev_rank:
					ranking += '<td>-</td>\n'
				elif curr_rank > prev_rank:
					# Down in ranking
					ranking += '<td>&#x2b07;%d</td>\n' % (curr_rank - prev_rank)
				else:
					# Up in ranking
					ranking += '<td>&#x2b06;%d</td>\n' % (prev_rank - curr_rank)
			else:
				ranking += '<td></td>\n'
				
			if info.units == '':
				ranking += '<td>{:d}</td>\n'.format(val)
				ranking += '<td>+{:d}</td>\n'.format(delta)
			else:
				ranking += '<td>{:.2f} {:s}</td>\n'.format(val, info.units)
				ranking += '<td>+{:.2f}</td>\n'.format(delta)

			ranking += '</tr>\n'
			
		tests_pn = self.cdata.get_state_tests_pn(state)[-1]
		tests_pnp = self.cdata.get_state_tests_pnp(state)[-1]
		if tests_pn != tests_pnp:
			print(state, tests_pn, tests_pnp)
			ranking += '<tr>\n'
			ranking += '<td>Pending tests</td>\n'
			ranking += '<td></td>\n'
			ranking += '<td></td>\n'
			ranking += '<td>%d</td>\n' % (tests_pnp - tests_pn)
			ranking += '</tr>\n'				

		ranking += '</tbody>\n'
		ranking += '</table>\n'

		ranking += '<div class="table-note">&#x2020; Change since previous day\'s value.</p>\n'

		return ranking


def usage():
	print('plot.py [options]')
	print('where options are:')
	print('  --all Generate all plots')
	print('  --anim Generate animated plots for top-N (implies --top)')
	print('  --combined Generate combined state plots')
	print('  --date <yyyymmdd> Only plot data up to date')
	print('  --individual Generate individual state plots')
	print('  --ranking Generate state ranking plots')
	print('  --top Generate state top-N plots')
	sys.exit(1)

def main(argv):
	try:
		opts, args = getopt.getopt(argv,
				"?hancid:rt",
				["?", "help", "all", "anim", "combined", "individual", "date=", "ranking", "top"])
	except getopt.GetoptError:
		usage()

	date = None
	gen_animated = False
	gen_combined = False
	gen_individual = False
	gen_top_n = False
	gen_ranking = False
	gen_html = True
	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			usage()
		if opt in ("-a", "--all"):
			gen_animated = True
			gen_combined = True
			gen_individual = True
			gen_top_n = True
			gen_ranking = True
		if opt in ("-n", "--anim"):
			gen_animated = True
			gen_top_n = True  # --anim requires --top_n
		if opt in ("-c", "--combined"):
			gen_combined = True
		if opt in ("-d", "--date"):
			date = arg
		if opt in ("-i", "--individual"):
			gen_individual = True
		if opt in ("-r", "--ranking"):
			gen_ranking = True
		if opt in ("-t", "--top"):
			gen_top_n = True

	covid_data = CovidData(date)
	covid_data.load_data()
	
	cases = CovidCases(covid_data)
	print('Processing data for', cases.date_str)

	# Calc plot data and ranking
	cases.calc_top_n()
	
	if gen_top_n:
		cases.generate_top_n_plots()

	if gen_combined:
		cases.generate_states_combined()

	if gen_individual:
		cases.generate_states_individual();

	cases.calc_state_ranks()
	
	# This relies only on the saved |ranking_data|.
	if gen_ranking:
		cases.calc_ranking_plot()

	if gen_html:
		cases.create_test_page_html()
		cases.create_state_html()
	
	# Note: Generating animated graphs modified the data in |covid_data|.
	if gen_top_n and gen_animated:
		# Process previous day data using top-N from current day.
		while int(covid_data.get_date()) > int('20200316'):
			cases.remove_last_day()
			cases.generate_top_n_plots()
		cases.export_anim()

if __name__ == "__main__":
	main(sys.argv[1:])
