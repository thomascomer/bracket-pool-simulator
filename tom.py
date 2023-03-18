YEAR = 2023
DATE_OF_FIRST_GAME = 16
import random
import re
import glob
import getBracketsFromPool
import time
import numpy as np
import os
from splinter import browser

class Team:
	def __init__(self, ID, name, seed):
		self.ID = ID
		self.name = name
		self.seed = int(seed)
		self.eliminated = False
		self.wins = 0  # number of wins in current sim
		self.kp = 0  # adjEM
		self.kptempo = 0  # tempo
		self.champ_count = 0
		self.total_wins = 0
		self.total_wincounts = [0, 0, 0, 0, 0, 0, 0]
		self.min_wins = 0
		self.next_opponent = None
		self.initial_opponent = None

	def elimination(self, level):
		self.wins = level
		self.next_opponent = self.initial_opponent
		self.eliminated = True

	def restore(self):
		self.champ_count += (self.wins == 6)
		self.total_wins += self.wins
		self.total_wincounts[self.wins] += 1
		self.eliminated = False
		self.wins = 0


class Entry:
	def __init__(self, filename: str):
		self.name = filename.split('/')[-1]
		self.scores_array = np.zeros(0, np.uint8)
		self.picks_array = np.zeros(64, np.uint8)
		self.winnings = 0
		self.winrate = 0
		self.average_score = 0
		self.picks = {}
		self.champ = None
		with open(filename, "r") as f:
			all_text = f.read()
		if len(all_text) > 5000:
			with open(filename, "w") as f:
				picked = r"<span class=\"picked.*?title=\".*?\""
				for pick in re.findall(picked, all_text, re.I):
					name = re.search(r"title=\".*", pick)[0][7:-1]
					f.write(name + ',')
			with open(filename) as f:
				all_text = f.read()
		if "could not be found" in all_text:
			self.picks["Indiana Wesleyan"] = None
		else:
			for pick in all_text.split(','):
				try:
					self.picks[pick] += 1
				except KeyError:
					self.picks[pick] = 1
				if self.picks[pick] == 6:
					self.champ = pick


class Pool:
	def __init__(self, groupID: str, year=YEAR):
		self.drawcount = 0
		self.winning_scores = None
		self.games_completed = 0
		self.entries = {}
		while self.entries == {}:
			for filename in glob.glob("html_sources/" + groupID + "/*"):
				entryName = filename.split('/')[-1]
				self.entries[entryName] = Entry(filename)
			if self.entries == {}:
				getBracketsFromPool.getBfromP(groupID, year=year)

	def determine_winscores(self):
		for entryname in self.entries:
			entry = self.entries[entryname]
			if self.winning_scores is None:
				self.winning_scores = entry.scores_array.copy()
			else:
				self.drawcount += 1
			self.winning_scores = np.maximum(self.winning_scores, entry.scores_array)


def update_scoreboard():  # day is the number of days completed, hour is the latest tipoff to be included on the incomplete day
	f1 = None
	with browser.Browser(headless=True) as b:
		b.visit("https://www.sports-reference.com/cbb/postseason/" + str(YEAR) + "-ncaa.html")
		scoreboard_html = b.html_snapshot()
		f1 = open(scoreboard_html)
	all_text = f1.read()
	winners = {}
	for longwinner in re.findall("<div class=\"winner\".*?</a>.*?</a>", all_text, re.DOTALL):
		winner = re.findall(">.*?</a>", longwinner)[-2][1:-4]
		longdate = re.findall("<a href=\".*?>", longwinner)[-1]
		date = re.search("\d{4}-\d\d-\d\d-\d\d", longdate)[0]
		game_month = int(date[-8])
		game_day = int(date[-5:-3]) + (31 if game_month == 4 else 0)
		game_hour = date[-2:]
		try:
			winners[str(game_day) + game_hour] += "," + winner
		except KeyError:
			winners[str(game_day) + game_hour] = winner
	f1.close()
	with open("corefolder/scoreboard" + str(YEAR) + ".txt", 'w') as f2:
		day = -1
		last_date = 0
		for winner in sorted(winners):
			hour = winner[-2:]
			date = int(winner[:2])
			if date > last_date:
				last_date = date
				day += 1
			f2.write("d" + str(day) + "h" + hour + ":" + winners[winner] + ',' + str(date) + '\n')


