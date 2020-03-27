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
	threshold = 100
	y_min = threshold
	y_max = 1000000
	title = 'COVID-19 US reported tests'
	subtitle = 'Since first day with %d tests' % threshold
	output_dir = 'tests'
	output_filebase = 'tests'
	x_label = 'Days since %dth reported test' % threshold
	y_label = 'Cumulative reported tests'

class C19TestsNorm:
	num_days = 35
	threshold = 10
	y_min = threshold
	y_max = 10000
	title = 'COVID-19 US States Reported Tests (Pos + Neg) per Million'
	subtitle = 'Since first day with %d tests/million' % threshold
	output_dir = 'tests-norm'
	output_filebase = 'tests'
	x_label = 'Days since %d reported tests per million people' % threshold
	y_label = 'Cumulative reported tests per million people'

	combined_num_days = 25
	combined_y_max = y_max
	y_ticks_lin = [0, 5000, 10000]
	y_ticks_log = [10,100,1000,10000]
	combined_footer = ['Each US state Pos + Neg tests compared with all other states',
			'Data is cumulative but some reported data is inconsistent',
			'Note: y=10000 is 1% of the state\'s population']

	individual_title = 'COVID-19 %s Reported Tests (Pos + Neg) per Million'

# Graph parameters for Reported Positive Cases
class C19Cases:
	num_days = 35
	threshold = 100
	y_min = threshold
	y_max = 200000
	title = 'COVID-19 US reported positive cases'
	subtitle = 'Since first day with %d cases' % threshold
	output_dir = 'cases'
	output_filebase = 'cases'
	x_label = 'Days since %dth reported positive case' % threshold
	y_label = 'Cumulative reported positive cases'

class C19CasesNorm:
	num_days = 35
	threshold = 10
	y_min = threshold
	y_max = 5000
	title = 'COVID-19 US States Reported Positive Cases per Million'
	subtitle = 'Since first day with %d positive cases/million' % threshold
	output_dir = 'cases-norm'
	output_filebase = 'cases'
	x_label = 'Days since %d reported positive cases per million people' % threshold
	y_label = 'Cumulative reported positive cases per million people'

	combined_num_days = 25
	combined_y_max = 2000
	y_ticks_lin = []
	y_ticks_log = []
	combined_footer = []
	
	individual_title = 'COVID-19 %s Reported Positive Cases per Million'

# Graph parameters for Reported Deaths
class C19Deaths:
	num_days = 35
	threshold = 10
	y_min = threshold
	y_max = 10000
	title = 'COVID-19 US reported deaths'
	subtitle = 'Since first day with %d deaths' % threshold
	output_dir = 'deaths'
	output_filebase = 'deaths'
	x_label = 'Days since %dth reported death' % threshold
	y_label = 'Cumulative reported deaths'

