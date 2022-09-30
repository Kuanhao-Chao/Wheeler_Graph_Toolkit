import requests, sys
import json

server = "https://rest.ensembl.org"
ext = "/homology/id/ENSG00000157764?sequence=cdna"

r = requests.get(server+ext, headers={ "Content-Type" : "application/json"})

if not r.ok:
  r.raise_for_status()
  sys.exit()

js_decoded = r.json()
# jtxt= str(repr(decoded))
# print(jtxt)

# jsonObject = json.loads(jtxt)
for key in js_decoded:
  print(key)
  # value = js_decoded[key]["homologies"]
  value = js_decoded[key][0]['homologies']
  for homo in value:
    print(len(homo['source']['align_seq']))
    print(len(homo['target']['align_seq']))
    # ['target'])
    print(">>> \n\n\n")

# the result is a Python dictionary:
