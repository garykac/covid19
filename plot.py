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

from usinfo import USInfo
from covid_data import CovidData

_italy_pop = 60549600  # 2020 from https://en.wikipedia.org/wiki/Demographics_of_Italy

# Number of states to include in plot
_top_n = 8

# Graph parameters for Reported Tests
class C19Tests:
	num_days = 35
	y_min = 100
	y_max = 1000000

class C19TestsNorm:
	num_days = 30
	y_min = 10
	y_max = 10000

# Graph parameters for Reported Positive Cases
class C19Cases:
	num_days = 35
	y_min = 100
	y_max = 200000

class C19CasesNorm:
	num_days = 35
	y_min = 10
	y_max = 2000

	x_label = 'Days since 10 reported positive cases per million people'
	y_label = 'Cumulative reported positive cases per million people'

# Graph parameters for Reported Deaths
class C19Deaths:
	num_days = 30
	y_min = 10
	y_max = 10000

class C19DeathsNorm:
	num_days = 25
	y_min = 1
	y_max = 150

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
		print 'Generating Top-n graphs'
		self.generate_top_n_tests()
		self.generate_top_n_cases()
		self.generate_top_n_deaths()
	
	# Generate graphs for a previous date (used for animations).
	def generate_top_n_anim_data(self):
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
		options.y_min = C19Tests.y_min
		options.y_max = C19Tests.y_max
		options.max_days = C19Tests.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 100th reported test'
		options.y_label = 'Cumulative reported tests'
		options.processor = self.process_filter
		options.threshold = 100
		options.ranking = self.cdata.get_test_rank()
		self.generate_plot(options)
		# Filtered for 100 tests, linear-scale
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 10 cases/million, log
		title = 'COVID-19 US reported tests per million\n(Since first day with 10 tests/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'tests-norm'
		options.output_filebase = 'tests'
		options.y_min = C19TestsNorm.y_min
		options.y_max = C19TestsNorm.y_max
		options.max_days = C19TestsNorm.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 10 reported tests per million people'
		options.y_label = 'Cumulative reported tests per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		options.ranking = self.cdata.get_test_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
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
		options.y_min = C19Cases.y_min
		options.y_max = C19Cases.y_max
		options.max_days = C19Cases.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 100th reported positive case'
		options.y_label = 'Cumulative reported positive cases'
		options.processor = self.process_filter
		options.threshold = 100
		options.ranking = self.cdata.get_case_rank()
		self.generate_plot(options)
		# Filtered for 100 cases, linear-scale
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 10 cases/million, log
		title = 'COVID-19 US reported positive cases per million\n(Since first day with 10 cases/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'cases-norm'
		options.output_filebase = 'cases'
		options.y_min = C19CasesNorm.y_min
		options.y_max = C19CasesNorm.y_max
		options.max_days = C19CasesNorm.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 10 reported positive cases per million people'
		options.y_label = 'Cumulative reported positive cases per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		options.ranking = self.cdata.get_case_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
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
		options.y_min = C19Deaths.y_min
		options.y_max = C19Deaths.y_max
		options.max_days = C19Deaths.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 10th reported death'
		options.y_label = 'Cumulative reported deaths'
		options.processor = self.process_filter
		options.threshold = 10
		options.ranking = self.cdata.get_death_rank()
		self.generate_plot(options)
		# Filtered for 100 cases, linear-scale
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
		self.generate_plot(options)

		# Normalized for population, filtered for 1 cases/million, log
		title = 'COVID-19 US reported death per million\n(Since first day with 1 death/million. Top %d states. %s scale)'
		options.use_log_scale = True
		options.output_dir = 'deaths-norm'
		options.output_filebase = 'deaths'
		options.y_min = C19DeathsNorm.y_min
		options.y_max = C19DeathsNorm.y_max
		options.max_days = C19DeathsNorm.num_days
		options.title = title % (_top_n, 'Log')
		options.x_label = 'Days since 1 reported death per million people'
		options.y_label = 'Cumulative reported deaths per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 1
		options.ranking = self.cdata.get_death_rank_norm()
		self.generate_plot(options)
		# Normalized for population, filtered for 10 cases/million, linear
		options.use_log_scale = False
		options.title = title % (_top_n, 'Linear')
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

		# Plot the top |_top_n| states.
		for i in xrange(_top_n):
			state = options.ranking[i];
			self.plot_data(ax, options.state_data(state), color_order[i],
					USInfo.state_pop[state], state, False,
					options.processor, options.threshold)

		self.plot_data(ax, options.italy_data(), 'black', _italy_pop, 'Italy', True,
				options.processor, options.threshold)
		self.plot_data(ax, options.us_data(), 'black', USInfo.us_pop, 'US', True,
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
		print 'Generating combined state graphs'
		self.generate_states_combined_tests()
		self.generate_states_combined_cases()
		self.generate_states_combined_deaths()
	
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
	
	def generate_states_combined_tests(self):
		plt.close('all')
		fig, axs = plt.subplots(14, 4, sharex=True, sharey=True)

		self.add_combined_title(axs[0,1], 
				'COVID-19 US States Reported Tests per Million',
				'Since first day with 10 tests/million')
		self.add_combined_footer(axs[13,0],
				['Each US state compared with all other states',
				'Data is cumulative but some reporting is inconsistent',
				'Note: y=10000 is 1% of the state\'s population',
				'Data from https://covidtracking.com'],
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
			ax.axis([0, C19TestsNorm.num_days, C19TestsNorm.y_min, C19TestsNorm.y_max])
			self.format_axes(ax, True)
			ax.set_yticks([10,100,1000,10000])
			
			# Plot data for all the states in light gray for reference.
			for s2 in USInfo.states:
				self.plot_data(ax, self.cdata.get_state_tests(s2), 'lt_gray',
						USInfo.state_pop[s2], '', False, self.process_normalize_and_filter, 10)	
			self.plot_data(ax, self.cdata.get_state_tests(s), 'dk_gray',
					USInfo.state_pop[s], s, True, self.process_normalize_and_filter, 10)

		fig.set_size_inches(8, 18)
		plt.savefig('tests-norm/states.png', dpi=150, bbox_inches='tight')

	def generate_states_combined_cases(self):
		plt.close('all')
		fig, axs = plt.subplots(14, 4, sharex=True, sharey=True)

		self.add_combined_title(axs[0,1], 
				'COVID-19 US States Reported Positive Cases per Million',
				'Since first day with 10 positive cases/million')
		self.add_combined_footer(axs[13,0],
				['Data from https://covidtracking.com'],
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
			#ax.set_title(s)
			ax.axis([0, C19CasesNorm.num_days, C19CasesNorm.y_min, C19CasesNorm.y_max])
			self.format_axes(ax, True)
			# Plot data for all the states in light gray for reference.
			for s2 in USInfo.states:
				self.plot_data(ax, self.cdata.get_state_cases(s2), 'lt_gray',
						USInfo.state_pop[s2], '', False, self.process_normalize_and_filter, 10)	
			self.plot_data(ax, self.cdata.get_state_cases(s), 'dk_gray',
					USInfo.state_pop[s], s, True, self.process_normalize_and_filter, 10)

		fig.set_size_inches(8, 18)
		plt.savefig('cases-norm/states.png', dpi=150, bbox_inches='tight')

	def generate_states_combined_deaths(self):
		plt.close('all')
		fig, axs = plt.subplots(14, 4, sharex=True, sharey=True)

		self.add_combined_title(axs[0,1], 
				'COVID-19 US States Reported Deaths per Million',
				'Since first day with 1 deaths/million')
		self.add_combined_footer(axs[13,0],
				['Data from https://covidtracking.com'],
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
			#ax.set_title(s)
			ax.axis([0, C19DeathsNorm.num_days, C19DeathsNorm.y_min, C19DeathsNorm.y_max])
			self.format_axes(ax, True)
			# Plot data for all the states in light gray for reference.
			for s2 in USInfo.states:
				self.plot_data(ax, self.cdata.get_state_deaths(s2), 'lt_gray',
						USInfo.state_pop[s2], '', False, self.process_normalize_and_filter, 1)
			self.plot_data(ax, self.cdata.get_state_deaths(s), 'dk_gray',
					USInfo.state_pop[s], s, True, self.process_normalize_and_filter, 1)

		fig.set_size_inches(8, 18)
		plt.savefig('deaths-norm/states.png', dpi=150, bbox_inches='tight')

	def generate_states_individual(self):
		self.generate_states_individual_cases()
	
	def generate_states_individual_cases(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_cases
		options.us_data = self.cdata.get_us_cases
		options.italy_data = self.cdata.get_italy_cases

		options.use_log_scale = True
		options.y_min = C19CasesNorm.y_min
		options.y_max = C19CasesNorm.y_max
		options.max_days = C19CasesNorm.num_days
		options.x_label = 'Days since 10 reported positive cases per million people'
		options.y_label = 'Cumulative reported positive cases per million people'
		options.processor = self.process_normalize_and_filter
		options.threshold = 10
		for state in USInfo.states:
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
		for s2 in USInfo.states:
			self.plot_data(ax, options.state_data(s2), 'lt_gray',
					USInfo.state_pop[s2], '', False, options.processor, options.threshold)

		self.plot_data(ax, options.state_data(state), 'dk_blue',
				USInfo.state_pop[state], state, True, options.processor, options.threshold)
		self.plot_data(ax, options.us_data(), 'black', USInfo.us_pop, 'US', True,
				options.processor, options.threshold)
		self.plot_data(ax, options.italy_data(), 'black', _italy_pop, 'Italy', True,
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
	print '  --anim Generate animated plots for top-N (implies --top)'
	print '  --combined Generate combined state plots'
	print '  --date <yyyymmdd> Only plot data up to date'
	print '  --individual Generate individual state plots'
	print '  --top Generate top-N plots'
	sys.exit(1)

def main(argv):
	try:
		opts, args = getopt.getopt(argv,
				"?hancid:t",
				["?", "help", "all", "anim", "combined", "individual", "date=", "top"])
	except getopt.GetoptError:
		usage()

	date = None
	gen_animated = False
	gen_combined = False
	gen_individual = False
	gen_top_n = False
	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			usage()
		if opt in ("-a", "--all"):
			gen_animated = True
			gen_combined = True
			gen_individual = True
			gen_top_n = True
		if opt in ("-n", "--anim"):
			gen_animated = True
			gen_top_n = True  # --anim requires --top_n
		if opt in ("-c", "--combined"):
			gen_combined = True
		if opt in ("-d", "--date"):
			date = arg
		if opt in ("-i", "--individual"):
			gen_individual = True
		if opt in ("-t", "--top"):
			gen_top_n = True

	covid_data = CovidData(date)
	covid_data.load_data()
	
	cases = CovidCases(covid_data)
	print 'Processing data for', cases.date_str

	if gen_top_n:
		cases.generate_top_n()
	
		if gen_animated:
			# Process previous day data using top-N from current day.
			while int(covid_data.get_date()) > int('20200316'):
				cases.remove_last_day()
				cases.generate_top_n_anim_data()
			cases.export_anim()

	if gen_combined:
		cases.generate_states_combined()

	if gen_individual:
		cases.generate_states_individual();
		
if __name__ == "__main__":
	main(sys.argv[1:])
