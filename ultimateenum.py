import sys
import requests
import time
import threading
import string
import json
import random
import dns.resolver
from bs4 import BeautifulSoup
import warnings

warnings.filterwarnings("ignore")

full_list = []
work_queue = []

tlock = threading.Lock()

debug = 0

def wayback(target):
 try:
  url = "https://web.archive.org/cdx/search/cdx?url=*.{}&output=json&collapse=urlkey".format(target)
  res = json.loads(requests.get(url=url, timeout=30, verify=False).text)
  domains_collected = []
  for resx in res[1:]:
   url = resx[2]
   if url.startswith("https://"):
    domain = url.split("https://")[1]
   elif url.startswith("http://"):
    domain = url.split("http://")[1]
   else: continue
   if "/" in domain: domain = domain.split("/")[0]
   if ":" in domain: domain = domain.split(":")[0]
   if not domain in domains_collected: domains_collected.append(domain)
  return domains_collected
 except:
  return []

def crtsh(target):
 try:
  url = "https://crt.sh/?q={}&output=json".format(target)
  res = json.loads(requests.get(url=url, timeout=30, verify=False).text)
  domains_collected = []
  for resx in res:
   if "name_value" in resx: domain = resx["name_value"]
   if "\n" in domain: domain = domain.split("\n")[0]
   if domain.startswith("*."): domain = domain.replace("*.", "")
   if not domain in domains_collected: domains_collected.append(domain)
  return domains_collected
 except:
  return []

def hackertarget(target):
 try:
  url = "https://api.hackertarget.com/hostsearch/?q={}".format(target)
  r=requests.get(url=url, timeout=30, verify=False)
  domains_collected = []
  for i in r.text.splitlines():
   domain = i.split(",")[0]
   if not domain in domains_collected: domains_collected.append(domain)
  return domains_collected
 except:
  return []

def urlscan(target):
 try:
  url = "https://urlscan.io/api/v1/search/?q=domain:{}".format(target)
  res = json.loads(requests.get(url=url, timeout=30, verify=False).text)
  domains_collected = []
  if not "results" in res: return []
  for resx in res["results"]:
   if resx["task"]["domain"] in domains_collected: continue
   domains_collected.append(resx["task"]["domain"])
  return domains_collected
 except:
  return []

def fdomain(current_domain):
 global full_list
 domains_collected = []
 funs = [urlscan, hackertarget, wayback, crtsh]
 random.shuffle(funs)
 for fun in funs:
  domains_collected.extend(fun(current_domain))
 domain_new = 0
 for domain in domains_collected:
  domain = domain.lower().strip()
  if not domain.endswith(main_domain): continue
  with tlock:
   if not domain in full_list:
    domain_new = 1
    print(domain)
    full_list.append(domain)
  if len(domain.split(".")) < 5 and domain_new == 1:
   try:
    while threading.active_count() >= threadcount: time.sleep(0.1)
    t=threading.Thread(target=fdomain, args=(domain,))
    t.start()
   except Exception as error:
    if debug == 1: print(error)

def try_resolve_domain(domain):
 try:
  resolver = dns.resolver.Resolver()
  resolver.timeout = 3
  resolver.lifetime = 3
  resolved = resolver.resolve(domain, "A")
  return True
 except Exception as error:
  return False

def brute():
 global full_list_copy, current_domain
 time.sleep(1)
 while len(full_list_copy):
  with tlock:
   current_domain = full_list_copy.pop(0)
  for word in full_wordlist:
   current_domain = "{}.{}".format(word, current_domain)
   with tlock:
    if current_domain in full_list: continue
   if try_resolve_domain(current_domain): 
    with tlock: full_list.append(current_domain)
    print(current_domain)

def crawl():
 global full_list_copy
 while len(full_list_copy):
  try:
   with tlock: current_domain = full_list_copy.pop(0)
   r = requests.get(url="https://{}".format(current_domain), timeout=30, verify=False)
   soup = BeautifulSoup(r.text, "html.parser")
   lfinds = [
    ["a","href"],
    ["iframe","src"],
    ["img","src"],
    ["embed","src"],
    ["link","href"],
    ["form","action"]
   ]
   for lfind in lfinds:
    for link in soup.find_all(lfind[0]):
     link = link.get(lfind[1])
     if not link: continue
     if link.startswith("https://"):
      domain = link.split("https://")[1]
      if "/" in domain: domain = domain.split("/")[0]
      if ":" in domain: domain = domain.split(":")[0]
      with tlock:
       if domain.endswith(main_domain) and not domain in full_list:
        full_list.append(domain)
        print(domain)
  except Exception as error:
   if debug == 1: print(error)

if len(sys.argv) < 3:
 print("<domain> <threads>")
 sys.exit(0)
work_queue.append(sys.argv[1])
full_list.append(sys.argv[1])
main_domain = sys.argv[1]
print(main_domain)
threadcount = int(sys.argv[2])
t=threading.Thread(target=fdomain, args=(main_domain,))
t.start()
t.join()
while threading.active_count() > 2:
 time.sleep(0.1)
full_wordlist = []
for i in full_list:
 words = i.split(".")
 full_wordlist.extend(words)
full_wordlist = list(set(full_wordlist))
full_wordlist_original = list(full_wordlist)
for word in full_wordlist_original:
 for word2 in full_wordlist_original:
  if word == word2: continue
  full_wordlist.append(f"{word}-{word2}")
  full_wordlist.append(f"{word}.{word2}")
full_wordlist = list(set(full_wordlist))
#if debug == 1: print(full_wordlist)
full_list_copy = list(set(full_list))
#if debug == 1: print(full_list_copy)
threads = []
for i in range(threadcount):
 t=threading.Thread(target=brute)
 t.start()
 threads.append(t)
for t in threads:
 t.join()
full_list_copy = list(full_list)
threads = []
for i in range(threadcount):
 t=threading.Thread(target=crawl)
 t.start()
 threads.append(t)
for t in threads:
 t.join()
