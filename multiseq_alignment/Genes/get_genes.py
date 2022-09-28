import requests, sys

server = "https://rest.ensembl.org"
ext = "/alignment/region/homo_sapiens/3:106040329-106040379"

r = requests.get(server+ext, headers={ "Content-Type" : "application/json"})

if not r.ok:
  r.raise_for_status()
  sys.exit()

decoded = r.json()
print(repr(decoded))
