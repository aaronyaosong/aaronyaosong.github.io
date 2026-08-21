import sys
sys.path.append('src')
from nz_coffee_tracker.categorization import clean_process, infer_process_rule_based
print(clean_process("rose tea honey co-ferment"))
print(clean_process("sugar cane process and washed"))
print(clean_process("washed patio dried"))