class C19DeathsNorm:
	num_days = 25
	threshold = 1
	y_min = threshold
	y_max = 150
	title = 'COVID-19 US States Reported Deaths per Million'
	subtitle = 'Since first day with %d death/million' % threshold
	output_dir = 'deaths-norm'
	output_filebase = 'deaths'
	x_label = 'Days since %d reported death per million people' % threshold
	y_label = 'Cumulative reported deaths per million people'

	combined_num_days = 20
	combined_y_max = 100
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

	def new_tests_options(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_tests
		options.us_data = self.cdata.get_us_tests
		options.italy_data = self.cdata.get_italy_tests
		return options
	
	def new_cases_options(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_cases
		options.us_data = self.cdata.get_us_cases
		options.italy_data = self.cdata.get_italy_cases
		return options

	def new_deaths_options(self):
		options = lambda: None  # An object that we can attach attributes to
		options.state_data = self.cdata.get_state_deaths
		options.us_data = self.cdata.get_us_deaths
		options.italy_data = self.cdata.get_italy_deaths
		return options

	# Generate main graphs for |plot_date|.
	def generate_top_n(self):
		print 'Generating Top-n graphs'
		self.generate_top_n_tests()
		self.generate_top_n_cases()
		self.generate_top_n_deaths()
	
	# Generate graphs for a previous date (used for animations).
	def generate_top_n_anim_data(self):
		print 'Processing animation data for', self.date_str
		print '  top-n',
		self.generate_top_n_tests()
		self.generate_top_n_cases()
		self.generate_top_n_deaths()

	def generate_top_n_tests(self):
		options = self.new_tests_options()		
		options.info_direct = C19Tests
		options.ranking_direct = self.cdata.get_test_rank()
		options.info_norm = C19TestsNorm
		options.ranking_norm = self.cdata.get_test_rank_norm()

		self.generate_top_n_data(options)
		
	def generate_top_n_cases(self):
		options = self.new_cases_options()
		options.info_direct = C19Cases
		options.ranking_direct = self.cdata.get_case_rank()
		options.info_norm = C19CasesNorm
		options.ranking_norm = self.cdata.get_case_rank_norm()
		
		self.generate_top_n_data(options)

	def generate_top_n_deaths(self):
		options = self.new_deaths_options()
		options.info_direct = C19Deaths
		options.ranking_direct = self.cdata.get_death_rank()
		options.info_norm = C19DeathsNorm
		options.ranking_norm = self.cdata.get_death_rank_norm()
		
		self.generate_top_n_data(options)

	# Generate a linear and a log top-n graph.
	def generate_top_n_data(self, options):
		print options.info.output_dir,
		options.info = options.info_direct
		options.processor = self.process_filter
		options.ranking = options.ranking_direct
		self.generate_top_n_data_scale(options, True)
		self.generate_top_n_data_scale(options, False)

		options.info = options.info_norm
		options.processor = self.process_normalize_and_filter
		options.ranking = options.ranking_norm
		self.generate_top_n_data_scale(options, True)
		self.generate_top_n_data_scale(options, False)

	# Generate top-n graph.
	def generate_top_n_data_scale(self, options, use_log_scale):
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
		self.add_footer(plt)

		# Plot the top |_top_n| states.
		for i in xrange(_top_n):
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

	def add_footer(self, plt):
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

	def generate_states_combined(self):
		print 'Generating combined state graphs'
		self.generate_states_combined_tests()
		self.generate_states_combined_cases()
		self.generate_states_combined_deaths()
	
	def generate_states_combined_tests(self):
		print '  combined tests'
		options = self.new_tests_options()
		options.info = C19TestsNorm
		options.ranking = self.cdata.get_test_rank_norm()
		options.processor = self.process_normalize_and_filter

		self.generate_states_combined_data(options, True)
		self.generate_states_combined_data(options, False)
	
	def generate_states_combined_cases(self):
		print '  combined cases'
		options = self.new_cases_options()
		options.info = C19CasesNorm
		options.ranking = self.cdata.get_case_rank_norm()
		options.processor = self.process_normalize_and_filter

		self.generate_states_combined_data(options, True)
		self.generate_states_combined_data(options, False)

	def generate_states_combined_deaths(self):
		print '  combined deaths'
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
		print 'Generating individual state graphs'
		self.generate_states_individual_tests()
		self.generate_states_individual_cases()
		self.generate_states_individual_deaths()
	
	def generate_states_individual_tests(self):
		print '  individual tests'
		options = self.new_tests_options()
		self.generate_states_individual_data(C19TestsNorm, options)
	
	def generate_states_individual_cases(self):
		print '  individual cases'
		options = self.new_cases_options()
		self.generate_states_individual_data(C19CasesNorm, options)
		
	def generate_states_individual_deaths(self):
		print '  individual deaths'
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

		scale = 'Linear'
		if use_log_scale:
			scale = 'Log'
		title1 = info.individual_title % state
		title = '%s\n(%s. %s scale)' % (title1, info.subtitle, scale)
		plt.title(title)
		self.add_footer(plt)
	
		# Plot data for all the states in light gray for reference.
		for s2 in USInfo.states:
			self.plot_data(ax, options.state_data(s2), 'lt_gray',
					USInfo.state_pop[s2], '', False, options.processor, info.threshold)

		self.plot_data(ax, options.state_data(state), 'dk_blue',
				USInfo.state_pop[state], state, True, options.processor, info.threshold)
		self.plot_data(ax, options.us_data(), 'black', USInfo.us_pop, 'US', True,
				options.processor, info.threshold)
		self.plot_data(ax, options.italy_data(), 'black', _italy_pop, 'Italy', True,
				options.processor, info.threshold)

		plt.legend(loc="lower right")

		output_dir = 'state/%s' % state
		if not os.path.exists(output_dir):
			os.makedirs(output_dir)

		suffix = 'lin'
		if use_log_scale:
			suffix = 'log'
		# Note: Use |info.output_dir| as filename since we don't create subdir for states.
		filename_date = '%s/%s-%s.png' % (output_dir, info.output_dir, suffix)
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
		# On combined graphs, the other states are in lt_gray
		if color == 'lt_gray':
			linewidth = 1
		
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
		
	def create_state_html(self):
		print 'Generating state html files'
		for s in USInfo.states:
			with open('state-index-template.txt') as fpin:
				with open('state/%s/index.html' % s, 'w') as fpout:
					for line in fpin:
						fpout.write(line.replace('%%STATE%%', USInfo.state_name[s]))

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

	if gen_combined:
		cases.generate_states_combined()

	if gen_individual:
		cases.generate_states_individual();
		
	if gen_top_n and gen_animated:
		# Process previous day data using top-N from current day.
		while int(covid_data.get_date()) > int('20200316'):
			cases.remove_last_day()
			cases.generate_top_n_anim_data()
		cases.export_anim()

	cases.create_state_html()
	
if __name__ == "__main__":
	main(sys.argv[1:])
