import sys
import random

with open(sys.argv[1]) as file:
	data = file.readlines()
	count = 0
	plus = 0
	for line in data:
		
		if count % 12 == 0:
			if random.randint(0, 4) == 1:
				plus += 1
			#print(plus)
			list = line.split()
			print(str(int(float(list[len(list) - 1]) * 100)))
		count = count + 1