def update_kp():
	f1 = None
	f2 = None
	with browser.Browser(headless=True) as b:
		b.visit("https://kenpom.com")
		kp_html = b.html_snapshot()
		f1 = open(kp_html)
	for line in f1.readlines():
		if "update\">Data" in line:
			longdate = re.search("Data.*?</a>", line)[0]
			date = re.search("\d{4}-\d\d-\d\d", longdate)[0]
			game_month = int(date[-4])
			game_day = int(date[-2:]) + (31 if game_month == 4 else 0)
			f2 = open("corefolder/kp" + str(game_day) + ".txt", 'w')
			f2.write("team,rating,tempo\n")
		if "a href=\"team.php" in line:
			teamname = re.search("a href=\"team.php.*?</a>", line)[0].split('>')[1][:-3]
			kp = re.search(r"[+-]\d\d?\.\d\d", line)[0]
			kptempo = re.findall(r"\d\d?\.\d", line)[3]
			f2.write(teamname + ',' + kp + ',' + kptempo + '\n')
	f1.close()
	f2.close()


def initialize_teams(day=0, hour=0) -> dict:
	game_day = str(DATE_OF_FIRST_GAME) #first day of games
	teams = {}
	year = str(YEAR)
	# get name, seed, and ID
	with open("corefolder/national_bracket" + year + ".html") as f1:  # this file is the "National Bracket" from espn.com and is used to initialize teams within the program
		for line in f1.readlines():
			if "scoreboard_teams" in line:
				for team in re.findall(r"{.*?\}", line):
					name = re.search(r"\"n\":\".*?\"", team)[0][5:-1]
					seed = re.search(r"\"s\":\d*?,", team)[0][4:-1]
					ID = re.search(r"\"id\":\d*?,", team)[0][5:-1]
					teams[name] = Team(ID, name, seed)
				break

	# look up how many games team has won
	f = None
	try:
		f = open("corefolder/scoreboard" + str(YEAR) + ".txt")
	except FileNotFoundError:
		update_scoreboard()
		f = open("corefolder/scoreboard" + str(YEAR) + ".txt")
	if f is None:
		raise FileNotFoundError("scoreboard not found")
	for line in f.readlines():
		if int(line[1]) < day or (int(line[1]) == day and int(line[3:5]) <= hour):
			for teamname in re.split(",|:", line)[1:]:
				try:
					teams[map_name(teamname.strip('\n'))].min_wins += 1
				except KeyError:
					game_day = teamname  # determine date of most relevant kp ratings for next section
		else:
			break

	# get kp data
	f2 = None
	try:
		f2 = open("corefolder/kp" + game_day[:-1] + ".txt")
	except FileNotFoundError:
		game_day2 = int(game_day)
		update_kp()
		do_continue = None
		while do_continue is None or game_day2 > 10:
			try:
				f2 = open("corefolder/kp" + str(game_day2) + ".txt")
				if game_day2 != int(game_day):
					print("kp ratings from the " + game_day[:-1] + "th not found, using ratings from the " + str(game_day2) + "th")
					print("to prevent the program from visiting kenpom.com every time you see this error, create and populate file " + "corefolder/kp" + game_day[:-1] + ".txt\na copy of another kp file will work fine")
				break
			except FileNotFoundError:
				if do_continue:
					game_day2 -= 1
				else:
					game_day2 += 1
				if game_day2 == 44:
					game_day2 = int(game_day) - 1
					do_continue = 1
	if f2 is None:
		raise FileNotFoundError("kp ratings not found")
	f2.readline()
	for line in f2.readlines():
		team = map_name(line.split(',')[0])
		try:
			teams[team].kp = int(100 * float(line.split(',')[1]))
			teams[team].kptempo = int (10 * float(line.split(',')[2]))
		except KeyError:
			pass
	f2.close()
	for team in teams:
		if teams[team].kptempo is 0:
			print(team + " team kp notation not recognized")

	return teams


