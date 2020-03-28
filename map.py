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

class MapData:
	def __init__(self):
		# FIPS for the New York City boroughs: New York, Kings, Queens, Bronx, Richmond
		self.nyc_fips = ['36061', '36047', '36081', '36005', '36085']
		# FIPS for counties that overlap with Kansas City, MO: Cass, Clay, Jackson, Platte
		self.kc_fips = ['29037', '29047', '29095', '29165']
	
	def load_census(self):
		self.names = {}
		self.area = {}
		self.density = {}
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
				label = data[6]
				area = data[11]
				pop_density = data[12]
				
				if len(fips) == 2:
					fips += '999'
				self.names[fips] = label
				self.area[fips] = float(area)
				self.density[fips] = float(pop_density)

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
		self.names['60999'] = 'American Samoa'
		self.area['60999'] = 76.83
		self.names['66999'] = 'Guam'
		self.area['66999'] = 212
		self.names['69999'] = 'Northern Mariana Islands'
		self.area['69999'] = 184.2
		self.names['78999'] = 'Virgin Islands'
		self.area['78999'] = 133.7
				
		#print self.names['53061'], self.area['53061']
		#print self.density['53061']
		#print self.names['36998'], self.area['36998']

	def load_nyt(self):
		self.cases = {}
		self.deaths = {}
		self.max_deaths_per_Nsqmi = 0
		self.max_cases_per_Nsqmi = 0
		max_deaths_fips = ''
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
				fips = data[3]
				cases = int(data[4])
				deaths = int(data[5])
				
				if date == '2020-03-25':					
					if fips == '' and county == 'New York City':
						fips = FIPS_NEW_YORK_CITY

					if fips in self.nyc_fips:
						print 'ERROR: data for NYC in', fips
					
					if not fips in self.names:
						print 'Unknown fips:', line.strip()

					self.cases[fips] = cases
					self.deaths[fips] = deaths

					cases_per_Nsqmi = cases * AREA_SCALE / self.area[fips]
					if cases_per_Nsqmi > self.max_cases_per_Nsqmi:
						self.max_cases_per_Nsqmi = cases_per_Nsqmi
					
					deaths_per_Nsqmi = deaths * AREA_SCALE / self.area[fips]
					if deaths_per_Nsqmi > self.max_deaths_per_Nsqmi:
						self.max_deaths_per_Nsqmi = deaths_per_Nsqmi
						max_deaths_fips = fips

		# Initialize data for the 5 NYC boroughs		
		for fips in self.nyc_fips:
			# Verify that there is not existing data for these regions.
			if fips in self.cases:
				print 'ERROR: Already have case data for', self.names[fips]
			if fips in self.deaths:
				print 'ERROR: Already have death data for', self.names[fips]
			self.cases[fips] = 0
			self.deaths[fips] = 0

		# Equally distribute the data amongst the 5 boroughs based on size (sq mi)
		for fips in self.nyc_fips:
			percent = self.area[fips] / self.area[FIPS_NEW_YORK_CITY]
			self.cases[fips] += self.cases[FIPS_NEW_YORK_CITY] * percent
			self.deaths[fips] += self.deaths[FIPS_NEW_YORK_CITY] * percent

		# Equally distribute the data amongst the 5 country that contain Kansas City, MO based on size (sq mi)
		# Add this data to the existing data for the region
		for fips in self.kc_fips:
			percent = self.area[fips] / self.area[FIPS_KANSAS_CITY_MO]
			self.cases[fips] += self.cases[FIPS_KANSAS_CITY_MO] * percent
			self.deaths[fips] += self.deaths[FIPS_KANSAS_CITY_MO] * percent
			
		#print fips, self.names['53061'], self.cases['53061'], self.deaths['53061']
		#print max_deaths_fips, self.names[max_deaths_fips], self.cases[max_deaths_fips], self.deaths[max_deaths_fips]

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
		val_log_max = math.log10(max_per_Nsqmi)
		with open(census_map) as fpin:
			with open(out_svg, 'w') as fpout:
				for line in fpin:
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
								self.write_color_style(fpout, 'c'+fips_style_id, scaled_log)
					else:
						line = line.replace('%%DATE%%', '25 Mar 2020')
						line = line.replace('%%TYPE%%', type)
						line = line.replace('%%LEGEND1%%', self.format_val(1.0, val_log_max))
						line = line.replace('%%LEGEND2%%', self.format_val(0.8, val_log_max))
						line = line.replace('%%LEGEND3%%', self.format_val(0.6, val_log_max))
						line = line.replace('%%LEGEND4%%', self.format_val(0.4, val_log_max))
						line = line.replace('%%LEGEND5%%', self.format_val(0.2, val_log_max))
						fpout.write(line)
	
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
		return '%e' % val

	def write_color_style(self, fp, name, value):
		#rgb = colorsys.hsv_to_rgb(1.0, scaled_log, 1.0)
		rgb = colorsys.hsv_to_rgb((1.0 - value) * 0.225, value, 1.0)
		color = "#{:02x}{:02x}{:02x}".format(int(255 * rgb[0]), int(255 * rgb[1]), int(255 * rgb[2]))
		#print fips, self.deaths[fips], death_log, death_log_max, scaled_log, rgb, color
		fp.write('  #%s {fill:%s;}\n' % (name, color))
	
def usage():
	print 'map.py [options]'
	print 'where options are:'
	sys.exit(1)

def main(argv):
	try:
		opts, args = getopt.getopt(argv,
				"?h",
				["?", "help"])
	except getopt.GetoptError:
		usage()

	for opt, arg in opts:
		if opt in ("-?", "-h", "--?", "--help"):
			usage()

	map_data = MapData()
	map_data.load_census()
	map_data.load_nyt()
	map_data.scan_svg()
	map_data.check_data()

	map_data.generate_map_cases()
	map_data.generate_map_deaths()
	
if __name__ == "__main__":
	main(sys.argv[1:])
