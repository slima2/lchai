import urllib.request, json
url = "http://inference-service:8000/api/v1/images/2816fff9-b1b8-4d77-a474-7cf2b418fd76/results/latest"
data = json.loads(urllib.request.urlopen(url).read())
print("predominant:", data.get("predominant_pattern"))
for p in sorted(data.get("pattern_results", []), key=lambda x: -x.get("percentage", 0))[:6]:
    print(f"  {p['pattern']}: {p['percentage']:.1f}%")