def map_name(team: str, year=YEAR) -> str:
	team = team.replace('amp;', '').replace(';', '')
	with open("corefolder/name_mapping" + str(year) + ".txt") as f:
		for line in f.readlines():
			if team in line.split(','):
				return line.split(',')[0]
	return team


def simulate(teams: dict, sim_count: int, day=0, hour=0):  # ~19 seconds for 100000 sims
	filename = "simsdata/"
	filename += "sim_d" + str(day) + 'h' + str(hour) + ".data"
	opp = None
	teams_dict = {}
	for teamname in teams:
		teams_dict[teamname] = True
		if opp is None:
			opp = teams[teamname]
		else:
			teams[teamname].initial_opponent = opp
			teams[teamname].next_opponent = opp
			opp.initial_opponent = teams[teamname]
			opp.next_opponent = teams[teamname]
			opp = None
	f = None
	try:
		f = open(filename, "wb")
	except FileNotFoundError:
		os.mkdir("simsdata")
		f = open(filename, "wb")
	for i in range(sim_count):
		sim_result = np.zeros(64, np.uint8)  # entries represent the number of wins for each team in the bracket
		alive = dict(teams_dict)
		for current_round in range(6):
			dead = {}
			for teamname in alive:
				team = teams[teamname]
				if opp is None:
					opp = team
				else:
					opp.next_opponent = team
					team.next_opponent = opp
					opp = None
					if team.min_wins > current_round:
						team.next_opponent.elimination(current_round)
						dead[team.next_opponent.name] = True
					elif team.next_opponent.min_wins > current_round:
						team.elimination(current_round)
						dead[team.name] = True
					else:
						spread = (team.kp - team.next_opponent.kp) * (team.kptempo + team.next_opponent.kptempo) / 200000
						teamA_is_favored = True
						if spread < 0:
							spread = spread * -1
							teamA_is_favored = False
						teamAwp = min(1, .0000016026 * spread**4 -.0000726490 * spread**3 - .0000795626 * spread**2 + .0431431202 * spread + 0.4738370223)  # avoid win prob > 1
						if not teamA_is_favored:
							teamAwp = 1 - teamAwp
						if random.random() < teamAwp:
							team.next_opponent.elimination(current_round)
							dead[team.next_opponent.name] = True
						else:
							team.elimination(current_round)
							dead[team.name] = True
			for teamname in dead:
				alive.pop(teamname)
		for teamname in alive:
			teams[teamname].elimination(6)
		team_idx = 0
		for teamname in teams:
			team = teams[teamname]
			sim_result[team_idx] = team.wins
			team_idx += 1
			team.restore()
		f.write(sim_result)
	f.close()


