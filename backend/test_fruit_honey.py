import sys
sys.path.append('src')
import re
from nz_coffee_tracker.categorization import clean_process

print(clean_process("peach honey"))
print(clean_process("strawberry natural"))
