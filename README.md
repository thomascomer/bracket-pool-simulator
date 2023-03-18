# bracket-pool-simulator

SUMMARY: This project uses team ratings from KenPom.com to predict the winner of an NCAA Tournament bracket pool. It is a work in progress.

INSTRUCTIONS: The program is set to run a simulation of the tournament current to the morning of March 18, show the results, and show the results of the Cognitive Elite pool. The program can be controlled by altering files and function parameters. It will take a few minutes to run any group the first time, depending on how many entries are in it. A new simulation takes about 30 seconds per 100,000 samples on my machine. The program runs in a few seconds when loading a previous simulation.

-----------------------------------

FUNCTIONS

main() gives the odds each entry has to win the pool. To see the results of a different group, go to the group's home page and copy the groupID field from the URL. Set be_quick to attempt to load results, and store if failed. refresh_sim will redo the simulation and can be convenient when altering files. day and hour determine which results will be included in the simulation; day complete days of games will be included and hour is the latest tip off time for inclusion.

kp_sim() prints the results of the simulation in the form "Team [1 2 3 4 5 6]" where 1...6 is the number of times Team wins at least that many games in the tournament. This is useful to confirm the results of main().

update_scoreboard() should be called when games are completed to include the results in future simulations. Results are not available immediately and in my experience a whole day's results become available the following morning.

-----------------------------------

FILES

scoreboard.txt can be doctored to consider different possible outcomes. A team is guaranteed at least as many wins as times its name appears on a line to be included by main(). Whether a line is included is determined by day and hour.

the results/ folder contains the results of main() if be_quick was set under a groupID folder, and the results of kp_sim(), both according to time.