def score(mypool: Pool, teams: dict, sim_count: int, day=0, hour=0, refresh_sim=False):
	simsfile = "simsdata/"
	team_idx = 0
	for team in teams:
		for entryname in mypool.entries:
			entry = mypool.entries[entryname]
			try:
				entry.picks_array[team_idx] = entry.picks[team]
			except KeyError:
				pass
		team_idx += 1
	simsfile += "sim_d" + str(day) + 'h' + str(hour) + ".data"
	if refresh_sim:
		simulate(teams, sim_count, day, hour)
	try:
		if os.path.getsize(simsfile) < 64 * sim_count:  # sim_count is a minimum, not an absolute
			simulate(teams, sim_count, day, hour)
		with open(simsfile, "rb") as f:
			sim_results = np.frombuffer(f.read(), np.uint8)
			sim_count = int(len(sim_results) / 64)
			for entryname in mypool.entries:
				entry = mypool.entries[entryname]
				entry.picks_array = np.tile(entry.picks_array, sim_count)
				entry.picks_array = np.power(2, np.minimum(entry.picks_array, sim_results)) - 1
				entry.picks_array = np.reshape(entry.picks_array, (-1, 64))
				entry.scores_array = entry.picks_array.sum(axis=1, dtype=np.uint8)
				entry.average_score = entry.scores_array.sum() / sim_count
	except FileNotFoundError:
		sim_time = time.process_time()
		simulate(teams, sim_count, day, hour)
		print("\nsim time:", end=' ')
		print(time.process_time() - sim_time, '\n')
		score(mypool, teams, sim_count, day, hour)


def print_output(mypool: Pool, groupID=0, be_quick=True, day=0, hour=0, print_average=False, print_champ=True, winner_only=False):
	mypool.determine_winscores()
	f = None
	params_id = print_average + 2 * print_champ
	if be_quick:
		try:
			f = open("results/" + str(groupID) + "/" + "d" + str(day) + 'h' + str(hour) + '_' + str(params_id) + ".txt", "w")
		except (NotADirectoryError, FileNotFoundError):
			try:
				os.mkdir("results")
			except FileExistsError:
				pass
			os.mkdir("results/" + str(groupID))
			f = open("results/" + str(groupID) + "/" + "d" + str(day) + 'h' + str(hour) + '_' + str(params_id) + ".txt", "w")
	sim_idx = 0
	for winscore in mypool.winning_scores:
		winner_list = []
		for entryname in mypool.entries:
			entry = mypool.entries[entryname]
			if entry.scores_array[sim_idx] == winscore:
				winner_list.append(entry)
		for winner in winner_list:
			winner.winnings += len(mypool.entries) / len(winner_list)
		sim_idx += 1
	for winner in winner_list:
		if winner_only and winner.winnings == len(mypool.entries) * len(mypool.winning_scores):
			print("\nwinner:", winner.name, end='')
			return
	print('\n')
	if be_quick:
		f.write('\n')
	if print_champ:
		print("CHAMP       ", end='')
		if be_quick:
			f.write("CHAMP       ")
	if print_average:
		print("AVG\t", end='\t')
		if be_quick:
			f.write("AVG\t\t")
	print("WINRATE\tENTRY", end='')
	if be_quick:
		f.write("WINRATE\tENTRY")
	order = {}
	entry_idx = 0
	for entryname in mypool.entries:
		entry = mypool.entries[entryname]
		order[entry.winnings + entry_idx / len(mypool.entries)] = entry  # +...len() prevents overwriting of tied entries
		entry_idx += 1
	for winnings in reversed(sorted(order)):
		entry = order[winnings]
		entry.winrate = entry.winnings / len(mypool.winning_scores)
		try:
			entry.picks["Indiana Wesleyan"]
			print("\nerror reading picks from " + entry.name, end='')
			if be_quick:
				f.write("\nerror reading picks from" + entry.name)
		except KeyError:
			if (not winner_only) or entry.winrate != 0:
				print('\n', end='')
				if be_quick:
					f.write('\n')
				if print_champ:
					print(entry.champ + ' ' * (12 - len(entry.champ)), end='')
					if be_quick:
						f.write(entry.champ + ' ' * (12 - len(entry.champ)))
				if print_average:
					print(f"{entry.average_score:.1f}\t", end='')
					if be_quick:
						f.write(f"{entry.average_score:.1f}\t")
				if entry.winrate != 0:
					print(f"{100 * entry.winrate / len(mypool.entries):.2f}" + "%\t" + entry.name, end='')
				else:
					print("0\t\t" + entry.name, end='')
				if be_quick:
					if entry.winrate != 0:
						f.write(f"{100 * entry.winrate / len(mypool.entries):.2f}" + "%\t" + entry.name)
					else:
						f.write("0\t\t" + entry.name)
			else:
				print("\neliminated: "+ entry.name, end='')
				if be_quick:
					f.write("\neliminated: " + entry.name)
	if be_quick:
		f.close()


