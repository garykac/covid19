from __future__ import division

import colorsys
import getopt
import math
import operator
import os
import re
import shutil
import subprocess
import sys


census_data = 'data/census/DEC_10_SF1_GCTPH1.US05PR/DEC_10_SF1_GCTPH1.US05PR.csv'
nyt_data = 'data/nyt/us-counties.csv'
census_map = 'data/us_counties.svg'
us_map_cases = 'us-cases.svg'
us_map_deaths = 'us-deaths.svg'

FIPS_NEW_YORK_CITY = '36998'
FIPS_KANSAS_CITY_MO = '29998'

AREA_SCALE = 1000000

# Max values per N square miles.
MAX_CASES_PNSM = 111574425.9
MAX_DEATHS_PNSM = 2564017.8

class MapData:
	def __init__(self):
		# FIPS for the New York City boroughs: New York, Kings, Queens, Bronx, Richmond
		self.nyc_fips = ['36061', '36047', '36081', '36005', '36085']
		# FIPS for counties that overlap with Kansas City, MO: Cass, Clay, Jackson, Platte
		self.kc_fips = ['29037', '29047', '29095', '29165']
	
		# Update fips data.
		# See also: https://www.economy.com/support/blog/buffet.aspx?did=EBD51E7D-8822-42F2-BD0D-8937239911E9
		self.updated_fips = [
			# "Changed name and code from Shannon County, South Dakota (46113) to Oglala Lakota County,
			# South Dakota (46102) effective May 1, 2015.
			# https://www.census.gov/quickfacts/fact/table/oglalalakotacountysouthdakota,SD/HSD410218
			['46113', '46102']
		]

	def load_census(self):
		self.names = {}
		self.area = {}
		self.density = {}
		self.state2fips = {}
		self.fips2state = {}
		self.state_fips_list = {}

		self.us_area = 0
		
		# Load data for states and Puerto Rico.
		with open(census_data) as fp:
			for line in fp:
				#  0: GEO.id - geo id, e.g., "0100000US"
				#  1: GEO.id2 - geo id, part 2, e.g., ""
				#  2: GEO.display-label geo label, e.g., "United States"
				#  3: GCT_STUB.target-geo-id - long fips id, e.g., "0500000US01001"
				#  4: GCT_STUB.target-geo-id2 - fips id, e.g., "01001"
				#  5: GCT_STUB.display-label - long label, e.g., "United States - Alabama - Autauga County"
				#  6: GCT_STUB.display-label - label, e.g., "Autauga County"
				#  7: HD01 - Population
				#  8: HD02 - Housing units
				#  9: SUBHD0301 - Area in square miles - Total
				# 10: SUBHD0302 - Area in square miles - Water
				# 11: SUBHD0303 - Area in square miles - Land
				# 12: SUBHD0401 - Density per square mile of land area - Population
				# 13: SUBHD0402 - Density per square mile of land area - Housing units
				data = line.strip().split(',')
				if data[0] == 'GEO.id':
					continue
				fips = data[4]
				full_label = data[5]
				state = full_label.split(' - ')[1] if '-' in full_label else ''
				label = data[6]
				area = float(data[11])  # Land area
				pop_density = float(data[12])
				
				if fips == '':
					if not label == 'United States':
						print 'ERROR: Blank fips for', label, ' fips=', fips
					continue

				# Handle states.
				if len(fips) == 2:
					fips += '999'
					self.state2fips[label] = fips
					self.fips2state[fips] = label
					self.state_fips_list[fips] = []
				else:
					# Gather a list of all fips within each state
					state_fips = fips[0:2] + '999'
					self.state_fips_list[state_fips].append(fips)

					self.us_area += area

				# Update fips id for regions that have changed.
				for f in updated_fips:
					if fips == f[0]:
						fips = f[1]
						print 'Updating fips from', f[0], 'to', f[1], 'for', label, state
				
				self.names[fips] = label
				self.area[fips] = area
				self.density[fips] = pop_density
						
		# Special FIPS for NYT data
		self.names[FIPS_NEW_YORK_CITY] = 'New York City'  # NY
		self.area[FIPS_NEW_YORK_CITY] = 0
		for f in self.nyc_fips:
			self.area[FIPS_NEW_YORK_CITY] += self.area[f]
					
		self.names[FIPS_KANSAS_CITY_MO] = 'Kansas City'  # MO
		self.area[FIPS_KANSAS_CITY_MO] = 0
		for f in self.kc_fips:
			self.area[FIPS_KANSAS_CITY_MO] += self.area[f]

		# Extra info for missing territories
		self.add_state('60999', 'American Samoa', 76.83)
		self.add_state('66999', 'Guam', 212)
		self.add_state('69999', 'Northern Mariana Islands', 184.2)
		self.add_state('78999', 'Virgin Islands', 133.7)
				
		#print self.names['53061'], self.area['53061']
		#print self.density['53061']
		#print self.names['36998'], self.area['36998']
		
	def add_state(self, fips, name, area):
		self.names[fips] = name
		self.area[fips] = area
		self.state2fips[name] = fips
		self.fips2state[fips] = name
	
	def load_nyt(self, process_date):
		self.curr_date = ''
		found_date = False
		
		self.us_cases = 0
		self.us_deaths = 0
		
		with open(nyt_data) as fp:
			for line in fp:
				# 0: date - "2020-01-21"
				# 1: county - "Snohomish"
				# 2: state - "Washington"
				# 3: fips - "53061"
				# 4: cases
				# 5: deaths 
				data = line.strip().split(',')
				if data[0] == 'date':
					continue
				date = data[0]
				county = data[1]
				state = data[2]
				fips = data[3]
				cases = int(data[4])
				deaths = int(data[5])
				
				if date != self.curr_date:
					# If finished processing the request date, then skip
					if process_date and self.curr_date == process_date:
						continue
					
					# Reset all data
					self.cases = {}
					self.deaths = {}
					self.max_cases_per_Nsqmi = 0
					self.max_deaths_per_Nsqmi = 0
					self.us_cases = 0
					self.us_deaths = 0

					unknown_state_cases = {}
					unknown_state_deaths = {}
					state_fips_with_cases = {}
					state_fips_with_deaths = {}
					
					# Initialize data for regions that require special handling.
					for fips in self.nyc_fips + self.kc_fips:
						self.cases[fips] = 0
						self.deaths[fips] = 0

					self.curr_date = date
					if date == process_date:
						found_date = True

				if process_date and date != process_date:
					continue
					
				if fips == '' and county == 'New York City':
					fips = FIPS_NEW_YORK_CITY

				if fips == '' and county == 'Kansas City' and state == 'Missouri':
					fips = FIPS_KANSAS_CITY_MO
					
				if fips in self.nyc_fips:
					print 'ERROR: data for NYC in', fips
				
				if fips == '':
					if state in self.state2fips:
						if cases != 0:
							unknown_state_cases[self.state2fips[state]] = cases
						if deaths != 0:
							unknown_state_deaths[self.state2fips[state]] = deaths
					else:
						print 'ERROR: Blank fips:', line.strip()
					continue

				if not fips in self.names:
					print 'Unknown fips:', line.strip()
					continue

				self.cases[fips] = cases
				self.deaths[fips] = deaths
				self.us_cases += cases
				self.us_deaths += deaths
				
				# Accumulate counties with data for each state. This is used to
				# distribute unknown cases to these counties. Note that unknown
				# values are not distributed to counties that report 0.
				state_fips = fips[0:2] + '999'
				if cases != 0:
					if not state_fips in state_fips_with_cases:
						state_fips_with_cases[state_fips] = []
					state_fips_with_cases[state_fips].append(fips)
				if deaths != 0:
					if not state_fips in state_fips_with_deaths:
						state_fips_with_deaths[state_fips] = []
					state_fips_with_deaths[state_fips].append(fips)
				
				# Keep track of max value so that we can normalize data to that value.
				cases_per_Nsqmi = cases * AREA_SCALE / self.area[fips]
				if cases_per_Nsqmi > self.max_cases_per_Nsqmi:
					self.max_cases_per_Nsqmi = cases_per_Nsqmi
				
				deaths_per_Nsqmi = deaths * AREA_SCALE / self.area[fips]
				if deaths_per_Nsqmi > self.max_deaths_per_Nsqmi:
					self.max_deaths_per_Nsqmi = deaths_per_Nsqmi

		# Overwrite calculated max per square mile values so that we use the same
		# value when plotting historical graphs.
		print 'Calculated max cases psm', self.max_cases_per_Nsqmi
		print 'Calculated max deaths psm', self.max_deaths_per_Nsqmi
		#self.max_cases_per_Nsqmi = MAX_CASES_PNSM
		#self.max_deaths_per_Nsqmi = MAX_CASES_PNSM
		
		if process_date and not found_date:
			print 'ERROR: Unable to find data for', process_date
			exit(1)
			
		# Equally distribute the data amongst the 5 boroughs based on size (sq mi)
		for fips in self.nyc_fips:
			percent = self.area[fips] / self.area[FIPS_NEW_YORK_CITY]
			self.cases[fips] += self.cases[FIPS_NEW_YORK_CITY] * percent
			self.deaths[fips] += self.deaths[FIPS_NEW_YORK_CITY] * percent

		# Equally distribute the data amongst the 5 country that contain Kansas City, MO based on size (sq mi)
		# Add this data to the existing data for the region
		for fips in self.kc_fips:
			percent = self.area[fips] / self.area[FIPS_KANSAS_CITY_MO]
			if FIPS_KANSAS_CITY_MO in self.cases:
				self.cases[fips] += self.cases[FIPS_KANSAS_CITY_MO] * percent
			if FIPS_KANSAS_CITY_MO in self.deaths:
				self.deaths[fips] += self.deaths[FIPS_KANSAS_CITY_MO] * percent
		
		# For the 'Unknown' data for each state, distribute it equally (based on area)
		# to the counties that have reported non-zero values.
		for state_fips in unknown_state_cases:
			# Ignore Puerto Rico, Virgin Islands, Guam and Northern Mariana Islands.
			# All cases are unknown and not on map yet.
			if state_fips in ['72999', '78999', '66999', '69999']:
				continue

			# Determine set of FIPS to distribute the cases to
			if state_fips in state_fips_with_cases:
				#print 'Distributing Unknowns cases for', self.fips2state[state_fips], 'to counties with data'
				target_fips = state_fips_with_cases[state_fips]
			else:
				# If all cases in a state are 'Unknown', then distribute to entire state
				print 'Distributing Unknowns cases for', self.fips2state[state_fips], 'to entire state'
				target_fips = self.state_fips_list[state_fips]
				for f in target_fips:
					self.cases[f] = 0
				
			# Calc total area for affected counties
			area = 0
			for fips in target_fips:
				area += self.area[fips]
			# Distribute the total to each affected county proportional to area.
			for fips in target_fips:
				self.cases[fips] += unknown_state_cases[state_fips] * (self.area[fips] / area)
		for state_fips in unknown_state_deaths:
			# Ignore Puerto Rico, Virgin Islands, Guam and Northern Mariana Islands - all cases are unknown and not on map yet.
			if state_fips in ['72999', '78999', '66999', '69999']:
				continue

			# Determine set of FIPS to distribute the deaths to
			if state_fips in state_fips_with_deaths:
				#print 'Distributing Unknowns deaths for', self.fips2state[state_fips], 'to counties with data'
				target_fips = state_fips_with_deaths[state_fips]
			else:
				# If all cases in a state are 'Unknown', then distribute to entire state
				print 'Distributing Unknowns deaths for', self.fips2state[state_fips], 'to entire state'
				target_fips = self.state_fips_list[state_fips]
				for f in target_fips:
					self.deaths[f] = 0
				
			# Calc total area for affected counties
			area = 0
			for fips in target_fips:
				area += self.area[fips]
			# Distribute the total to each affected county proportional to area.
			for fips in target_fips:
				self.deaths[fips] += unknown_state_deaths[state_fips] * (self.area[fips] / area)

		#print fips, self.names['53061'], self.cases['53061'], self.deaths['53061']

		print 'US total: cases', self.us_cases, 'deaths', self.us_deaths
		
	def scan_svg(self):
		self.map_ids = {}
		with open(census_map) as fp:
			for line in fp:
				# Match lines with 'id="FIPS_02185"'
				m = re.search(r'id="c(\d\d\d\d\d)"', line)
				if m:
					self.map_ids[m.group(1)] = True
	
	def check_data(self):
		for fips in self.cases:
			if not fips in self.map_ids:
				if fips[2:] == '999':
					# State level
					continue
				if fips[2:] == '998':
					# Special region
					continue
				print 'Unable to find', fips, 'on map.'

	def generate_map_cases(self):
		self.generate_map('Cases', us_map_cases, self.cases, self.max_cases_per_Nsqmi)
		
	def generate_map_deaths(self):
		self.generate_map('Deaths', us_map_deaths, self.deaths, self.max_deaths_per_Nsqmi)
		
	def generate_map(self, type, out_svg, data, max_per_Nsqmi):
		d = self.curr_date
		months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
		date_str = d[8:10] + ' ' + months[int(d[5:7])-1] + ' ' + d[0:4]

		val_log_max = math.log10(max_per_Nsqmi)
		with open(census_map) as fpin:
			with open(out_svg, 'w') as fpout:
				for line in fpin:
					if 'inkscape' in line:
						if line.strip() == 'inkscape:connector-curvature="0"':
							continue
					if line.startswith('  #INSERT_STYLES'):
						self.write_color_style(fpout, 'legend-1', 1.0)
						self.write_color_style(fpout, 'legend-2', 0.8)
						self.write_color_style(fpout, 'legend-3', 0.6)
						self.write_color_style(fpout, 'legend-4', 0.4)
						self.write_color_style(fpout, 'legend-5', 0.2)
						for fips in data.keys():
							# The CSS style id for coloring this region.
							fips_style_id = fips
							if fips == '66999':
								continue
							if fips in self.nyc_fips:
								# NYT data for NYC is all combined into one value. So
								# Use the same color for each borough.
								fips = FIPS_NEW_YORK_CITY
							if fips == FIPS_KANSAS_CITY_MO:
								continue
							if data[fips] != 0:
								val_log = math.log10(data[fips] * AREA_SCALE / self.area[fips])
								if val_log < 0:
									print 'Bad', type, 'log:', fips, val_log
								# Scale the log values to be 0.0 - 1.0
								scaled_log = val_log / val_log_max
								if scaled_log > 1.0:
									print 'WARNING: clamping scaled value that exceeds max:', scaled_log, 'for', fips, self.names[fips]
									scaled_log = 1.0
								self.write_color_style(fpout, 'c'+fips_style_id, scaled_log)
					else:
						line = line.replace('%%DATE%%', date_str)
						line = line.replace('%%TYPE%%', type)
						line = line.replace('%%LEGEND1%%', self.format_val(1.0, val_log_max))
						line = line.replace('%%LEGEND2%%', self.format_val(0.8, val_log_max))
						line = line.replace('%%LEGEND3%%', self.format_val(0.6, val_log_max))
						line = line.replace('%%LEGEND4%%', self.format_val(0.4, val_log_max))
						line = line.replace('%%LEGEND5%%', self.format_val(0.2, val_log_max))
						fpout.write(line)

		ymd = d[0:4] + d[5:7] + d[8:10]
		(name, suffix) = out_svg.split('.')
		archive = 'map-%s/%s-%s.svg' % (name, name, ymd)
		shutil.copy(out_svg, archive)
	
	def format_val(self, percent, log_max):
		val = (10 ** (percent * log_max)) / AREA_SCALE
		if val > 9:
			return '%.0f' % val
		if val > 0.4:
			return '%.1f' % val
		if val > 0.01:
			return '%.2f' % val
		if val > 0.001:
			return '%.3f' % val
		if val > 0.0001:
			return '%.4f' % val
		if val > 0.00001:
			return '%.5f' % val
		return '%.2e' % val

	def write_color_style(self, fp, name, value):
		#rgb = colorsys.hsv_to_rgb(1.0, scaled_log, 1.0)
		rgb = colorsys.hsv_to_rgb((1.0 - value) * 0.225, value, 1.0)
		color = "#{:02x}{:02x}{:02x}".format(int(255 * rgb[0]), int(255 * rgb[1]), int(255 * rgb[2]))
		#print fips, self.deaths[fips], death_log, death_log_max, scaled_log, rgb, color
		fp.write('  #%s {fill:%s;}\n' % (name, color))
	
	def animate(self):
		self.animate_data('map-us-cases', 'us-cases')
		self.animate_data('map-us-deaths', 'us-deaths')

	def animate_data(self, dir, filebase):
		files = os.listdir(dir)
		last_file = ''
		print '  Converting svg files'
		for f in sorted(files):
			(name, suffix) = f.split('.')
			if suffix != 'svg':
				continue
			svg_file = '%s/%s.svg' % (dir, name)
			png_file = '%s/%s.png' % (dir, name)
			# Record last file so that we can hold it longer at end of animation.
			if png_file > last_file:
				last_file = png_file
			if os.path.exists(png_file):
				continue
			print '    ', name
			subprocess.call(['svg2png', svg_file, '-o', png_file])

		print '  Combining images'
		subprocess.call(['convert', '-morph', '1', '-delay', '15', '%s/*.png' % dir, '-delay', '240', last_file, '%s.gif' % filebase])

def usage():
	print 'map.py [options]'
	print 'where options are:'
	print '  --help'
	print '  --anim'
	print '  --date yyyy-mm-dd'
	sys.exit(1)

def main(argv):
	try:
		opts, args = getopt.getopt(argv,
				"?had:",
				["?", "help", "anim", "date="])
	except getopt.GetoptError:
		usage()

	process_date = None
	animate = False
	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			usage()
		if opt in ("-a", "--anim"):
			animate = True
		if opt in ("-d", "--date"):
			process_date = arg

	map_data = MapData()
	map_data.load_census()
	map_data.load_nyt(process_date)
	map_data.scan_svg()
	map_data.check_data()

	map_data.generate_map_cases()
	map_data.generate_map_deaths()

	if animate:
		map_data.animate()
		
if __name__ == "__main__":
	main(sys.argv[1:])
