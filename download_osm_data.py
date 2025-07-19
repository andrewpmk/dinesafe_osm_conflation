import overpy
import csv
import json

# Initialize Overpass API
api = overpy.Overpass()

# Query: All restaurants in the City of Toronto
query = """
[out:json][timeout:120];
area["wikidata"="Q172"]->.searchArea;
(
    node["amenity"~"^(restaurant|fast_food)$"](area.searchArea);
    way["amenity"~"^(restaurant|fast_food)$"](area.searchArea);
    relation["amenity"~"^(restaurant|fast_food)$"](area.searchArea);
    node["shop"~"^(convenience|supermarket)$"](area.searchArea);
    way["shop"~"^(convenience|supermarket)$"](area.searchArea);
    relation["shop"~"^(convenience|supermarket)$"](area.searchArea);
);
out center;
"""

# Run query
result = api.query(query)

# Gather results
pois = []

# Nodes
for node in result.nodes:
    pois.append({
        "name": node.tags.get("name", ""),
        "lat": node.lat,
        "lon": node.lon,
        "type": "node",
        "id": node.id,
        "tags": json.dumps(node.tags)
    })

# Ways
for way in result.ways:
    pois.append({
        "name": way.tags.get("name", ""),
        "lat": way.center_lat,
        "lon": way.center_lon,
        "type": "way",
        "id": way.id,
        "tags": json.dumps(way.tags)
    })

# Relations
for rel in result.relations:
    center = rel.get_center()
    pois.append({
        "name": rel.tags.get("name", ""),
        "lat": rel.center_lat,
        "lon": rel.center_lon,
        "type": "relation",
        "id": rel.id,
        "tags": json.dumps(rel.tags)
    })

print(pois)

# Export data to csv
with open('toronto_pois.csv', 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['name', 'lat', 'lon', 'type', 'id', 'tags']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()
    for poi in pois:
        writer.writerow(poi)