def quick_output(groupID: int, day=0, hour=0, print_average=False, print_champ=True):
	params_id = print_average + 2 * print_champ
	try:
		with open("results/" + str(groupID) + "/" + "d" + str(day) + 'h' + str(hour) + '_' + str(params_id) + ".txt") as f:
			print(f.read())
		return True
	except FileNotFoundError:
		return False


def main(day, hour=0, groupID):
	# PARAMETERS
	sim_count = 100000
	be_quick = True  # attempt to store and look up results
	refresh_sim = False  # may have no effect if be_quick is True
	'''	refresh_sim makes simsdata/sim_d{day}h{hour}.data refresh. Otherwise the results
		will be the same each run even if be_quick is not set

		be_quick prints results/{groupID}/d{day}h{hour}_{param_id}.txt if the file is present;
		else writes the results to it. If it is not set the pool results are not saved.'''
	print_average = True
	print_champ = True

	if be_quick and quick_output(groupID, day, hour, print_average=print_average, print_champ=print_champ):
		return
	teams = initialize_teams(day, hour)

	mypool = Pool(str(groupID))
	score(mypool, teams, sim_count, day=day, hour=hour, refresh_sim=refresh_sim)  # .75 seconds for 100k sims
	print_output(mypool, groupID, be_quick, day, hour, print_average=print_average, print_champ=print_champ,
				 winner_only=True)  # .45 seconds for 100k sims


def kp_sim(day, hour=0):
	sim_count = 10000  # only if the sim is not found
	teams = initialize_teams(day, hour)
	f = None
	try:
		f = open("simsdata/sim_d" + str(day) + 'h' + str(hour) + ".data", "rb")
	except FileNotFoundError:
		simulate(teams, sim_count, day, hour)
		f = open("simsdata/sim_d" + str(day) + 'h' + str(hour) + ".data", "rb")
	sim_results = np.reshape(np.frombuffer(f.read(), np.uint8), (-1,64)).transpose()
	champ_count_order = {}
	team_idx = 0
	for teamname in teams:
		team = teams[teamname]
		for i in range(7):
			team.total_wincounts[i] += len(sim_results[team_idx][np.equal(sim_results[team_idx], i)])
		for j in range(5, 0, -1):
			team.total_wincounts[j] += team.total_wincounts[j + 1]
		team.champ_count = team.total_wincounts[6]
		champ_count_order[team.champ_count + team.total_wincounts[1]/(sim_count + 1) + team_idx/(sim_count * 100)] = team
		team_idx += 1
	f2 = None
	try:
		f2 = open("results/sim_results/d" + str(day) + 'h' + str(hour) + ".txt", 'w')
	except FileNotFoundError:
		os.mkdir("results/sim_results")
		f2 = open("results/sim_results/d" + str(day) + 'h' + str(hour) + ".txt", 'w')
	for teamwins in sorted(champ_count_order):
		team = champ_count_order[teamwins]
		print(team.name, ' ' * (16 - len(team.name)), team.total_wincounts[1:])
		f2.write(str(team.seed) + ' ' + team.name + ' ' * (17 - len(team.name)) + ' ' + str(team.total_wincounts[1:]) + '\n')
	f.close()
	f2.close()


if __name__ == "__main__":
	day = 2
	hour = 0
	# update_scoreboard()
	main(day, hour, 5313306) #ce
	main(day, hour, 5724994) #high rollers
	kp_sim(day, hour) #this function has no effect on simsdata/ it will output
						#a readable version of simsdata/ if present else will perform
	 					#a sim without writing to simsdata/ and always writes
						#its output to results/sim_results/d{day}h{hour}.txt
